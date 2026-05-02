"""End-to-end eval: does the agent pick the canonical target for a known disease?

Each entry has a list of "acceptable" UniProt IDs — passing means the agent's
chosen target is one of them. We deliberately allow >1 per disease because most
real diseases have multiple valid drug targets (e.g. Alzheimer's has APP, PSEN1,
MAPT all defensible).

These targets are public, well-established disease–target relationships. They
are NOT hardcoded into the agent or its prompt. The agent must recover them
from UniProt + OpenTargets and reason about which to pick.
"""
from __future__ import annotations
import asyncio
import json
import time
import uuid
from dataclasses import dataclass, asdict

from .db import init_db, SessionLocal, Job, Target
from .workers.pipeline import run_pipeline
from sqlalchemy import select
from sqlalchemy.orm import selectinload


# Disease -> set of UniProt IDs that count as a correct pick
# Sources: OpenTargets max association score targets + clinical drug literature
KNOWN_TARGETS: dict[str, list[str]] = {
    "type 2 diabetes mellitus": ["P37231", "P14672", "Q92887", "Q9Y5Y9"],
    # PPARG (rosiglitazone), GLUT4, MRP2, SGLT2 (dapagliflozin)
    "non-small cell lung cancer": ["P00533", "P04626", "P15056", "P36888"],
    # EGFR, ERBB2/HER2, BRAF, FLT3
    "Alzheimer disease": ["P49768", "P05067", "P10636", "Q9NR96", "P49810"],
    # PSEN1, APP, MAPT, BACE1 (verubecestat), PSEN2
    "rheumatoid arthritis": ["P01375", "P05231", "P14784", "P40189", "P29597", "O60674"],
    # Legacy: TNF (adalimumab), IL6, IL2RB, IL6ST
    # Modern: TYK2 (deucravacitinib, 2022 approval), JAK2
    "Parkinson disease": ["P37840", "Q99497", "O60260", "P09936", "Q5S007", "Q9BXM7"],
    # Legacy: SNCA, PARK7/DJ-1, PRKN, UCHL1
    # Modern: LRRK2 (BIIB122 Phase 3), PINK1
    "chronic myeloid leukemia": ["P00519", "P11274", "P10721"],
    # ABL1 (imatinib), BCR, KIT
}

# HARD MODE — no clean "canonical" answer. Pass = picked target appears in a
# 2024–2026 review or active trial as plausible. Reviewed manually rather than
# allowlisted; results recorded in docs/notes/.
# These are deliberately diseases where literature is fragmented or
# ambiguous — closer to a real research scenario than the textbook diseases.
HARD_MODE_DISEASES: list[str] = [
    "idiopathic pulmonary fibrosis",
    "long COVID",
    "Friedreich ataxia",
    "amyotrophic lateral sclerosis",
]


@dataclass
class EvalResult:
    disease: str
    picked_uniprot: str | None
    picked_protein: str | None
    accepted_targets: list[str]
    pass_: bool
    duration_seconds: float
    error: str | None = None
    job_id: str | None = None


async def evaluate_one(disease: str, accepted: list[str]) -> EvalResult:
    job_id = uuid.uuid4().hex[:12]
    async with SessionLocal() as s:
        s.add(Job(id=job_id, disease_input=disease, status="pending"))
        await s.commit()

    t0 = time.monotonic()
    try:
        await run_pipeline(job_id, disease)
    except Exception as e:
        return EvalResult(
            disease=disease,
            picked_uniprot=None,
            picked_protein=None,
            accepted_targets=accepted,
            pass_=False,
            duration_seconds=round(time.monotonic() - t0, 1),
            error=str(e),
            job_id=job_id,
        )
    duration = round(time.monotonic() - t0, 1)

    async with SessionLocal() as s:
        stmt = select(Job).where(Job.id == job_id).options(selectinload(Job.targets))
        res = await s.execute(stmt)
        job = res.scalar_one_or_none()
        target = job.targets[0] if job and job.targets else None

    picked = target.uniprot_id if target else None
    # In hard mode (empty accepted list), we don't have a ground truth — record
    # the pick and mark as MANUAL_REVIEW (treated as None for pass count)
    if not accepted:
        passed = False  # neither pass nor fail; require manual review
    else:
        passed = bool(picked and picked in accepted)
    return EvalResult(
        disease=disease,
        picked_uniprot=picked,
        picked_protein=target.protein_name if target else None,
        accepted_targets=accepted,
        pass_=passed,
        duration_seconds=duration,
        job_id=job_id,
    )


async def run_eval(diseases: list[str] | None = None, hard: bool = False) -> dict:
    await init_db()
    if hard:
        # No allowlist — record what the agent picks for manual review
        targets = {d: [] for d in (diseases or HARD_MODE_DISEASES)}
    else:
        targets = {d: KNOWN_TARGETS[d] for d in (diseases or list(KNOWN_TARGETS))}

    results: list[EvalResult] = []
    overall_t0 = time.monotonic()
    for disease, accepted in targets.items():
        print(f"  evaluating: {disease}", flush=True)
        r = await evaluate_one(disease, accepted)
        results.append(r)
        status = "PASS" if r.pass_ else "FAIL"
        suffix = f" -> {r.picked_uniprot} ({r.picked_protein})" if r.picked_uniprot else f" -> ERROR: {r.error}"
        print(f"    {status}{suffix} [{r.duration_seconds}s]", flush=True)

    elapsed = round(time.monotonic() - overall_t0, 1)
    n_pass = sum(1 for r in results if r.pass_)
    return {
        "total": len(results),
        "passed": n_pass,
        "score": f"{n_pass}/{len(results)}",
        "elapsed_seconds": elapsed,
        "results": [asdict(r) for r in results],
    }


def print_summary(report: dict) -> None:
    print()
    print(f"  Score: {report['score']}  Time: {report['elapsed_seconds']}s")
    print()
    print("  | Disease                          | Picked   | Protein                            | Result |")
    print("  |----------------------------------|----------|------------------------------------|--------|")
    for r in report["results"]:
        d = r["disease"][:32].ljust(32)
        u = (r["picked_uniprot"] or "-").ljust(8)
        p = (r["picked_protein"] or "-")[:34].ljust(34)
        ok = "PASS" if r["pass_"] else "FAIL"
        print(f"  | {d} | {u} | {p} | {ok}   |")


if __name__ == "__main__":
    report = asyncio.run(run_eval())
    print_summary(report)
    with open("eval_report.json", "w") as f:
        json.dump(report, f, indent=2)
    raise SystemExit(0 if report["passed"] == report["total"] else 1)
