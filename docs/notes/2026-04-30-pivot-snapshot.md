# Snapshot — 2026-04-30, just before the harness pivot

This is the state of the project at the moment we decided to pivot from "drug
discovery app" to "drug discovery harness". Captured so a future session can
recover context without spelunking git history.

## What works end-to-end (verified)

- `POST /api/discover` with a disease name → background job
- Gemini agent loop (model: `gemini-3.1-flash-lite-preview`) calls bio tools
  in sequence; survives transient 503s with exponential backoff
- Tool list: search_uniprot, search_opentargets, fetch_structure (PDB
  fallback to AlphaFold), detect_binding_pockets (centroid stub),
  fetch_approved_drugs_for_target (repurposing-first), fetch_chembl_library,
  run_docking (heuristic stub), screen_lipinski (RDKit), score_synthesizability
  (SAScore via RDKit Contrib + heuristic fallback), predict_admet_batch,
  predict_admet_batch
- Agent emits structured JSON in final response; pipeline parses and
  populates DB rows (Target → Structure → DockingResult)
- HTML report rendered (dark research theme, repurposing section, SA pills)
- React frontend (Vite + TS + Tailwind + NGL) with three panes:
  reasoning stream (SSE) · NGL viewer + pocket sphere · candidates table
- Mechanism-of-action explanation endpoint (lazy, cached per candidate)
- Cytoscape graph view (Disease → Target → Structure → Drug)

## Verified disease runs

| Disease input | Target picked (correct) | Top approved drug (real) |
|---|---|---|
| type 2 diabetes mellitus | PPARG (P37231) | Rosiglitazone |
| non-small cell lung cancer | EGFR (P00533) | Sunitinib |
| Alzheimer disease | PSEN1 (P49768) | (none, ChEMBL has no max_phase=4 PSEN1 binders) |

## What's stubbed (be honest about this)

- Docking: heuristic affinity from LogP/MW. Real Vina needs `pip install vina`
  + AutoDock binary on PATH.
- Pockets: centroid of all CA atoms. Real fpocket/P2Rank not wired.
- ADMET: LogP/TPSA proxies. Real ADMETlab2/pkCSM not integrated.

## File layout (pre-pivot)

```
backend/
  app/
    main.py               FastAPI entry
    config.py
    db.py                 SQLAlchemy async, SQLite
    api/routes.py         /discover, /jobs/{id}, /events, /candidates,
                          /structure, /report, /candidates/{rank}/explain,
                          /graph
    agent/
      orchestrator.py     Gemini function-calling loop, retry on 503
      tools.py            tool dispatch + Gemini function declarations
      prompts.py          drug-discovery system prompt (repurposing-first)
    services/             uniprot, opentargets, structures, pockets,
                          molecules, docking, admet, repurposing, synthesis,
                          explain, reports
    workers/
      pipeline.py         background runner; parses agent JSON → DB rows
      events.py           in-memory pub/sub for SSE
    templates/
      report.html.j2      dark theme report
frontend/
  src/
    App.tsx, main.tsx, types.ts, index.css
    pages/Home.tsx, Workspace.tsx
    components/ReasoningStream.tsx, StructureViewer.tsx,
               CandidatesTable.tsx, GraphView.tsx
    lib/api.ts            fetch helpers + SSE consumer
```

## Why we're pivoting now

User signal during the second session: we keep adding features (mechanism
explainer, knowledge graph, etc.) and they all fit, but the natural shape
isn't "an app with more features" — it's "a harness with skills". The codebase
is right at the inflection point where another vertical feature add makes the
generalization harder, not easier. Better to pay the refactor tax now while
the surface area is small.

## Key code paths to preserve through the refactor

- The agent loop in `app/agent/orchestrator.py` (Gemini-specific calls + retry
  + event publishing) — this becomes provider-agnostic in Phase 2
- `app/workers/pipeline.py` _clean_summary + _extract_json_block + the
  selectinload-based eager-loading dance (we hit the async lazy-load bug once
  already)
- The tool dispatch in `app/agent/tools.py` — splits cleanly into "harness
  patterns" (the dispatcher itself) vs "skill content" (the bio function
  declarations)

## Latest job IDs in dev DB (handy for testing post-refactor)

- `b070fdf66b0b` — NSCLC / EGFR / Sunitinib (most recent, with SA + repurposing)
- `6014114796c3` — type 2 diabetes / PPARG / Rosiglitazone
- `8b2a1c08800b` — Alzheimer's / PSEN1 (older, pre-structured-output)
