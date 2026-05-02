# ADR 0002 — Build a minimal harness, do not fork Hermes Agent

- **Status:** accepted
- **Date:** 2026-04-30

## Context

Hermes Agent (Nous Research, Feb 2026) is the obvious reference for an agentic
harness with persistent memory, self-created skills, and multiple frontends.
~100k+ stars, mature project. The natural question: fork it and write
drug-discovery as a Hermes skill?

## Decision

**No.** Build a minimal harness in this repo. Be inspired by Hermes; do not
adopt it as a dependency.

## Reasoning

- Hermes optimizes for the personal-assistant use case (Telegram/Discord/email
  chatops, evolving user model, casual tasks). Our use case is research-grade
  bioinformatics with deterministic tool chains, structured outputs, and a
  scientific UI. The shapes diverge.
- The current code is already ~80% of a minimal harness. Finishing it is faster
  than learning Hermes' plugin API and adapting bio-tools to fit it.
- Forking inherits Hermes' roadmap and design choices we may not want. Building
  our own keeps the mental model small.
- "Self-improving / skill creation from experience" is impressive in demos but
  brittle in research workflows where reproducibility matters. We want
  *deliberate* memory (cached structures, prior target picks per disease class),
  not emergent skill genesis.

## What we'll borrow conceptually

- **Skill-as-folder** (mirror Anthropic's `SKILL.md` convention; Hermes does this).
- **Persistent memory keyed by skill + context** (disease class for us).
- **Multi-frontend by design** (web UI today; CLI next; potentially MCP server).
- **Harness-engineering vocabulary** (instructions, constraints, feedback loops,
  memory, orchestration as the five layers — see Hermes docs).

## What we explicitly will not borrow

- Telegram/Discord/Slack/WhatsApp connectors (out of scope).
- Self-modifying skills / skill creation at runtime (footgun for science).
- "Build deepening model of who you are across sessions" (unnecessary for
  research workflows).
- Hermes' specific memory backend.

## Reversibility

If this turns out to be wrong, switching to Hermes-as-dependency later is not
hard — drug-discovery tools are already a self-contained module. We'd port them
to Hermes' skill format. Cost of being wrong: a few days of refactor.
