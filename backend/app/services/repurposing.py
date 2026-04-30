"""Drug repurposing — pull FDA-approved drugs from ChEMBL for fast-track screening.

Repurposing approved drugs is faster, cheaper, and lower-risk than novel discovery
because pharmacokinetics and toxicity are already characterized.
"""
import httpx

CHEMBL_BASE = "https://www.ebi.ac.uk/chembl/api/data"


async def fetch_approved_drugs(limit: int = 100) -> list[dict]:
    """Fetch FDA-approved (max_phase=4) small molecules from ChEMBL."""
    params = {
        "max_phase": 4,
        "molecule_type": "Small molecule",
        "limit": limit,
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{CHEMBL_BASE}/molecule.json", params=params)
        if r.status_code != 200:
            return []
        molecules = r.json().get("molecules", [])
    out = []
    for m in molecules:
        smi = (m.get("molecule_structures") or {}).get("canonical_smiles")
        if not smi:
            continue
        out.append({
            "chembl_id": m.get("molecule_chembl_id"),
            "name": m.get("pref_name"),
            "smiles": smi,
            "max_phase": m.get("max_phase"),
            "first_approval": m.get("first_approval"),
            "indication_class": m.get("indication_class"),
            "approved": True,
        })
    return out


async def fetch_approved_drugs_for_target(uniprot_id: str, limit: int = 30) -> list[dict]:
    """Approved drugs with measured activity against this target — strongest repurposing leads."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(f"{CHEMBL_BASE}/target/search.json", params={"q": uniprot_id, "limit": 3})
        if r.status_code != 200:
            return []
        targets = r.json().get("targets", [])
        if not targets:
            return []
        chembl_target = targets[0].get("target_chembl_id")

        # activities filtered to approved drugs (max_phase=4)
        r = await client.get(
            f"{CHEMBL_BASE}/activity.json",
            params={
                "target_chembl_id": chembl_target,
                "molecule_max_phase": 4,
                "limit": limit,
                "standard_type": "IC50",
                "format": "json",
            },
        )
        if r.status_code != 200:
            return []
        activities = r.json().get("activities", [])

    seen = set()
    out = []
    for a in activities:
        smi = a.get("canonical_smiles")
        cid = a.get("molecule_chembl_id")
        if not smi or cid in seen:
            continue
        seen.add(cid)
        out.append({
            "chembl_id": cid,
            "name": a.get("molecule_pref_name"),
            "smiles": smi,
            "ic50_nm": a.get("standard_value"),
            "approved": True,
        })
    return out
