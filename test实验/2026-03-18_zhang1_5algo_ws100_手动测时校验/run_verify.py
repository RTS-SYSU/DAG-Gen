#!/usr/bin/env python3
"""zhang1 五算法 runtime vs 手动测时校验 (ws=100, r=10)"""
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

WORK_SCALE = 100
REPEATS = 10
CPU_SET = [0, 1]
CORES_PER_TASK = 2

BASES = ["zhang1"]
ALGOS = ["cpf", "heft", "zhao2020", "wcet_first", "t_level"]
RULE = "effective_line_merge"

MANUAL_ROOT = ROOT / "manual_runs"
RUNTIME_ROOT = ROOT / "runtime_results"
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
        "gcc", "-O0", "-g", "-std=c11", "-pthread", "-lm",
        "-I", str(src_path.parent),
        f"-DWORK_SCALE={WORK_SCALE}",
        src_path.name, "-o", str(out_bin),
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
    env = {"WORK_SCALE": str(WORK_SCALE)}
    runs: list[dict[str, Any]] = []
    times_ns: list[int] = []
    for idx in range(REPEATS):
        rc, stdout, stderr, wall_ns = run_with_affinity(
            [str(bin_path)], cwd=bin_path.parent, env=env,
            cpu_set=CPU_SET, use_sudo=False,
        )
        write_text(bin_path.parent / f"run_{idx+1:02d}.stdout.log", stdout or "")
        write_text(bin_path.parent / f"run_{idx+1:02d}.stderr.log", stderr or "")
        parsed_s = parse_internal_time_seconds(stdout or "", stderr or "")
        if rc != 0 or parsed_s is None:
            raise RuntimeError(f"manual run failed: {bin_path} rc={rc}")
        parsed_ns = int(round(parsed_s * 1e9))
        times_ns.append(parsed_ns)
        runs.append({
            "run": idx + 1,
            "program_total_ns": parsed_ns,
            "wall_ns": int(wall_ns),
            "returncode": int(rc),
        })
    return {"times_ns": times_ns, "summary_ns": summarize_ns(times_ns), "runs": runs}


def source_pair(base: str, algo: str) -> tuple[Path, Path]:
    root = REPO / "中间结果" / base / "pipeline" / "instrument" / "level2" / RULE / algo
    return root / "source_original.c", root / "source_instrumented.c"


def run_runtime_compare_for_algo(base: str, algo: str) -> Path:
    baseline_c, prio_c = source_pair(base, algo)
    config_path = ROOT / f"runtime_task_{base}_{algo}.json"
    config = {
        "tasks": [{
            "baseline_c": str(baseline_c),
            "prio_c": str(prio_c),
            "work_scale": WORK_SCALE,
            "repeats": REPEATS,
            "cores_per_task": CORES_PER_TASK,
            "cpu_list": CPU_SET,
            "use_sudo": False,
        }],
        "queue_mode": True,
    }
    write_text(config_path, json.dumps(config, ensure_ascii=False, indent=2))
    algo_runtime_root = RUNTIME_ROOT / f"{base}_{algo}"
    algo_runtime_root.mkdir(parents=True, exist_ok=True)
    before = set(algo_runtime_root.rglob("summary.json"))
    cmd = [
        "python3",
        str(REPO / "tools" / "runtime_compare" / "main.py"),
        "--cli", "--results-root", str(algo_runtime_root),
        "--config", str(config_path), "--wait",
    ]
    print(f"  running runtime_compare for {base}/{algo} ...")
    proc = subprocess.run(cmd, cwd=REPO, capture_output=True, text=True)
    write_text(ROOT / f"runtime_{base}_{algo}.stdout.log", proc.stdout or "")
    write_text(ROOT / f"runtime_{base}_{algo}.stderr.log", proc.stderr or "")
    if proc.returncode != 0:
        raise RuntimeError(f"runtime_compare failed for {base}/{algo}\n{proc.stderr[-400:]}")
    after = set(algo_runtime_root.rglob("summary.json"))
    new_items = sorted(after - before)
    if len(new_items) != 1:
        raise RuntimeError(f"unexpected summary count for {base}/{algo}: {len(new_items)}")
    return new_items[0]


def rel_gap_pct(a_ns: float, b_ns: float) -> float:
    if abs(a_ns) < 1e-12:
        return 0.0
    return abs(a_ns - b_ns) / abs(a_ns) * 100.0


def build_report(manual: dict, runtime_summaries: dict) -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    for base in BASES:
        for algo in ALGOS:
            key = f"{base}/{algo}"
            rt_path = runtime_summaries[key]
            rt_data = json.loads(read_text(rt_path))
            m_bl = manual[key]["baseline"]
            m_pr = manual[key]["prio"]

            rt_bl_mean_ns = float(rt_data["baseline"]["stats"]["mean_s"]) * 1e9
            rt_pr_mean_ns = float(rt_data["prio"]["stats"]["mean_s"]) * 1e9
            m_bl_mean_ns = float(m_bl["summary_ns"]["mean_ns"])
            m_pr_mean_ns = float(m_pr["summary_ns"]["mean_ns"])

            cases.append({
                "base": base, "algo": algo,
                "runtime_summary_path": str(rt_path),
                "manual": {"baseline": m_bl, "prio": m_pr},
                "runtime": {
                    "baseline_mean_ns": rt_bl_mean_ns,
                    "prio_mean_ns": rt_pr_mean_ns,
                    "raw": rt_data,
                },
                "comparison": {
                    "baseline_gap_pct": rel_gap_pct(m_bl_mean_ns, rt_bl_mean_ns),
                    "prio_gap_pct": rel_gap_pct(m_pr_mean_ns, rt_pr_mean_ns),
                },
            })
    return {
        "work_scale": WORK_SCALE, "repeats": REPEATS,
        "cpu_set": CPU_SET, "cores_per_task": CORES_PER_TASK,
        "cases": cases,
    }


def render_report_md(report: dict[str, Any]) -> str:
    lines = [
        "# zhang1 五算法 runtime vs 手动测时校验（ws=100, r=10）",
        "",
        "## 1. 实验目的",
        "",
        "- 验证 `runtime_compare` 工具在 `work_scale=100` 下对 5 个算法的测时是否与程序体内手动计时一致。",
        "- 手动测时：在 `main()` 体内注入 `clock_gettime(CLOCK_MONOTONIC_RAW)` 计时。",
        "- 对象：`zhang1` 的 cpf / heft / zhao2020 / wcet_first / t_level。",
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
        "| 算法 | 版本 | 手动均值(s) | runtime均值(s) | 偏差 |",
        "|------|------|----------:|-------------:|-----:|",
    ]
    for case in report["cases"]:
        m_bl = case["manual"]["baseline"]["summary_ns"]["mean_ns"]
        m_pr = case["manual"]["prio"]["summary_ns"]["mean_ns"]
        r_bl = case["runtime"]["baseline_mean_ns"]
        r_pr = case["runtime"]["prio_mean_ns"]
        lines.append(
            f"| {case['algo']} | baseline | {m_bl/1e9:.6f} | {r_bl/1e9:.6f} | {case['comparison']['baseline_gap_pct']:.3f}% |"
        )
        lines.append(
            f"| {case['algo']} | prio | {m_pr/1e9:.6f} | {r_pr/1e9:.6f} | {case['comparison']['prio_gap_pct']:.3f}% |"
        )
    lines.extend([
        "",
        "## 4. 各算法 baseline vs prio 对比",
        "",
        "| 算法 | 手动 baseline(s) | 手动 prio(s) | 手动提升% | runtime baseline(s) | runtime prio(s) | runtime提升% |",
        "|------|----------------:|------------:|---------:|-------------------:|---------------:|------------:|",
    ])
    for case in report["cases"]:
        m_bl = case["manual"]["baseline"]["summary_ns"]["mean_ns"] / 1e9
        m_pr = case["manual"]["prio"]["summary_ns"]["mean_ns"] / 1e9
        r_bl = case["runtime"]["baseline_mean_ns"] / 1e9
        r_pr = case["runtime"]["prio_mean_ns"] / 1e9
        m_imp = (m_bl - m_pr) / m_bl * 100 if m_bl > 0 else 0
        r_imp = (r_bl - r_pr) / r_bl * 100 if r_bl > 0 else 0
        lines.append(
            f"| {case['algo']} | {m_bl:.6f} | {m_pr:.6f} | {m_imp:+.2f}% | {r_bl:.6f} | {r_pr:.6f} | {r_imp:+.2f}% |"
        )
    lines.extend([
        "",
        "## 5. 结论",
        "",
        "- 以上对比基于真实运行数据。",
        "- 若手动均值与 runtime 均值偏差保持很小（<5%），说明 `runtime_compare` 的测时口径可信。",
        "- 详细原始数据见 `report.json` 及各子目录中的日志文件。",
        "",
    ])
    return "\n".join(lines)


def main() -> int:
    if MANUAL_ROOT.exists():
        shutil.rmtree(MANUAL_ROOT)
    if RUNTIME_ROOT.exists():
        shutil.rmtree(RUNTIME_ROOT)

    manual: dict[str, Any] = {}
    runtime_summaries: dict[str, Path] = {}

    for base in BASES:
        for algo in ALGOS:
            key = f"{base}/{algo}"
            baseline_src, prio_src = source_pair(base, algo)
            print(f"\n=== {key} ===")

            # --- 手动测时 ---
            manual[key] = {}
            for label, src in (("baseline", baseline_src), ("prio", prio_src)):
                case_dir = MANUAL_ROOT / base / algo / label
                print(f"  manual {label} ...")
                prepared_src = prepare_manual_source(src, case_dir)
                bin_path = case_dir / ("app_" + label)
                compile_manual_source(prepared_src, bin_path)
                run_data = run_manual_binary(bin_path)
                manual[key][label] = {
                    "source": str(src),
                    "prepared_source": str(prepared_src),
                    **run_data,
                }
                mean_s = run_data["summary_ns"]["mean_ns"] / 1e9
                print(f"    mean = {mean_s:.6f} s")

            # --- runtime_compare ---
            summary_path = run_runtime_compare_for_algo(base, algo)
            runtime_summaries[key] = summary_path
            rt_data = json.loads(read_text(summary_path))
            print(f"    runtime baseline mean = {rt_data['baseline']['stats']['mean_s']:.6f} s")
            print(f"    runtime prio mean     = {rt_data['prio']['stats']['mean_s']:.6f} s")

    report = build_report(manual, runtime_summaries)
    write_text(REPORT_JSON, json.dumps(report, ensure_ascii=False, indent=2))
    write_text(REPORT_MD, render_report_md(report))
    print(f"\nreport: {REPORT_JSON}")
    print(f"report_md: {REPORT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
