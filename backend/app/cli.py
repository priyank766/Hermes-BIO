"""hermes-bio CLI -- minimal entry point.

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
        "description": "Disease to ranked drug candidates (UniProt, OpenTargets, "
                       "PDB/AlphaFold, ChEMBL, RDKit). Repurposing-first, SAScore-aware.",
        "required": ["--disease"],
    },
}


# ----- commands ------------------------------------------------------------

def cmd_mcp(args: argparse.Namespace) -> int:
    """Start the MCP server (stdio). Plug into Claude Code, Cursor, etc."""
    from .mcp_server import main as mcp_main
    mcp_main()
    return 0


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


def cmd_explore(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_explore(args))


async def _cmd_explore(args: argparse.Namespace) -> int:
    from .services.underexplored import find_underexplored_targets
    print(_color("hermes-bio :: explore", BOLD))
    print(_color(f"  hunting underexplored druggable targets for: {args.disease}", DIM))
    print(_color("  filter: high genetic association | low max_phase | structure available", DIM))
    print()
    rows = await find_underexplored_targets(args.disease, top_n=args.top)
    if not rows:
        print(_color("  no targets found", DIM))
        return 1
    print(_color(f"  {'symbol':<10} {'uniprot':<10} {'assoc':>6} {'max_ph':>6} {'cmpds':>6} {'struct':>6}  {'score':>6}  label", DIM))
    print(_color("  " + "-" * 110, DIM))
    for r in rows[:args.top]:
        sym = (r["symbol"] or "?")[:10].ljust(10)
        u = (r["uniprot_id"] or "-")[:10].ljust(10)
        assoc = f"{r['association_score']:.2f}" if r["association_score"] else "  -  "
        u_score = r["underexplored_score"]
        score_color = EMERALD if u_score > 0.4 else AMBER if u_score > 0.2 else DIM
        score_str = _color(f"{u_score:.3f}", score_color)
        struct = "yes" if r["has_structure"] else "no"
        max_ph = r["max_phase_reached"]
        cmpds = r["compound_count"]
        print(f"  {_color(sym, EMERALD)} {u} {assoc:>6} {max_ph:>6} {cmpds:>6} {struct:>6}  {score_str:>15}  {r['label']}")
        if args.verbose and r["name"]:
            print(_color(f"             {r['name']}", DIM))
    if args.json:
        with open(args.json, "w") as f:
            json.dump(rows, f, indent=2)
        print(_color(f"\n  written {len(rows)} entries to {args.json}", DIM))
    return 0


def cmd_repurpose(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_repurpose(args))


async def _cmd_repurpose(args: argparse.Namespace) -> int:
    from .services.cross_repurposing import cross_indication_candidates
    from .services.opentargets import get_validated_targets

    excludes = [s.strip() for s in (args.exclude or "").split(",") if s.strip()]
    target = args.target

    if args.from_disease:
        print(_color(f"hermes-bio :: repurpose --from-disease", BOLD))
        print(_color(f"  picking top target for: {args.from_disease}", DIM))
        targets = await get_validated_targets(args.from_disease, size=5)
        chosen = next((t for t in targets if t.get("uniprot_id")), None)
        if not chosen:
            print(_color("  could not pick a target -- no OpenTargets hits with UniProt mapping", RED), file=sys.stderr)
            return 1
        target = chosen["uniprot_id"]
        print(_color(f"  picked: {target} ({chosen.get('symbol')}) -- {chosen.get('name')}", EMERALD))
        if not excludes:
            words = [w for w in args.from_disease.lower().split() if len(w) > 3]
            excludes = words
            print(_color(f"  auto-exclude keywords: {', '.join(excludes)}", DIM))
        print()

    print(_color(f"hermes-bio :: repurpose", BOLD))
    print(_color(f"  cross-indication hunt for target: {target}", DIM))
    if excludes:
        print(_color(f"  excluding indications matching: {', '.join(excludes)}", DIM))
    print()
    rows = await cross_indication_candidates(target, exclude_disease_keywords=excludes)
    if not rows:
        print(_color("  no candidates found", DIM))
        return 1
    print(_color(f"  {'name':<28} {'potency':>10} {'type':>5}  approved indications (non-excluded)", DIM))
    print(_color("  " + "-" * 110, DIM))
    cross = [r for r in rows if r.get("is_cross_indication")]
    for r in cross[:args.top]:
        name = (r["name"] or r["chembl_id"])[:28].ljust(28)
        pot = f"{r['potency_nm']:.1f}nM" if r["potency_nm"] < 1e6 else "-"
        t = (r["potency_type"] or "")[:5].rjust(5)
        ind = (r.get("all_indications_summary") or "-")[:70]
        print(f"  {_color(name, EMERALD)} {pot:>10} {t}  {ind}")
    print(_color(f"\n  {len(cross)} cross-indication candidates (out of {len(rows)} approved binders)", DIM))
    if not cross and rows:
        print(_color("  (no cross-indication hits -- all binders' approved indications match excluded keywords)", DIM))
        print(_color("  inspecting top binders for diagnostic:", DIM))
        for r in rows[:5]:
            name = (r.get("name") or r["chembl_id"])[:28].ljust(28)
            ind = (r.get("all_indications_summary") or "(no indication data)")[:70]
            print(f"    {name}  {ind}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump(rows, f, indent=2)
    return 0


def cmd_investigate(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_investigate(args))


async def _cmd_investigate(args: argparse.Namespace) -> int:
    from .services.opentargets import get_validated_targets
    from .services.underexplored import find_underexplored_targets
    from .services.cross_repurposing import cross_indication_candidates

    disease = args.disease
    print(_color("hermes-bio :: investigate", BOLD))
    print(_color(f"  unified workflow: pick target -> underexplored alternatives -> cross-indication leads", DIM))
    print(_color(f"  disease: {disease}", DIM))
    print()

    print(_color("[1] top OpenTargets target", BOLD))
    ts = await get_validated_targets(disease, size=5)
    chosen = next((t for t in ts if t.get("uniprot_id")), None)
    if not chosen:
        print(_color("  could not resolve disease to a target", RED), file=sys.stderr)
        return 1
    target_uniprot = chosen["uniprot_id"]
    print(_color(f"  {target_uniprot} ({chosen.get('symbol')}) -- {chosen.get('name')}", EMERALD))
    print(_color(f"  association_score = {chosen.get('association_score'):.3f}", DIM))
    print()

    print(_color("[2] underexplored alternative targets", BOLD))
    rows = await find_underexplored_targets(disease, top_n=10)
    high = [r for r in rows if r["underexplored_score"] > 0.15][:5]
    if not high:
        print(_color("  (no strongly underexplored alternatives in top OpenTargets hits)", DIM))
    for r in high:
        sc = r["underexplored_score"]
        sym = (r["symbol"] or "?")[:10].ljust(10)
        print(f"  {_color(sym, EMERALD)} {r['uniprot_id']:<10} score={sc:.3f}  {r['label']}")
    print()

    print(_color("[3] cross-indication repurposing on top target", BOLD))
    excludes = [w for w in disease.lower().split() if len(w) > 3]
    print(_color(f"  excluding indication keywords: {', '.join(excludes)}", DIM))
    cands = await cross_indication_candidates(target_uniprot, exclude_disease_keywords=excludes)
    cross = [c for c in cands if c.get("is_cross_indication")][:6]
    if not cross:
        print(_color("  (no cross-indication leads -- all approved binders are within-disease)", DIM))
    for c in cross:
        name = (c.get("name") or c["chembl_id"])[:28].ljust(28)
        pot = f"{c['potency_nm']:.1f}nM" if c["potency_nm"] < 1e6 else "-"
        ind = (c.get("all_indications_summary") or "-")[:60]
        print(f"  {_color(name, EMERALD)} {pot:>10}  {ind}")
    print()

    print(_color("[summary]", BOLD))
    print(f"  primary target:       {_color(target_uniprot, EMERALD)} ({chosen.get('symbol')})")
    print(f"  underexplored alts:   {len(high)}")
    print(f"  cross-indication:     {len(cross)} approved drugs with off-disease use")

    if args.json:
        out = {
            "disease": disease,
            "primary_target": chosen,
            "underexplored": high,
            "cross_indication": cross,
        }
        with open(args.json, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(_color(f"\n  written to {args.json}", DIM))

    return 0


def cmd_eval(args: argparse.Namespace) -> int:
    return asyncio.run(_cmd_eval(args))


async def _cmd_eval(args: argparse.Namespace) -> int:
    from . import eval as eval_mod
    diseases = args.diseases.split(",") if args.diseases else None
    print(_color("hermes-bio :: eval", BOLD))
    if args.hard:
        print(_color("  HARD MODE -- diseases without canonical targets; pick will need manual review", DIM))
    else:
        print(_color("  agentic harness regression -- does the agent recover canonical targets?", DIM))
    print()
    report = await eval_mod.run_eval(diseases, hard=args.hard)
    eval_mod.print_summary(report)
    if args.json:
        with open(args.json, "w") as f:
            json.dump(report, f, indent=2)
        print(_color(f"\n  report written to {args.json}", DIM))
    return 0 if report["passed"] == report["total"] else 1


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
    from .db import SessionLocal, Job
    async with SessionLocal() as s:
        s.add(Job(id=job_id, disease_input=args.disease, status="pending"))
        await s.commit()

    if args.output != "json":
        print(_color(f"hermes-bio :: drug-discovery", BOLD))
        print(_color(f"  disease: {args.disease}", DIM))
        print(_color(f"  job:     {job_id}", DIM))
        print()

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

    from .db import Job, SessionLocal as _SL
    async with _SL() as s:
        j = await s.get(Job, job_id)
        succeeded = bool(j and j.status == "completed")

    if args.output == "json":
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
        return 0 if succeeded else 1

    return 0 if succeeded else 1


def _print_event(evt: dict) -> None:
    t = evt.get("type")
    ts = (evt.get("ts") or "")[11:19]
    if t == "status":
        print(_color(f"[{ts}] status: {evt.get('status')}", DIM))
    elif t == "memory_recall":
        print(_color(f"[{ts}] memory recall:", PURPLE))
        for line in (evt.get("note") or "").splitlines():
            print(_color(f"         {line}", PURPLE))
    elif t == "reasoning":
        print(_color(f"[{ts}] reasoning: {evt.get('text', '')}", CYAN))
    elif t == "tool_call":
        args_s = ", ".join(f"{k}={truncate(str(v))}" for k, v in (evt.get("args") or {}).items())
        print(_color(f"[{ts}] call {evt.get('name')}({args_s})", EMERALD))
    elif t == "tool_result":
        print(_color(f"[{ts}] ok   {evt.get('name')} {truncate(evt.get('summary', ''), 100)}", DIM))
    elif t == "retry":
        print(_color(f"[{ts}] retry HTTP {evt.get('code')} in {evt.get('delay')}s", AMBER))
    elif t == "structured_result":
        print(_color(f"[{ts}] structured result captured", EMERALD))
    elif t == "done":
        print(_color(f"[{ts}] done -- pipeline complete -> {evt.get('report_path')}", GREEN))
    elif t == "error":
        print(_color(f"[{ts}] error: {evt.get('error')}", RED))


def truncate(s: str, n: int = 50) -> str:
    return s if len(s) <= n else s[:n] + "..."


# ----- argparse ------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="hermes-bio",
        description="An agentic harness for bioinformatics. Drug-discovery flagship skill.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run", help="run a skill end-to-end")
    p_run.add_argument("skill", choices=list(SKILLS.keys()))
    p_run.add_argument("--disease", help="disease name (drug-discovery skill)")
    p_run.add_argument("--output", choices=["pretty", "json"], default="pretty")
    p_run.add_argument("--gemini-key", help="override GEMINI_API_KEY for this run")
    p_run.add_argument("--model", help="override Gemini model (e.g. gemini-3.1-pro-preview)")
    p_run.set_defaults(func=cmd_run)

    p_mcp = sub.add_parser("mcp", help="start MCP server (stdio) -- connects to Claude Code / Cursor / any MCP host")
    p_mcp.set_defaults(func=cmd_mcp)

    p_skills = sub.add_parser("skills", help="manage skills")
    p_skills_sub = p_skills.add_subparsers(dest="skills_cmd", required=True)
    p_skills_list = p_skills_sub.add_parser("list", help="list available skills")
    p_skills_list.set_defaults(func=cmd_skills_list)

    p_exp = sub.add_parser("explore", help="hunt underexplored druggable targets for a disease (Mode B)")
    p_exp.add_argument("--disease", required=True)
    p_exp.add_argument("--top", type=int, default=10)
    p_exp.add_argument("--json", help="write JSON report")
    p_exp.add_argument("-v", "--verbose", action="store_true")
    p_exp.set_defaults(func=cmd_explore)

    p_rep = sub.add_parser("repurpose", help="find FDA-approved drugs that bind a target but are approved for OTHER conditions (Mode C)")
    p_rep.add_argument("--target", help="UniProt ID, e.g. P00533")
    p_rep.add_argument("--from-disease", help="auto-pick top target for this disease then repurpose on it")
    p_rep.add_argument("--exclude", help="comma-separated keywords matching primary indication to skip")
    p_rep.add_argument("--top", type=int, default=15)
    p_rep.add_argument("--json", help="write JSON report")
    p_rep.set_defaults(func=cmd_repurpose)

    p_inv = sub.add_parser("investigate", help="unified workflow: pick target -> underexplored alts -> cross-indication")
    p_inv.add_argument("--disease", required=True)
    p_inv.add_argument("--json", help="write JSON report")
    p_inv.set_defaults(func=cmd_investigate)

    p_eval = sub.add_parser("eval", help="run the canonical-targets regression suite (Mode A)")
    p_eval.add_argument("--diseases", help="comma-separated subset (default: all)")
    p_eval.add_argument("--json", help="write full report JSON to this path")
    p_eval.add_argument("--hard", action="store_true", help="run hard-mode diseases (no canonical answer)")
    p_eval.add_argument("--model", help="override Gemini model")
    p_eval.set_defaults(func=cmd_eval)

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
    try:
        sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
        sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    except Exception:
        pass
    parser = build_parser()
    args = parser.parse_args(argv)
    if getattr(args, "gemini_key", None):
        os.environ["GEMINI_API_KEY"] = args.gemini_key
    if getattr(args, "model", None):
        from .config import settings
        settings.gemini_model = args.model
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
