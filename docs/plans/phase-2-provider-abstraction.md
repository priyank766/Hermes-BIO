# Phase 2 — Provider abstraction (Gemini + Anthropic)

**Goal:** add Anthropic as a second provider behind a small Protocol, so the
agent loop is not Gemini-coupled. Verify the same disease produces a sensible
result on both.

## Steps

- [ ] Define `core/providers/base.py`:
  ```python
  class ProviderResponse:
      content_text: str
      tool_calls: list[ToolCall]   # name, args, id
      finished: bool

  class Provider(Protocol):
      name: str
      def complete(self, *, system: str, messages: list[Message],
                   tools: list[ToolSchema]) -> ProviderResponse: ...
  ```
- [ ] Refactor `core/providers/gemini.py` to implement `Provider`
- [ ] Implement `core/providers/anthropic.py` using `anthropic` SDK with
      `tool_use` blocks
- [ ] Update `core/agent/orchestrator.py` to accept any `Provider`, not call
      `genai.Client` directly
- [ ] Resolve provider at job-creation time:
  - CLI flag (Phase 3)
  - `PROVIDER` env var
  - Default: gemini (existing behavior)
- [ ] API: accept optional `provider` field in `POST /api/discover`
- [ ] Verify a discovery run on Anthropic produces a comparable target choice

## Non-goals

- OpenAI (add later if asked)
- Streaming events from provider (still collect-then-publish for now)
- Prompt caching (defer; only Anthropic supports it richly)

## Verification

Same disease, two providers, equivalent target chosen (same UniProt or same
disease's canonical target):

```bash
PROVIDER=gemini  curl -X POST .../discover -d '{"disease":"NSCLC"}'  # → EGFR
PROVIDER=anthropic curl -X POST .../discover -d '{"disease":"NSCLC"}'  # → EGFR
```
