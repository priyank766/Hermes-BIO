# ADR 0004 — Defer Phase 1 refactor and provider abstraction; ship memory + CLI first

- **Status:** accepted
- **Date:** 2026-04-30
- **Supersedes:** ordering only (not content) of plans/phase-*.md

## Context

Phase 1 (refactor into `core/` + `skills/`) was the originally-planned next
step. User signal: skip providers entirely for now and prioritize features
users feel (memory + CLI) over architectural cleanup.

## Decision

New order:
1. **Phase 4 (memory)** — done in current `backend/app/` layout. No refactor.
2. **Phase 3 (CLI)** — done in current layout. No refactor.
3. **Phase 1 (refactor into core/skills/)** — deferred until we add a *second*
   skill or a second provider. The abstraction has no cost-justification yet.
4. **Phase 2 (provider abstraction)** — deferred indefinitely. Gemini works.
   Revisit if a user actually asks for Anthropic/OpenAI.

## Why

- Refactoring for one skill is YAGNI. The right time to factor out `core/` is
  when we have a second skill that would share it. Premature abstraction
  locks in the wrong shape.
- Memory and CLI are observable to the user; refactor is invisible.
- The current code is small enough (~15 files, ~2k LOC) that refactoring later
  is cheap. Doing it now buys nothing.

## Consequences

- `core/` and `skills/` directories don't exist yet. Anything that would have
  gone there goes in `backend/app/` for now.
- Phase plans 1 and 2 stay in `docs/plans/` but are not the active work.
  When/if revived, their checklists are still accurate.
- Memory module lives at `backend/app/memory.py`. Will move to `core/memory.py`
  when Phase 1 happens.

## Reversibility

This decision is fully reversible. If a second skill or a second provider
becomes important, run Phase 1 then. The bio code is already organized in a
way that makes extraction mechanical (services/ are pure, prompts are isolated,
tool dispatch is a single dict).
