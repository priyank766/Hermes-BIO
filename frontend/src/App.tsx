import { Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import Workspace from "./pages/Workspace";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col bg-zinc-950">
      <header className="border-b border-zinc-800/80 backdrop-blur px-6 py-3 flex items-center gap-4 sticky top-0 z-10 bg-zinc-950/85">
        <Link to="/" className="flex items-center gap-2 group">
          <div className="w-6 h-6 rounded bg-gradient-to-br from-accent to-emerald-700 flex items-center justify-center font-mono text-[10px] font-bold text-zinc-950 group-hover:scale-105 transition">hb</div>
          <span className="font-mono text-sm tracking-tight text-zinc-100">
            hermes-bio
          </span>
          <span className="font-mono text-[11px] tracking-wider text-zinc-500 hidden sm:inline">
            / agentic harness for drug discovery
          </span>
        </Link>
        <nav className="ml-auto flex items-center gap-5 text-xs text-zinc-400 font-mono">
          <span>repurposing-first</span>
          <span className="text-zinc-700">/</span>
          <span>sa-aware</span>
          <span className="text-zinc-700">/</span>
          <span>streaming</span>
        </nav>
      </header>
      <main className="flex-1 min-h-0">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/job/:jobId" element={<Workspace />} />
        </Routes>
      </main>
    </div>
  );
}
