import httpx
from pathlib import Path
from ..config import settings

ALPHAFOLD_API = "https://alphafold.ebi.ac.uk/api/prediction/{uniprot_id}"
PDB_SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"


async def fetch_alphafold(uniprot_id: str) -> dict | None:
    """Returns dict with pdb_path and quality (mean pLDDT) or None."""
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.get(ALPHAFOLD_API.format(uniprot_id=uniprot_id))
        if r.status_code != 200:
            return None
        entries = r.json()
        if not entries:
            return None
        entry = entries[0]
        pdb_url = entry.get("pdbUrl")
        if not pdb_url:
            return None
        pdb_data = (await client.get(pdb_url)).text
        out_path = settings.structures_dir / f"{uniprot_id}_AF.pdb"
        out_path.write_text(pdb_data)
        return {
            "pdb_path": str(out_path),
            "source": "AlphaFold",
            "quality_score": entry.get("globalMetricValue") or entry.get("confidenceScore"),
            "uniprot_id": uniprot_id,
        }


async def fetch_pdb_for_uniprot(uniprot_id: str) -> dict | None:
    """Search RCSB PDB for an experimental structure of this UniProt entry."""
    query = {
        "query": {
            "type": "terminal",
            "service": "text",
            "parameters": {
                "attribute": "rcsb_polymer_entity_container_identifiers.reference_sequence_identifiers.database_accession",
                "operator": "exact_match",
                "value": uniprot_id,
            },
        },
        "return_type": "entry",
        "request_options": {"paginate": {"start": 0, "rows": 1}},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(PDB_SEARCH, json=query)
        if r.status_code != 200:
            return None
        results = r.json().get("result_set", [])
        if not results:
            return None
        pdb_id = results[0]["identifier"]
        pdb_data = (await client.get(f"https://files.rcsb.org/download/{pdb_id}.pdb")).text
        out_path = settings.structures_dir / f"{pdb_id}.pdb"
        out_path.write_text(pdb_data)
        return {
            "pdb_path": str(out_path),
            "source": "PDB",
            "quality_score": None,
            "pdb_id": pdb_id,
            "uniprot_id": uniprot_id,
        }
