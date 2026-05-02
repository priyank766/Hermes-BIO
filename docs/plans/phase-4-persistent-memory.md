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

- [ ] Add `harness_memory` table
- [ ] `core/memory.py` with `get(scope, key)`, `put(scope, key, value, ttl)`,
      `recall(scope) -> dict` for batch
- [ ] In `skills/drug_discovery/`, decorate selected service calls to write
      results to memory
- [ ] In orchestrator, before the first model call, fetch memory for
      `(skill, disease_normalized)` and inject as a system note
- [ ] CLI subcommands above
- [ ] Verify: run "type 2 diabetes" twice. Second run uses cached UniProt /
      OpenTargets / structure / approved-drug data; agent log shows "using
      cached target P37231 from 2 minutes ago".

## What we are explicitly not building

- A "memory tool" the agent can call. The agent doesn't decide what to
  remember; the harness does.
- Vector store / semantic search. Exact-key lookup is enough; complexity later
  only if a real need surfaces.
- Cross-skill memory. Each skill's memory is scoped to itself.
