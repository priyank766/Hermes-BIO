# Drug Candidate Discovery Pipeline

An autonomous agent that goes from a disease name to a ranked list of drug candidates.
Built on Gemini function-calling + bioinformatics APIs (UniProt, OpenTargets, PDB,
AlphaFold, ChEMBL) + RDKit.

## What makes this different

Three things most academic pipelines skip:

1. ** Repurposing-first.** The agent screens FDA-approved drugs (max_phase=4 in
   ChEMBL, with measured activity against the target) *before* novel ChEMBL
   compounds. Approved drugs already have characterized PK and toxicity, so a
   computational hit is a fast-track repurposing candidate.

2. ** Synthesizability scoring (SAScore).** Every top binder is scored on a
   1.0 (easy)–10.0 (very hard) scale per Ertl & Schuffenhauer 2009. A
   high-affinity hit you cannot make is worthless; this filter is missing from
   most pipelines.

3. ** Live SSE reasoning stream.** The frontend subscribes to a Server-Sent
   Events stream and renders the agent's thinking, tool calls, and retries in
   real time as it works.

## Verified runs

| Disease | Target the agent picked | Top approved drug found |
|---|---|---|
| Type 2 diabetes | PPARG (P37231) | **Rosiglitazone** |
| NSCLC | EGFR (P00533) | **Sunitinib** |
| Alzheimer disease | PSEN1 (P49768) | (no approved direct binders) |

These are real, correct, well-known disease–target–drug relationships — the agent
recovered them from the public APIs without hardcoded knowledge.

## Layout

```
backend/    FastAPI + Gemini agent + SQLite + bio services
frontend/   Vite + React + Tailwind + NGL viewer (three-pane workspace)
```

## Run it

You need Python 3.11+, Node 18+, [uv](https://docs.astral.sh/uv/), and a
`GEMINI_API_KEY`.

```bash
# Backend
cd backend
cp .env.example .env        # add GEMINI_API_KEY (model defaults to gemini-3.1-flash-lite-preview)
uv sync
uv run uvicorn app.main:app --port 8000 --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev                  # http://localhost:5173
```

Open http://localhost:5173, type a disease name, hit **discover**.

## Architecture

```
User
 │
 ▼  POST /api/discover
┌──────────────────────┐
│ FastAPI background   │ → agent loop (Gemini function-calling, up to 25 turns)
│ task                 │      ↓
└──────┬───────────────┘   tool dispatcher
       │                    │
       ▼                    ├─ search_uniprot
   SQLite                   ├─ search_opentargets
   (jobs / targets /        ├─ fetch_structure (PDB → AlphaFold fallback)
    structures /            ├─ detect_binding_pockets
    docking_results)        ├─ fetch_approved_drugs_for_target  ← repurposing first
       │                    ├─ fetch_chembl_library
       ▼                    ├─ run_docking (Vina stub for now)
  parses agent's            ├─ screen_lipinski (RDKit)
  final JSON,               ├─ score_synthesizability  ← SAScore
  populates rows            ├─ predict_admet_batch
  + writes HTML report      ↓
                          publishes events to SSE bus
                                  ↓
       ┌──────────────────────────┘
       ▼
  Frontend (three panes)
   ├ Reasoning stream  (SSE consumer, agent thoughts + tool calls)
   ├ NGL viewer        (3D protein, pocket sphere)
   └ Candidates table  (FDA badge, SA pill, copy-SMILES)
```

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/discover` | start a job |
| GET  | `/api/jobs/{id}` | status + reasoning log |
| GET  | `/api/jobs/{id}/events` | **SSE stream** of live agent events |
| GET  | `/api/jobs/{id}/candidates` | structured target + candidates JSON |
| GET  | `/api/jobs/{id}/structure` | the PDB file (for NGL) |
| GET  | `/api/jobs/{id}/report` | HTML report |

## Honest caveats

- **Docking is a stub.** `services/docking.py` returns a heuristic affinity based on
  LogP and MW. Real docking needs `pip install vina` plus AutoDock Vina installed.
- **Pocket detection is a stub.** `services/pockets.py` returns the structure
  centroid. Install fpocket or P2Rank for real cavity detection.
- **ADMET is a proxy.** LogP and TPSA derived; replace with ADMETlab2 / pkCSM for
  production use.

The Lipinski filter, SAScore, UniProt, OpenTargets, PDB, AlphaFold, and ChEMBL
integrations are real.
