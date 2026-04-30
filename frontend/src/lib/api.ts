import type { CandidatesPayload, Job, ReasoningEvent } from "../types";

const API = "/api";

export async function startDiscovery(disease: string): Promise<{ job_id: string; status: string }> {
  const r = await fetch(`${API}/discover`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ disease }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function getJob(jobId: string): Promise<Job> {
  const r = await fetch(`${API}/jobs/${jobId}`);
  if (!r.ok) throw new Error(`job ${jobId}: ${r.status}`);
  return r.json();
}

export async function getCandidates(jobId: string): Promise<CandidatesPayload> {
  const r = await fetch(`${API}/jobs/${jobId}/candidates`);
  if (!r.ok) throw new Error(`candidates: ${r.status}`);
  return r.json();
}

export const structureUrl = (jobId: string) => `${API}/jobs/${jobId}/structure`;
export const reportUrl = (jobId: string) => `${API}/jobs/${jobId}/report`;

export async function explainCandidate(jobId: string, rank: number): Promise<{ explanation: string; cached: boolean }> {
  const r = await fetch(`${API}/jobs/${jobId}/candidates/${rank}/explain`, { method: "POST" });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export type GraphPayload = {
  nodes: { data: { id: string; label: string; type: string; [k: string]: unknown } }[];
  edges: { data: { source: string; target: string; type: string; weight?: number } }[];
};

export async function getGraph(jobId: string): Promise<GraphPayload> {
  const r = await fetch(`${API}/jobs/${jobId}/graph`);
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export function subscribeEvents(jobId: string, onEvent: (e: ReasoningEvent) => void): () => void {
  const es = new EventSource(`${API}/jobs/${jobId}/events`);
  es.onmessage = (m) => {
    try {
      onEvent(JSON.parse(m.data) as ReasoningEvent);
    } catch {
      /* ignore */
    }
  };
  es.onerror = () => {
    /* let browser auto-reconnect; fail silent */
  };
  return () => es.close();
}
