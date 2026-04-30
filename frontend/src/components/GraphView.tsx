import { useEffect, useRef } from "react";
import cytoscape, { type Core, type ElementDefinition } from "cytoscape";
import { useQuery } from "@tanstack/react-query";
import { getGraph } from "../lib/api";

const NODE_STYLE_BY_TYPE: Record<string, { bg: string; border: string }> = {
  disease:       { bg: "#1e1e22", border: "#a1a1aa" },
  target:        { bg: "#0f3325", border: "#34d399" },
  structure:     { bg: "#1a1a1f", border: "#71717a" },
  drug_approved: { bg: "#0f3325", border: "#34d399" },
  drug_novel:    { bg: "#1a1a1f", border: "#71717a" },
};

export default function GraphView({ jobId }: { jobId: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["graph", jobId],
    queryFn: () => getGraph(jobId),
    refetchInterval: 5000,
  });

  useEffect(() => {
    if (!containerRef.current || !data) return;

    const elements: ElementDefinition[] = [
      ...data.nodes.map((n) => ({ data: n.data })),
      ...data.edges.map((e) => ({ data: e.data })),
    ];

    if (cyRef.current) {
      cyRef.current.json({ elements });
      cyRef.current.layout({ name: "concentric", concentric: nodeConcentric, levelWidth: () => 1, padding: 30 } as any).run();
      return;
    }

    cyRef.current = cytoscape({
      container: containerRef.current,
      elements,
      style: [
        {
          selector: "node",
          style: {
            "background-color": (n: any) => NODE_STYLE_BY_TYPE[n.data("type")]?.bg ?? "#27272a",
            "border-color": (n: any) => NODE_STYLE_BY_TYPE[n.data("type")]?.border ?? "#52525b",
            "border-width": 1.5,
            "label": "data(label)",
            "color": "#e4e4e7",
            "font-size": 11,
            "font-family": "ui-sans-serif, system-ui",
            "text-valign": "center",
            "text-halign": "center",
            "text-wrap": "ellipsis",
            "text-max-width": "100",
            "width": (n: any) => sizeFor(n.data("type")),
            "height": (n: any) => sizeFor(n.data("type")),
          },
        },
        {
          selector: "edge",
          style: {
            "width": 1,
            "line-color": "#3f3f46",
            "target-arrow-color": "#3f3f46",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "opacity": 0.7,
          },
        },
        {
          selector: 'edge[type = "binds"]',
          style: {
            "width": (e: any) => Math.max(1, (e.data("weight") ?? 5) * 0.4),
            "line-color": "#34d399",
            "target-arrow-color": "#34d399",
            "opacity": 0.6,
          },
        },
        {
          selector: ":selected",
          style: { "border-color": "#34d399", "border-width": 3 },
        },
      ],
      layout: { name: "concentric", concentric: nodeConcentric, levelWidth: () => 1, padding: 30 } as any,
      wheelSensitivity: 0.2,
    });
  }, [data]);

  useEffect(() => {
    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
  }, []);

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-full" />
      {isLoading && (
        <div className="absolute inset-0 flex items-center justify-center text-zinc-500 font-mono text-sm">
          building graph…
        </div>
      )}
      {error && (
        <div className="absolute inset-0 flex items-center justify-center text-red-400 font-mono text-sm">
          {String(error)}
        </div>
      )}
      {data && (
        <div className="absolute top-3 left-3 text-xs font-mono text-zinc-500 bg-zinc-950/70 px-2 py-1 rounded">
          disease → target → structure → drug · {data.nodes.length} nodes
        </div>
      )}
      <div className="absolute bottom-3 right-3 flex gap-2 text-[10px] font-mono">
        <Legend color="#a1a1aa" label="disease" />
        <Legend color="#34d399" label="target / FDA drug" />
        <Legend color="#71717a" label="novel / structure" />
      </div>
    </div>
  );
}

function nodeConcentric(node: cytoscape.NodeSingular): number {
  const t = node.data("type");
  return ({ disease: 4, target: 3, structure: 2, drug_approved: 1, drug_novel: 1 }[t as string] ?? 0);
}

function sizeFor(t: string): number {
  return ({ disease: 70, target: 60, structure: 45, drug_approved: 50, drug_novel: 45 }[t] ?? 40);
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="bg-zinc-950/70 px-2 py-1 rounded flex items-center gap-1.5 text-zinc-400">
      <span className="w-2 h-2 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}
