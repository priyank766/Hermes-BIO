import { Routes, Route, Link } from "react-router-dom";
import Home from "./pages/Home";
import Workspace from "./pages/Workspace";

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="border-b border-zinc-800 px-6 py-3 flex items-center gap-4">
        <Link to="/" className="font-mono text-sm tracking-tight">
          <span className="text-accent">▲</span>{" "}
          <span className="text-zinc-100">drug-discovery</span>
          <span className="text-zinc-500">.agent</span>
        </Link>
        <span className="text-xs text-zinc-500 ml-auto font-mono">
          repurposing-first · sa-aware · streaming
        </span>
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
