# Phase 3 — Minimal CLI (BYOK)

**Goal:** make the harness usable from a terminal without the web UI. Spirit
of `claude` / `codex` / `gemini` CLIs, but ~100x simpler.

**Explicit non-goals:** terminal UI (TUI), file editing, slash commands,
sandboxed bash, MCP, hooks. Those are months of work and outside scope.

## Surface

```bash
# Run the drug-discovery skill end-to-end
hermes-bio run drug-discovery --disease "type 2 diabetes mellitus"

# Pick provider
hermes-bio run drug-discovery --disease "..." --provider anthropic

# Output formats
hermes-bio run drug-discovery --disease "..." --output json    # default: pretty stream

# Configure API keys
hermes-bio config set anthropic-key sk-ant-...
hermes-bio config set gemini-key ...
hermes-bio config show     # shows providers configured (keys redacted)

# List available skills
hermes-bio skills list
```

## Implementation

- [x] `app/cli.py` using argparse (zero deps, per ADR-0004 layout deferral)
- [x] Streaming: subscribes to the in-memory `workers.events` bus same as SSE
- [x] ANSI color output to TTY only; falls back to plain text in pipes
- [x] `--output json` emits final structured result + status as one JSON blob
- [x] Exit codes: 0 success, 1 agent failure, 2 user error (bad subcommand)
- [x] `hermes-bio` script entry point via `[project.scripts]` + hatchling
- [x] Forces `sys.stdout.reconfigure(encoding="utf-8")` for Windows cp1252
- [x] **Verified**: `hermes-bio run drug-discovery --disease "..."` produces
      streaming output matching the frontend's reasoning panel; memory
      recall card prints in purple; final report path emitted on done.

## Deferred to Phase 3.1 (when needed)

- `~/.hermes-bio/config.toml` for persistent BYOK (today: env var / `.env`)
- `--provider anthropic` flag (waiting on Phase 2)
- `python -m app.cli` invocation (the entry-point script is enough for now)

## Verification

```bash
# fresh shell, no env vars
hermes-bio run drug-discovery --disease "NSCLC" --gemini-key "$GEMINI_API_KEY"
# expect streaming reasoning + final JSON to stdout, exit 0

hermes-bio run drug-discovery --disease "NSCLC" --output json --gemini-key "..."
# expect: single JSON object, exit 0
```

## What this enables next

- Cron / batch / pipeline use: `hermes-bio` becomes a building block
- CI smoke tests of the agent loop without spinning up the web stack
- Headless deployment without React frontend
