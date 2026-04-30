"""AutoDock Vina docking — stub. Wire `vina` Python package when installed."""
import random
from rdkit import Chem
from rdkit.Chem import Descriptors


def dock_molecule(pdb_path: str, pocket_center: list[float], smiles: str) -> dict:
    """Dock a single molecule. Stub returns a heuristic affinity for development."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"smiles": smiles, "affinity": 0.0, "error": "invalid SMILES"}
    # Heuristic: bigger lipophilic molecules tend toward stronger affinity (very rough)
    logp = Descriptors.MolLogP(mol)
    mw = Descriptors.MolWt(mol)
    base = -4.0 - 0.4 * logp - 0.005 * mw
    affinity = round(base + random.uniform(-1.5, 1.5), 2)
    return {"smiles": smiles, "affinity": affinity, "stub": True}


def dock_batch(pdb_path: str, pocket_center: list[float], smiles_list: list[str]) -> list[dict]:
    return [dock_molecule(pdb_path, pocket_center, smi) for smi in smiles_list]
