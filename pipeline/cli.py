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
    c_sched.add_argument("--algo", default="cpf")

    c_inst = sub.add_parser("instrument", help="Run instrument stage")
    c_inst.add_argument("--base-name", required=True)
    c_inst.add_argument("--level", required=True, choices=["level1", "level2", "level3"])
    c_inst.add_argument("--rule", required=True)
    c_inst.add_argument("--algo", default="cpf")
    c_inst.add_argument("--mode", default="auto", choices=["auto", "specialized", "generic"])

    c_info = sub.add_parser("list", help="List rules and algos")
    c_info.add_argument("--level", default=None, choices=["level1", "level2", "level3"])

    c_all = sub.add_parser("run_all", help="Run full pipeline (collect → blocks → timing → schedule × 6 → instrument × 6)")
    c_all.add_argument("--source", type=Path, required=True, help="源文件路径，如 源文件/zhang1/zhang1.c")
    c_all.add_argument("--base-name", default=None, help="测试用例名（默认取源文件名）")
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

        print(f"=== Pipeline 完整流程: {base_name} ===")
        print(f"    源文件: {source}")
        print(f"    level={level}, rule={rule}")
        print(f"    算法: {', '.join(algos)}")
        print()

        # 第1阶段: 源码准备（确认源文件存在）
        print("=== 第1阶段: 源码准备 ===")
        if not source.exists():
            print(f"    ✗ 源文件不存在: {source}")
            return 1
        print(f"    ✓ 源文件: {source}")

        # 第2阶段: 编译展开（生成 .233r.expand）
        print("=== 第2阶段: 编译展开 ===")
        expand_file = source.parent / f"{source.name}.233r.expand"
        gcc_cmd = ["gcc", "-fdump-rtl-expand", "-c", str(source), "-o", str(source.parent / f"{source.stem}.o")]
        result = _sp.run(gcc_cmd, cwd=str(source.parent), capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    ✗ GCC 编译失败: {result.stderr[:500]}")
            return 1
        if not expand_file.exists():
            print(f"    ✗ expand 文件未生成: {expand_file}")
            return 1
        print(f"    ✓ expand: {expand_file}")

        # 第3阶段: DAG 生成
        print("=== 第3阶段: DAG 生成 ===")
        gen_env = dict(os.environ)
        gen_env["PYTHONPATH"] = str(base_dir.parent)

        # 3a: 生成 threads-only 视图 (配置文件/{base_name}_threads.dot)
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
            print(f"    ✗ DAG 生成(threads)失败: {result.stderr[:500]}")
            return 1
        print(f"    ✓ threads 视图生成完成")

        # 3b: 生成完整 DAG 视图 (配置文件/{base_name}.dot)
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
            print(f"    ✗ DAG 生成(full)失败: {result.stderr[:500]}")
            return 1
        print(f"    ✓ 完整 DAG 视图生成完成")

        # 3c: 确保 生成dag图/dag.dot 存在 (collector 前置检查需要)
        results_root = base_dir / "中间结果" / base_name
        dag_dot_path = results_root / "生成dag图" / "dag.dot"
        if not dag_dot_path.exists():
            dag_dot_path.parent.mkdir(parents=True, exist_ok=True)
            # 复制完整视图 dot 文件作为 dag.dot
            config_dot = results_root / "配置文件" / f"{base_name}.dot"
            if config_dot.exists():
                import shutil
                shutil.copy2(config_dot, dag_dot_path)
                print(f"    ✓ dag.dot 已从完整视图复制")
            else:
                dag_dot_path.touch()
                print(f"    ✓ dag.dot 已创建(空)")
        print(f"    ✓ DAG 生成完成")

        # 第4阶段: Collect
        print("=== 第4阶段: Collect ===")
        payload = run_collector(base_dir=base_dir, base_name=base_name, source_file=source)
        print(f"    ✓ Collect 完成")

        # 第5阶段: Blocks
        print("=== 第5阶段: Blocks ===")
        payload = run_blocks(base_dir=base_dir, base_name=base_name, level=level, rule_name=rule)
        print(f"    ✓ Blocks 完成")

        # 第6阶段: Timing
        print("=== 第6阶段: Timing ===")
        payload = run_timing_stage(base_dir=base_dir, base_name=base_name, level=level, rule_name=rule, repeats=args.repeats)
        print(f"    ✓ Timing 完成")

        # 第7阶段: Schedule (6 个算法)
        print("=== 第7阶段: Schedule ===")
        for algo in algos:
            payload = run_schedule_stage(base_dir=base_dir, base_name=base_name, level=level, rule_name=rule, algo_name=algo)
            prio_count = len(payload.get("priorities", {}))
            print(f"    ✓ {algo}: {prio_count} 个优先级")

        # 第8阶段: Instrument (6 个算法)
        print("=== 第8阶段: Instrument ===")
        for algo in algos:
            payload = run_instrument_stage(
                base_dir=base_dir, base_name=base_name, level=level,
                rule_name=rule, algo_name=algo, instrument_mode=args.mode,
            )
            prio_count = payload.get("priority_count", 0)
            print(f"    ✓ {algo}: {prio_count} 个优先级插桩")

        print()
        print(f"=== 完成: {base_name} 全部 8 个阶段 ===")
        print(f"    result: {payload.get('result_dir', '')}")
        print(f"    timing: {payload.get('timing_dir', '')}")
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
