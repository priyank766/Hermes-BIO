import httpx

OT_GRAPHQL = "https://api.platform.opentargets.org/api/v4/graphql"

DISEASE_TARGETS_QUERY = """
query DiseaseTargets($efoId: String!, $size: Int!) {
  disease(efoId: $efoId) {
    id
    name
    associatedTargets(page: {index: 0, size: $size}) {
      rows {
        target { id approvedSymbol approvedName proteinIds { id source } }
        score
      }
    }
  }
}
"""

DISEASE_SEARCH_QUERY = """
query SearchDisease($q: String!) {
  search(queryString: $q, entityNames: ["disease"], page: {index: 0, size: 1}) {
    hits { id name entity }
  }
}
"""


async def find_efo_id(disease: str) -> str | None:
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(OT_GRAPHQL, json={"query": DISEASE_SEARCH_QUERY, "variables": {"q": disease}})
        r.raise_for_status()
        hits = r.json().get("data", {}).get("search", {}).get("hits", [])
        for h in hits:
            if h.get("entity") == "disease":
                return h.get("id")
    return None


async def get_validated_targets(disease: str, size: int = 15) -> list[dict]:
    efo = await find_efo_id(disease)
    if not efo:
        return []
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            OT_GRAPHQL,
            json={"query": DISEASE_TARGETS_QUERY, "variables": {"efoId": efo, "size": size}},
        )
        r.raise_for_status()
        data = r.json().get("data", {}).get("disease") or {}
    rows = data.get("associatedTargets", {}).get("rows", [])
    out = []
    for row in rows:
        t = row.get("target", {})
        uniprot = next(
            (p["id"] for p in t.get("proteinIds", []) if p.get("source") == "uniprot_swissprot"),
            None,
        )
        out.append({
            "ensembl_id": t.get("id"),
            "symbol": t.get("approvedSymbol"),
            "name": t.get("approvedName"),
            "uniprot_id": uniprot,
            "association_score": row.get("score"),
        })
    return out
