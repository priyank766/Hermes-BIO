"""Binding pocket detection. Stub implementation — wire fpocket/P2Rank when installed."""
from pathlib import Path


def detect_pockets(pdb_path: str) -> list[dict]:
    """Return list of candidate pockets. Each dict: id, score, volume, residues, center."""
    # Placeholder: derive a single naive pocket from the structure's centroid.
    # Replace with `fpocket` CLI invocation: subprocess.run(["fpocket", "-f", pdb_path]).
    p = Path(pdb_path)
    if not p.exists():
        return []
    coords = []
    for line in p.read_text().splitlines():
        if line.startswith("ATOM") and line[12:16].strip() == "CA":
            try:
                coords.append((float(line[30:38]), float(line[38:46]), float(line[46:54])))
            except ValueError:
                continue
    if not coords:
        return []
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    cz = sum(c[2] for c in coords) / len(coords)
    return [{
        "id": "pocket_1",
        "score": 0.5,
        "volume": 500.0,
        "center": [cx, cy, cz],
        "residues": [],
        "note": "stub — install fpocket/P2Rank for real detection",
    }]
