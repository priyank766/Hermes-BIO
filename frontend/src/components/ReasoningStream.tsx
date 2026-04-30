import { useEffect, useRef, useState } from "react";
import { subscribeEvents } from "../lib/api";
import type { ReasoningEvent } from "../types";

const ICONS: Record<string, string> = {
  status: "●",
  reasoning: "💭",
  tool_call: "→",
  tool_result: "✓",
  retry: "↻",
  done: "✔",
  error: "✗",
  structured_result: "📋",
};

const COLORS: Record<string, string> = {
  status: "text-zinc-400",
  reasoning: "text-zinc-200",
  tool_call: "text-accent",
  tool_result: "text-zinc-500",
  retry: "text-amber-400",
  done: "text-accent",
  error: "text-red-400",
  structured_result: "text-accent",
};

export default function ReasoningStream({ jobId }: { jobId: string }) {
  const [events, setEvents] = useState<ReasoningEvent[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEvents([]);
    const unsub = subscribeEvents(jobId, (e) => setEvents((prev) => [...prev, e]));
    return unsub;
  }, [jobId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  return (
    <div className="h-full overflow-y-auto px-4 py-3 font-mono text-[13px] leading-relaxed">
      {events.length === 0 && (
        <div className="text-zinc-600 italic">awaiting agent…</div>
      )}
      {events.map((e, i) => (
        <EventLine key={i} e={e} />
      ))}
      <div ref={endRef} />
    </div>
  );
}

function EventLine({ e }: { e: ReasoningEvent }) {
  const icon = ICONS[e.type] ?? "·";
  const color = COLORS[e.type] ?? "text-zinc-400";
  const time = e.ts ? new Date(e.ts).toLocaleTimeString() : "";

  if (e.type === "tool_call") {
    return (
      <div className="mb-1">
        <span className="text-zinc-600 text-[11px] mr-2">{time}</span>
        <span className={color}>{icon} {e.name}</span>
        <span className="text-zinc-500"> ({fmtArgs(e.args)})</span>
      </div>
    );
  }
  if (e.type === "tool_result") {
    return (
      <div className="mb-1">
        <span className="text-zinc-600 text-[11px] mr-2">{time}</span>
        <span className={color}>{icon} {e.name}</span>
        {e.summary && <span className="text-zinc-600 ml-2">{truncate(e.summary, 90)}</span>}
      </div>
    );
  }
  if (e.type === "reasoning") {
    return (
      <div className="my-2 px-3 py-2 bg-zinc-900/60 border-l-2 border-accent rounded-r whitespace-pre-wrap">
        <span className="text-zinc-600 text-[11px] mr-2">{time}</span>
        <span className={color}>{e.text}</span>
      </div>
    );
  }
  if (e.type === "retry") {
    return (
      <div className="mb-1">
        <span className="text-zinc-600 text-[11px] mr-2">{time}</span>
        <span className={color}>{icon} retry (HTTP {e.code}, {e.delay}s)</span>
      </div>
    );
  }
  if (e.type === "error") {
    return (
      <div className="my-2 px-3 py-2 bg-red-950/40 border-l-2 border-red-400 rounded-r">
        <span className={color}>{icon} {e.error}</span>
      </div>
    );
  }
  if (e.type === "done") {
    return (
      <div className="my-2 px-3 py-2 bg-emerald-950/40 border-l-2 border-accent rounded-r">
        <span className={color}>{icon} pipeline complete</span>
      </div>
    );
  }
  return (
    <div className="mb-1">
      <span className="text-zinc-600 text-[11px] mr-2">{time}</span>
      <span className={color}>{icon} {e.type}</span>
    </div>
  );
}

function fmtArgs(args: Record<string, unknown> | undefined): string {
  if (!args) return "";
  return Object.entries(args)
    .map(([k, v]) => {
      if (Array.isArray(v)) return `${k}=[${v.length}]`;
      const s = typeof v === "string" ? v : JSON.stringify(v);
      return `${k}=${truncate(s, 40)}`;
    })
    .join(", ");
}

function truncate(s: string, n: number): string {
  return s.length > n ? s.slice(0, n) + "…" : s;
}
