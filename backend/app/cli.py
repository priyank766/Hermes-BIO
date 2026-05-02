"""hermes-bio CLI — minimal entry point.

Spirit of `claude` / `codex` / `gemini` CLIs but ~100x simpler. Streams the
same agent event bus to stdout, returns the structured result.

Usage:
  hermes-bio run drug-discovery --disease "type 2 diabetes mellitus"
  hermes-bio run drug-discovery --disease "..." --output json
  hermes-bio memory show
  hermes-bio memory clear --prefix disease:
  hermes-bio skills list
"""
from __future__ import annotations
import argparse
import asyncio
import json
import os
import sys
import uuid
from typing import Any

# ANSI colors (no rich dep)
RESET = "\033[0m"
DIM = "\033[2m"
GREEN = "\033[32m"
EMERALD = "\033[38;5;42m"
AMBER = "\033[38;5;214m"
RED = "\033[31m"
PURPLE = "\033[35m"
CYAN = "\033[36m"
BOLD = "\033[1m"


def _color(text: str, code: str) -> str:
    if not sys.stdout.isatty():
        return text
    return f"{code}{text}{RESET}"


# ----- skills registry -----------------------------------------------------

SKILLS = {
    "drug-discovery": {
        "description": "Disease → ranked drug candidates (UniProt, OpenTargets, "
                       "PDB/AlphaFold, ChEMBL, RDKit). Repurposing-first, SAScore-aware.",
        "required": ["--disease"],
    },
}


# ----- commands ------------------------------------------------------------

def cmd_skills_list(args: argparse.Namespace) -> int:
    print(_color("available skills:", BOLD))
    for name, info in SKILLS.items():
        print(f"  {_color(name, EMERALD)}  {info['description']}")
    return 0


def cmd_memory_show(args: argparse.Namespace) -> int:
    asyncio.run(_memory_show(args))
    return 0


async def _memory_show(args: argparse.Namespace) -> None:
    from . import memory
    from .db import init_db
    await init_db()
    items = await memory.recall(args.scope, prefix=args.prefix)
    if not items:
        print(_color(f"(no memory in scope '{args.scope}'"
                     f"{' prefix='+args.prefix if args.prefix else ''})", DIM))
        return
    for it in items:
        print(_color(it["key"], EMERALD), _color(f"  ({it['created_at']})", DIM))
        if args.verbose:
            print(json.dumps(it["value"], indent=2))
        else:
            v = it["value"]
            preview = ", ".join(f"{k}={truncate(str(v[k]))}" for k in list(v.keys())[:4])
            print(f"  {_color(preview, DIM)}")


def cmd_memory_clear(args: argparse.Namespace) -> int:
    n = asyncio.run(_memory_clear(args))
    print(_color(f"deleted {n} entries", AMBER))
    return 0


async def _memory_clear(args: argparse.Namespace) -> int:
    from . import memory
    from .db import init_db
    await init_db()
    return await memory.clear(args.scope, prefix=args.prefix)


def cmd_run(args: argparse.Namespace) -> int:
    if args.skill not in SKILLS:
        print(_color(f"unknown skill: {args.skill}", RED), file=sys.stderr)
        return 2
    if args.skill == "drug-discovery":
        if not args.disease:
            print(_color("--disease required for drug-discovery", RED), file=sys.stderr)
            return 2
        return asyncio.run(_run_drug_discovery(args))
    return 2


async def _run_drug_discovery(args: argparse.Namespace) -> int:
    from .db import init_db
    from .workers.pipeline import run_pipeline
    from .workers import events as bus

    await init_db()

    job_id = uuid.uuid4().hex[:12]
    # We need a Job row to satisfy pipeline's DB access
    from .db import SessionLocal, Job
    async with SessionLocal() as s:
        s.add(Job(id=job_id, disease_input=args.disease, status="pending"))
        await s.commit()

    if args.output != "json":
        print(_color(f"▲ hermes-bio · drug-discovery", BOLD))
        print(_color(f"  disease: {args.disease}", DIM))
        print(_color(f"  job:     {job_id}", DIM))
        print()

    # Subscribe to the bus and run the pipeline concurrently
    final_holder: dict[str, Any] = {}

    async def reader() -> None:
        async for evt in bus.subscribe(job_id):
            if args.output == "json":
                if evt.get("type") == "structured_result":
                    final_holder["data"] = evt.get("data")
                if evt.get("type") in ("done", "error"):
                    break
                continue
            _print_event(evt)
            if evt.get("type") in ("done", "error"):
                break

    runner = asyncio.create_task(run_pipeline(job_id, args.disease))
    listener = asyncio.create_task(reader())
    await asyncio.gather(runner, listener)

    if args.output == "json":
        # Emit candidates from DB (covers the case where SSE missed events)
        from .db import Job, Target, Structure
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        async with SessionLocal() as s:
            stmt = select(Job).where(Job.id == job_id).options(
                selectinload(Job.targets).selectinload(Target.structures).selectinload(Structure.docking_results)
            )
            res = await s.execute(stmt)
            job = res.scalar_one_or_none()
        out = {"job_id": job_id, "disease": args.disease, "status": job.status if job else "unknown"}
        if final_holder.get("data"):
            out["result"] = final_holder["data"]
        print(json.dumps(out, indent=2, default=str))
        return 0 if (job and job.status == "completed") else 1

    return 0 if final_holder else 1


def _print_event(evt: dict) -> None:
    t = evt.get("type")
    ts = (evt.get("ts") or "")[11:19]  # HH:MM:SS
    if t == "status":
        print(_color(f"[{ts}] ● status: {evt.get('status')}", DIM))
    elif t == "memory_recall":
        print(_color(f"[{ts}] 🧠 memory recall:", PURPLE))
        for line in (evt.get("note") or "").splitlines():
            print(_color(f"      {line}", PURPLE))
    elif t == "reasoning":
        print(_color(f"[{ts}] 💭 {evt.get('text', '')}", CYAN))
    elif t == "tool_call":
        args_s = ", ".join(f"{k}={truncate(str(v))}" for k, v in (evt.get("args") or {}).items())
        print(_color(f"[{ts}] → {evt.get('name')}({args_s})", EMERALD))
    elif t == "tool_result":
        print(_color(f"[{ts}] ✓ {evt.get('name')} {truncate(evt.get('summary', ''), 100)}", DIM))
    elif t == "retry":
        print(_color(f"[{ts}] ↻ retry HTTP {evt.get('code')} in {evt.get('delay')}s", AMBER))
    elif t == "structured_result":
        print(_color(f"[{ts}] 📋 final result captured", EMERALD))
    elif t == "done":
        print(_color(f"[{ts}] ✔ pipeline complete → {evt.get('report_path')}", GREEN))
    elif t == "error":
        print(_color(f"[{ts}] ✗ {evt.get('error')}", RED))


def truncate(s: str, n: int = 50) -> str:
    return s if len(s) <= n else s[:n] + "…"


# ----- argparse ------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hermes-bio",
        description="An agentic harness for bioinformatics. Drug-discovery flagship skill.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # run
    p_run = sub.add_parser("run", help="run a skill end-to-end")
    p_run.add_argument("skill", choices=list(SKILLS.keys()))
    p_run.add_argument("--disease", help="disease name (drug-discovery skill)")
    p_run.add_argument("--output", choices=["pretty", "json"], default="pretty")
    p_run.add_argument("--gemini-key", help="override GEMINI_API_KEY for this run")
    p_run.set_defaults(func=cmd_run)

    # skills
    p_skills = sub.add_parser("skills", help="manage skills")
    p_skills_sub = p_skills.add_subparsers(dest="skills_cmd", required=True)
    p_skills_list = p_skills_sub.add_parser("list", help="list available skills")
    p_skills_list.set_defaults(func=cmd_skills_list)

    # memory
    p_mem = sub.add_parser("memory", help="inspect / clear harness memory")
    p_mem_sub = p_mem.add_subparsers(dest="mem_cmd", required=True)
    p_mem_show = p_mem_sub.add_parser("show", help="dump memory entries")
    p_mem_show.add_argument("--scope", default="drug_discovery")
    p_mem_show.add_argument("--prefix", default=None)
    p_mem_show.add_argument("-v", "--verbose", action="store_true")
    p_mem_show.set_defaults(func=cmd_memory_show)
    p_mem_clear = p_mem_sub.add_parser("clear", help="delete memory entries")
    p_mem_clear.add_argument("--scope", default="drug_discovery")
    p_mem_clear.add_argument("--prefix", default=None)
    p_mem_clear.set_defaults(func=cmd_memory_clear)

    return p


def main(argv: list[str] | None = None) -> int:
    # Force utf-8 stdout on Windows so emoji + arrows don't cp1252-explode
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "gemini_key", None):
        os.environ["GEMINI_API_KEY"] = args.gemini_key
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
