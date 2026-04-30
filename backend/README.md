# Drug Discovery Pipeline — Backend

Agentic drug-candidate discovery pipeline. Gemini orchestrates UniProt, OpenTargets, PDB/AlphaFold, ChEMBL, RDKit, docking and ADMET tools to produce a ranked candidate list and a report.

## Setup (uv)

```bash
cd backend
cp .env.example .env        # set GEMINI_API_KEY
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

## API

- `POST /api/discover` — body `{"disease": "Alzheimer's"}` → `{"job_id": ...}`
- `GET  /api/jobs/{job_id}` — status, reasoning log
- `GET  /api/jobs/{job_id}/report` — HTML report (when status = completed)

## Layout

```
app/
  main.py              FastAPI entry
  config.py            settings
  db.py                SQLAlchemy async (SQLite)
  api/routes.py        REST endpoints
  agent/
    orchestrator.py    Gemini function-calling loop
    tools.py           tool dispatcher + Gemini function declarations
    prompts.py         system prompt
  services/
    uniprot.py         UniProt search
    opentargets.py     OpenTargets GraphQL
    structures.py      PDB + AlphaFold fetchers
    pockets.py         binding pocket detection (stub — wire fpocket)
    molecules.py       ChEMBL + RDKit Lipinski
    docking.py         AutoDock Vina (stub — wire `vina` package)
    admet.py           ADMET predictor (stub)
    reports.py         Jinja2 HTML report
  templates/report.html.j2
  workers/pipeline.py  background job runner
```

## Stubs (replace for production)

- `services/docking.py` — heuristic affinity. Install AutoDock Vina + `pip install vina`.
- `services/pockets.py` — single centroid pocket. Install `fpocket` CLI or P2Rank.
- `services/admet.py` — LogP/TPSA proxies. Wire ADMETlab2 / pkCSM API.
