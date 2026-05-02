# ADR 0001 — Pivot from "drug-discovery app" to "drug-discovery harness"

- **Status:** accepted
- **Date:** 2026-04-30
- **Supersedes:** —

## Context

We built a working agentic drug-discovery pipeline (FastAPI + Gemini function-calling
+ React frontend) over two sessions. It correctly identifies disease targets,
fetches structures, runs repurposing-first screening, scores synthesizability, and
streams reasoning to a three-pane UI. End-to-end verified for type 2 diabetes
(PPARG/Rosiglitazone), NSCLC (EGFR/Sunitinib), Alzheimer's (PSEN1).

User signal: "I don't want to just build the chatbot or LLM or agent — I want
to build an agentic harness that works for this, something like Hermes Agent."

## Decision

Treat the drug-discovery pipeline as **the flagship skill of a generalizable
agentic harness**, not as a one-off application. Refactor in place toward a
core-and-skills layout. Do not throw away current code; reuse it as the first
skill plugin.

## Why this is the right framing

- Harness engineering is empirically the dominant lever once you've picked a
  capable base model (LangChain's experiment moved a benchmark +13.7% with the
  model held constant — see `notes/2026-04-30-pivot-snapshot.md`).
- The same codebase becomes reusable across other bio domains (protein design,
  variant analysis, pathway discovery) by adding skills, not rewriting the loop.
- Provider-agnostic + BYOK matters because a researcher with an Anthropic key
  shouldn't need a Google one to use this. CLI + library form factors broaden
  reach beyond the web app.
- "Drug-discovery agent" is a crowded narrative; "drug-discovery harness with
  swappable skills and providers" is more durable and more honest about what
  the leverage actually is.

## What we are not deciding

- Whether to fork Nous Research's Hermes Agent. See ADR 0002.
- Which providers to support. See ADR 0003.
- Whether to build a Claude-Code-style terminal UI. **No** — explicit non-goal
  for the foreseeable future. Plain stdout-streaming CLI is enough.

## Consequences

- The current FastAPI+React surface becomes one of (eventually) several
  frontends — others might be CLI, MCP server, Slack, etc.
- Scope discipline matters: every new feature gets evaluated as "does it belong
  in `core/` (every skill benefits) or `skills/drug_discovery/` (only this
  benefits)?"
- We pay a small refactor tax now to get a much larger generalization payoff later.

## Risks

1. **Becoming yet another agent framework.** Mitigation: do not abstract
   prematurely. Only generalize patterns that appear in two skills.
2. **Refactor stalls progress.** Mitigation: phased plan keeps the system
   working at every phase boundary. See `plans/phase-1-refactor-into-core-skills.md`.
3. **Hermes-clone temptation.** Mitigation: explicit non-goal in ADR 0002 to
   replicate Hermes' personal-assistant surface (Telegram, Discord, etc.).
