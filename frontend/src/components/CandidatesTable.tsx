import { useState } from "react";
import { explainCandidate } from "../lib/api";
import type { Candidate } from "../types";

export default function CandidatesTable({ candidates, jobId }: { candidates: Candidate[]; jobId: string }) {
  const [tab, setTab] = useState<"approved" | "novel" | "all">("approved");
  const [copied, setCopied] = useState<string | null>(null);
  const [openRank, setOpenRank] = useState<number | null>(null);
  const [explanations, setExplanations] = useState<Record<number, string>>({});
  const [loading, setLoading] = useState<number | null>(null);

  const approved = candidates.filter((c) => c.is_approved_drug);
  const novel = candidates.filter((c) => !c.is_approved_drug);
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

  if (candidates.length === 0) {
    return (
      <div className="h-full flex items-center justify-center text-zinc-600 font-mono text-sm">
        no candidates yet
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex border-b border-zinc-800 px-3 pt-2 gap-1 text-sm">
        <Tab active={tab === "approved"} onClick={() => setTab("approved")}>
          🎯 repurposing <span className="text-zinc-500">({approved.length})</span>
        </Tab>
        <Tab active={tab === "novel"} onClick={() => setTab("novel")}>
          novel <span className="text-zinc-500">({novel.length})</span>
        </Tab>
        <Tab active={tab === "all"} onClick={() => setTab("all")}>
          all <span className="text-zinc-500">({candidates.length})</span>
        </Tab>
      </div>
      <div className="overflow-y-auto flex-1">
        {list.length === 0 ? (
          <p className="p-4 text-zinc-600 font-mono text-sm">no {tab} candidates</p>
        ) : (
          <ul className="divide-y divide-zinc-900">
            {list.map((c) => (
              <li key={c.rank} className="px-4 py-3 hover:bg-zinc-900/40">
                <div className="flex items-baseline justify-between mb-1">
                  <div className="flex items-center gap-2">
                    <span className="text-zinc-500 font-mono text-xs">#{c.rank}</span>
                    {c.name && <span className="text-zinc-100 text-sm font-medium">{c.name}</span>}
                    {c.is_approved_drug && <Pill kind="approved">FDA</Pill>}
                  </div>
                  <span className="font-mono text-sm text-accent">{c.binding_affinity.toFixed(2)}</span>
                </div>
                <button
                  className="font-mono text-[11px] text-zinc-500 hover:text-zinc-300 break-all text-left w-full"
                  title="click to copy SMILES"
                  onClick={() => {
                    navigator.clipboard?.writeText(c.smiles);
                    setCopied(c.smiles);
                    setTimeout(() => setCopied(null), 1200);
                  }}
                >
                  {copied === c.smiles ? "✓ copied" : c.smiles}
                </button>
                <div className="flex gap-2 mt-2 flex-wrap text-[11px] items-center">
                  <Pill kind={c.lipinski_pass ? "ok" : "bad"}>
                    lipinski {c.lipinski_pass ? "✓" : "✗"}
                  </Pill>
                  {c.synthesis_score !== null && (
                    <Pill kind={c.synthesis_score < 3.5 ? "ok" : c.synthesis_score < 6 ? "warn" : "bad"}>
                      SA {c.synthesis_score.toFixed(1)}
                    </Pill>
                  )}
                  {c.toxicity_score !== null && (
                    <Pill kind={c.toxicity_score < 0.3 ? "ok" : c.toxicity_score < 0.6 ? "warn" : "bad"}>
                      tox {c.toxicity_score.toFixed(2)}
                    </Pill>
                  )}
                  {c.absorption_score !== null && (
                    <Pill kind={c.absorption_score > 0.6 ? "ok" : c.absorption_score > 0.3 ? "warn" : "bad"}>
                      abs {c.absorption_score.toFixed(2)}
                    </Pill>
                  )}
                  <button
                    className="ml-auto text-[11px] text-accent hover:underline font-medium"
                    onClick={() => toggleExplain(c.rank)}
                  >
                    {openRank === c.rank ? "hide MoA" : "explain MoA"}
                  </button>
                </div>
                {openRank === c.rank && (
                  <div className="mt-2 px-3 py-2 bg-zinc-900/60 border-l-2 border-accent rounded-r text-[12px] text-zinc-300 leading-relaxed">
                    {loading === c.rank ? (
                      <span className="text-zinc-500 italic">generating mechanism explanation…</span>
                    ) : (
                      explanations[c.rank] ?? "no explanation"
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Tab({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-3 py-2 rounded-t border-b-2 -mb-px transition ${
        active ? "border-accent text-zinc-100" : "border-transparent text-zinc-400 hover:text-zinc-200"
      }`}
    >
      {children}
    </button>
  );
}

function Pill({ kind, children }: { kind: "approved" | "ok" | "warn" | "bad"; children: React.ReactNode }) {
  const cls = {
    approved: "bg-emerald-500/15 text-accent border-emerald-500/30",
    ok: "bg-emerald-500/10 text-accent border-emerald-500/20",
    warn: "bg-amber-500/10 text-amber-400 border-amber-500/20",
    bad: "bg-red-500/10 text-red-400 border-red-500/20",
  }[kind];
  return (
    <span className={`px-2 py-0.5 rounded-full border font-medium tracking-wide ${cls}`}>
      {children}
    </span>
  );
}
