# Phase 1 — Refactor into `core/` and `skills/`

**Goal:** lift the existing code into a layout that makes "harness vs skill"
explicit. **No behavior changes.** Frontend, API endpoints, agent output all
identical at the end.

## Target layout

```
backend/
  core/                              the harness — domain-agnostic
    __init__.py
    agent/
      orchestrator.py                provider-agnostic loop (only Gemini wired today)
      prompts.py                     base meta-prompt; per-skill prompts come from skills
      events.py                      pub/sub bus (moved from workers/events.py)
    providers/
      base.py                        Protocol (filled in Phase 2; stub now)
      gemini.py                      wraps current google.genai calls
    tools.py                         @tool decorator + registry + dispatch
    skills.py                        SKILL.md loader + Skill dataclass
    memory.py                        stub for Phase 4
    db.py                            unchanged
    config.py                        unchanged
  skills/
    drug_discovery/
      SKILL.md                       human-readable description, when to load
      __init__.py
      tools.py                       move from app/agent/tools.py
      prompts.py                     move from app/agent/prompts.py
      services/                      move from app/services/
        uniprot.py
        opentargets.py
        structures.py
        pockets.py
        molecules.py
        docking.py
        admet.py
        repurposing.py
        synthesis.py
        explain.py
        reports.py
      templates/
        report.html.j2
  web/                               the FastAPI surface (renamed from app/)
    main.py
    api/routes.py
    workers/pipeline.py
```

## Steps

- [ ] Create `backend/core/` and `backend/skills/drug_discovery/` directories
- [ ] Move `app/agent/orchestrator.py` → `core/agent/orchestrator.py`
- [ ] Move `app/agent/prompts.py` → `skills/drug_discovery/prompts.py` (skill-specific)
- [ ] Move `app/agent/tools.py` → `skills/drug_discovery/tools.py` (skill-specific)
- [ ] Move `app/services/*` → `skills/drug_discovery/services/*`
- [ ] Move `app/templates/` → `skills/drug_discovery/templates/`
- [ ] Move `app/workers/events.py` → `core/agent/events.py`
- [ ] Rename `app/` → `web/`. Keep `web/main.py`, `web/api/`, `web/workers/`.
- [ ] Add `core/skills.py` with a `Skill` dataclass (system_prompt, tools, name)
- [ ] Modify `core/agent/orchestrator.py` to take a `Skill` object instead of
      hardcoded imports
- [ ] Modify `web/workers/pipeline.py` to load the `drug_discovery` skill and
      pass to the orchestrator
- [ ] Update all imports
- [ ] Verify backend boots (`uv run uvicorn web.main:app`)
- [ ] Verify a discovery run completes end-to-end with same output as before
- [ ] Update `pyproject.toml` package paths if needed
- [ ] Add `SKILL.md` for drug_discovery describing what it does + when an
      orchestrator should load it

## Non-goals for this phase

- Multiple providers (Phase 2)
- CLI (Phase 3)
- Memory (Phase 4)
- Multiple skills (later)

## Verification

```bash
cd backend && uv run uvicorn web.main:app --port 8000
# in another shell:
curl -X POST http://127.0.0.1:8000/api/discover \
  -H "Content-Type: application/json" \
  -d '{"disease":"type 2 diabetes mellitus"}'
# poll /api/jobs/{id} until completed
# expect: PPARG target, Rosiglitazone in candidates, status=completed
```

If the run succeeds and produces the same shape of output as before the
refactor, phase 1 is done.
