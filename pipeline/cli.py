from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Optional

from .algo_registry import list_algos
from .runner import (
    default_rule_for_level,
    run_blocks,
    run_collector,
    run_instrument_stage,
    run_schedule_stage,
    run_timing_stage,
)
from .rules_registry import list_rules
from .timing_config import DEFAULT_TIMING_REPEATS


def _print_json(payload) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _resolve_base_name(base_name: Optional[str], source: Optional[Path], expand: Optional[Path]) -> str:
    if base_name:
        return base_name
    if source is not None:
        return source.stem
    if expand is not None:
        stem = expand.stem
        if stem.endswith(".233r"):
            stem = stem[:-5]
        if "." in stem:
            stem = stem.split(".", 1)[0]
        return stem
    raise SystemExit("base_name unresolved; provide --base-name or --source/--expand")


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Pipeline modular workflow CLI")
    ap.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1])
    sub = ap.add_subparsers(dest="cmd", required=True)

    c_collect = sub.add_parser("collect", help="Generate pipeline block_info")
    c_collect.add_argument("--base-name", default=None)
    c_collect.add_argument("--source", type=Path, required=True)

    c_blocks = sub.add_parser("blocks", help="Run one block rule")
    c_blocks.add_argument("--base-name", required=True)
    c_blocks.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_blocks.add_argument("--rule", default=None)
    c_blocks.add_argument("--source", type=Path, default=None)

    c_timing = sub.add_parser("timing", help="Run timing stage")
    c_timing.add_argument("--base-name", required=True)
    c_timing.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_timing.add_argument("--rule", required=True)
    c_timing.add_argument("--repeats", type=int, default=DEFAULT_TIMING_REPEATS)

    c_sched = sub.add_parser("schedule", help="Run schedule stage")
    c_sched.add_argument("--base-name", required=True)
    c_sched.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_sched.add_argument("--rule", required=True)
    c_sched.add_argument("--algo", default="LPF")

    c_inst = sub.add_parser("instrument", help="Run instrument stage")
    c_inst.add_argument("--base-name", required=True)
    c_inst.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_inst.add_argument("--rule", required=True)
    c_inst.add_argument("--algo", default="LPF")
    c_inst.add_argument("--mode", default="auto", choices=["auto", "specialized", "generic"])

    c_info = sub.add_parser("list", help="List rules and algos")
    c_info.add_argument("--level", default=None, choices=["level1", "level2", "level3"])

    c_all = sub.add_parser("run_all", help="Run full pipeline (collect → blocks → timing → schedule × 6 → instrument × 6)")
    c_all.add_argument("--source", type=Path, required=True, help="Source file path, e.g. source_files/zhang1/zhang1.c")
    c_all.add_argument("--base-name", default=None, help="Test case name (defaults to source file stem)")
    c_all.add_argument("--level", default="level2", choices=["level1", "level2", "level3"])
    c_all.add_argument("--rule", default="effective_line_merge")
    c_all.add_argument("--repeats", type=int, default=DEFAULT_TIMING_REPEATS)
    c_all.add_argument("--mode", default="auto", choices=["auto", "specialized", "generic"])

    args = ap.parse_args(argv)
    base_dir = args.base_dir.resolve()

    if args.cmd == "collect":
        base_name = _resolve_base_name(args.base_name, args.source, None)
        payload = run_collector(base_dir=base_dir, base_name=base_name, source_file=args.source.resolve())
        _print_json(payload)
        return 0

    if args.cmd == "blocks":
        rule_name = args.rule or default_rule_for_level(args.level)
        if not rule_name:
            raise SystemExit(f"no rule configured for {args.level}")
        payload = run_blocks(
            base_dir=base_dir,
            base_name=args.base_name,
            level=args.level,
            rule_name=rule_name,
            source_file=args.source.resolve() if args.source else None,
        )
        _print_json(payload)
        return 0

    if args.cmd == "timing":
        payload = run_timing_stage(
            base_dir=base_dir,
            base_name=args.base_name,
            level=args.level,
            rule_name=args.rule,
            repeats=args.repeats,
        )
        _print_json(payload)
        return 0

    if args.cmd == "schedule":
        payload = run_schedule_stage(
            base_dir=base_dir,
            base_name=args.base_name,
            level=args.level,
            rule_name=args.rule,
            algo_name=args.algo,
        )
        _print_json(payload)
        return 0

    if args.cmd == "instrument":
        payload = run_instrument_stage(
            base_dir=base_dir,
            base_name=args.base_name,
            level=args.level,
            rule_name=args.rule,
            algo_name=args.algo,
            instrument_mode=args.mode,
        )
        _print_json(payload)
        return 0

    if args.cmd == "list":
        if args.level:
            _print_json({"level": args.level, "rules": sorted(list_rules(args.level).keys()), "algos": sorted(list_algos().keys())})
        else:
            _print_json(
                {
                    "rules": {lvl: sorted(list_rules(lvl).keys()) for lvl in ("level1", "level2", "level3")},
                    "algos": sorted(list_algos().keys()),
                }
            )
        return 0

    if args.cmd == "run_all":
        import os
        import subprocess as _sp
        import sys
        source = args.source.resolve()
        base_name = _resolve_base_name(args.base_name, source, None)
        level = args.level
        rule = args.rule or default_rule_for_level(level) or "effective_line_merge"
        algos = sorted(list_algos().keys())

        print(f"=== Pipeline full workflow: {base_name} ===")
        print(f"    Source file: {source}")
        print(f"    level={level}, rule={rule}")
        print(f"    Algorithms: {', '.join(algos)}")
        print()

        # Stage 1: Source preparation (confirm source file exists)
        print("=== Stage 1: Source preparation ===")
        if not source.exists():
            print(f"    ✗ Source file not found: {source}")
            return 1
        print(f"    ✓ Source file: {source}")

        # Stage 2: Compile and expand (discover GCC-generated *.expand dump)
        print("=== Stage 2: Compile and expand ===")
        expand_pattern = f"{source.name}.*r.expand"
        gcc_cmd = ["gcc", "-fdump-rtl-expand", "-c", str(source), "-o", str(source.parent / f"{source.stem}.o")]
        result = _sp.run(gcc_cmd, cwd=str(source.parent), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ✗ GCC compilation failed: {result.stderr[:500]}")
            return 1
        expand_candidates = sorted(source.parent.glob(expand_pattern), key=lambda p: p.stat().st_mtime, reverse=True)
        expand_file = expand_candidates[0] if expand_candidates else None
        if expand_file is None:
            print(f"    ✗ Expand file not generated under: {source.parent / expand_pattern}")
            return 1
        print(f"    ✓ expand: {expand_file}")

        # Stage 3: DAG generation
        print("=== Stage 3: DAG generation ===")
        gen_env = dict(os.environ)
        gen_env["PYTHONPATH"] = str(base_dir.parent)

        # 3a: Generate threads-only view (config_files/{base_name}_threads.dot)
        gen_cmd_threads = [
            sys.executable, "-m",
            f"{base_dir.name}.generation.legacy",
            str(expand_file),
            "--threads-only",
            "--source-file", str(source),
            "--output-base", str(base_dir),
            "--force",
        ]
        result = _sp.run(gen_cmd_threads, cwd=str(base_dir.parent), capture_output=True, text=True, env=gen_env)
        if result.returncode != 0:
            print(f"    ✗ DAG generation (threads) failed: {result.stderr[:500]}")
            return 1
        print(f"    ✓ Threads view generation Completedd")

        # 3b: Generate full DAG view (config_files/{base_name}.dot)
        gen_cmd_full = [
            sys.executable, "-m",
            f"{base_dir.name}.generation.legacy",
            str(expand_file),
            "--source-file", str(source),
            "--output-base", str(base_dir),
            "--force",
        ]
        result = _sp.run(gen_cmd_full, cwd=str(base_dir.parent), capture_output=True, text=True, env=gen_env)
        if result.returncode != 0:
            print(f"    ✗ DAG generation (full) failed: {result.stderr[:500]}")
            return 1
        print(f"    ✓ Full DAG view generation Completedd")

        # 3c: Ensure dag_generation/dag.dot exists (required by collector pre-check)
        results_root = base_dir / "intermediate_results" / base_name
        dag_dot_path = results_root / "dag_generation" / "dag.dot"
        if not dag_dot_path.exists():
            dag_dot_path.parent.mkdir(parents=True, exist_ok=True)
            # Copy full view dot file as dag.dot
            config_dot = results_root / "config_files" / f"{base_name}.dot"
            if config_dot.exists():
                import shutil
                shutil.copy2(config_dot, dag_dot_path)
                print(f"    ✓ dag.dot copied from full view")
            else:
                dag_dot_path.touch()
                print(f"    ✓ dag.dot created (empty)")
        print(f"    ✓ DAG generation Completedd")

        # Stage 4: Collect
        print("=== Stage 4: Collect ===")
        payload = run_collector(base_dir=base_dir, base_name=base_name, source_file=source)
        print(f"    ✓ Collect Completedd")

        # Stage 5: Blocks
        print("=== Stage 5: Blocks ===")
        payload = run_blocks(base_dir=base_dir, base_name=base_name, level=level, rule_name=rule)
        print(f"    ✓ Blocks Completedd")

        # Stage 6: Timing
        print("=== Stage 6: Timing ===")
        payload = run_timing_stage(base_dir=base_dir, base_name=base_name, level=level, rule_name=rule, repeats=args.repeats)
        print(f"    ✓ Timing Completedd")

        # Stage 7: Schedule (6 algorithms)
        print("=== Stage 7: Schedule ===")
        for algo in algos:
            payload = run_schedule_stage(base_dir=base_dir, base_name=base_name, level=level, rule_name=rule, algo_name=algo)
            prio_count = len(payload.get("priorities", {}))
            print(f"    ✓ {algo}: {prio_count} priorities")

        # Stage 8: Instrument (6 algorithms)
        print("=== Stage 8: Instrument ===")
        for algo in algos:
            payload = run_instrument_stage(
                base_dir=base_dir, base_name=base_name, level=level,
                rule_name=rule, algo_name=algo, instrument_mode=args.mode,
            )
            prio_count = payload.get("priority_count", 0)
            print(f"    ✓ {algo}: {prio_count} priorities instrumented")

        print()
        print(f"=== Completed: {base_name} all 8 stages ===")
        print(f"    result: {payload.get('result_dir', '')}")
        print(f"    timing: {payload.get('timing_dir', '')}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
