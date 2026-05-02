export type ReasoningEvent = {
  ts: string;
  type: "status" | "reasoning" | "tool_call" | "tool_result" | "retry" | "done" | "error" | "structured_result" | "memory_recall";
  note?: string;
  iteration?: number;
  text?: string;
  name?: string;
  args?: Record<string, unknown>;
  summary?: string;
  status?: string;
  error?: string;
  delay?: number;
  code?: number;
  data?: unknown;
};

export type Candidate = {
  rank: number;
  smiles: string;
  name: string | null;
  binding_affinity: number;
  lipinski_pass: boolean | null;
  toxicity_score: number | null;
  absorption_score: number | null;
  synthesis_score: number | null;
  is_approved_drug: boolean;
};

export type CandidatesPayload = {
  job_id: string;
  target: {
    uniprot_id: string;
    protein_name: string;
    druggability_score: number | null;
    rationale: string | null;
  } | null;
  structure: {
    pdb_path: string;
    source: string;
    quality_score: number | null;
    pocket_center: number[] | null;
  } | null;
  candidates: Candidate[];
};

export type Job = {
  job_id: string;
  disease: string;
  status: "pending" | "running" | "completed" | "failed";
  progress: number;
  current_step: number;
  error: string | null;
  reasoning_log: ReasoningEvent[];
};
