#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


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


def _safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _cpu_set_str(cpu_set) -> str:
    if isinstance(cpu_set, list):
        return ",".join(str(x) for x in cpu_set)
    return "" if cpu_set is None else str(cpu_set)


def _stats_to_vals(stats: Dict) -> Tuple[float, float, float, float]:
    mean_s = _safe_float(stats.get("mean_s"))
    max_s = _safe_float(stats.get("max_s"))
    min_s = _safe_float(stats.get("min_s"))
    n = int(float(stats.get("n", 0)))
    total_s = mean_s * n if n > 0 else float("nan")
    return mean_s, total_s, max_s, min_s


def _extract_algo_from_text(text: str) -> str:
    patterns = [
        r"effective_line_merge/([^/]+)/",
        r"/baseline/([^/]+)/",
        r"/prio/([^/]+)/",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()
    return ""


def _algo_name_from_summary(data: Dict) -> str:
    for side in ("baseline", "prio"):
        obj = data.get(side, {})
        for key in ("c_file", "compile_cmd"):
            algo_name = _extract_algo_from_text(str(obj.get(key, "")))
            if algo_name:
                return algo_name
    return ""


def _algo_sort_key(algo_name: str) -> Tuple[int, str]:
    if algo_name in PREFERRED_ALGO_ORDER:
        return (PREFERRED_ALGO_ORDER.index(algo_name), algo_name)
    return (len(PREFERRED_ALGO_ORDER), algo_name)


def collect_rows(platform_dir: Path) -> List[Row]:
    rows: List[Row] = []
    for summary_path in sorted(platform_dir.rglob("summary.json")):
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            base_stats = data["baseline"]["stats"]
            prio_stats = data["prio"]["stats"]
            b_mean, b_total, b_max, b_min = _stats_to_vals(base_stats)
            p_mean, p_total, p_max, p_min = _stats_to_vals(prio_stats)
            rows.append(
                Row(
                    platform=platform_dir.name,
                    algo_name=_algo_name_from_summary(data),
                    created_at=str(data.get("created_at", "")),
                    work_scale=int(data.get("work_scale", 0)),
                    repeats=int(data.get("repeats", 0)),
                    cpu_set=_cpu_set_str(data.get("cpu_set")),
                    cores_per_task=int(data.get("cores_per_task", 0)),
                    baseline_mean_s=b_mean,
                    prio_mean_s=p_mean,
                    improvement_ratio=(None if data.get("improvement_ratio") is None else float(data["improvement_ratio"])),
                    delta_mean_s=_safe_float(data.get("delta_mean_s")),
                    baseline_total_s=b_total,
                    prio_total_s=p_total,
                    baseline_min_s=b_min,
                    baseline_max_s=b_max,
                    prio_min_s=p_min,
                    prio_max_s=p_max,
                    out_dir=str(summary_path.parent),
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
        parts = [part.strip() for part in cpu_set.split(",") if part.strip().isdigit()]
        if not parts:
            return cpu_set
        nums = sorted({int(part) for part in parts})
        if nums == list(range(nums[0], nums[-1] + 1)):
            return f"{nums[0]}-{nums[-1]}"
        return ",".join(str(num) for num in nums)

    lines: List[str] = []
    lines.append("# algo5：rk3588 实验结果统计\n\n")
    lines.append("说明：按 summary.json 汇总，算法名从实验路径推断，total=mean*n，improvement=(baseline-prio)/baseline。\n\n")
    for platform, rows in grouped_rows:
        lines.append(f"## {platform}\n\n")
        lines.append("| 算法名 | work_scale | repeats | cpu | baseline mean (s) | prio mean (s) | improvement | delta (s) | created_at |\n")
        lines.append("|:---|---:|---:|:---|---:|---:|---:|---:|:---|\n")
        for row in rows:
            improve = "" if row.improvement_ratio is None else f"{(row.improvement_ratio * 100):.2f}%"
            cpu = f"{fmt_cpu_set(row.cpu_set)} (c{row.cores_per_task})"
            lines.append(
                f"| {row.algo_name} | {row.work_scale} | {row.repeats} | {cpu} | {row.baseline_mean_s:.6f} | {row.prio_mean_s:.6f} | {improve} | {row.delta_mean_s:.6f} | {row.created_at} |\n"
            )
        lines.append("\n")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build rk3588 algo5 runtime result tables from summary.json files.")
    parser.add_argument(
        "--source",
        default="tools/runtime_compare/实验结果/rk3588实验结果/实验结果汇总",
        help="Source root containing rk3588 result groups.",
    )
    parser.add_argument(
        "--out",
        default="experiment/algo5（rk3588统计）/tables",
        help="Output tables directory.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    source_root = (repo_root / args.source).resolve()
    out_dir = (repo_root / args.out).resolve()

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
