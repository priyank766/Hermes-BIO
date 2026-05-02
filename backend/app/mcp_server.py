"""MCP server exposing the hermes-bio harness to MCP-aware editors
(Claude Code, Cursor, etc).

Tools surfaced:
  - explore_underexplored_targets(disease) -> list of underexplored druggable targets
  - find_cross_indication_drugs(uniprot_id, exclude_keywords) -> off-disease leads
  - investigate_disease(disease) -> composed: pick target + alts + repurposing
  - run_full_discovery(disease) -> full agentic pipeline (slow, ~60s)
  - get_memory(disease) -> what the harness remembers about this disease class

STDIO transport. Run via `hermes-bio mcp`. Never print to stdout outside the
MCP protocol — use logging only.
"""
from __future__ import annotations
import asyncio
import logging
import uuid
from typing import Any

from fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="[%(name)s] %(levelname)s: %(message)s")
log = logging.getLogger("hermes-bio.mcp")

mcp = FastMCP("hermes-bio")


@mcp.tool
async def explore_underexplored_targets(disease: str, top: int = 8) -> dict:
    """Find proteins with strong disease association but little drug-development activity.

    Returns up to `top` candidates ranked by an underexplored score
    (genetic_assoc × drug_gap × not_crowded × structure_available). Use this to
    triage 'high biology, low chemistry' targets for early-stage research.

    Example: disease="idiopathic pulmonary fibrosis" returns RTEL1, SFTPA2,
    MUC5B etc — known IPF risk genes with zero approved drugs.
    """
    from .services.underexplored import find_underexplored_targets
    rows = await find_underexplored_targets(disease, top_n=max(top, 10))
    return {
        "disease": disease,
        "count": len(rows),
        "candidates": rows[:top],
    }


@mcp.tool
async def find_cross_indication_drugs(
    uniprot_id: str,
    exclude_keywords: list[str] | None = None,
    top: int = 12,
) -> dict:
    """For a target (UniProt ID), find FDA-approved drugs that bind it but are
    primarily approved for OTHER conditions.

    `exclude_keywords`: terms to filter out from indications. E.g. for an
    oncology target, pass ['cancer', 'carcinoma', 'tumor', 'neoplasm'] to
    surface non-oncology cross-indications.

    Returns approved binders with potency, primary indications, and a
    cross-indication flag. Real off-label / repurposing leads.
    """
    from .services.cross_repurposing import cross_indication_candidates
    rows = await cross_indication_candidates(
        uniprot_id, exclude_disease_keywords=exclude_keywords or [], top_potency=max(top * 2, 25)
    )
    cross = [r for r in rows if r.get("is_cross_indication")][:top]
    return {
        "target_uniprot": uniprot_id,
        "exclude_keywords": exclude_keywords or [],
        "total_approved_binders": len(rows),
        "cross_indication_count": len(cross),
        "candidates": cross,
    }


@mcp.tool
async def investigate_disease(disease: str) -> dict:
    """Composed workflow: pick top OpenTargets target → list underexplored
    alternatives → run cross-indication repurposing on the picked target.

    One-call snapshot of plausible research directions for a disease.
    """
    from .services.opentargets import get_validated_targets
    from .services.underexplored import find_underexplored_targets
    from .services.cross_repurposing import cross_indication_candidates

    targets = await get_validated_targets(disease, size=5)
    chosen = next((t for t in targets if t.get("uniprot_id")), None)
    if not chosen:
        return {"disease": disease, "error": "no OpenTargets hits with UniProt mapping"}

    alts_task = asyncio.create_task(find_underexplored_targets(disease, top_n=10))
    excludes = [w for w in disease.lower().split() if len(w) > 3]
    cross_task = asyncio.create_task(
        cross_indication_candidates(chosen["uniprot_id"], exclude_disease_keywords=excludes)
    )
    alts = await alts_task
    cross = await cross_task

    return {
        "disease": disease,
        "primary_target": chosen,
        "underexplored_alternatives": [r for r in alts if r["underexplored_score"] > 0.15][:5],
        "cross_indication_drugs": [c for c in cross if c.get("is_cross_indication")][:6],
    }


@mcp.tool
async def run_full_discovery(disease: str) -> dict:
    """Run the full agentic drug-discovery pipeline (slow: ~60s).

    Agent picks a target, fetches structure, screens approved drugs against
    it, runs docking + Lipinski + SAScore + ADMET, returns a ranked candidate
    list. Use this when you want the agent's reasoned end-to-end output, not
    just the API-driven shortcuts.
    """
    from .db import init_db, SessionLocal, Job, Target, Structure
    from .workers.pipeline import run_pipeline
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    await init_db()
    job_id = uuid.uuid4().hex[:12]
    async with SessionLocal() as s:
        s.add(Job(id=job_id, disease_input=disease, status="pending"))
        await s.commit()

    await run_pipeline(job_id, disease)

    async with SessionLocal() as s:
        stmt = select(Job).where(Job.id == job_id).options(
            selectinload(Job.targets).selectinload(Target.structures).selectinload(Structure.docking_results)
        )
        res = await s.execute(stmt)
        job = res.scalar_one_or_none()
        if not job or job.status != "completed":
            return {"disease": disease, "job_id": job_id, "status": job.status if job else "missing", "error": job.error if job else None}
        target = job.targets[0] if job.targets else None
        candidates: list[dict] = []
        if target and target.structures:
            for d in sorted(target.structures[0].docking_results, key=lambda x: x.rank):
                candidates.append({
                    "rank": d.rank,
                    "smiles": d.molecule_smiles,
                    "name": d.molecule_name,
                    "binding_affinity": d.binding_affinity,
                    "lipinski_pass": d.lipinski_pass,
                    "synthesis_score": d.synthesis_score,
                    "is_approved_drug": d.is_approved_drug,
                })
    return {
        "disease": disease,
        "job_id": job_id,
        "target": {"uniprot_id": target.uniprot_id, "name": target.protein_name} if target else None,
        "candidates": candidates,
    }


@mcp.tool
async def get_harness_memory(disease: str | None = None) -> dict:
    """Inspect what the harness already knows about diseases / targets.

    If `disease` is provided, returns the cached entry for that disease class.
    Otherwise returns all entries in the drug_discovery scope.
    """
    from . import memory
    from .db import init_db
    await init_db()
    if disease:
        cached = await memory.get("drug_discovery", memory.disease_key(disease))
        return {"disease": disease, "cached": cached}
    items = await memory.recall("drug_discovery")
    return {"count": len(items), "items": items}


def main() -> None:
    log.info("starting hermes-bio MCP server (stdio)")
    mcp.run()


if __name__ == "__main__":
    main()
