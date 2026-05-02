# 2026-05-02 — Memory + CLI shipped

Phase 4 (memory) and Phase 3 (CLI) landed in this order, per ADR-0004.

## Verified

| Test | Result |
|---|---|
| `hermes-bio skills list` | OK |
| `hermes-bio memory show` (empty scope) | clean message, exit 0 |
| `hermes-bio run drug-discovery --disease "type 2 diabetes mellitus"` (1st) | full run, ~90s, exit 0, memory populated |
| `hermes-bio memory show -v` after run | `disease:type-2-diabetes-mellitus` + `uniprot:P37231` keys visible |
| `hermes-bio run drug-discovery --disease "type 2 diabetes mellitus"` (2nd) | 🧠 recall fired immediately, ~27s (3× faster), exit 0 |

The 2nd run's behavior is exactly what we wanted from deliberate memory:
agent skipped exploring alternatives, went straight to cached PPARG / 1FM6,
still produced Rosiglitazone in the final candidates.

## Bug fixed in this session

- CLI returned exit 1 even on successful pretty-mode runs because the
  success check was tied to `final_holder` (only populated in JSON mode).
  Now derives success from `Job.status == "completed"`.
- CP1252 encoding crash on Windows when emoji/arrows hit the console; fixed
  by `sys.stdout.reconfigure(encoding="utf-8")` early in `main()`.

## What's next (no decision yet)

Open candidates from `docs/plans/`:
- Phase 1 refactor (still deferred — no second skill yet to justify it)
- Phase 2 providers (still deferred — Gemini works fine)
- New work the user might want: real fpocket integration, pose viewer,
  multi-target runs (Q6 in `open-questions.md`), eval suite (Q7).

State of the world is solid. Good stopping point.
