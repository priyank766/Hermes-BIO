"""Cross-disease repurposing: for a target T, find FDA-approved drugs whose
PRIMARY indication is something other than the disease class associated with
T, but which have measured activity on T.

Real repurposing wins (metformin→cancer, sildenafil→PH) come from this exact
pattern: a drug already de-risked for one disease shows mechanistic
relevance to another.

Data plumbing:
  1. UniProt -> ChEMBL target ID
  2. activity.json -> approved drugs (max_phase=4) with measured potency
  3. molecule.json -> pref_name + synonyms
  4. drug_indication.json -> structured indication list (EFO + MeSH)
"""
from __future__ import annotations
import asyncio
import httpx

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"


async def _resolve_target(client: httpx.AsyncClient, uniprot_id: str) -> str | None:
    r = await client.get(f"{CHEMBL_BASE}/target/search.json", params={"q": uniprot_id, "limit": 3})
    if r.status_code != 200:
        return None
    targets = r.json().get("targets", [])
    return targets[0].get("target_chembl_id") if targets else None


async def _fetch_approved_binders(client: httpx.AsyncClient, chembl_target: str) -> dict[str, dict]:
    """All approved drugs with measured activity on this target. De-dup keeping best potency."""
    r = await client.get(
        f"{CHEMBL_BASE}/activity.json",
        params={
            "target_chembl_id": chembl_target,
            "molecule_max_phase": 4,
            "limit": 200,
            "standard_type__in": "IC50,Ki,Kd",
            "format": "json",
        },
    )
    if r.status_code != 200:
        return {}
    activities = r.json().get("activities", [])
    best: dict[str, dict] = {}
    for a in activities:
        mid = a.get("molecule_chembl_id")
        if not mid:
            continue
        try:
            potency = float(a.get("standard_value") or 1e9)
        except (TypeError, ValueError):
            continue
        if mid not in best or potency < best[mid]["potency_nm"]:
            best[mid] = {
                "chembl_id": mid,
                "name": a.get("molecule_pref_name"),
                "smiles": a.get("canonical_smiles"),
                "potency_nm": potency,
                "potency_type": a.get("standard_type"),
            }
    return best


async def _fetch_indications(client: httpx.AsyncClient, mid: str) -> list[dict]:
    """ChEMBL drug_indication endpoint — structured indications per drug."""
    r = await client.get(
        f"{CHEMBL_BASE}/drug_indication.json",
        params={"molecule_chembl_id": mid, "limit": 50, "format": "json"},
    )
    if r.status_code != 200:
        return []
    rows = r.json().get("drug_indications", [])
    return [
        {
            "mesh_heading": ind.get("mesh_heading"),
            "efo_term": ind.get("efo_term"),
            "max_phase_for_ind": ind.get("max_phase_for_ind"),
        }
        for ind in rows
    ]


async def _fetch_pref_name(client: httpx.AsyncClient, mid: str) -> str | None:
    r = await client.get(f"{CHEMBL_BASE}/molecule/{mid}.json")
    if r.status_code != 200:
        return None
    return r.json().get("pref_name")


async def cross_indication_candidates(
    uniprot_id: str,
    exclude_disease_keywords: list[str] | None = None,
    top_potency: int = 40,
) -> list[dict]:
    """Returns approved binders enriched with indications and an
    is_cross_indication flag (= drug has at least one approved indication NOT
    matching any keyword in exclude_disease_keywords).

    `top_potency` limits how many of the strongest binders we hit the indication
    endpoint for (1 extra HTTP call each), to keep latency reasonable.
    """
    excludes = [k.lower() for k in (exclude_disease_keywords or [])]
    async with httpx.AsyncClient(timeout=60) as client:
        chembl_target = await _resolve_target(client, uniprot_id)
        if not chembl_target:
            return []
        binders = await _fetch_approved_binders(client, chembl_target)
        if not binders:
            return []

        # Sort by potency, take top N for indication enrichment
        sorted_ids = sorted(binders.keys(), key=lambda i: binders[i]["potency_nm"])[:top_potency]

        async def enrich(mid: str) -> dict:
            row = binders[mid]
            indications, pref = await asyncio.gather(
                _fetch_indications(client, mid),
                _fetch_pref_name(client, mid) if not row.get("name") else asyncio.sleep(0, result=row.get("name")),
            )
            row["name"] = row.get("name") or pref or mid
            row["indications"] = indications

            # Determine cross-indication: at least one indication does NOT match
            # any exclude keyword
            ind_strs = [
                f"{i.get('mesh_heading') or ''} {i.get('efo_term') or ''}".lower()
                for i in indications
            ]
            row["all_indications_summary"] = "; ".join(
                sorted({i.get("mesh_heading") for i in indications if i.get("mesh_heading")})
            ) or "—"
            cross = []
            for s in ind_strs:
                if not s.strip():
                    continue
                if not excludes or not any(k in s for k in excludes):
                    cross.append(s)
            row["is_cross_indication"] = bool(cross) and bool(indications)
            row["non_excluded_indications"] = cross
            return row

        enriched = await asyncio.gather(*(enrich(mid) for mid in sorted_ids))
    enriched.sort(key=lambda r: r["potency_nm"])
    return enriched
