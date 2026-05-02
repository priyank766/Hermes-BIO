"""Underexplored-target finder.

For a disease, surface targets that look genuinely understudied:
  - high OpenTargets disease-association score (real biological evidence)
  - BUT few/no approved drugs against them (low max_phase in ChEMBL)
  - AND a structure exists or is predictable (otherwise no actionable next step)

Returns ranked candidates with a "why this is interesting" rationale that the
agent can summarize. The pitch to a researcher: "here are 3 proteins worth a
literature week."
"""
from __future__ import annotations
import asyncio
import httpx
from . import opentargets, structures

CHEMBL_TARGET = "https://www.ebi.ac.uk/chembl/api/data/target/search.json"
CHEMBL_MOLECULES = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"


async def _chembl_target_drug_stats(uniprot_id: str) -> dict:
    """How drugged is this target? Returns max_phase reached + count of bioactive compounds."""
    out = {"max_phase": 0, "compound_count": 0, "approved_count": 0, "chembl_target_id": None}
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            r = await client.get(CHEMBL_TARGET, params={"q": uniprot_id, "limit": 3})
            if r.status_code != 200:
                return out
            targets = r.json().get("targets", [])
            if not targets:
                return out
            chembl_id = targets[0].get("target_chembl_id")
            out["chembl_target_id"] = chembl_id
            if not chembl_id:
                return out

            # Count drugs at each phase that target this protein
            r = await client.get(
                CHEMBL_MOLECULES,
                params={"target_chembl_id": chembl_id, "limit": 200, "format": "json"},
            )
            if r.status_code != 200:
                return out
            mols = r.json().get("molecules", [])
            out["compound_count"] = len(mols)
            phases = [m.get("max_phase") or 0 for m in mols]
            out["max_phase"] = max(phases) if phases else 0
            out["approved_count"] = sum(1 for p in phases if p == 4)
        except Exception:
            pass
    return out


def _underexplored_score(target: dict, stats: dict, has_structure: bool) -> float:
    """Higher = more underexplored. We want strong genetic evidence × low drug
    development × actionable (has structure)."""
    assoc = target.get("association_score") or 0.0
    max_phase = stats.get("max_phase", 0)
    compound_count = stats.get("compound_count", 0)

    # Bigger genetic signal = better
    genetic = assoc

    # Less drug development = more underexplored.
    # max_phase 0–4: 0 best (untouched), 4 worst (already approved drug)
    drug_gap = max(0.0, 1.0 - (max_phase / 4.0))

    # Few compounds = not crowded. Saturate at 100.
    crowding_penalty = min(1.0, compound_count / 100.0)
    not_crowded = 1.0 - crowding_penalty

    # Must be actionable (has 3D structure)
    actionable = 1.0 if has_structure else 0.3

    return round(genetic * drug_gap * not_crowded * actionable, 4)


def _label(score: float, max_phase: int, count: int) -> str:
    if score > 0.4:
        return "highly underexplored"
    if score > 0.2:
        return "moderately underexplored"
    if max_phase == 4:
        return "well-drugged (approved compound exists)"
    if count > 100:
        return "crowded chemical space"
    return "low signal"


async def find_underexplored_targets(disease: str, top_n: int = 15) -> list[dict]:
    """Pull top OpenTargets associations, filter, score, sort."""
    targets = await opentargets.get_validated_targets(disease, size=top_n)
    if not targets:
        return []

    out: list[dict] = []
    # Run ChEMBL stats + structure checks concurrently
    async def enrich(t: dict) -> dict | None:
        u = t.get("uniprot_id")
        if not u:
            return None
        stats_task = asyncio.create_task(_chembl_target_drug_stats(u))
        # structure: just probe AlphaFold (always available for human proteins) or
        # PDB. Cheap "is there one?" check by trying alphafold metadata.
        struct_task = asyncio.create_task(_probe_structure(u))
        stats = await stats_task
        has_structure = await struct_task
        score = _underexplored_score(t, stats, has_structure)
        return {
            "uniprot_id": u,
            "symbol": t.get("symbol"),
            "name": t.get("name"),
            "association_score": t.get("association_score"),
            "max_phase_reached": stats["max_phase"],
            "compound_count": stats["compound_count"],
            "approved_count": stats["approved_count"],
            "has_structure": has_structure,
            "underexplored_score": score,
            "label": _label(score, stats["max_phase"], stats["compound_count"]),
        }

    enriched = await asyncio.gather(*(enrich(t) for t in targets))
    out = [e for e in enriched if e]
    out.sort(key=lambda x: x["underexplored_score"], reverse=True)
    return out


async def _probe_structure(uniprot_id: str) -> bool:
    """Cheap check — AlphaFold has predictions for ~all human SwissProt entries.
    Use GET because some endpoints don't support HEAD."""
    async with httpx.AsyncClient(timeout=15) as client:
        try:
            r = await client.get(
                f"https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}",
                follow_redirects=True,
            )
            if r.status_code != 200:
                return False
            data = r.json()
            return bool(data) and isinstance(data, list) and len(data) > 0
        except Exception:
            return False
