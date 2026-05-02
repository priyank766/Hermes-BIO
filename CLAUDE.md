# CLAUDE.md — Project front door

This file is the brief you read first. Keep it short. The detailed history,
decisions, and plans live in [`docs/`](./docs/).

## What this project is (now)

**An agentic harness for bioinformatics, with drug-discovery as the flagship
skill.**

We pivoted on 2026-04-30 from "a drug-discovery app" to "a harness whose first
skill is drug-discovery". See [`docs/decisions/0001-pivot-to-harness.md`](./docs/decisions/0001-pivot-to-harness.md)
for the why.

A user feeds a disease name; the harness loads the `drug_discovery` skill;
an LLM (Gemini today; Anthropic + others later) drives a tool-use loop over
UniProt, OpenTargets, PDB/AlphaFold, ChEMBL, RDKit, and stub docking/ADMET to
produce a ranked candidate list. Repurposing-first (FDA-approved drugs before
novel ChEMBL); SAScore on every top hit; live SSE reasoning stream.

## Read these first when starting a session

1. **[`docs/notes/`](./docs/notes/)** (latest by date) — current state of the
   project, what works, what's stubbed.
2. **[`docs/decisions/`](./docs/decisions/)** — accepted ADRs. These are the
   constraints. Newest first:
   - `0003-provider-strategy.md` — Gemini-first, narrow Protocol, LiteLLM later
   - `0002-build-minimal-not-fork-hermes.md` — don't fork Nous Hermes
   - `0001-pivot-to-harness.md` — why we're a harness, not an app
3. **[`docs/plans/`](./docs/plans/)** — current phase. As of writing: phase 0
   complete, phase 1 (refactor into `core/` + `skills/`) is up next.
4. **[`docs/open-questions.md`](./docs/open-questions.md)** — known unresolved
   design choices.
5. **[`docs/glossary.md`](./docs/glossary.md)** — terms.

## When you finish work that mattered

- Add or update a note in `docs/notes/` if state changed.
- Write a new ADR in `docs/decisions/` if you made a tradeoff.
- Tick checkboxes in the current `docs/plans/phase-*.md`.
- Don't edit old ADRs. Supersede with new ones.

## Code layout (current — pre-Phase-1)

```
backend/    FastAPI + Gemini agent + SQLite + bio services
frontend/   Vite + React + Tailwind + NGL viewer (3-pane research UI)
docs/       project journal (read CLAUDE.md → docs/ before coding)
```

Code layout will change in Phase 1 (refactor into `core/`, `skills/`, `web/`,
`cli/`). See `docs/plans/phase-1-refactor-into-core-skills.md`.

## Run it

Backend (`backend/`): `uv sync && uv run uvicorn app.main:app --port 8000`
(needs `GEMINI_API_KEY` in `backend/.env`).
Frontend (`frontend/`): `npm install && npm run dev` → http://localhost:5173

## Verified disease runs (proof the agent picks real targets)

| Disease | Target picked | Top approved drug found |
|---|---|---|
| Type 2 diabetes | PPARG (P37231) | Rosiglitazone |
| NSCLC | EGFR (P00533) | Sunitinib |
| Alzheimer disease | PSEN1 (P49768) | (no max_phase=4 binders) |

These are real disease/target/drug relationships recovered from public APIs,
not hardcoded.

## Honest stubs (replace for production)

- Docking — heuristic affinity from LogP/MW. Real Vina needs `pip install vina`.
- Pockets — centroid only. Wire fpocket or P2Rank.
- ADMET — LogP/TPSA proxies. Real ADMETlab2 / pkCSM not integrated.

UniProt, OpenTargets, PDB, AlphaFold, ChEMBL, Lipinski, SAScore are real.

## Non-goals (explicit)

- Terminal UI / Claude-Code-style frontend
- Self-modifying skills (Hermes-style emergent skill creation)
- Telegram / Discord / Slack / WhatsApp connectors
- Hosting other people's API keys (BYOK only)

## Hand-off note

If you're a future Claude session: do not pretend to remember things from
prior sessions. Read `docs/notes/` and `docs/decisions/` first. The
codebase is the source of truth for what runs; `docs/` is the source of
truth for *why* it runs that way.
