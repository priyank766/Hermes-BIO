import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { startDiscovery } from "../lib/api";

const EXAMPLES = [
  "type 2 diabetes mellitus",
  "Alzheimer disease",
  "Parkinson disease",
  "non-small cell lung cancer",
  "rheumatoid arthritis",
  "idiopathic pulmonary fibrosis",
];

export default function Home() {
  const [disease, setDisease] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const nav = useNavigate();

  async function submit(d: string) {
    if (!d.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const { job_id } = await startDiscovery(d);
      nav(`/job/${job_id}`);
    } catch (e) {
      setErr(String(e));
      setBusy(false);
    }
  }

  return (
    <div className="max-w-3xl mx-auto py-24 px-6">
      <div className="mb-2 text-[11px] font-mono uppercase tracking-[0.2em] text-zinc-500">
        an agentic harness, not a chatbot
      </div>
      <h1 className="text-4xl font-medium tracking-tight mb-4 text-zinc-100 leading-tight">
        Disease name in. <span className="text-accent">Ranked drug candidates</span> out.
      </h1>
      <p className="text-zinc-400 mb-12 leading-relaxed text-[15px] max-w-xl">
        Chains UniProt, OpenTargets, RCSB PDB, AlphaFold and ChEMBL through a
        Gemini function-calling loop. Repurposing-first against FDA-approved
        drugs. Synthesizability scoring. Persistent memory across runs.
      </p>

      <form
        className="flex gap-2 mb-3"
        onSubmit={(e) => {
          e.preventDefault();
          submit(disease);
        }}
      >
        <input
          autoFocus
          value={disease}
          onChange={(e) => setDisease(e.target.value)}
          placeholder="e.g. type 2 diabetes mellitus"
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-md px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent focus:ring-1 focus:ring-accent/40 transition font-mono text-sm"
          disabled={busy}
        />
        <button
          disabled={busy || !disease.trim()}
          className="bg-accent text-zinc-950 font-medium px-7 rounded-md hover:bg-emerald-300 disabled:opacity-40 disabled:cursor-not-allowed transition text-sm tracking-wide"
        >
          {busy ? "starting…" : "discover"}
        </button>
      </form>
      {err && <p className="text-red-400 mt-3 text-sm font-mono">{err}</p>}

      <div className="mt-10">
        <p className="text-[11px] uppercase tracking-[0.2em] text-zinc-500 mb-3 font-mono">examples</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((e) => (
            <button
              key={e}
              onClick={() => {
                setDisease(e);
                submit(e);
              }}
              disabled={busy}
              className="text-sm bg-zinc-900/60 border border-zinc-800 hover:border-accent/60 hover:bg-zinc-900 text-zinc-300 px-3 py-1.5 rounded-md transition font-mono disabled:opacity-40"
            >
              {e}
            </button>
          ))}
        </div>
      </div>

      <div className="mt-20 pt-8 border-t border-zinc-900 grid grid-cols-1 sm:grid-cols-3 gap-6 text-sm">
        <Stat label="canonical regression" value="6 / 6" detail="diseases recovered without seeded knowledge" />
        <Stat label="hard-mode eval" value="4 / 4" detail="match 2023 FDA approvals or P3 trials" />
        <Stat label="end-to-end" value="~60s" detail="from disease name to ranked drug candidates" />
      </div>
    </div>
  );
}

function Stat({ label, value, detail }: { label: string; value: string; detail: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.2em] text-zinc-500 font-mono mb-1">{label}</div>
      <div className="text-2xl font-medium text-accent tabular-nums">{value}</div>
      <div className="text-xs text-zinc-500 mt-0.5">{detail}</div>
    </div>
  );
}
