# docs/ — Project Journal

This directory is the long-term memory of the project. It survives sessions, model
swaps, and refactors. If a future me (Claude or human) needs to know **why** the
project looks the way it does, **where** it's headed, or **what we already tried
and rejected** — it lives here.

## Layout

```
docs/
  README.md                    you are here
  glossary.md                  terms used throughout
  open-questions.md            unresolved design choices, parked decisions
  decisions/                   ADRs (Architecture Decision Records)
    0001-pivot-to-harness.md   why we're not just an app
    0002-build-minimal-not-fork-hermes.md
    0003-provider-strategy.md  Gemini-first, multi later
  plans/                       phased roadmap
    phase-0-docs-and-pivot.md
    phase-1-refactor-into-core-skills.md
    phase-2-provider-abstraction.md
    phase-3-minimal-cli.md
    phase-4-persistent-memory.md
  notes/                       working memory, snapshots
    2026-04-30-pivot-snapshot.md   what worked before pivot
```

## Conventions

- **ADRs** are immutable. If a decision changes, write a new ADR that supersedes
  the old one — don't edit the old one. (Models the chain of reasoning, not just
  the latest answer.)
- **Plans** are mutable but versioned by file name. `phase-1-refactor.md` is a
  living checklist; we mark items done with `[x]`.
- **Notes** are scratch — anything worth remembering in 2 weeks. Datestamped.
- **Glossary** stays definitive: when introducing a new term in any other doc,
  add it to glossary.md.

## How to use this from a Claude session

When starting work, read in this order:
1. `notes/` (most recent first) — what state is the project in?
2. `decisions/` (newest first) — what constraints am I bound by?
3. `plans/` (current phase) — what am I trying to do?
4. Codebase.

When ending work that mattered, write:
- A new note in `notes/` if the state changed.
- A new ADR in `decisions/` if a tradeoff was made.
- Update the current plan's checklist.

## Why this is not just CLAUDE.md

`CLAUDE.md` is the front door — high-level brief, kept short. This dir is the
detailed history that informs how the front door is interpreted. They serve
different purposes; both should exist.
