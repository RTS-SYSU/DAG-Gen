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
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return m.group(1).strip()
    return ""


def _algo_name_from_summary(data: Dict) -> str:
    for side in ("baseline", "prio"):
        obj = data.get(side, {})
        for key in ("c_file", "compile_cmd"):
            val = str(obj.get(key, ""))
            algo = _extract_algo_from_text(val)
            if algo:
                return algo
    return ""


def collect_rows(platform_dir: Path) -> List[Row]:
    rows: List[Row] = []
    platform = platform_dir.name

    for summary_path in sorted(platform_dir.rglob("summary.json")):
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            base_stats = data["baseline"]["stats"]
            prio_stats = data["prio"]["stats"]
            b_mean, b_total, b_max, b_min = _stats_to_vals(base_stats)
            p_mean, p_total, p_max, p_min = _stats_to_vals(prio_stats)
            rows.append(
                Row(
                    platform=platform,
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

    rows.sort(key=lambda r: (r.platform, r.algo_name, r.work_scale, r.repeats, r.cpu_set, r.cores_per_task, r.created_at))
    return rows


def write_csv(path: Path, rows: List[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
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
        for r in rows:
            w.writerow(
                [
                    r.platform,
                    r.algo_name,
                    r.work_scale,
                    r.repeats,
                    f"{r.baseline_mean_s:.9f}",
                    f"{r.prio_mean_s:.9f}",
                    "" if r.improvement_ratio is None else f"{r.improvement_ratio:.9f}",
                    f"{r.delta_mean_s:.9f}",
                    f"{r.baseline_total_s:.9f}",
                    f"{r.prio_total_s:.9f}",
                    f"{r.baseline_min_s:.9f}",
                    f"{r.baseline_max_s:.9f}",
                    f"{r.prio_min_s:.9f}",
                    f"{r.prio_max_s:.9f}",
                    r.cpu_set,
                    r.cores_per_task,
                    r.created_at,
                    r.out_dir,
                ]
            )


def write_markdown(path: Path, grouped_rows: List[Tuple[str, List[Row]]]) -> None:
    lines: List[str] = []
    lines.append("# 第四次实验：虚拟机实验结果统计\n\n")
    lines.append("说明：按 summary.json 汇总，total=mean*n，improvement=(baseline-prio)/baseline。\n\n")
    for platform, rows in grouped_rows:
        lines.append(f"## {platform}\n\n")
        lines.append("| 算法 | work_scale | repeats | cpu_set | baseline mean (s) | prio mean (s) | improvement | delta (s) | created_at |\n")
        lines.append("|:---|---:|---:|:---|---:|---:|---:|---:|:---|\n")
        for r in rows:
            improve = "" if r.improvement_ratio is None else f"{(r.improvement_ratio * 100):.2f}%"
            lines.append(
                f"| {r.algo_name} | {r.work_scale} | {r.repeats} | {r.cpu_set} (c{r.cores_per_task}) | "
                f"{r.baseline_mean_s:.6f} | {r.prio_mean_s:.6f} | {improve} | {r.delta_mean_s:.6f} | {r.created_at} |\n"
            )
        lines.append("\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build VM runtime stats tables from summary.json files.")
    ap.add_argument(
        "--source",
        default="tools/runtime_compare/实验结果/第四次实验结果/虚拟机",
        help="Source root containing zhang1/zhang2/zhang3 subdirs",
    )
    ap.add_argument(
        "--out",
        default="experiment/第四次实验/虚拟机/tables",
        help="Output tables directory",
    )
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[4]
    source_root = (repo_root / args.source).resolve()
    out_dir = (repo_root / args.out).resolve()

    if not source_root.exists():
        print(f"Source not found: {source_root}")
        return 1

    platform_dirs = sorted([p for p in source_root.iterdir() if p.is_dir() and not p.name.startswith(".")])
    if not platform_dirs:
        print(f"No platform dirs under: {source_root}")
        return 1

    all_rows: List[Row] = []
    grouped: List[Tuple[str, List[Row]]] = []
    for platform_dir in platform_dirs:
        rows = collect_rows(platform_dir)
        if not rows:
            continue
        grouped.append((platform_dir.name, rows))
        all_rows.extend(rows)
        write_csv(out_dir / f"runtime_results_{platform_dir.name}.csv", rows)

    all_rows.sort(key=lambda r: (r.platform, r.algo_name, r.work_scale, r.repeats, r.cpu_set, r.cores_per_task, r.created_at))
    write_csv(out_dir / "runtime_results_all.csv", all_rows)
    write_markdown(out_dir / "runtime_results_by_platform.md", grouped)
    print(f"Done. platforms={len(grouped)} rows={len(all_rows)} out={out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
