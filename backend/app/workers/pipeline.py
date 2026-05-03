"""Background pipeline runner. Drives the agent, persists structured results, streams events."""
import json
import logging
import re
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..db import SessionLocal, Job, Target, Structure, DockingResult
from ..agent.orchestrator import run_agent
from ..services.reports import render_report
from .. import memory
from . import events as bus

SCOPE = "drug_discovery"

log = logging.getLogger(__name__)


async def _append_log(job_id: str, entry: dict) -> None:
    async with SessionLocal() as s:
        job = await s.get(Job, job_id)
        if job is None:
            return
        log_list = list(job.reasoning_log or [])
        log_list.append({"ts": datetime.utcnow().isoformat(), **entry})
        job.reasoning_log = log_list
        await s.commit()


def _clean_summary(text: str) -> str:
    """Strip the JSON fenced block from the agent's final text -- it's already in the
    structured tables above. Keep only the prose rationale."""
    if not text:
        return ""
    cleaned = re.sub(r"```json\s*\{.*?\}\s*```", "", text, flags=re.DOTALL)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


def _summary_to_html(text: str) -> str:
    """Convert the cleaned agent rationale (lightweight markdown) into safe HTML
    for the report template. Handles ### headings, **bold**, lists, and paragraphs.
    """
    if not text:
        return ""
    import html as _html
    lines = text.splitlines()
    out: list[str] = []
    in_list = False
    paragraph: list[str] = []

    def flush_para():
        nonlocal paragraph
        if paragraph:
            joined = " ".join(p.strip() for p in paragraph if p.strip())
            if joined:
                out.append(f"<p>{_inline(joined)}</p>")
            paragraph = []

    def _inline(s: str) -> str:
        s = _html.escape(s)
        s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*\n]+?)\*(?!\*)", r"<em>\1</em>", s)
        s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
        return s

    for raw in lines:
        line = raw.rstrip()
        # heading
        m = re.match(r"^#{1,6}\s+(.+)$", line)
        if m:
            if in_list:
                out.append("</ul>"); in_list = False
            flush_para()
            out.append(f"<h3>{_inline(m.group(1))}</h3>")
            continue
        # bullet
        m = re.match(r"^[-*]\s+(.+)$", line)
        if m:
            flush_para()
            if not in_list:
                out.append("<ul style='margin: 0.4em 0 0.6em 1.2em; padding: 0; list-style: disc;'>")
                in_list = True
            out.append(f"<li style='margin: 0.2em 0;'>{_inline(m.group(1))}</li>")
            continue
        # blank line -> end paragraph / list
        if not line.strip():
            if in_list:
                out.append("</ul>"); in_list = False
            flush_para()
            continue
        # accumulate paragraph text
        paragraph.append(line)

    if in_list:
        out.append("</ul>")
    flush_para()
    return "\n".join(out)


def _extract_json_block(text: str) -> Optional[dict]:
    """Pull the JSON object out of the agent's final summary."""
    if not text:
        return None
    # Try fenced ```json block first
    m = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL)
    if not m:
        # Fall back to first {...} that parses
        m = re.search(r"(\{.*\})", text, re.DOTALL)
    if not m:
        return None
    candidate = m.group(1)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


async def _persist_structured(job_id: str, parsed: dict, pdb_path_hint: str | None) -> None:
    async with SessionLocal() as s:
        job = await s.get(Job, job_id)
        if not job:
            return
        target_data = parsed.get("target") or {}
        structure_data = parsed.get("structure") or {}
        candidates = parsed.get("candidates") or []

        if target_data.get("uniprot_id"):
            t = Target(
                job_id=job_id,
                uniprot_id=target_data.get("uniprot_id", ""),
                protein_name=target_data.get("protein_name", ""),
                druggability_score=target_data.get("druggability_score"),
                rationale=target_data.get("rationale"),
                selected=True,
            )
            s.add(t)
            await s.flush()

            pdb_path = structure_data.get("pdb_path") or pdb_path_hint or ""
            if pdb_path:
                struct = Structure(
                    target_id=t.id,
                    pdb_path=pdb_path,
                    source=structure_data.get("source", "unknown"),
                    quality_score=structure_data.get("quality_score"),
                    pocket_data={"center": structure_data.get("pocket_center")},
                )
                s.add(struct)
                await s.flush()

                ranked = sorted(candidates, key=lambda c: c.get("binding_affinity", 0))
                for rank, c in enumerate(ranked, start=1):
                    s.add(DockingResult(
                        structure_id=struct.id,
                        molecule_smiles=c.get("smiles", ""),
                        molecule_name=c.get("name"),
                        binding_affinity=float(c.get("binding_affinity") or 0.0),
                        rank=rank,
                        lipinski_pass=c.get("lipinski_pass"),
                        toxicity_score=c.get("toxicity_score"),
                        absorption_score=c.get("absorption_score"),
                        synthesis_score=c.get("synthesis_score"),
                        is_approved_drug=bool(c.get("is_approved")),
                    ))
        await s.commit()


def _find_pdb_path_in_log(log_entries: list[dict]) -> str | None:
    for e in log_entries:
        if e.get("type") == "tool_result" and e.get("name") == "fetch_structure":
            summary = e.get("summary", "")
            m = re.search(r'"pdb_path":\s*"([^"]+)"', summary)
            if m:
                return m.group(1)
    return None


async def _build_memory_note(disease: str) -> str | None:
    """Read what the harness already knows about this disease class."""
    cached = await memory.get(SCOPE, memory.disease_key(disease))
    if not cached:
        return None
    v = cached["value"]
    target_uniprot = v.get("target_uniprot")
    target_name = v.get("target_name")
    structure_pdb = v.get("structure_pdb")
    pocket_center = v.get("pocket_center")
    approved_hits = v.get("approved_hits") or []
    bits = [
        f"On a previous run for this disease class on {cached['created_at'][:10]}, you chose:",
        f"- target: {target_uniprot} ({target_name})" if target_uniprot else None,
        f"- structure: PDB {structure_pdb}" if structure_pdb else None,
        f"- pocket_center: {pocket_center}" if pocket_center else None,
    ]
    if approved_hits:
        bits.append(f"- top approved hits: {', '.join(h.get('name') or h.get('chembl_id') or '?' for h in approved_hits[:5])}")
    bits.append("Reuse these if they still look right; revisit if you have a better idea.")
    return "\n".join(b for b in bits if b)


async def _persist_memory_for(job_id: str, disease: str) -> None:
    """After a successful run, cache target+structure+top approved drugs."""
    async with SessionLocal() as s:
        stmt = select(Job).where(Job.id == job_id).options(
            selectinload(Job.targets)
            .selectinload(Target.structures)
            .selectinload(Structure.docking_results)
        )
        res = await s.execute(stmt)
        job = res.scalar_one_or_none()
        if not job or not job.targets:
            return
        t = job.targets[0]
        st = t.structures[0] if t.structures else None
        approved = [
            {
                "rank": d.rank, "smiles": d.molecule_smiles, "name": d.molecule_name,
                "affinity": d.binding_affinity,
            }
            for d in (sorted(st.docking_results, key=lambda x: x.rank) if st else [])
            if d.is_approved_drug
        ][:5]
    payload = {
        "target_uniprot": t.uniprot_id,
        "target_name": t.protein_name,
        "structure_pdb": (st.pdb_path.split("\\")[-1].split("/")[-1].split("_")[0].split(".")[0]) if st else None,
        "structure_source": st.source if st else None,
        "pocket_center": (st.pocket_data or {}).get("center") if st else None,
        "approved_hits": approved,
        "last_job_id": job_id,
    }
    await memory.put(SCOPE, memory.disease_key(disease), payload, ttl=memory.TTL_TARGET_PICK)
    if t.uniprot_id:
        await memory.put(SCOPE, memory.uniprot_key(t.uniprot_id),
                         {"name": t.protein_name, "structure_pdb": payload["structure_pdb"]},
                         ttl=memory.TTL_STRUCTURE)


async def run_pipeline(job_id: str, disease: str) -> None:
    log.info("starting job %s for %s", job_id, disease)
    async with SessionLocal() as s:
        job = await s.get(Job, job_id)
        if job is None:
            return
        job.status = "running"
        await s.commit()

    await bus.publish(job_id, {"type": "status", "status": "running", "ts": datetime.utcnow().isoformat()})

    memory_note = await _build_memory_note(disease)
    if memory_note:
        await bus.publish(job_id, {"type": "memory_recall", "note": memory_note,
                                   "ts": datetime.utcnow().isoformat()})

    async def on_event(evt: dict) -> None:
        evt_full = {"ts": datetime.utcnow().isoformat(), **evt}
        await bus.publish(job_id, evt_full)
        await _append_log(job_id, evt)

    try:
        result = await run_agent(disease, on_event=on_event, memory_note=memory_note)
        final_text = result.get("final_text", "")

        async with SessionLocal() as s:
            job = await s.get(Job, job_id)
            log_entries = list(job.reasoning_log or []) if job else []
        pdb_hint = _find_pdb_path_in_log(log_entries)

        parsed = _extract_json_block(final_text)
        if parsed:
            await _persist_structured(job_id, parsed, pdb_hint)
            await bus.publish(job_id, {"type": "structured_result", "data": parsed,
                                       "ts": datetime.utcnow().isoformat()})

        # Render HTML report from structured data (eager-load to avoid async lazy-load)
        async with SessionLocal() as s:
            stmt = select(Job).where(Job.id == job_id).options(
                selectinload(Job.targets)
                .selectinload(Target.structures)
                .selectinload(Structure.docking_results)
            )
            res = await s.execute(stmt)
            job = res.scalar_one_or_none()
            target = None
            structure = None
            candidates_rows: list[dict] = []
            if job and job.targets:
                t = job.targets[0]
                target = {
                    "uniprot_id": t.uniprot_id,
                    "protein_name": t.protein_name,
                    "druggability_score": t.druggability_score,
                    "rationale": t.rationale,
                }
                if t.structures:
                    st = t.structures[0]
                    structure = {
                        "pdb_path": st.pdb_path,
                        "source": st.source,
                        "quality_score": st.quality_score,
                    }
                    for d in sorted(st.docking_results, key=lambda x: x.rank):
                        candidates_rows.append({
                            "rank": d.rank,
                            "molecule_smiles": d.molecule_smiles,
                            "molecule_name": d.molecule_name,
                            "binding_affinity": d.binding_affinity,
                            "lipinski_pass": d.lipinski_pass,
                            "toxicity_score": d.toxicity_score,
                            "absorption_score": d.absorption_score,
                            "synthesis_score": d.synthesis_score,
                            "is_approved_drug": d.is_approved_drug,
                        })
            context = {
                "job_id": job_id,
                "disease": disease,
                "generated_at": datetime.utcnow().isoformat(),
                "target": target,
                "structure": structure,
                "candidates": candidates_rows,
                "approved_candidates": [c for c in candidates_rows if c["is_approved_drug"]],
                "novel_candidates": [c for c in candidates_rows if not c["is_approved_drug"]],
                "summary_text": _clean_summary(final_text),
                "summary_html": _summary_to_html(_clean_summary(final_text)),
                "confidence": (parsed or {}).get("confidence"),
                "limitations": (parsed or {}).get("limitations"),
                "tool_calls": result.get("tool_calls", []),
            }
            report_path = render_report(job_id, context)
        # Mark complete in a fresh session
        async with SessionLocal() as s:
            j = await s.get(Job, job_id)
            if j:
                j.status = "completed"
                j.progress = 100
                await s.commit()
        # Cache learnings for next run
        try:
            await _persist_memory_for(job_id, disease)
        except Exception:
            log.exception("memory persist failed (non-fatal)")
        log.info("job %s done -> %s", job_id, report_path)
        await bus.publish(job_id, {"type": "done", "report_path": report_path,
                                   "ts": datetime.utcnow().isoformat()})
    except Exception as e:
        log.exception("pipeline failed")
        async with SessionLocal() as s:
            job = await s.get(Job, job_id)
            if job:
                job.status = "failed"
                job.error = str(e)
                await s.commit()
        await bus.publish(job_id, {"type": "error", "error": str(e),
                                   "ts": datetime.utcnow().isoformat()})
