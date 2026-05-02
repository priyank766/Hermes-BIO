# MCP Integration

`hermes-bio` exposes its three research-utility modes as MCP tools so any
MCP-aware host (Claude Desktop, Claude Code, Cursor, etc.) can use this
harness as a research assistant.

## What gets exposed

| MCP tool | What it does | Latency |
|---|---|---|
| `explore_underexplored_targets(disease, top)` | High biology × low chemistry shortlist | ~5–10s |
| `find_cross_indication_drugs(uniprot_id, exclude_keywords, top)` | Approved drugs that bind T but are approved for OTHER conditions | ~10–20s |
| `investigate_disease(disease)` | Composed: pick target + alts + repurposing in one call | ~15–25s |
| `run_full_discovery(disease)` | Full agentic pipeline (slow — picks target, fetches structure, docks, filters) | ~60–120s |
| `get_harness_memory(disease?)` | Inspect what the harness has cached | <1s |

## Connect to Claude Desktop

Add to `~/.config/Claude/claude_desktop_config.json` (Linux/Mac) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "hermes-bio": {
      "command": "uv",
      "args": ["--directory", "C:/Users/Priyank/Documents/CODE/DRUG-DISCOVERY-PIPELINE/backend", "run", "hermes-bio", "mcp"],
      "env": {
        "GEMINI_API_KEY": "your-key",
        "GEMINI_MODEL": "gemini-3.1-flash-lite-preview"
      }
    }
  }
}
```

Restart Claude Desktop; the five tools appear in the MCP tools menu.

## Connect to Claude Code

```bash
claude mcp add hermes-bio --transport stdio --command "uv" \
  --args="--directory,/path/to/backend,run,hermes-bio,mcp"
```

Or edit `.claude.json` in your home directory:

```json
{
  "mcpServers": {
    "hermes-bio": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/path/to/backend", "run", "hermes-bio", "mcp"]
    }
  }
}
```

## Connect to Cursor

Cursor's MCP config lives at `~/.cursor/mcp.json` (or workspace
`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "hermes-bio": {
      "command": "uv",
      "args": ["--directory", "/path/to/backend", "run", "hermes-bio", "mcp"]
    }
  }
}
```

## Example interactions

Once connected, in Claude Code / Desktop:

> "Use hermes-bio to find underexplored targets for **Friedreich ataxia**."

→ Host invokes `explore_underexplored_targets(disease="Friedreich ataxia")`,
returns FXN, mitochondrial iron-sulfur proteins, etc.

> "What FDA-approved drugs bind **PPARG** but are approved for diseases
> other than diabetes?"

→ Host invokes `find_cross_indication_drugs(uniprot_id="P37231",
exclude_keywords=["diabetes", "diabetic"])`, returns FARGLITAZAR for
liver cirrhosis, etc.

> "Run the full discovery pipeline on **non-small cell lung cancer**."

→ Host invokes `run_full_discovery(disease="...")`, agent loop runs in
the harness, returns target + ranked candidates.

## Why this matters

Most agent frameworks ARE MCP clients. Few of them ARE MCP servers exposing
domain-specific capability. This makes the harness composable into other
agentic workflows — e.g. a Claude Code session can use `hermes-bio` as one
of many tools while writing a research report, without requiring
hermes-bio to know anything about the broader workflow.

## Limitations

- The MCP server runs in the same process as the discovery pipeline; long
  `run_full_discovery` calls will block the MCP host's call slot.
- API keys come from the env passed by the MCP host config (above) or
  inherit from the parent shell.
- No HTTP/SSE transport yet — stdio only. Add later if a remote-host use
  case appears.
