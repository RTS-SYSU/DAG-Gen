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
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"))
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

    c_sched = sub.add_parser("schedule", help="Run schedule stage")
    c_sched.add_argument("--base-name", required=True)
    c_sched.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_sched.add_argument("--rule", required=True)
    c_sched.add_argument("--algo", default="cpf")

    c_inst = sub.add_parser("instrument", help="Run instrument stage")
    c_inst.add_argument("--base-name", required=True)
    c_inst.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_inst.add_argument("--rule", required=True)
    c_inst.add_argument("--algo", default="cpf")
    c_inst.add_argument("--mode", default="auto", choices=["auto", "specialized", "generic"])

    c_info = sub.add_parser("list", help="List rules and algos")
    c_info.add_argument("--level", default=None, choices=["level1", "level2", "level3"])

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

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
