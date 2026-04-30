import { useEffect, useRef, useState } from "react";
import * as NGL from "ngl";
import { structureUrl } from "../lib/api";

type Props = {
  jobId: string;
  pocketCenter?: number[] | null;
  ready: boolean;
};

export default function StructureViewer({ jobId, pocketCenter, ready }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<NGL.Stage | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!containerRef.current || !ready) return;
    const stage = new NGL.Stage(containerRef.current, { backgroundColor: "#0a0a0b" });
    stageRef.current = stage;
    const onResize = () => stage.handleResize();
    window.addEventListener("resize", onResize);

    stage
      .loadFile(structureUrl(jobId), { ext: "pdb" })
      .then((c) => {
        if (!c) return;
        c.addRepresentation("cartoon", { colorScheme: "chainid", smoothSheet: true });
        c.addRepresentation("ball+stick", {
          sele: "hetero and not water",
          colorScheme: "element",
        });
        if (pocketCenter && pocketCenter.length === 3) {
          const shape = new NGL.Shape("pocket");
          shape.addSphere(pocketCenter as [number, number, number], [0.2, 0.83, 0.6], 4, "binding pocket");
          stage.addComponentFromObject(shape).addRepresentation("buffer", { opacity: 0.35 });
        }
        c.autoView();
        setLoaded(true);
      })
      .catch((e) => setError(String(e)));

    return () => {
      window.removeEventListener("resize", onResize);
      stage.dispose();
      stageRef.current = null;
    };
  }, [jobId, ready, pocketCenter]);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {!ready && (
        <Overlay text="awaiting structure retrieval…" />
      )}
      {ready && !loaded && !error && <Overlay text="loading PDB…" />}
      {error && <Overlay text={`error: ${error}`} red />}
      {loaded && (
        <div className="absolute top-3 left-3 text-xs font-mono text-zinc-500 bg-zinc-950/70 px-2 py-1 rounded">
          NGL · cartoon + hetero
          {pocketCenter && <span className="text-accent"> · pocket</span>}
        </div>
      )}
    </div>
  );
}

function Overlay({ text, red }: { text: string; red?: boolean }) {
  return (
    <div className="absolute inset-0 flex items-center justify-center">
      <span className={`font-mono text-sm ${red ? "text-red-400" : "text-zinc-500"}`}>
        {text}
      </span>
    </div>
  );
}
