#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
sys.path.insert(0, str(REPO))

from tools.runtime_compare.utils.affinity import rewrite_sched_setaffinity_cpu_set, run_with_affinity
from tools.runtime_compare.utils.time_parse import parse_internal_time_seconds

WORK_SCALE = 10
REPEATS = 10
CPU_SET = [0, 1]
CORES_PER_TASK = 2

BASES = ["zhang1", "zhang2", "zhang3"]
ALGO = "zhao2020"
RULE = "effective_line_merge"

MANUAL_ROOT = ROOT / "manual_runs"
RUNTIME_ROOT = ROOT / "runtime_results"
CONFIG_PATH = ROOT / "runtime_task.json"
REPORT_JSON = ROOT / "report.json"
REPORT_MD = ROOT / "实验报告.md"


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def summarize_ns(values_ns: list[int]) -> dict[str, float]:
    vals = [float(v) for v in values_ns]
    return {
        "count": float(len(vals)),
        "mean_ns": float(statistics.fmean(vals)),
        "min_ns": float(min(vals)),
        "max_ns": float(max(vals)),
        "stddev_ns": float(statistics.pstdev(vals) if len(vals) > 1 else 0.0),
    }


def inject_main_timer(source_text: str) -> str:
    helper = """
#include <stdint.h>

static uint64_t my_now_ns(void) {
  struct timespec ts;
#ifdef CLOCK_MONOTONIC_RAW
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
#else
  clock_gettime(CLOCK_MONOTONIC, &ts);
#endif
  return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}
"""
    if "static uint64_t my_now_ns(void)" not in source_text:
        if "#include <time.h>\n" in source_text:
            source_text = source_text.replace("#include <time.h>\n", "#include <time.h>\n" + helper, 1)
        else:
            source_text = helper + "\n" + source_text
    source_text, n1 = re.subn(
        r"(int\s+main\s*\(\s*void\s*\)\s*\{\s*\n)",
        r"\1  uint64_t __prog_t0_ns = my_now_ns();\n",
        source_text,
        count=1,
    )
    source_text, n2 = re.subn(
        r"(\n)([ \t]*)return\s+0\s*;\s*\n([ \t]*)\}\s*$",
        r'\1\2fprintf(stderr, "PROGRAM_TOTAL_NS=%llu\\n", (unsigned long long)(my_now_ns() - __prog_t0_ns));\n\2return 0;\n\3}\n',
        source_text,
        count=1,
    )
    if n1 != 1 or n2 != 1 or "PROGRAM_TOTAL_NS=" not in source_text:
        raise RuntimeError("failed to inject PROGRAM_TOTAL_NS printer into main()")
    return source_text


def prepare_manual_source(src_path: Path, dst_dir: Path) -> Path:
    dst_dir.mkdir(parents=True, exist_ok=True)
    text = read_text(src_path)
    text, _ = rewrite_sched_setaffinity_cpu_set(text, CPU_SET)
    text = inject_main_timer(text)
    dst_path = dst_dir / src_path.name
    write_text(dst_path, text)
    if '#include "prio_runtime.h"' in text:
        shutil.copy2(REPO / "level1" / "prio_runtime.h", dst_dir / "prio_runtime.h")
    return dst_path


def compile_manual_source(src_path: Path, out_bin: Path) -> str:
    cmd = [
        "gcc",
        "-O0",
        "-g",
        "-std=c11",
        "-pthread",
        "-lm",
        "-I",
        str(src_path.parent),
        f"-DWORK_SCALE={WORK_SCALE}",
        src_path.name,
        "-o",
        str(out_bin),
    ]
    proc = subprocess.run(cmd, cwd=src_path.parent, capture_output=True, text=True)
    write_text(
        src_path.parent / "compile.log",
        "CMD: " + " ".join(cmd) + "\n" + (proc.stdout or "") + (proc.stderr or ""),
    )
    if proc.returncode != 0:
        raise RuntimeError(f"compile failed: {src_path}\n{proc.stderr[-400:]}")
    return " ".join(cmd)


def run_manual_binary(bin_path: Path) -> dict[str, Any]:
    env = dict()
    env.update({"WORK_SCALE": str(WORK_SCALE)})
    runs: list[dict[str, Any]] = []
    times_ns: list[int] = []
    for idx in range(REPEATS):
        rc, stdout, stderr, wall_ns = run_with_affinity(
            [str(bin_path)],
            cwd=bin_path.parent,
            env=env,
            cpu_set=CPU_SET,
            use_sudo=False,
        )
        write_text(bin_path.parent / f"run_{idx+1:02d}.stdout.log", stdout or "")
        write_text(bin_path.parent / f"run_{idx+1:02d}.stderr.log", stderr or "")
        parsed_s = parse_internal_time_seconds(stdout or "", stderr or "")
        if rc != 0 or parsed_s is None:
            raise RuntimeError(f"manual run failed: {bin_path} rc={rc}")
        parsed_ns = int(round(parsed_s * 1e9))
        times_ns.append(parsed_ns)
        runs.append(
            {
                "run": idx + 1,
                "program_total_ns": parsed_ns,
                "wall_ns": int(wall_ns),
                "returncode": int(rc),
            }
        )
    return {
        "times_ns": times_ns,
        "summary_ns": summarize_ns(times_ns),
        "runs": runs,
    }


def source_pair(base: str) -> tuple[Path, Path]:
    root = REPO / "中间结果" / base / "pipeline" / "instrument" / "level2" / RULE / ALGO
    return root / "source_original.c", root / "source_instrumented.c"


def run_runtime_compare() -> list[Path]:
    summaries: list[Path] = []
    stdout_blocks: list[str] = []
    stderr_blocks: list[str] = []
    for base in BASES:
        baseline_c, prio_c = source_pair(base)
        config_path = ROOT / f"runtime_task_{base}.json"
        config = {
            "tasks": [
                {
                    "baseline_c": str(baseline_c),
                    "prio_c": str(prio_c),
                    "work_scale": WORK_SCALE,
                    "repeats": REPEATS,
                    "cores_per_task": CORES_PER_TASK,
                    "cpu_list": CPU_SET,
                    "use_sudo": False,
                }
            ],
            "queue_mode": True,
        }
        write_text(config_path, json.dumps(config, ensure_ascii=False, indent=2))
        before = set(RUNTIME_ROOT.rglob("summary.json"))
        cmd = [
            "python3",
            str(REPO / "tools" / "runtime_compare" / "main.py"),
            "--cli",
            "--results-root",
            str(RUNTIME_ROOT),
            "--config",
            str(config_path),
            "--wait",
        ]
        proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
        stdout_blocks.append(f"== {base} ==\n{proc.stdout or ''}")
        stderr_blocks.append(f"== {base} ==\n{proc.stderr or ''}")
        if proc.returncode != 0:
            raise RuntimeError(f"runtime_compare failed for {base}\n{proc.stderr[-400:]}")
        after = set(RUNTIME_ROOT.rglob("summary.json"))
        new_items = sorted(after - before)
        if len(new_items) != 1:
            raise RuntimeError(f"unexpected runtime summary count for {base}: {len(new_items)}")
        summaries.extend(new_items)
    write_text(ROOT / "runtime_compare.stdout.log", "\n".join(stdout_blocks))
    write_text(ROOT / "runtime_compare.stderr.log", "\n".join(stderr_blocks))
    return summaries


def rel_gap_pct(a_ns: float, b_ns: float) -> float:
    if abs(a_ns) < 1e-12:
        return 0.0
    return abs(a_ns - b_ns) / abs(a_ns) * 100.0


def build_report(manual: dict[str, Any], runtime_summaries: list[Path]) -> dict[str, Any]:
    runtime_by_base: dict[str, dict[str, Any]] = {}
    for path in runtime_summaries:
        data = json.loads(read_text(path))
        base = Path(data["baseline"]["c_file"]).parents[5].name
        runtime_by_base[base] = {
            "summary_path": str(path),
            "baseline": data["baseline"],
            "prio": data["prio"],
            "raw": data,
        }

    cases: list[dict[str, Any]] = []
    baseline_gaps: list[float] = []
    prio_gaps: list[float] = []

    for base in BASES:
        runtime_item = runtime_by_base[base]
        manual_baseline = manual[base]["baseline"]
        manual_prio = manual[base]["prio"]

        runtime_baseline_mean_ns = float(runtime_item["baseline"]["stats"]["mean_s"]) * 1e9
        runtime_prio_mean_ns = float(runtime_item["prio"]["stats"]["mean_s"]) * 1e9
        manual_baseline_mean_ns = float(manual_baseline["summary_ns"]["mean_ns"])
        manual_prio_mean_ns = float(manual_prio["summary_ns"]["mean_ns"])

        baseline_gap_pct = rel_gap_pct(manual_baseline_mean_ns, runtime_baseline_mean_ns)
        prio_gap_pct = rel_gap_pct(manual_prio_mean_ns, runtime_prio_mean_ns)
        baseline_gaps.append(baseline_gap_pct)
        prio_gaps.append(prio_gap_pct)

        cases.append(
            {
                "base": base,
                "runtime_summary_path": runtime_item["summary_path"],
                "manual": {
                    "baseline": manual_baseline,
                    "prio": manual_prio,
                },
                "runtime": {
                    "baseline_times_ns": [int(round(float(x) * 1e9)) for x in runtime_item["baseline"]["times_s"]],
                    "baseline_summary_ns": {
                        "mean_ns": runtime_baseline_mean_ns,
                        "min_ns": float(runtime_item["baseline"]["stats"]["min_s"]) * 1e9,
                        "max_ns": float(runtime_item["baseline"]["stats"]["max_s"]) * 1e9,
                        "count": float(runtime_item["baseline"]["stats"]["n"]),
                    },
                    "prio_times_ns": [int(round(float(x) * 1e9)) for x in runtime_item["prio"]["times_s"]],
                    "prio_summary_ns": {
                        "mean_ns": runtime_prio_mean_ns,
                        "min_ns": float(runtime_item["prio"]["stats"]["min_s"]) * 1e9,
                        "max_ns": float(runtime_item["prio"]["stats"]["max_s"]) * 1e9,
                        "count": float(runtime_item["prio"]["stats"]["n"]),
                    },
                },
                "comparison": {
                    "baseline_mean_gap_pct": baseline_gap_pct,
                    "prio_mean_gap_pct": prio_gap_pct,
                    "baseline_delta_ns": runtime_baseline_mean_ns - manual_baseline_mean_ns,
                    "prio_delta_ns": runtime_prio_mean_ns - manual_prio_mean_ns,
                },
            }
        )

    return {
        "work_scale": WORK_SCALE,
        "repeats": REPEATS,
        "cpu_set": CPU_SET,
        "cores_per_task": CORES_PER_TASK,
        "cases": cases,
        "overall": {
            "baseline_mean_gap_pct": summarize_ns([int(round(x * 1e6)) for x in baseline_gaps]),
            "prio_mean_gap_pct": summarize_ns([int(round(x * 1e6)) for x in prio_gaps]),
        },
    }


def render_report_md(report: dict[str, Any]) -> str:
    lines = [
        "# zhang1/2/3 runtime 工具与程序体内手动测时校验",
        "",
        "## 1. 实验目的",
        "",
        "- 验证 `runtime_compare` 输出是否与程序体内手动计时口径一致。",
        "- 手动测时方式：直接在 `main` 函数体内记录开始/结束时间，并输出 `PROGRAM_TOTAL_NS`。",
        "- 对象：`zhang1`、`zhang2`、`zhang3` 的 `zhao2020` baseline/prio 两个版本。",
        "",
        "## 2. 实验配置",
        "",
        f"- `work_scale = {report['work_scale']}`",
        f"- `repeats = {report['repeats']}`",
        f"- `cpu_set = {report['cpu_set']}`",
        f"- `cores_per_task = {report['cores_per_task']}`",
        "",
        "## 3. 结果对比",
        "",
        "| 程序 | 版本 | 手动均值(ns) | runtime均值(ns) | 偏差 |",
        "|---|---|---:|---:|---:|",
    ]
    for case in report["cases"]:
        lines.append(
            f"| {case['base']} | baseline | {case['manual']['baseline']['summary_ns']['mean_ns']:.1f} | "
            f"{case['runtime']['baseline_summary_ns']['mean_ns']:.1f} | {case['comparison']['baseline_mean_gap_pct']:.3f}% |"
        )
        lines.append(
            f"| {case['base']} | prio | {case['manual']['prio']['summary_ns']['mean_ns']:.1f} | "
            f"{case['runtime']['prio_summary_ns']['mean_ns']:.1f} | {case['comparison']['prio_mean_gap_pct']:.3f}% |"
        )
    lines.extend(
        [
            "",
            "## 4. 结论",
            "",
            "- 以上对比基于真实运行数据，不是估算值。",
            "- 若 `手动均值` 与 `runtime均值` 的偏差保持很小，说明 `runtime_compare` 的内部计时读取口径是可信的。",
            "- 详细原始数据见 `report.json` 以及各子目录中的 `run_*.stderr.log`、`summary.json`。",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    if MANUAL_ROOT.exists():
        shutil.rmtree(MANUAL_ROOT)
    if RUNTIME_ROOT.exists():
        shutil.rmtree(RUNTIME_ROOT)

    manual: dict[str, Any] = {}
    for base in BASES:
        baseline_src, prio_src = source_pair(base)
        manual[base] = {}
        for label, src in (("baseline", baseline_src), ("prio", prio_src)):
            case_dir = MANUAL_ROOT / base / label
            prepared_src = prepare_manual_source(src, case_dir)
            bin_path = case_dir / ("app_" + label)
            compile_cmd = compile_manual_source(prepared_src, bin_path)
            run_data = run_manual_binary(bin_path)
            manual[base][label] = {
                "source": str(src),
                "prepared_source": str(prepared_src),
                "compile_cmd": compile_cmd,
                **run_data,
            }

    runtime_summaries = run_runtime_compare()
    report = build_report(manual, runtime_summaries)
    write_text(REPORT_JSON, json.dumps(report, ensure_ascii=False, indent=2))
    write_text(REPORT_MD, render_report_md(report))
    print(f"report: {REPORT_JSON}")
    print(f"report_md: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
