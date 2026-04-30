import httpx

UNIPROT_SEARCH = "https://rest.uniprot.org/uniprotkb/search"


async def search_disease_proteins(disease: str, limit: int = 10) -> list[dict]:
    """Query UniProt for reviewed human proteins associated with a disease."""
    # UniProt accepts free-text in query; cc_disease restricts to disease annotations
    safe = disease.replace('"', "")
    query = f'(cc_disease:"{safe}") AND (organism_id:9606) AND (reviewed:true)'
    params = {
        "query": query,
        "format": "json",
        "size": limit,
        "fields": "accession,id,protein_name,gene_names,cc_disease,length",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(UNIPROT_SEARCH, params=params)
        r.raise_for_status()
        data = r.json()
    results = []
    for entry in data.get("results", []):
        protein_name = (
            entry.get("proteinDescription", {})
            .get("recommendedName", {})
            .get("fullName", {})
            .get("value", "")
        )
        genes = [g.get("geneName", {}).get("value") for g in entry.get("genes", []) if g.get("geneName")]
        results.append({
            "uniprot_id": entry.get("primaryAccession"),
            "name": entry.get("uniProtkbId"),
            "protein_name": protein_name,
            "genes": [g for g in genes if g],
            "length": entry.get("sequence", {}).get("length"),
        })
    return results
