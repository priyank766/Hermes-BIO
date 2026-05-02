import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Depends
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from ..db import Job, Target, Structure, DockingResult, get_session, SessionLocal
from ..workers.pipeline import run_pipeline
from ..workers import events as bus
from ..config import settings
from ..services.explain import explain_mechanism
from .. import memory

router = APIRouter(prefix="/api")


class DiscoverRequest(BaseModel):
    disease: str


@router.post("/discover")
async def discover(
    body: DiscoverRequest,
    bg: BackgroundTasks,
    s: AsyncSession = Depends(get_session),
) -> dict:
    if not body.disease.strip():
        raise HTTPException(400, "disease required")
    job_id = uuid.uuid4().hex[:12]
    job = Job(id=job_id, disease_input=body.disease, status="pending")
    s.add(job)
    await s.commit()
    bg.add_task(run_pipeline, job_id, body.disease)
    return {"job_id": job_id, "status": "started"}


@router.get("/jobs/{job_id}")
async def get_job(job_id: str, s: AsyncSession = Depends(get_session)) -> dict:
    job = await s.get(Job, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    return {
        "job_id": job.id,
        "disease": job.disease_input,
        "status": job.status,
        "progress": job.progress,
        "current_step": job.current_step,
        "error": job.error,
        "reasoning_log": job.reasoning_log or [],
    }


@router.get("/jobs/{job_id}/events")
async def job_events(job_id: str):
    """Server-Sent Events stream of agent reasoning + tool calls."""
    async def gen():
        async for event in bus.subscribe(job_id):
            yield f"data: {json.dumps(event)}\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream", headers={
        "Cache-Control": "no-cache",
        "X-Accel-Buffering": "no",
    })


@router.get("/jobs/{job_id}/candidates")
async def get_candidates(job_id: str, s: AsyncSession = Depends(get_session)) -> dict:
    stmt = select(Job).where(Job.id == job_id).options(
        selectinload(Job.targets).selectinload(Target.structures).selectinload(Structure.docking_results)
    )
    res = await s.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "job not found")
    out = []
    target = job.targets[0] if job.targets else None
    if target and target.structures:
        for d in sorted(target.structures[0].docking_results, key=lambda x: x.rank):
            out.append({
                "rank": d.rank,
                "smiles": d.molecule_smiles,
                "name": d.molecule_name,
                "binding_affinity": d.binding_affinity,
                "lipinski_pass": d.lipinski_pass,
                "toxicity_score": d.toxicity_score,
                "absorption_score": d.absorption_score,
                "synthesis_score": d.synthesis_score,
                "is_approved_drug": d.is_approved_drug,
            })
    return {
        "job_id": job_id,
        "target": {
            "uniprot_id": target.uniprot_id,
            "protein_name": target.protein_name,
            "druggability_score": target.druggability_score,
            "rationale": target.rationale,
        } if target else None,
        "structure": {
            "pdb_path": target.structures[0].pdb_path,
            "source": target.structures[0].source,
            "quality_score": target.structures[0].quality_score,
            "pocket_center": (target.structures[0].pocket_data or {}).get("center"),
        } if target and target.structures else None,
        "candidates": out,
    }


@router.get("/jobs/{job_id}/structure")
async def get_structure(job_id: str, s: AsyncSession = Depends(get_session)):
    stmt = select(Job).where(Job.id == job_id).options(
        selectinload(Job.targets).selectinload(Target.structures)
    )
    res = await s.execute(stmt)
    job = res.scalar_one_or_none()
    if not job or not job.targets or not job.targets[0].structures:
        raise HTTPException(404, "structure not available yet")
    pdb_path = Path(job.targets[0].structures[0].pdb_path)
    if not pdb_path.exists():
        raise HTTPException(404, "PDB file missing")
    return FileResponse(str(pdb_path), media_type="chemical/x-pdb", filename=pdb_path.name)


@router.post("/jobs/{job_id}/candidates/{rank}/explain")
async def explain_candidate(job_id: str, rank: int, s: AsyncSession = Depends(get_session)) -> dict:
    """Generate (or fetch cached) mechanism-of-action explanation for one candidate."""
    stmt = select(Job).where(Job.id == job_id).options(
        selectinload(Job.targets).selectinload(Target.structures).selectinload(Structure.docking_results)
    )
    res = await s.execute(stmt)
    job = res.scalar_one_or_none()
    if not job or not job.targets:
        raise HTTPException(404, "job or target not found")
    target = job.targets[0]
    structure = target.structures[0] if target.structures else None
    if not structure:
        raise HTTPException(404, "structure not found")
    candidate = next((d for d in structure.docking_results if d.rank == rank), None)
    if not candidate:
        raise HTTPException(404, "candidate not found")

    if candidate.mechanism_explanation:
        return {"rank": rank, "explanation": candidate.mechanism_explanation, "cached": True}

    text = explain_mechanism(
        target_uniprot=target.uniprot_id,
        target_name=target.protein_name,
        disease=job.disease_input,
        smiles=candidate.molecule_smiles,
        drug_name=candidate.molecule_name,
        is_approved=candidate.is_approved_drug,
        binding_affinity=candidate.binding_affinity,
    )
    candidate.mechanism_explanation = text
    await s.commit()
    return {"rank": rank, "explanation": text, "cached": False}


@router.get("/jobs/{job_id}/graph")
async def get_graph(job_id: str, s: AsyncSession = Depends(get_session)) -> dict:
    """Cytoscape-shaped graph: Disease → Target → Pocket → Drugs."""
    stmt = select(Job).where(Job.id == job_id).options(
        selectinload(Job.targets).selectinload(Target.structures).selectinload(Structure.docking_results)
    )
    res = await s.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "job not found")

    nodes = [{"data": {"id": "disease", "label": job.disease_input, "type": "disease"}}]
    edges: list[dict] = []
    for t in job.targets:
        tid = f"target:{t.uniprot_id}"
        nodes.append({"data": {
            "id": tid, "label": t.uniprot_id, "type": "target",
            "name": t.protein_name, "score": t.druggability_score,
        }})
        edges.append({"data": {"source": "disease", "target": tid, "type": "associated"}})
        for st in t.structures:
            sid = f"struct:{st.id}"
            nodes.append({"data": {
                "id": sid, "label": st.source, "type": "structure",
                "pdb_path": st.pdb_path,
            }})
            edges.append({"data": {"source": tid, "target": sid, "type": "has_structure"}})
            for d in sorted(st.docking_results, key=lambda x: x.rank)[:8]:
                did = f"drug:{d.id}"
                nodes.append({"data": {
                    "id": did,
                    "label": d.molecule_name or f"#{d.rank}",
                    "type": "drug_approved" if d.is_approved_drug else "drug_novel",
                    "rank": d.rank,
                    "affinity": d.binding_affinity,
                    "smiles": d.molecule_smiles,
                    "approved": d.is_approved_drug,
                    "synthesis_score": d.synthesis_score,
                }})
                edges.append({"data": {
                    "source": sid, "target": did, "type": "binds",
                    "weight": abs(d.binding_affinity),
                }})
    return {"nodes": nodes, "edges": edges}


@router.get("/memory")
async def get_memory(scope: str = "drug_discovery", prefix: str | None = None) -> dict:
    """Inspect what the harness remembers."""
    items = await memory.recall(scope, prefix=prefix)
    return {"scope": scope, "prefix": prefix, "items": items, "count": len(items)}


@router.delete("/memory")
async def clear_memory(scope: str = "drug_discovery", prefix: str | None = None) -> dict:
    deleted = await memory.clear(scope, prefix=prefix)
    return {"scope": scope, "prefix": prefix, "deleted": deleted}


@router.get("/jobs/{job_id}/report")
async def get_report(job_id: str, s: AsyncSession = Depends(get_session)):
    job = await s.get(Job, job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.status != "completed":
        raise HTTPException(409, f"job status: {job.status}")
    path = settings.reports_dir / f"{job_id}.html"
    if not path.exists():
        raise HTTPException(404, "report not generated")
    return FileResponse(str(path), media_type="text/html")
