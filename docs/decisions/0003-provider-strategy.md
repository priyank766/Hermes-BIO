# ADR 0003 — Provider strategy: Gemini-first, narrow Protocol, LiteLLM later

- **Status:** accepted
- **Date:** 2026-04-30

## Context

The user wants BYOK across "all providers" eventually (Anthropic, OpenAI,
Gemini, Ollama, etc.), in the spirit of Claude Code / Codex / Gemini CLI.
Provider abstraction has real cost: tool-call shapes, thinking/reasoning
fields, prompt caching, streaming all diverge between SDKs.

## Decision

Three layers, stacked from concrete to abstract:

1. **Now (already done):** direct `google.genai` SDK calls in
   `core/agent/orchestrator.py`.
2. **Phase 2:** introduce `core/providers/base.py` — a small Python `Protocol`
   exposing exactly what the agent loop needs: `complete(messages, tools,
   system) -> response_with_tool_calls_or_text`. Adapters for `gemini.py` and
   `anthropic.py`. Hand-rolled. No external abstraction yet.
3. **Phase 5+ (only if needed):** if we add a third provider and the adapter
   work becomes painful, swap the adapter layer for `litellm` and keep our
   Protocol on top.

## Why this order

- Direct SDK calls give us full access to provider-specific features (thinking,
  caching, structured outputs) that abstractions hide or lose.
- Two adapters is enough to surface the abstraction's shape. One isn't.
- LiteLLM is excellent but takes a position on tool-call shape that may not
  match what we want. Postpone the dependency until we know it pays for itself.

## API key resolution order

For each provider:
1. CLI flag (`--anthropic-key sk-...`)
2. Environment variable (`ANTHROPIC_API_KEY`)
3. Config file (`~/.hermes-bio/config.toml`, plain TOML, never committed)
4. Per-job override (web UI form field — not stored)

Never log keys. Never write keys to the project repo. Per-job CLI keys may
appear in shell history; that's the user's responsibility.

## Out of scope for this ADR

- Streaming abstraction (deferred — for now, providers stream natively in their
  SDK, and we collect-then-publish to our event bus).
- Prompt-cache normalization (deferred — Anthropic's cache_control is rich;
  Gemini's model is different; we keep them separate until a real use case
  forces unification).
