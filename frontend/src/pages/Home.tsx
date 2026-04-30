import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { startDiscovery } from "../lib/api";

const EXAMPLES = [
  "type 2 diabetes mellitus",
  "Alzheimer disease",
  "Parkinson disease",
  "non-small cell lung cancer",
  "rheumatoid arthritis",
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
    <div className="max-w-2xl mx-auto py-20 px-6">
      <h1 className="text-3xl font-medium tracking-tight mb-2">
        From disease name to ranked drug candidates.
      </h1>
      <p className="text-zinc-400 mb-10 leading-relaxed">
        An autonomous agent screens UniProt, OpenTargets, PDB/AlphaFold and ChEMBL — runs
        repurposing-first against FDA-approved drugs, scores synthesizability, and streams
        its reasoning live.
      </p>
      <form
        className="flex gap-2"
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
          className="flex-1 bg-zinc-900 border border-zinc-800 rounded-md px-4 py-3 text-zinc-100 placeholder-zinc-600 focus:outline-none focus:border-accent transition"
          disabled={busy}
        />
        <button
          disabled={busy || !disease.trim()}
          className="bg-accent text-zinc-950 font-medium px-6 rounded-md hover:bg-accent-dim disabled:opacity-50 disabled:cursor-not-allowed transition"
        >
          {busy ? "starting…" : "discover"}
        </button>
      </form>
      {err && <p className="text-red-400 mt-3 text-sm">{err}</p>}
      <div className="mt-8">
        <p className="text-xs uppercase tracking-wider text-zinc-500 mb-3">examples</p>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((e) => (
            <button
              key={e}
              onClick={() => {
                setDisease(e);
                submit(e);
              }}
              disabled={busy}
              className="text-sm bg-zinc-900 border border-zinc-800 hover:border-accent text-zinc-300 px-3 py-1.5 rounded-md transition"
            >
              {e}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
