import { useEffect, useMemo, useRef, useState } from "react";
import { subscribeEvents } from "../lib/api";
import type { ReasoningEvent } from "../types";

/**
 * Compact activity log.
 * - Pairs tool_call/tool_result into a single line per tool invocation
 * - Renders reasoning blocks as paragraphs
 * - Highlights memory-recall and errors
 * - Hides raw JSON dumps; shows a one-line summary instead
 */
export default function ActivityLog({ jobId }: { jobId: string }) {
  const [events, setEvents] = useState<ReasoningEvent[]>([]);
  const [showRaw, setShowRaw] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setEvents([]);
    const unsub = subscribeEvents(jobId, (e) => setEvents((prev) => [...prev, e]));
    return unsub;
  }, [jobId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [events.length]);

  const items = useMemo(() => coalesce(events), [events]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-4 py-2 border-b border-zinc-800 flex items-center justify-between">
        <span className="text-[11px] text-zinc-500 font-mono">{items.length} events</span>
        <button
          className="text-[11px] text-zinc-500 hover:text-zinc-300 font-mono transition"
          onClick={() => setShowRaw((v) => !v)}
        >
          {showRaw ? "hide raw" : "show raw"}
        </button>
      </div>
      <div className="flex-1 overflow-y-auto px-5 py-3">
        {items.length === 0 && (
          <div className="text-zinc-600 italic text-sm font-mono">awaiting agent…</div>
        )}
        <ol className="space-y-2.5">
          {items.map((it, i) => (
            <li key={i}>
              {it.kind === "tool" && (
                <ToolLine
                  name={it.name}
                  argsLine={it.argsLine}
                  ok={it.ok}
                  ts={it.ts}
                  summary={showRaw ? it.summary : undefined}
                />
              )}
              {it.kind === "reasoning" && <ReasoningLine text={it.text} ts={it.ts} />}
              {it.kind === "memory" && <MemoryLine note={it.note} ts={it.ts} />}
              {it.kind === "error" && <ErrorLine text={it.text} ts={it.ts} />}
              {it.kind === "retry" && <RetryLine code={it.code} delay={it.delay} ts={it.ts} />}
              {it.kind === "done" && <DoneLine ts={it.ts} />}
              {it.kind === "status" && <StatusLine status={it.status} ts={it.ts} />}
            </li>
          ))}
          <div ref={endRef} />
        </ol>
      </div>
    </div>
  );
}

// ----- coalescing logic -----------------------------------------------------

type Item =
  | { kind: "status"; status: string; ts: string }
  | { kind: "memory"; note: string; ts: string }
  | { kind: "reasoning"; text: string; ts: string }
  | { kind: "tool"; name: string; argsLine: string; ok: boolean; ts: string; summary?: string }
  | { kind: "retry"; code?: number; delay?: number; ts: string }
  | { kind: "error"; text: string; ts: string }
  | { kind: "done"; ts: string };

function coalesce(events: ReasoningEvent[]): Item[] {
  const out: Item[] = [];
  const pendingCalls: Map<string, { args: string; ts: string; index: number }> = new Map();

  for (const e of events) {
    const ts = e.ts || "";
    if (e.type === "tool_call" && e.name) {
      const argsLine = fmtArgs(e.args);
      out.push({ kind: "tool", name: e.name, argsLine, ok: false, ts });
      pendingCalls.set(e.name, { args: argsLine, ts, index: out.length - 1 });
    } else if (e.type === "tool_result" && e.name) {
      const pending = pendingCalls.get(e.name);
      if (pending) {
        out[pending.index] = {
          kind: "tool",
          name: e.name,
          argsLine: pending.args,
          ok: true,
          ts: pending.ts,
          summary: e.summary,
        };
        pendingCalls.delete(e.name);
      }
    } else if (e.type === "reasoning" && e.text) {
      out.push({ kind: "reasoning", text: e.text, ts });
    } else if (e.type === "memory_recall" && e.note) {
      out.push({ kind: "memory", note: e.note, ts });
    } else if (e.type === "retry") {
      out.push({ kind: "retry", code: e.code, delay: e.delay, ts });
    } else if (e.type === "error") {
      out.push({ kind: "error", text: e.error || "error", ts });
    } else if (e.type === "done") {
      out.push({ kind: "done", ts });
    } else if (e.type === "status" && e.status) {
      out.push({ kind: "status", status: e.status, ts });
    }
  }
  return out;
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

function truncate(s: string, n: number) {
  return s.length > n ? s.slice(0, n) + "…" : s;
}

function fmtTime(ts: string) {
  if (!ts) return "";
  const d = new Date(ts);
  return d.toLocaleTimeString([], { hour12: false });
}

// ----- line components ------------------------------------------------------

function ToolLine({ name, argsLine, ok, ts, summary }: { name: string; argsLine: string; ok: boolean; ts: string; summary?: string }) {
  return (
    <div className="flex gap-3 items-start">
      <Dot ok={ok} />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[12.5px] text-zinc-200">{name}</span>
          <span className="font-mono text-[11px] text-zinc-500 truncate">{argsLine}</span>
          <span className="ml-auto font-mono text-[10px] text-zinc-600 tabular-nums shrink-0">{fmtTime(ts)}</span>
        </div>
        {summary && (
          <div className="mt-0.5 font-mono text-[11px] text-zinc-600 break-all max-h-24 overflow-hidden">
            {truncate(summary, 220)}
          </div>
        )}
      </div>
    </div>
  );
}

function ReasoningLine({ text, ts }: { text: string; ts: string }) {
  return (
    <div className="bg-zinc-900/60 border-l-2 border-accent rounded-r px-3 py-2">
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[10px] tracking-[0.15em] text-zinc-500 font-mono uppercase">reasoning</span>
        <span className="font-mono text-[10px] text-zinc-600 tabular-nums">{fmtTime(ts)}</span>
      </div>
      <p className="text-[12.5px] text-zinc-200 leading-relaxed whitespace-pre-wrap">{stripMarkdown(text)}</p>
    </div>
  );
}

function MemoryLine({ note, ts }: { note: string; ts: string }) {
  return (
    <div className="bg-purple-950/30 border-l-2 border-purple-400 rounded-r px-3 py-2">
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[10px] tracking-[0.15em] text-purple-300 font-mono uppercase">memory recall</span>
        <span className="font-mono text-[10px] text-zinc-600 tabular-nums">{fmtTime(ts)}</span>
      </div>
      <p className="text-[12.5px] text-purple-100/90 leading-relaxed whitespace-pre-wrap">{note}</p>
    </div>
  );
}

function ErrorLine({ text, ts }: { text: string; ts: string }) {
  return (
    <div className="bg-red-950/40 border-l-2 border-red-400 rounded-r px-3 py-2">
      <div className="flex items-baseline justify-between mb-1">
        <span className="text-[10px] tracking-[0.15em] text-red-300 font-mono uppercase">error</span>
        <span className="font-mono text-[10px] text-zinc-600 tabular-nums">{fmtTime(ts)}</span>
      </div>
      <p className="text-[12.5px] text-red-200 leading-relaxed">{text}</p>
    </div>
  );
}

function RetryLine({ code, delay, ts }: { code?: number; delay?: number; ts: string }) {
  return (
    <div className="flex gap-3 items-baseline">
      <span className="text-amber-400 text-[11px] font-mono uppercase tracking-[0.15em] shrink-0">retry</span>
      <span className="text-zinc-400 font-mono text-[12.5px]">HTTP {code} · waiting {delay}s</span>
      <span className="ml-auto font-mono text-[10px] text-zinc-600 tabular-nums shrink-0">{fmtTime(ts)}</span>
    </div>
  );
}

function DoneLine({ ts }: { ts: string }) {
  return (
    <div className="bg-emerald-950/40 border-l-2 border-accent rounded-r px-3 py-2 flex items-baseline justify-between">
      <span className="text-[11px] text-accent font-mono uppercase tracking-[0.15em]">pipeline complete</span>
      <span className="font-mono text-[10px] text-zinc-600 tabular-nums">{fmtTime(ts)}</span>
    </div>
  );
}

function StatusLine({ status, ts }: { status: string; ts: string }) {
  return (
    <div className="flex gap-3 items-baseline">
      <span className="text-zinc-500 text-[11px] font-mono uppercase tracking-[0.15em] shrink-0">status</span>
      <span className="text-zinc-300 font-mono text-[12.5px]">{status}</span>
      <span className="ml-auto font-mono text-[10px] text-zinc-600 tabular-nums shrink-0">{fmtTime(ts)}</span>
    </div>
  );
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 ${ok ? "bg-accent" : "bg-amber-400 animate-pulse"}`}
    />
  );
}

function stripMarkdown(text: string): string {
  return text
    .replace(/^#{1,6}\s+/gm, "")
    .replace(/\*\*(.+?)\*\*/g, "$1")
    .replace(/\*(.+?)\*/g, "$1")
    .replace(/`([^`]+)`/g, "$1")
    .replace(/^[-*]\s+/gm, "• ");
}
