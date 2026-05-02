# Phase 4 — Persistent memory (deliberate, not emergent)

**Goal:** make a second run on the same disease class faster + smarter than the
first. Boring, deterministic memory — not Hermes-style "self-creating skills".

## What gets remembered

| Memory | Key | Value | Why |
|---|---|---|---|
| Target picks | (skill, disease_normalized) | list of (uniprot_id, score, picked_at) | Skip OpenTargets call if we already chose well |
| Structure quality | uniprot_id | (best_pdb_id, source, quality, fetched_at) | Avoid re-downloading |
| Pocket center | pdb_id | [x, y, z] | Avoid re-running pocket detection |
| Approved-drug hits | uniprot_id | list of {chembl_id, smiles, affinity} | Skip re-docking known approved hits |
| Failed lookups | (api, key) | error, ts | Don't hammer broken endpoints |

Deliberately **not** remembered: anything user-specific, free-form notes about
the user, conversation history. This is a research tool, not a chatbot.

## Storage

- SQLite table `harness_memory` (key TEXT, value JSON, updated_at TIMESTAMP).
  Same DB as jobs; new file optional but probably overkill.
- TTL per key class: structures = 90 days, target picks = 30 days, failed
  lookups = 1 hour.
- Read at agent loop start: prepend a system reminder with relevant memories
  ("we previously chose PPARG for type 2 diabetes — high confidence").
- Write on each successful tool result via a small write-through helper.

## API

- `GET /api/memory` — debug endpoint: dump current memory keyed by skill
- `DELETE /api/memory?prefix=...` — admin reset
- CLI: `hermes-bio memory show` / `hermes-bio memory clear`

## Steps

- [x] Add `harness_memory` table (in `app/db.py`, not `core/`, per ADR-0004)
- [x] `app/memory.py` with `get`, `put`, `recall`, `clear`; key normalizers
      (`disease_key`, `uniprot_key`, `pdb_key`); TTL constants
- [x] In `pipeline.py`, `_persist_memory_for(job_id, disease)` writes
      target+structure+approved-hits at end of successful run
- [x] In `orchestrator.run_agent`, accept `memory_note` and inject as
      `<harness-memory>` block in system prompt
- [x] In `pipeline.py`, `_build_memory_note(disease)` reads cached entry,
      formats prose note, publishes `memory_recall` event for UI
- [x] API endpoints: `GET /api/memory`, `DELETE /api/memory`
- [x] CLI subcommands: `memory show [-v]`, `memory clear [--prefix ...]`
- [x] Frontend ReasoningStream renders `memory_recall` (purple 🧠 card)
- [x] **Verified**: ran "type 2 diabetes mellitus" twice. First run ~90s,
      populated memory. Second run ~27s, fired memory recall, agent
      jumped straight to cached UniProt P37231 + PDB 1FM6, skipped redundant
      exploration. Same target, same structure, same approved-drug class
      (Rosiglitazone). 🧠 line visible in CLI stdout and frontend stream.

## What we are explicitly not building

- A "memory tool" the agent can call. The agent doesn't decide what to
  remember; the harness does.
- Vector store / semantic search. Exact-key lookup is enough; complexity later
  only if a real need surfaces.
- Cross-skill memory. Each skill's memory is scoped to itself.
