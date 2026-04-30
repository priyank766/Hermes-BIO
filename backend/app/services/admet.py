"""ADMET prediction stub. Replace with ADMETlab2/pkCSM API or local model."""
from rdkit import Chem
from rdkit.Chem import Descriptors, Crippen


def predict_admet(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"valid": False}
    logp = Crippen.MolLogP(mol)
    tpsa = Descriptors.TPSA(mol)
    # crude proxies
    absorption_score = max(0.0, min(1.0, 1.0 - abs(logp - 2.5) / 5.0))
    toxicity_score = min(1.0, 0.1 + max(0, logp - 5) * 0.2)  # higher = more toxic
    return {
        "valid": True,
        "logp": logp,
        "tpsa": tpsa,
        "absorption_score": round(absorption_score, 3),
        "toxicity_score": round(toxicity_score, 3),
        "stub": True,
    }
