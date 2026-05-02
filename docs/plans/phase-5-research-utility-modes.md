# Phase 5 — Research utility modes (B, C, D)

**Goal:** turn this from a working agentic harness into something that can
genuinely help a researcher save time, not just rediscover textbook drugs.

See ADR 0005 for the framing. This plan is the implementation checklist.

## Mode B — `explore` (underexplored druggable targets)

- [x] `services/underexplored.py` — pulls top OpenTargets associations,
      enriches each with ChEMBL drug-development stats (max_phase, compound
      count) and an AlphaFold-availability probe
- [x] Underexplored score = genetic_assoc × drug_gap × not_crowded × actionable
- [x] CLI: `hermes-bio explore --disease "..." [--top N] [--json out.json]`
- [x] Smoke verified on idiopathic pulmonary fibrosis: surfaces RTEL1, SFTPA2,
      MUC5B as top picks — these are real IPF risk genes (telomere
      maintenance, surfactant biology, MUC5B promoter variant). Drug-
      development activity on them is sparse → "underexplored druggable" is
      the right label.
- [ ] Validate against a 2024–2026 review of underexplored IPF/PD targets
      (manual review, capture in `docs/notes/`)

## Mode C — `repurpose` (cross-indication hunt)

- [x] `services/cross_repurposing.py` v1 (used `indication_class`, returned
      mostly nulls — abandoned)
- [x] v2: switched to ChEMBL `drug_indication.json` endpoint for structured
      indication data; concurrent enrichment of pref_name + indications for
      top-N binders by potency
- [x] CLI: `hermes-bio repurpose --target <UniProt> [--exclude k1,k2,...] [--top N]`
- [ ] Smoke test on EGFR (P00533) with cancer keywords excluded — looking for
      non-oncology approved binders. RUNNING.
- [ ] Smoke test on PPARG (P37231) — should surface anti-diabetic
      thiazolidinediones AND any non-diabetic indications (e.g. some PPARG
      modulators have been studied off-label)
- [ ] Add `--from-disease "..."` shortcut: agent picks a target for the
      disease, then runs cross-indication on it (one-step "give me
      repurposing leads for X")

## Mode D — Hard-mode eval

- [x] `eval.HARD_MODE_DISEASES` list (4 diseases: IPF, long COVID, FA, ALS)
- [x] CLI: `hermes-bio eval --hard` runs them, no allowlist (agent's pick is
      recorded for manual review)
- [ ] Run hard-mode eval, capture picks
- [ ] Manual literature review against 2024–2026 sources for each pick
- [ ] Score documented in `docs/notes/<date>-hard-mode-results.md`

## `--model` override

- [x] All discovery/eval CLI commands accept `--model <id>` to override the
      Gemini model in use (default from `.env`)
- [x] Default in `.env` is now `gemini-3.1-pro-preview` (per user) — better
      reasoning for these modes; flash-lite was fine for the canonical
      pipeline only

## Bragging-rights criteria (from ADR 0005)

To declare research-utility (not just plumbing), need ≥1 of:

1. **Mode B:** surfaces a target that appears in a 2024–2026 review as
   "promising but understudied" — e.g. RTEL1 for IPF would qualify if we can
   cite a recent review. Action item.
2. **Mode C:** surfaces a known repurposing pair we did NOT seed (e.g.
   metformin→cancer) from public ChEMBL alone.
3. **Mode D:** ≥3/4 picks defensible against literature.

## Out of scope for Phase 5

- Combining the modes into a single pipeline (e.g. `explore` → pick a target →
  auto-run `repurpose` on it). Compose by hand for now.
- Selectivity panels (proper cross-target binding analysis). Single-target
  potency only.
- Patent landscape (deferred to Phase 6+).
- Reinforcement loop (using past picks to weight future ones beyond simple
  memory). Out of scope by design — see ADR 0002 (we are not Hermes).
