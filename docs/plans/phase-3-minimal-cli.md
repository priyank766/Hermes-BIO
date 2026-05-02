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

- [ ] `core/cli/__main__.py` using `click` or `typer` (lighter — argparse if
      we want zero deps)
- [ ] `core/config.py` extended: read `~/.hermes-bio/config.toml`
- [ ] Streaming: subscribe to the same internal event bus the SSE endpoint
      uses, render line-by-line to stdout (color via `rich` optional)
- [ ] `--output json` returns the final structured result as a single JSON
      blob (matches current `/api/jobs/{id}/candidates` shape)
- [ ] Exit codes: 0 success, 1 agent failure, 2 user error (bad args)
- [ ] Make the CLI importable as a module and invokable as `python -m hermes_bio`
      AND as a `hermes-bio` script (entry point in `pyproject.toml`)

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
