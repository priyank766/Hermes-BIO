"""Synthesizability score (SAScore — Ertl & Schuffenhauer 2009).

RDKit ships sascorer.py in Contrib/SA_Score. We try to import it; if unavailable,
fall back to a heuristic based on ring complexity, stereocenters and heavy-atom count.
Score scale: 1.0 (very easy to synthesize) → 10.0 (very hard).
"""
from rdkit import Chem
from rdkit.Chem import Descriptors, rdMolDescriptors

try:
    from rdkit.Chem import RDConfig
    import sys, os
    sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
    import sascorer  # type: ignore
    _HAVE_SASCORER = True
except Exception:
    _HAVE_SASCORER = False


def _heuristic(mol) -> float:
    """Rough proxy: penalize stereo, fused rings, large size, exotic atoms."""
    if mol is None:
        return 10.0
    heavy = mol.GetNumHeavyAtoms()
    rings = rdMolDescriptors.CalcNumRings(mol)
    aromatic = rdMolDescriptors.CalcNumAromaticRings(mol)
    stereo = sum(1 for a in mol.GetAtoms() if a.GetChiralTag() != Chem.ChiralType.CHI_UNSPECIFIED)
    spiro = rdMolDescriptors.CalcNumSpiroAtoms(mol)
    bridgehead = rdMolDescriptors.CalcNumBridgeheadAtoms(mol)
    score = 1.5 + 0.04 * heavy + 0.3 * stereo + 0.4 * spiro + 0.5 * bridgehead + 0.1 * (rings - aromatic)
    return float(min(10.0, max(1.0, score)))


def sa_score(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {"valid": False, "score": None, "label": "invalid"}
    if _HAVE_SASCORER:
        try:
            score = float(sascorer.calculateScore(mol))
        except Exception:
            score = _heuristic(mol)
    else:
        score = _heuristic(mol)
    if score < 3.5:
        label = "easy"
    elif score < 6:
        label = "moderate"
    else:
        label = "hard"
    return {
        "valid": True,
        "score": round(score, 2),
        "label": label,
        "method": "ertl-schuffenhauer" if _HAVE_SASCORER else "heuristic",
    }
