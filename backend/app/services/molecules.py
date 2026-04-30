"""Molecule library + RDKit Lipinski filtering."""
import httpx
from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski

CHEMBL_TARGET = "https://www.ebi.ac.uk/chembl/api/data/target/search.json"
CHEMBL_MOLECULES = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"


async def fetch_chembl_molecules(uniprot_id: str, limit: int = 50) -> list[dict]:
    """Fetch ChEMBL bioactive molecules associated with a UniProt target."""
    async with httpx.AsyncClient(timeout=60) as client:
        # 1. Find ChEMBL target ID
        r = await client.get(CHEMBL_TARGET, params={"q": uniprot_id, "limit": 5})
        if r.status_code != 200:
            return []
        targets = r.json().get("targets", [])
        if not targets:
            return []
        chembl_target_id = targets[0].get("target_chembl_id")

        # 2. Fetch molecules (simple query — for production use activity endpoint)
        r = await client.get(
            "https://www.ebi.ac.uk/chembl/api/data/activity.json",
            params={"target_chembl_id": chembl_target_id, "limit": limit, "standard_type": "IC50"},
        )
        if r.status_code != 200:
            return []
        activities = r.json().get("activities", [])
        out = []
        seen = set()
        for a in activities:
            smi = a.get("canonical_smiles")
            cid = a.get("molecule_chembl_id")
            if not smi or cid in seen:
                continue
            seen.add(cid)
            out.append({
                "chembl_id": cid,
                "smiles": smi,
                "ic50_nm": a.get("standard_value"),
            })
        return out


def lipinski_check(smiles: str) -> dict:
    """Apply Lipinski's Rule of Five."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"valid": False, "pass": False, "violations": ["invalid SMILES"]}
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Lipinski.NumHDonors(mol)
    hba = Lipinski.NumHAcceptors(mol)
    violations = []
    if mw > 500: violations.append(f"MW={mw:.1f}>500")
    if logp > 5: violations.append(f"LogP={logp:.2f}>5")
    if hbd > 5: violations.append(f"HBD={hbd}>5")
    if hba > 10: violations.append(f"HBA={hba}>10")
    return {
        "valid": True,
        "pass": len(violations) <= 1,
        "mw": mw, "logp": logp, "hbd": hbd, "hba": hba,
        "violations": violations,
    }
