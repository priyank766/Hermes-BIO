import { useState } from "react";
import { explainCandidate } from "../lib/api";
import type { Candidate } from "../types";

type TabKey = "approved" | "novel" | "all";

export default function CandidatesTable({ candidates, jobId }: { candidates: Candidate[]; jobId: string }) {
  const approved = candidates.filter((c) => c.is_approved_drug);
  const novel = candidates.filter((c) => !c.is_approved_drug);

  const initialTab: TabKey = approved.length ? "approved" : candidates.length ? "all" : "approved";
  const [tab, setTab] = useState<TabKey>(initialTab);
  const [copied, setCopied] = useState<string | null>(null);
  const [openRank, setOpenRank] = useState<number | null>(null);
  const [explanations, setExplanations] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<number | null>(null);

  const list = tab === "approved" ? approved : tab === "novel" ? novel : candidates;

  async function toggleExplain(rank: number) {
    if (openRank === rank) {
      setOpenRank(null);
      return;
    }
    setOpenRank(rank);
    if (explanations[rank]) return;
    setLoading(rank);
    try {
      const { explanation } = await explainCandidate(jobId, rank);
      setExplanations((p) => ({ ...p, [rank]: explanation }));
    } catch (e) {
      setExplanations((p) => ({ ...p, [rank]: `error: ${e}` }));
    } finally {
      setLoading(null);
    }
  }

  return (
    <div>
      <div className="flex border-b border-zinc-800 px-3 pt-2 gap-1 text-sm">
        <Tab active={tab === "approved"} onClick={() => setTab("approved")} count={approved.length}>
          repurposing
        </Tab>
        <Tab active={tab === "novel"} onClick={() => setTab("novel")} count={novel.length}>
          novel
        </Tab>
        <Tab active={tab === "all"} onClick={() => setTab("all")} count={candidates.length}>
          all
        </Tab>
      </div>

      {candidates.length === 0 ? (
        <EmptyState
          title="no candidates yet"
          sub="agent is still working — table fills once docking and filtering complete"
        />
      ) : list.length === 0 ? (
        <EmptyState
          title={`no ${tab} candidates`}
          sub={tab === "approved"
            ? "no FDA-approved drugs were ranked into the top hits"
            : tab === "novel"
            ? "all top hits are FDA-approved repurposing leads"
            : "no candidates in this view"}
        />
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-[10px] uppercase tracking-[0.15em] text-zinc-500 font-mono">
              <th className="text-right px-4 py-2.5 w-10">#</th>
              <th className="text-left px-4 py-2.5">molecule</th>
              <th className="text-right px-3 py-2.5 w-24">affinity</th>
              <th className="text-center px-3 py-2.5 w-24">lipinski</th>
              <th className="text-center px-3 py-2.5 w-20">SA</th>
              <th className="text-right px-3 py-2.5 w-16">tox</th>
              <th className="text-right px-3 py-2.5 w-16">abs</th>
              <th className="text-center px-3 py-2.5 w-20">status</th>
              <th className="px-3 py-2.5 w-24"></th>
            </tr>
          </thead>
          <tbody>
            {list.map((c) => (
              <Row
                key={c.rank}
                c={c}
                copied={copied === c.smiles}
                onCopy={() => {
                  navigator.clipboard?.writeText(c.smiles);
                  setCopied(c.smiles);
                  setTimeout(() => setCopied(null), 1200);
                }}
                open={openRank === c.rank}
                explaining={loading === c.rank}
                explanation={explanations[c.rank]}
                onToggleExplain={() => toggleExplain(c.rank)}
              />
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function Row({ c, copied, onCopy, open, explaining, explanation, onToggleExplain }: {
  c: Candidate; copied: boolean; onCopy: () => void;
  open: boolean; explaining: boolean; explanation?: string; onToggleExplain: () => void;
}) {
  return (
    <>
      <tr className="border-b border-zinc-900 hover:bg-zinc-900/40 transition">
        <td className="text-right px-4 py-3.5 align-top text-zinc-500 font-mono tabular-nums">{c.rank}</td>
        <td className="px-4 py-3.5 align-top">
          {c.name && (
            <div className="text-zinc-100 font-medium leading-tight mb-0.5">{c.name}</div>
          )}
          <button
            className="font-mono text-[11px] text-zinc-500 hover:text-zinc-300 break-all text-left leading-relaxed transition"
            title="click to copy SMILES"
            onClick={onCopy}
          >
            {copied ? <span className="text-accent">copied</span> : c.smiles}
          </button>
        </td>
        <td className="text-right px-3 py-3.5 align-top font-mono tabular-nums text-accent">{c.binding_affinity.toFixed(2)}</td>
        <td className="text-center px-3 py-3.5 align-top">
          {c.lipinski_pass === null ? (
            <span className="text-zinc-600 text-xs">—</span>
          ) : c.lipinski_pass ? (
            <Pill kind="ok">pass</Pill>
          ) : (
            <Pill kind="bad">fail</Pill>
          )}
        </td>
        <td className="text-center px-3 py-3.5 align-top">
          {c.synthesis_score !== null ? (
            <Pill kind={c.synthesis_score < 3.5 ? "ok" : c.synthesis_score < 6 ? "warn" : "bad"}>
              {c.synthesis_score.toFixed(1)}
            </Pill>
          ) : (
            <span className="text-zinc-600 text-xs">—</span>
          )}
        </td>
        <td className="text-right px-3 py-3.5 align-top font-mono tabular-nums text-zinc-300">
          {c.toxicity_score !== null ? c.toxicity_score.toFixed(2) : <span className="text-zinc-600">—</span>}
        </td>
        <td className="text-right px-3 py-3.5 align-top font-mono tabular-nums text-zinc-300">
          {c.absorption_score !== null ? c.absorption_score.toFixed(2) : <span className="text-zinc-600">—</span>}
        </td>
        <td className="text-center px-3 py-3.5 align-top">
          {c.is_approved_drug ? <Pill kind="approved">FDA</Pill> : <Pill kind="novel">novel</Pill>}
        </td>
        <td className="px-3 py-3.5 align-top text-right">
          <button
            onClick={onToggleExplain}
            className="text-[11px] text-accent hover:underline font-medium font-mono"
          >
            {open ? "hide" : "explain"}
          </button>
        </td>
      </tr>
      {open && (
        <tr>
          <td></td>
          <td colSpan={8} className="px-4 pb-4 align-top">
            <div className="bg-zinc-950 border-l-2 border-accent rounded-r px-4 py-3 text-[13px] text-zinc-300 leading-relaxed">
              <div className="text-[10px] tracking-[0.18em] text-zinc-500 mb-1.5 font-mono uppercase">mechanism of action</div>
              {explaining ? (
                <span className="text-zinc-500 italic">generating mechanism explanation…</span>
              ) : (
                explanation ?? "no explanation available"
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

function EmptyState({ title, sub }: { title: string; sub: string }) {
  return (
    <div className="px-6 py-14 text-center">
      <div className="text-zinc-500 font-mono text-sm">{title}</div>
      <div className="text-zinc-600 text-xs mt-1.5 max-w-md mx-auto leading-relaxed">{sub}</div>
    </div>
  );
}

function Tab({ active, onClick, count, children }: {
  active: boolean;
  onClick: () => void;
  count?: number;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 rounded-t border-b-2 -mb-px transition flex items-center gap-1.5 text-sm ${
        active ? "border-accent text-zinc-100" : "border-transparent text-zinc-500 hover:text-zinc-300"
      }`}
    >
      <span>{children}</span>
      {count !== undefined && (
        <span className={`text-[10px] tabular-nums px-1.5 py-0.5 rounded font-mono ${
          active ? "bg-accent/20 text-accent" : "bg-zinc-900 text-zinc-500"
        }`}>
          {count}
        </span>
      )}
    </button>
  );
}

function Pill({ kind, children }: { kind: "approved" | "ok" | "warn" | "bad" | "novel"; children: React.ReactNode }) {
  const cls = {
    approved: "bg-emerald-500/15 text-accent border-emerald-500/30",
    novel: "bg-zinc-500/10 text-zinc-400 border-zinc-700",
    ok: "bg-emerald-500/10 text-accent border-emerald-500/20",
    warn: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    bad: "bg-red-500/10 text-red-400 border-red-500/20",
  }[kind];
  return (
    <span className={`px-2 py-0.5 rounded-full border font-medium tracking-wide font-mono text-[10px] inline-block ${cls}`}>
      {children}
    </span>
  );
}
