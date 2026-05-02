# Glossary

Terms used across the project. When introducing a new term in any other doc,
add it here too.

| Term | Meaning |
|---|---|
| **Agent** | An LLM in a tool-use loop with the ability to make multi-step decisions. |
| **Harness** | The wrapper around the model: instructions, tools, memory, orchestration, evals. The harness, not the model, is the main lever for capability. |
| **Skill** | A scoped capability (system prompt + tool set + maybe data). Loaded on demand. Anthropic-style `SKILL.md` files. |
| **Provider** | An LLM API vendor: Anthropic, OpenAI, Google (Gemini), local Ollama, etc. |
| **BYOK** | Bring Your Own Key — user supplies their own API credentials per provider. |
| **Tool** | A function callable by the agent via structured arguments. Backend dispatches by name. |
| **MCP** | Model Context Protocol — Anthropic's open standard for exposing tools/resources to agents. Cross-vendor. |
| **SSE** | Server-Sent Events. One-way HTTP streaming used to push reasoning events to the frontend. |
| **ADR** | Architecture Decision Record. Immutable doc capturing one decision and its rationale. |
| **SAScore** | Synthetic Accessibility Score (Ertl & Schuffenhauer 2009). 1.0 easy → 10.0 hard. |
| **Lipinski Ro5** | Rule of Five druglikeness filter (MW≤500, logP≤5, HBD≤5, HBA≤10). |
| **ADMET** | Absorption, Distribution, Metabolism, Excretion, Toxicity — pharmacokinetic profile. |
| **Repurposing** | Using an FDA-approved drug for a new indication. Cheaper/faster than novel discovery. |
| **Pocket** | Cavity on a protein surface where a drug-sized molecule can bind. |
| **pLDDT** | AlphaFold per-residue confidence (0–100). >70 reasonable, >90 high. |
| **PDB** | Protein Data Bank — public archive of experimental structures. |
| **UniProt ID** | Stable accession for a protein, e.g. `P49768`. |
