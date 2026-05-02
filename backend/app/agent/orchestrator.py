"""Gemini-powered agent orchestration loop."""
import asyncio
import json
import logging
from typing import Callable, Awaitable
from google import genai
from google.genai import types
from google.genai import errors as genai_errors

from ..config import settings
from .tools import TOOL_DECLARATIONS, DISPATCH
from .prompts import SYSTEM_PROMPT

log = logging.getLogger(__name__)

MAX_ITERATIONS = 25


def _build_tools() -> list[types.Tool]:
    return [types.Tool(function_declarations=TOOL_DECLARATIONS)]


async def run_agent(
    disease: str,
    on_event: Callable[[dict], Awaitable[None]] | None = None,
    memory_note: str | None = None,
) -> dict:
    """Run the agent loop. on_event is called with reasoning/tool events.

    memory_note: optional prose injected as a system-reminder before the user
    turn. Use it to surface facts the harness already knows (cached structures,
    prior target picks for this disease class, etc.).
    """
    client = genai.Client(api_key=settings.gemini_api_key)
    tools = _build_tools()

    system_instruction = SYSTEM_PROMPT
    if memory_note:
        system_instruction = f"{SYSTEM_PROMPT}\n\n<harness-memory>\n{memory_note}\n</harness-memory>"

    config = types.GenerateContentConfig(
        system_instruction=system_instruction,
        tools=tools,
        temperature=0.4,
    )

    contents: list[types.Content] = [
        types.Content(
            role="user",
            parts=[types.Part.from_text(text=f"Discover drug candidates for: {disease}")],
        )
    ]

    final_text = ""
    tool_calls_made: list[dict] = []

    for iteration in range(MAX_ITERATIONS):
        # Retry transient 503/429 with exponential backoff
        response = None
        last_err: Exception | None = None
        for attempt in range(6):
            try:
                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=contents,
                    config=config,
                )
                break
            except genai_errors.APIError as e:
                last_err = e
                code = getattr(e, "code", None)
                if code in (429, 503) and attempt < 5:
                    delay = min(2 ** attempt, 20)
                    log.warning("gemini %s, retrying in %ss (attempt %d)", code, delay, attempt + 1)
                    if on_event:
                        await on_event({"type": "retry", "code": code, "delay": delay})
                    await asyncio.sleep(delay)
                    continue
                raise
        if response is None:
            raise last_err or RuntimeError("gemini call failed")

        candidate = response.candidates[0]
        parts = candidate.content.parts or []
        contents.append(candidate.content)

        function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]
        text_parts = [p.text for p in parts if getattr(p, "text", None)]

        if text_parts and on_event:
            await on_event({"type": "reasoning", "iteration": iteration, "text": "\n".join(text_parts)})

        if not function_calls:
            final_text = "\n".join(text_parts)
            break

        # Execute all function calls in this turn
        function_responses = []
        for fc in function_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            log.info("tool call: %s(%s)", name, args)
            if on_event:
                await on_event({"type": "tool_call", "name": name, "args": args})

            handler = DISPATCH.get(name)
            if handler is None:
                result = {"error": f"unknown tool: {name}"}
            else:
                try:
                    result = await handler(**args)
                except Exception as e:
                    log.exception("tool error")
                    result = {"error": str(e)}

            tool_calls_made.append({"name": name, "args": args, "result_summary": _summarize(result)})
            if on_event:
                await on_event({"type": "tool_result", "name": name, "summary": _summarize(result)})

            function_responses.append(
                types.Part.from_function_response(name=name, response=result)
            )

        contents.append(types.Content(role="user", parts=function_responses))
    else:
        log.warning("agent hit max iterations")

    return {
        "final_text": final_text,
        "tool_calls": tool_calls_made,
    }


def _summarize(result: dict) -> str:
    """Compact one-line summary for logs."""
    try:
        s = json.dumps(result, default=str)
        return s if len(s) < 240 else s[:240] + "…"
    except Exception:
        return str(result)[:240]
