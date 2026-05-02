# LinkedIn post — drafts

Three lengths. Pick one or remix. Replace `<repo-url>` with your GitHub link
once pushed.

---

## Long version (~350 words) — recommended for first post

Most "AI for drug discovery" demos do exactly one thing: pick a known
disease, pick a known target, find a known approved drug, declare victory.
That's a smoke test, not a research tool — anyone can Google PPARG for
diabetes.

So I built **hermes-bio** — an agentic harness designed around three things
researchers *actually* need help with, not the things that demo well.

🔬 **Mode A — Regression baseline**
Six canonical disease/target pairs. The agent recovers all six (PPARG, EGFR,
PSEN1, ABL1) — and on rheumatoid arthritis + Parkinson's it picked the
**2022–2026 next-generation targets** (TYK2, LRRK2), not the 1990s textbook
ones. It's reading current OpenTargets evidence, not regurgitating drug
history.

🧬 **Mode B — Underexplored targets**
For idiopathic pulmonary fibrosis, the harness surfaces **RTEL1, SFTPA2,
MUC5B** as top "high biology, low chemistry" picks — the canonical IPF
genetic risk genes, all with zero approved drugs. A literature-week of
triage in 8 seconds.

💊 **Mode C — Cross-indication repurposing**
For MTOR (excluding oncology), it surfaces **sirolimus** for aplastic
anemia and **tacrolimus** for rheumatoid arthritis. Real off-label leads
from public ChEMBL data alone, no seeding.

🎯 **Hard-mode eval — 4/4 defensible**
On four diseases without canonical answers (IPF, long COVID, Friedreich
ataxia, ALS), the agent picked targets matching **2023 FDA approvals or
active Phase-3 trials** every time — including frataxin (Skyclarys, Feb
2023) and SOD1 (Tofersen, Apr 2023).

Stack:
• Gemini function-calling agent loop (with persistent memory — repeat runs
3× faster)
• React + NGL viewer + Cytoscape graph UI
• CLI with BYOK
• MCP server — plug into Claude Code / Cursor / Claude Desktop
• Honest stubs (docking, fpocket, ADMET) clearly labeled — the scientific
claim is in target selection + repurposing triage, not docking accuracy

Built solo. Public APIs only (UniProt, OpenTargets, PDB, AlphaFold,
ChEMBL). Code, architecture, and a full project journal of design
decisions:

→ <repo-url>

#AgenticAI #DrugDiscovery #Bioinformatics #AI #ComputationalBiology #LLM #MCP

---

## Medium version (~180 words)

I built **hermes-bio** — an agentic harness for drug-discovery research.
Not a chatbot, not another "ask GPT for a drug" demo.

Three real research-utility modes:

🧬 **explore** — high genetic association × low drug development. For IPF,
surfaces RTEL1, SFTPA2, MUC5B (the canonical risk genes, zero approved
drugs).

💊 **repurpose** — FDA-approved drugs that bind a target but are approved
for *other* diseases. For MTOR (no oncology), surfaces sirolimus for
aplastic anemia, tacrolimus for RA.

🎯 **discover** — full agentic pipeline through UniProt, OpenTargets, PDB,
AlphaFold, ChEMBL with repurposing-first screening.

**Hard-mode eval result: 4/4 defensible** picks on diseases without
canonical answers. For Friedreich ataxia → frataxin (matches Skyclarys,
FDA Feb 2023). For ALS → SOD1 (matches Tofersen, FDA Apr 2023).

Built with: Gemini function-calling, FastAPI, React + NGL viewer,
persistent memory, MCP server (works in Claude Code / Cursor / Desktop).

Code + journal + architecture: <repo-url>

#AgenticAI #DrugDiscovery #Bioinformatics

---

## Short version (~80 words) — for the impatient

Built **hermes-bio**: an agentic harness for drug discovery, not a chatbot.

Three modes — discover, explore (underexplored targets), repurpose
(cross-indication FDA drugs). Eval: 6/6 canonical disease–target pairs
recovered + 4/4 picks on hard-mode diseases match 2023 FDA approvals or
Phase 3 trials.

Stack: Gemini function-calling, FastAPI, React + NGL, persistent memory,
MCP server (works in Claude Code).

Code + journal: <repo-url>

#AgenticAI #DrugDiscovery #Bioinformatics

---

## Tips for posting

- **Add a screenshot or GIF.** LinkedIn rewards visual posts. The
  three-pane workspace is the photogenic shot — agent reasoning panel +
  NGL protein + candidates table. Or a short loom of the CLI streaming.
- **Tag the right people.** Researchers in computational biology, anyone
  working on agent harnesses, founders building MCP-aware tools.
- **Don't over-claim.** The "4/4 defensible" framing is honest — say
  "matches 2023 FDA approvals," not "discovered" or "predicted." Stubs
  for docking and ADMET should be acknowledged in the comments if anyone
  asks.
- **Lead with the eval result + hard-mode finding** — that's the strongest
  hook. The plumbing of the harness is interesting to engineers; the
  result is interesting to everyone.
