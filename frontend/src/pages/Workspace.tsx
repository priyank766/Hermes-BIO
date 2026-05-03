import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCandidates, getJob, reportUrl } from "../lib/api";
import ActivityLog from "../components/ActivityLog";
import StructureViewer from "../components/StructureViewer";
import CandidatesTable from "../components/CandidatesTable";

export default function Workspace() {
  const { jobId = "" } = useParams();

  const job = useQuery({
    queryKey: ["job", jobId],
    queryFn: () => getJob(jobId),
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "completed" || s === "failed" ? false : 3000;
    },
  });

  const candidates = useQuery({
    queryKey: ["candidates", jobId],
    queryFn: () => getCandidates(jobId),
    refetchInterval: (q) => {
      const s = job.data?.status;
      const haveData = (q.state.data?.candidates?.length ?? 0) > 0;
      if (s === "failed") return false;
      if (s === "completed" && haveData) return false;
      return 3000;
    },
  });

  const target = candidates.data?.target;
  const structure = candidates.data?.structure;
  const status = job.data?.status;
  const candidatesList = candidates.data?.candidates ?? [];
  const approvedCount = candidatesList.filter((c) => c.is_approved_drug).length;

  return (
    <div className="h-full overflow-y-auto">
      {/* Header band */}
      <div className="border-b border-zinc-800 bg-zinc-950/85 sticky top-0 z-10 backdrop-blur">
        <div className="max-w-6xl mx-auto px-8 py-4 flex items-center gap-4">
          <div className="flex-1 min-w-0">
            <div className="text-[10px] tracking-[0.2em] uppercase text-zinc-500 font-mono mb-1">
              discovery run
            </div>
            <h1 className="text-xl font-medium text-zinc-100 truncate">
              {job.data?.disease ?? "…"}
            </h1>
          </div>
          <StatusPill status={status} />
          {status === "completed" && (
            <a
              href={reportUrl(jobId)}
              target="_blank"
              rel="noreferrer"
              className="text-xs bg-accent text-zinc-950 px-4 py-2 rounded-md font-medium hover:bg-emerald-300 transition tracking-wide"
            >
              full report
            </a>
          )}
        </div>
      </div>

      <div className="max-w-6xl mx-auto px-8 py-8 space-y-10">
        {/* Hero — target + 3D viewer side-by-side */}
        <section className="grid grid-cols-1 lg:grid-cols-[1fr_460px] gap-6">
          <TargetCard target={target} structure={structure} candidatesCount={candidatesList.length} approvedCount={approvedCount} />
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg overflow-hidden h-[420px] flex flex-col">
            <div className="px-4 py-2.5 border-b border-zinc-800 flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono">structure</span>
              {structure && (
                <span className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono">
                  {structure.source}
                  {structure.quality_score != null && structure.quality_score > 0 && (
                    <span className="text-zinc-600"> · pLDDT {structure.quality_score.toFixed(0)}</span>
                  )}
                </span>
              )}
            </div>
            <div className="flex-1 min-h-0 relative">
              <StructureViewer
                jobId={jobId}
                ready={!!structure}
                pocketCenter={structure?.pocket_center}
              />
            </div>
          </div>
        </section>

        {/* Candidates */}
        <section>
          <SectionHeader title="ranked candidates" subtitle={candidatesList.length ? `${candidatesList.length} compound${candidatesList.length === 1 ? "" : "s"} · ${approvedCount} FDA-approved` : "awaiting docking"} />
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg overflow-hidden">
            <CandidatesTable candidates={candidatesList} jobId={jobId} />
          </div>
        </section>

        {/* Agent activity */}
        <section>
          <SectionHeader title="agent activity" subtitle="live tool-call timeline" />
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg max-h-[480px] overflow-hidden">
            <ActivityLog jobId={jobId} />
          </div>
        </section>
      </div>
    </div>
  );
}

function TargetCard({ target, structure, candidatesCount, approvedCount }: {
  target?: { uniprot_id: string; protein_name: string; druggability_score: number | null; rationale: string | null } | null;
  structure?: { pdb_path: string; source: string; quality_score: number | null; pocket_center: number[] | null } | null;
  candidatesCount: number;
  approvedCount: number;
}) {
  if (!target) {
    return (
      <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-6 flex items-center justify-center text-zinc-500 text-sm h-[420px]">
        agent is selecting target…
      </div>
    );
  }
  return (
    <div className="bg-zinc-900/40 border border-zinc-800 rounded-lg p-6 h-[420px] flex flex-col">
      <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-3">selected target</div>
      <div className="flex items-baseline gap-3 mb-1">
        <h2 className="text-2xl font-medium text-zinc-100 tracking-tight">{target.protein_name}</h2>
      </div>
      <div className="flex items-center gap-4 text-sm font-mono text-zinc-500 mb-5">
        <span><span className="text-zinc-600">uniprot</span>{" "}<span className="text-accent">{target.uniprot_id}</span></span>
        {target.druggability_score != null && (
          <span><span className="text-zinc-600">druggability</span>{" "}<span className="text-zinc-300">{target.druggability_score.toFixed(3)}</span></span>
        )}
      </div>

      {target.rationale && (
        <p className="text-zinc-300 text-sm leading-relaxed mb-5 italic flex-1 overflow-y-auto">
          {target.rationale}
        </p>
      )}

      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-zinc-800">
        <Stat label="candidates" value={candidatesCount.toString()} accent={candidatesCount > 0} />
        <Stat label="FDA-approved" value={approvedCount.toString()} accent={approvedCount > 0} />
        <Stat label="structure" value={structure?.source ?? "—"} accent={!!structure} />
      </div>
    </div>
  );
}

function Stat({ label, value, accent }: { label: string; value: string; accent: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.15em] text-zinc-500 font-mono mb-1">{label}</div>
      <div className={`text-lg font-medium tabular-nums ${accent ? "text-accent" : "text-zinc-500"}`}>{value}</div>
    </div>
  );
}

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="flex items-baseline justify-between mb-3 px-1">
      <h2 className="text-[11px] uppercase tracking-[0.2em] text-zinc-400 font-mono">{title}</h2>
      {subtitle && <span className="text-[11px] text-zinc-500 font-mono">{subtitle}</span>}
    </div>
  );
}

function StatusPill({ status }: { status?: string }) {
  const cls =
    status === "completed"
      ? "bg-emerald-500/15 text-accent border-emerald-500/30"
      : status === "failed"
      ? "bg-red-500/10 text-red-400 border-red-500/20"
      : status === "running"
      ? "bg-amber-500/10 text-amber-400 border-amber-500/20 animate-pulse"
      : "bg-zinc-500/10 text-zinc-400 border-zinc-500/20";
  return (
    <span className={`px-3 py-1 text-[11px] rounded-full border font-mono tracking-wide ${cls}`}>
      {status ?? "…"}
    </span>
  );
}
