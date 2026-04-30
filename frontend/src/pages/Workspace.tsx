import { useState } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getCandidates, getJob, reportUrl } from "../lib/api";
import ReasoningStream from "../components/ReasoningStream";
import StructureViewer from "../components/StructureViewer";
import CandidatesTable from "../components/CandidatesTable";
import GraphView from "../components/GraphView";

export default function Workspace() {
  const { jobId = "" } = useParams();
  const [centerView, setCenterView] = useState<"structure" | "graph">("structure");

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
    refetchInterval: () => {
      const s = job.data?.status;
      return s === "completed" || s === "failed" ? false : 4000;
    },
  });

  const target = candidates.data?.target;
  const structure = candidates.data?.structure;
  const status = job.data?.status;

  return (
    <div className="h-full flex flex-col">
      {/* Status bar */}
      <div className="border-b border-zinc-800 px-6 py-2 flex items-center gap-4 text-sm">
        <span className="text-zinc-300">{job.data?.disease ?? "…"}</span>
        <StatusPill status={status} />
        {target && (
          <span className="font-mono text-xs text-zinc-400">
            target:{" "}
            <span className="text-zinc-100">{target.uniprot_id}</span>{" "}
            <span className="text-zinc-500">{target.protein_name}</span>
          </span>
        )}
        {structure && (
          <span className="font-mono text-xs text-zinc-400">
            struct: <span className="text-zinc-100">{structure.source}</span>
          </span>
        )}
        <span className="ml-auto text-xs text-zinc-500 font-mono">job {jobId}</span>
        {status === "completed" && (
          <a
            href={reportUrl(jobId)}
            target="_blank"
            rel="noreferrer"
            className="text-xs bg-accent text-zinc-950 px-3 py-1 rounded font-medium hover:bg-accent-dim transition"
          >
            report ↗
          </a>
        )}
      </div>

      {/* Three-pane layout */}
      <div className="flex-1 grid grid-cols-[360px_1fr_400px] min-h-0">
        <aside className="border-r border-zinc-800 min-h-0 overflow-hidden">
          <PaneHeader>reasoning stream</PaneHeader>
          <div className="h-[calc(100%-2.25rem)]">
            <ReasoningStream jobId={jobId} />
          </div>
        </aside>

        <section className="border-r border-zinc-800 min-h-0 overflow-hidden">
          <div className="px-4 py-2 border-b border-zinc-900 flex items-center justify-between">
            <span className="text-[11px] uppercase tracking-widest text-zinc-500 font-mono">
              {centerView === "structure" ? "structure" : "knowledge graph"}
            </span>
            <div className="flex gap-1 text-[11px] font-mono">
              <ViewBtn active={centerView === "structure"} onClick={() => setCenterView("structure")}>
                3D
              </ViewBtn>
              <ViewBtn active={centerView === "graph"} onClick={() => setCenterView("graph")}>
                graph
              </ViewBtn>
            </div>
          </div>
          <div className="h-[calc(100%-2.25rem)]">
            {centerView === "structure" ? (
              <StructureViewer
                jobId={jobId}
                ready={!!structure}
                pocketCenter={structure?.pocket_center}
              />
            ) : (
              <GraphView jobId={jobId} />
            )}
          </div>
        </section>

        <aside className="min-h-0 overflow-hidden">
          <PaneHeader>candidates</PaneHeader>
          <div className="h-[calc(100%-2.25rem)]">
            <CandidatesTable candidates={candidates.data?.candidates ?? []} jobId={jobId} />
          </div>
        </aside>
      </div>

      {target?.rationale && (
        <div className="border-t border-zinc-800 px-6 py-3 text-sm text-zinc-300 italic">
          <span className="text-zinc-500 mr-2 not-italic font-mono text-xs">RATIONALE</span>
          {target.rationale}
        </div>
      )}
    </div>
  );
}

function PaneHeader({ children }: { children: React.ReactNode }) {
  return (
    <div className="px-4 py-2 border-b border-zinc-900 text-[11px] uppercase tracking-widest text-zinc-500 font-mono">
      {children}
    </div>
  );
}

function ViewBtn({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-2 py-0.5 rounded transition ${
        active ? "bg-accent text-zinc-950" : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800"
      }`}
    >
      {children}
    </button>
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
    <span className={`px-2 py-0.5 text-xs rounded-full border font-mono ${cls}`}>
      {status ?? "…"}
    </span>
  );
}
