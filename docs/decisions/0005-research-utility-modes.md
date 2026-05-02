# ADR 0005 — Three modes for research utility (not just plumbing)

- **Status:** accepted
- **Date:** 2026-05-02

## Context

User feedback: "if we are testing it with proven old drug data that won't be
helpful for researchers — we have to do something where this can actually help
researchers." Sharp and correct. Recovering PPARG for type 2 diabetes proves
the plumbing works but is not a research finding; PPARG/rosiglitazone has been
in textbooks for 20 years.

For this project to claim research utility — and be brag-worthy on
LinkedIn/GitHub honestly — the agent must surface findings that are not
trivial-Google-searches.

## Decision

Add three distinct discovery modes alongside the existing pipeline:

### Mode A — `discover` (existing)
Disease → canonical target → known drugs. **Purpose:** regression test +
demonstration. Honest framing: "the plumbing works on diseases with known
answers." Not a research claim.

### Mode B — `explore` (new)
Find **underexplored druggable targets** for a disease. Definition:
- High OpenTargets association score (genetic/biological evidence)
- Low max_phase in ChEMBL (no approved drug yet)
- Few existing bioactive compounds (chemical matter is sparse)
- 3D structure available (actionable next step exists)

Output: ranked list of "proteins worth a literature week." Saves a researcher
days of triage. Implementation: `services/underexplored.py` + CLI
`hermes-bio explore --disease "..."`.

### Mode C — `repurpose` (new)
For a chosen target T, find **FDA-approved drugs whose primary indication is
something else entirely** but which have measured ChEMBL activity against T.
This is exactly how real repurposing studies are run (metformin→cancer,
sildenafil→pulmonary hypertension, etc.).

Output: cross-indication candidates with primary indication, mechanism, and
measured potency. Each row is a "this drug treats X but might also help Y"
hypothesis. Implementation: `services/cross_repurposing.py` + CLI
`hermes-bio repurpose --target P00533`.

### Mode D — Hard-mode eval
Extend `app/eval.py` with diseases where there is **no single canonical
target** and the agent must reason about plausibility:
- Idiopathic pulmonary fibrosis
- Long COVID / post-acute sequelae of SARS-CoV-2
- Friedreich's ataxia (rare disease, sparse literature)

Pass criterion: target appears in a 2024–2026 review article as plausible.
Reviewed manually rather than allowlisted, with results recorded in
`docs/notes/`.

## Why this matters

- **Mode A** alone can't be honestly described as "an AI agent for drug
  discovery." It can be honestly described as "a working agentic harness."
- **Mode B** is the most defensible single research-utility claim. The output
  is a triage shortlist, which is concrete, falsifiable, and a real
  time-saver. Researchers do this triage manually today.
- **Mode C** is the highest-impact demo but also the most likely to surface
  noise (any kinase inhibitor binds dozens of kinases). Needs careful
  filtering and selectivity scoring.
- **Mode D** is the most honest test. If we can show the agent picks
  literature-defensible targets on diseases without obvious answers, that's
  a real signal.

## Model strategy per mode

- **Mode A (discover):** `gemini-3.1-flash-lite-preview` (cheap, fast, fine
  for following the canonical pipeline)
- **Mode B (explore):** `gemini-3.1-pro-preview` (more reasoning, fewer runs,
  worth the cost for novel-target judgment)
- **Mode C (repurpose):** `gemini-3.1-pro-preview` (selectivity reasoning is
  non-trivial; pro is worth it)
- **Mode D (hard eval):** `gemini-3.1-pro-preview`

Implementation: `--model <id>` CLI flag overrides; each mode picks a sensible
default. Per-mode default lives in `app/cli.py`.

## Bragging-rights criteria

For LinkedIn/GitHub claims, we need ≥1 of:

1. Mode B surfaces a target that appears in a 2024–2026 review as "promising
   but understudied," AND we can show the agent's reasoning trace converging
   on it.
2. Mode C surfaces a known repurposing example we did not seed (e.g. metformin
   for cancer or sildenafil for pulmonary hypertension), discovered from
   public ChEMBL data alone.
3. Mode D scores ≥3/4 on hard diseases vs a literature-defensible answer key.

If we get any one of these, the project has a real claim. Without them, this
remains "an interesting harness with a working pipeline."

## Out of scope

- Wet-lab validation (obvious — we have no lab).
- Patent landscape analysis (would be valuable for repurposing, deferred).
- Selectivity scoring for Mode C beyond "primary indication ≠ target's
  disease" (proper kinase selectivity needs cross-target panels).
