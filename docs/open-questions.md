# Open Questions

Unresolved design choices. Each one becomes an ADR or a closed question
eventually.

## Q1 — Is `core/` extractable into its own pip-installable package?

If yes, it could be `pip install hermes-bio-core` and the drug-discovery skill
becomes `pip install hermes-bio-skill-drug-discovery`. Plugin discovery via
entry points.

**Lean:** yes long-term, no for Phase 1. Premature packaging hurts iteration speed.

## Q2 — Real docking (Vina) — bundled or optional?

Installing AutoDock Vina on Windows is awkward. Options:
- (a) Optional extra: `uv sync --extra docking` installs `vina` + expects
  binary on PATH. Stub stays as default.
- (b) Containerize: a Docker image with Vina + fpocket pre-installed. The
  service shells out to a sidecar.
- (c) Hosted: call a remote docking service. We don't run one; this is
  hypothetical.

**Lean:** (a) for now. Document the install steps. (b) if anyone deploys.

## Q3 — Where does the disease-class taxonomy live?

For memory keys, "type 2 diabetes mellitus" and "type II diabetes" should
resolve to the same scope. EFO IDs (which OpenTargets uses) are the right
canonical form.

**Lean:** normalize to EFO ID at memory-write time. If no EFO, store raw
disease string (warn).

## Q4 — Skill discovery: file-system scan or registry?

Options for "which skills exist?":
- (a) Scan `skills/*/SKILL.md` at startup
- (b) Explicit registry in code or config

**Lean:** (a). Anthropic's skills work this way; matches mental model.

## Q5 — Are mechanism explanations a tool or a side effect?

Currently `/api/jobs/{id}/candidates/{rank}/explain` is a separate endpoint
that calls Gemini directly outside the agent loop. Alternative: make it a
tool the agent can call as part of the main run.

**Lean:** keep as separate endpoint. The explanation is a UX feature for
humans browsing results, not part of the agent's task.

## Q6 — Multi-target runs?

Currently the agent picks one target per disease. Many real diseases have
multiple useful targets (e.g. cancer pathways). Should the agent run a
parallel screen across top-3 targets?

**Lean:** no for Phase 1. Add as a tool/CLI flag later: `--targets 3`.

## Q7 — Eval / regression suite?

We have no automated check that "type 2 diabetes → PPARG" survives a
refactor. After Phase 1, add a smoke test:

```bash
uv run pytest tests/eval_known_diseases.py
```

Three diseases, three expected target UniProts. Asserts one of the top-3
picks matches the canonical target. Cheap insurance.

## Q8 — Fast path: skip the agent loop when memory has the answer?

If memory says "for type 2 diabetes we picked PPARG with high confidence
yesterday", do we still run the full agent loop, or fast-track to the
docking step?

**Lean:** still run the loop; let the agent decide based on the memory note
prepended to the system prompt. Fast paths bypass the agent's judgment,
which defeats the point.
