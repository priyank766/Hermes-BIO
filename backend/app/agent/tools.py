"""Tool dispatcher for the Gemini agent. Each tool wraps a service call."""
from ..services import uniprot, opentargets, structures, pockets, molecules, docking, admet, repurposing, synthesis


async def search_uniprot(disease: str, limit: int = 10) -> dict:
    return {"proteins": await uniprot.search_disease_proteins(disease, limit)}


async def search_opentargets(disease: str, size: int = 15) -> dict:
    return {"targets": await opentargets.get_validated_targets(disease, size)}


async def fetch_structure(uniprot_id: str, prefer: str = "pdb") -> dict:
    if prefer == "pdb":
        s = await structures.fetch_pdb_for_uniprot(uniprot_id)
        if s:
            return s
    s = await structures.fetch_alphafold(uniprot_id)
    return s or {"error": f"no structure available for {uniprot_id}"}


async def detect_binding_pockets(pdb_path: str) -> dict:
    return {"pockets": pockets.detect_pockets(pdb_path)}


async def fetch_chembl_library(uniprot_id: str, limit: int = 50) -> dict:
    return {"molecules": await molecules.fetch_chembl_molecules(uniprot_id, limit)}


async def fetch_approved_drugs_for_target(uniprot_id: str, limit: int = 30) -> dict:
    """Repurposing: FDA-approved drugs with measured activity against this target."""
    return {"drugs": await repurposing.fetch_approved_drugs_for_target(uniprot_id, limit)}


async def screen_lipinski(smiles_list: list[str]) -> dict:
    return {"results": [{"smiles": s, **molecules.lipinski_check(s)} for s in smiles_list]}


async def run_docking(pdb_path: str, pocket_center: list[float], smiles_list: list[str]) -> dict:
    return {"results": docking.dock_batch(pdb_path, pocket_center, smiles_list)}


async def predict_admet_batch(smiles_list: list[str]) -> dict:
    return {"results": [{"smiles": s, **admet.predict_admet(s)} for s in smiles_list]}


async def score_synthesizability(smiles_list: list[str]) -> dict:
    """SAScore (Ertl & Schuffenhauer 2009): 1.0 easy → 10.0 hard. A high-affinity hit
    that is unsynthesizable is useless; this is a key filter most pipelines skip."""
    return {"results": [{"smiles": s, **synthesis.sa_score(s)} for s in smiles_list]}


# ---- Function declarations for Gemini ----
TOOL_DECLARATIONS = [
    {
        "name": "search_uniprot",
        "description": "Search UniProt for human proteins associated with a disease.",
        "parameters": {
            "type": "object",
            "properties": {
                "disease": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["disease"],
        },
    },
    {
        "name": "search_opentargets",
        "description": "Get validated drug targets for a disease from OpenTargets with association scores.",
        "parameters": {
            "type": "object",
            "properties": {
                "disease": {"type": "string"},
                "size": {"type": "integer"},
            },
            "required": ["disease"],
        },
    },
    {
        "name": "fetch_structure",
        "description": "Fetch a 3D structure for a UniProt ID. Tries PDB first, falls back to AlphaFold.",
        "parameters": {
            "type": "object",
            "properties": {
                "uniprot_id": {"type": "string"},
                "prefer": {"type": "string", "enum": ["pdb", "alphafold"]},
            },
            "required": ["uniprot_id"],
        },
    },
    {
        "name": "detect_binding_pockets",
        "description": "Detect candidate binding pockets on a PDB structure file.",
        "parameters": {
            "type": "object",
            "properties": {"pdb_path": {"type": "string"}},
            "required": ["pdb_path"],
        },
    },
    {
        "name": "fetch_approved_drugs_for_target",
        "description": "REPURPOSING-FIRST. Fetch FDA-approved drugs (max_phase=4) with measured activity against this UniProt target. Always try these BEFORE novel ChEMBL screens — approved drugs already have characterized PK/toxicity, so a hit here is a fast-track candidate.",
        "parameters": {
            "type": "object",
            "properties": {
                "uniprot_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["uniprot_id"],
        },
    },
    {
        "name": "fetch_chembl_library",
        "description": "Fetch the broader bioactive molecule library from ChEMBL for a UniProt target. Use AFTER fetch_approved_drugs_for_target if more diversity is needed.",
        "parameters": {
            "type": "object",
            "properties": {
                "uniprot_id": {"type": "string"},
                "limit": {"type": "integer"},
            },
            "required": ["uniprot_id"],
        },
    },
    {
        "name": "screen_lipinski",
        "description": "Apply Lipinski's Rule of Five to a list of SMILES.",
        "parameters": {
            "type": "object",
            "properties": {
                "smiles_list": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["smiles_list"],
        },
    },
    {
        "name": "run_docking",
        "description": "Run molecular docking (AutoDock Vina) of SMILES into a binding pocket.",
        "parameters": {
            "type": "object",
            "properties": {
                "pdb_path": {"type": "string"},
                "pocket_center": {"type": "array", "items": {"type": "number"}},
                "smiles_list": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["pdb_path", "pocket_center", "smiles_list"],
        },
    },
    {
        "name": "predict_admet_batch",
        "description": "Predict ADMET properties (absorption, toxicity) for SMILES.",
        "parameters": {
            "type": "object",
            "properties": {
                "smiles_list": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["smiles_list"],
        },
    },
    {
        "name": "score_synthesizability",
        "description": "Compute SAScore (Ertl & Schuffenhauer): 1.0=easy, 10.0=very hard. A high-affinity hit that cannot be synthesized is worthless. Run on top binders.",
        "parameters": {
            "type": "object",
            "properties": {
                "smiles_list": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["smiles_list"],
        },
    },
]

DISPATCH = {
    "search_uniprot": search_uniprot,
    "search_opentargets": search_opentargets,
    "fetch_structure": fetch_structure,
    "detect_binding_pockets": detect_binding_pockets,
    "fetch_approved_drugs_for_target": fetch_approved_drugs_for_target,
    "fetch_chembl_library": fetch_chembl_library,
    "screen_lipinski": screen_lipinski,
    "run_docking": run_docking,
    "predict_admet_batch": predict_admet_batch,
    "score_synthesizability": score_synthesizability,
}
