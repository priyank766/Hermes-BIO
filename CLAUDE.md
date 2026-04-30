Here's the complete brief you can hand off to another Claude agent:

---

## Drug Candidate Discovery Pipeline — Full Build Spec

### What We're Building

An end-to-end agentic AI system where a user inputs a disease name and gets back a ranked list of drug candidates with a full scientific report. The agent autonomously chains together bioinformatics tools, reasons about intermediate results, and adapts its strategy based on what it finds.

### Architecture

```
User Input (disease name)
        │
        ▼
┌─────────────────────┐
│  Agent Orchestrator  │  ← Claude API (reasoning + decision making)
│  (FastAPI backend)   │
└─────┬───────────────┘
      │
      ├──→ Step 1: Target Identification
      │     - Query UniProt API for proteins associated with disease
      │     - Query OpenTargets API for validated drug targets
      │     - Agent RANKS targets by druggability score
      │     - Output: target protein ID + justification
      │
      ├──→ Step 2: Structure Retrieval
      │     - Fetch 3D structure from PDB (if experimental structure exists)
      │     - If not → call AlphaFold DB API for predicted structure
      │     - Agent VALIDATES structure quality (pLDDT score check)
      │     - If quality too low → try homology modeling fallback
      │     - Output: .pdb file of target protein
      │
      ├──→ Step 3: Binding Site Detection
      │     - Use P2Rank or fpocket to detect binding pockets
      │     - Agent SELECTS the most promising pocket based on:
      │       volume, druggability score, proximity to known active sites
      │     - Output: pocket coordinates + residue list
      │
      ├──→ Step 4: Molecule Library Screening
      │     - Pull candidates from ZINC20 or ChEMBL (filtered subset)
      │     - Run molecular docking via AutoDock Vina
      │     - Agent decides batch size, timeout, and retry strategy
      │     - Output: ranked molecules by binding affinity (kcal/mol)
      │
      ├──→ Step 5: Filtering & Validation
      │     - Lipinski's Rule of 5 (druglikeness check)
      │     - ADMET prediction (absorption, toxicity) via ADMETlab or pkCSM
      │     - If top candidate fails toxicity → agent searches for structural analogs
      │     - Output: filtered candidate list with pass/fail flags
      │
      └──→ Step 6: Report Generation
            - Full PDF/HTML report with:
              • Disease background
              • Target protein rationale
              • 3D binding visualization (py3Dmol)
              • Ranked candidates table
              • ADMET profiles
              • Confidence scores + limitations
            - Output: downloadable report
```

### Tech Stack

| Component | Tool |
|---|---|
| Backend | FastAPI (Python) |
| Agent brain | Claude API with tool_use |
| Protein data | UniProt API, PDB API, AlphaFold DB API |
| Target validation | OpenTargets API |
| Binding pockets | P2Rank or fpocket |
| Docking | AutoDock Vina (via Python bindings `vina` package) |
| Molecule library | ZINC20 subset or ChEMBL API |
| Druglikeness | RDKit (Lipinski filters) |
| ADMET | ADMETlab2 API or pkCSM API |
| 3D visualization | py3Dmol (embedded in report) |
| Report | Jinja2 templates → HTML/PDF |
| Frontend | React + Tailwind (simple dashboard) |
| Deploy | Railway or Fly.io (backend) + Vercel (frontend) |

### Database / State

```
PostgreSQL (or SQLite for MVP):
  - jobs table: id, disease_input, status, created_at
  - targets table: job_id, uniprot_id, protein_name, druggability_score
  - structures table: target_id, pdb_path, source (PDB/AlphaFold), quality_score
  - docking_results table: structure_id, molecule_smiles, binding_affinity, rank
  - admet_results table: molecule_id, lipinski_pass, toxicity_score, absorption_score
  - reports table: job_id, report_path, generated_at
```

### What Makes It Agentic (Not Just a Pipeline)

The Claude agent makes real decisions at each step:

1. **Target selection** — if multiple proteins are linked to the disease, it reasons about which one is most druggable and explains why
2. **Structure fallback** — if PDB has no good structure, it tries AlphaFold; if AlphaFold quality is low, it flags this and adjusts confidence
3. **Docking retry** — if initial docking gives poor results (all affinities > -5 kcal/mol), it widens the molecule search or tries a different binding pocket
4. **Toxic candidate handling** — if the best binder is toxic, it doesn't just drop it; it searches for structural analogs with similar binding but better safety profiles
5. **Confidence scoring** — every output includes the agent's confidence and reasoning, not just raw numbers

### API Endpoints

```
POST /api/discover
  body: { "disease": "Alzheimer's" }
  returns: { "job_id": "abc123", "status": "started" }

GET /api/jobs/{job_id}
  returns: { "status": "docking", "progress": 65, "current_step": 4 }

GET /api/jobs/{job_id}/report
  returns: { "report_url": "/reports/abc123.html", "candidates": [...] }

GET /api/jobs/{job_id}/candidates
  returns: [{ "smiles": "...", "affinity": -8.2, "lipinski": true, "toxicity": "low" }]
```

### Frontend Pages

1. **Home** — input disease name, hit "Discover"
2. **Job tracker** — live progress bar showing which step the agent is on, with reasoning logs streaming in real-time
3. **Results** — interactive table of candidates, 3D protein viewer (py3Dmol), downloadable report

### MVP Scope (What to Build First)

**Week 1:**
- FastAPI skeleton with Claude tool_use agent loop
- UniProt + AlphaFold API integration (Steps 1-2)
- Basic binding pocket detection with fpocket
- SQLite for state

**Week 2:**
- AutoDock Vina docking with a small ZINC subset (~1000 molecules)
- RDKit Lipinski filtering
- HTML report generation with Jinja2
- Simple React frontend with job tracking

**Week 3:**
- ADMET predictions
- Analog search fallback logic
- py3Dmol 3D visualization in report
- Deploy to Railway + Vercel

### Key Python Packages

```
pip install fastapi uvicorn anthropic
pip install biopython          # UniProt/PDB parsing
pip install vina               # AutoDock Vina bindings
pip install rdkit              # Molecule analysis, Lipinski
pip install fpocket            # Binding pocket detection (or use P2Rank CLI)
pip install py3Dmol            # 3D visualization
pip install jinja2             # Report templates
pip install sqlalchemy         # Database ORM
pip install httpx              # Async API calls
```

---

Copy this entire thing and hand it to the other agent. It has everything needed to start building.