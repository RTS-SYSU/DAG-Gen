#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


PREFERRED_ALGO_ORDER = ["cpf", "lpf", "heft", "zhao2020"]


@dataclass(frozen=True)
class Row:
    platform: str
    algo_name: str
    created_at: str
    work_scale: int
    repeats: int
    cpu_set: str
    cores_per_task: int
    baseline_mean_s: float
    prio_mean_s: float
    improvement_ratio: Optional[float]
    delta_mean_s: float
    baseline_total_s: float
    prio_total_s: float
    baseline_min_s: float
    baseline_max_s: float
    prio_min_s: float
    prio_max_s: float
    out_dir: str


def _safe_float(value) -> float:
    try:
        return float(value)
    except Exception:
        return float("nan")


def _extract_algo_from_text(text: str) -> str:
    for pattern in (
        r"effective_line_merge/([^/]+)/",
        r"/baseline/([^/\s]+)",
        r"/prio/([^/\s]+)",
    ):
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def _algo_name_from_run_dir(run_dir: Path) -> str:
    compile_logs = [
        run_dir / "baseline" / "compile.log",
        run_dir / "prio" / "compile.log",
    ]
    for compile_log in compile_logs:
        if not compile_log.exists():
            continue
        text = compile_log.read_text(encoding="utf-8", errors="ignore")
        algo_name = _extract_algo_from_text(text)
        if algo_name:
            return algo_name
    return ""


def _parse_run_dir_name(run_dir: Path) -> Tuple[str, int, int]:
    name = run_dir.name
    match = re.match(r"(.+)_ws(\d+)_r(\d+)$", name)
    if not match:
        return name, 0, 0
    return match.group(1), int(match.group(2)), int(match.group(3))


def _parse_run_log(run_log: Path) -> Tuple[List[float], List[float]]:
    baseline_vals: List[float] = []
    prio_vals: List[float] = []
    current: Optional[str] = None
    for line in run_log.read_text(encoding="utf-8", errors="ignore").splitlines():
        section = re.match(r"===\s+(baseline|prio)\s+run", line.strip())
        if section:
            current = section.group(1)
            continue
        value_match = re.search(r"wall_s=([0-9]*\.?[0-9]+)", line)
        if value_match and current:
            value = _safe_float(value_match.group(1))
            if current == "baseline":
                baseline_vals.append(value)
            else:
                prio_vals.append(value)
    return baseline_vals, prio_vals


def _stats_from_values(values: List[float]) -> Tuple[float, float, float, float]:
    if not values:
        return float("nan"), float("nan"), float("nan"), float("nan")
    mean_s = sum(values) / len(values)
    total_s = sum(values)
    max_s = max(values)
    min_s = min(values)
    return mean_s, total_s, max_s, min_s


def _infer_cpu_set(platform: str) -> str:
    if "zhang3" in platform:
        return "1,2"
    return "0,1"


def _algo_sort_key(algo_name: str) -> Tuple[int, str]:
    if algo_name in PREFERRED_ALGO_ORDER:
        return (PREFERRED_ALGO_ORDER.index(algo_name), algo_name)
    return (len(PREFERRED_ALGO_ORDER), algo_name)


def collect_rows(platform_dir: Path) -> List[Row]:
    rows: List[Row] = []
    for run_log in sorted(platform_dir.rglob("run.log")):
        try:
            run_dir = run_log.parent
            created_at, work_scale, repeats = _parse_run_dir_name(run_dir)
            baseline_vals, prio_vals = _parse_run_log(run_log)
            b_mean, b_total, b_max, b_min = _stats_from_values(baseline_vals)
            p_mean, p_total, p_max, p_min = _stats_from_values(prio_vals)
            cpu_set = _infer_cpu_set(platform_dir.name)
            delta_mean_s = p_mean - b_mean
            improvement_ratio = None if b_mean == 0 or b_mean != b_mean or p_mean != p_mean else (b_mean - p_mean) / b_mean
            rows.append(
                Row(
                    platform=platform_dir.name,
                    algo_name=_algo_name_from_run_dir(run_dir),
                    created_at=created_at,
                    work_scale=work_scale,
                    repeats=repeats,
                    cpu_set=cpu_set,
                    cores_per_task=len(cpu_set.split(",")),
                    baseline_mean_s=b_mean,
                    prio_mean_s=p_mean,
                    improvement_ratio=improvement_ratio,
                    delta_mean_s=delta_mean_s,
                    baseline_total_s=b_total,
                    prio_total_s=p_total,
                    baseline_min_s=b_min,
                    baseline_max_s=b_max,
                    prio_min_s=p_min,
                    prio_max_s=p_max,
                    out_dir=str(run_dir),
                )
            )
        except Exception:
            continue

    rows.sort(
        key=lambda row: (
            row.platform,
            _algo_sort_key(row.algo_name),
            row.work_scale,
            row.repeats,
            row.cpu_set,
            row.cores_per_task,
            row.created_at,
        )
    )
    return rows


def write_csv(path: Path, rows: List[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "platform",
                "算法名",
                "work_scale",
                "repeats",
                "baseline_mean_s",
                "prio_mean_s",
                "improvement_ratio",
                "delta_mean_s",
                "baseline_total_s",
                "prio_total_s",
                "baseline_min_s",
                "baseline_max_s",
                "prio_min_s",
                "prio_max_s",
                "cpu_set",
                "cores_per_task",
                "created_at",
                "out_dir",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.platform,
                    row.algo_name,
                    row.work_scale,
                    row.repeats,
                    f"{row.baseline_mean_s:.9f}",
                    f"{row.prio_mean_s:.9f}",
                    "" if row.improvement_ratio is None else f"{row.improvement_ratio:.9f}",
                    f"{row.delta_mean_s:.9f}",
                    f"{row.baseline_total_s:.9f}",
                    f"{row.prio_total_s:.9f}",
                    f"{row.baseline_min_s:.9f}",
                    f"{row.baseline_max_s:.9f}",
                    f"{row.prio_min_s:.9f}",
                    f"{row.prio_max_s:.9f}",
                    row.cpu_set,
                    row.cores_per_task,
                    row.created_at,
                    row.out_dir,
                ]
            )


def write_markdown(path: Path, grouped_rows: List[Tuple[str, List[Row]]]) -> None:
    def fmt_cpu_set(cpu_set: str) -> str:
        parts = [p.strip() for p in cpu_set.split(",") if p.strip().isdigit()]
        if not parts:
            return cpu_set
        nums = sorted({int(p) for p in parts})
        if nums == list(range(nums[0], nums[-1] + 1)):
            return f"{nums[0]}-{nums[-1]}"
        return ",".join(str(n) for n in nums)

    parts: List[str] = []
    parts.append("# algo5：rk3588 实验结果统计\n\n")
    parts.append("说明：按 run.log 汇总 wall_s，算法名从 compile.log 路径推断，cpu_set 对这批数据按平台名回退推断。\n\n")
    for platform, rows in grouped_rows:
        parts.append(f"## {platform}\n\n")
        parts.append("| 算法名 | work_scale | repeats | cpu | baseline mean (s) | prio mean (s) | improvement | delta (s) | created_at |\n")
        parts.append("|:---|---:|---:|:---|---:|---:|---:|---:|:---|\n")
        for row in rows:
            improve = "" if row.improvement_ratio is None else f"{(row.improvement_ratio * 100):.2f}%"
            cpu = f"{fmt_cpu_set(row.cpu_set)} (c{row.cores_per_task})"
            parts.append(
                f"| {row.algo_name} | {row.work_scale} | {row.repeats} | {cpu} | {row.baseline_mean_s:.6f} | {row.prio_mean_s:.6f} | {improve} | {row.delta_mean_s:.6f} | {row.created_at} |\n"
            )
        parts.append("\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build rk3588 algo5 runtime result tables from summary.json files.")
    parser.add_argument(
        "--source",
        default="/home/chove/Desktop/ScratchDAG/tools/runtime_compare/实验结果/rk3588实验结果/实验结果汇总",
        help="Source root containing rk3588 result groups.",
    )
    parser.add_argument(
        "--out",
        default="/home/chove/Desktop/ScratchDAG/experiment/algo5（rk3588统计）/tables",
        help="Output tables directory.",
    )
    args = parser.parse_args()

    source_root = Path(args.source).resolve()
    out_dir = Path(args.out).resolve()

    if not source_root.exists():
        print(f"Source not found: {source_root}")
        return 1

    platform_dirs = sorted([path for path in source_root.iterdir() if path.is_dir() and not path.name.startswith(".")])
    if not platform_dirs:
        print(f"No platform dirs under: {source_root}")
        return 1

    all_rows: List[Row] = []
    grouped_rows: List[Tuple[str, List[Row]]] = []
    for platform_dir in platform_dirs:
        rows = collect_rows(platform_dir)
        if not rows:
            continue
        grouped_rows.append((platform_dir.name, rows))
        all_rows.extend(rows)
        write_csv(out_dir / f"runtime_results_{platform_dir.name}.csv", rows)

    all_rows.sort(
        key=lambda row: (
            row.platform,
            _algo_sort_key(row.algo_name),
            row.work_scale,
            row.repeats,
            row.cpu_set,
            row.cores_per_task,
            row.created_at,
        )
    )
    write_csv(out_dir / "runtime_results_all.csv", all_rows)
    write_markdown(out_dir / "runtime_results_by_platform.md", grouped_rows)
    print(f"Done. platforms={len(grouped_rows)} rows={len(all_rows)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
