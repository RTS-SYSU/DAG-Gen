#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class Row:
    suite: str
    platform: str
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


def _stats_to_vals(stats: Dict) -> Tuple[float, float, float, float]:
    mean_s = _safe_float(stats.get("mean_s"))
    max_s = _safe_float(stats.get("max_s"))
    min_s = _safe_float(stats.get("min_s"))
    n = int(float(stats.get("n", 0)))
    total_s = mean_s * n if n > 0 else float("nan")
    return mean_s, total_s, max_s, min_s


def _cpu_set_str(cpu_set) -> str:
    if isinstance(cpu_set, list):
        return ",".join(str(x) for x in cpu_set)
    return "" if cpu_set is None else str(cpu_set)


def collect_rows(platform: str, suite: str, roots: Iterable[Path]) -> List[Row]:
    rows: List[Row] = []
    for root in roots:
        for summary_path in sorted(root.rglob("summary.json")):
            try:
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                base_stats = data["baseline"]["stats"]
                prio_stats = data["prio"]["stats"]
                b_mean, b_total, b_max, b_min = _stats_to_vals(base_stats)
                p_mean, p_total, p_max, p_min = _stats_to_vals(prio_stats)
                rows.append(
                    Row(
                        suite=suite,
                        platform=platform,
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
    rows.sort(key=lambda r: (r.suite, r.work_scale, r.repeats, r.cpu_set, r.cores_per_task, r.created_at))
    return rows


def write_csv(path: Path, rows: List[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "suite",
                "platform",
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
                    r.suite,
                    r.platform,
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


def write_markdown(path: Path, sections: List[Tuple[str, List[Row]]]) -> None:
    def fmt_cpu_set(cpu_set: str) -> str:
        parts = [p.strip() for p in cpu_set.split(",") if p.strip().isdigit()]
        if not parts:
            return cpu_set
        nums = sorted({int(p) for p in parts})
        if nums == list(range(nums[0], nums[-1] + 1)):
            return f"{nums[0]}-{nums[-1]}"
        return ",".join(str(n) for n in nums)

    def render(title: str, rows: List[Row]) -> str:
        lines: List[str] = []
        lines.append(f"## {title}\n\n")
        lines.append("| work_scale | repeats | cpu | baseline mean (s) | prio mean (s) | improvement | delta (s) | created_at |\n")
        lines.append("|---:|---:|:---|---:|---:|---:|---:|:---|\n")
        for r in rows:
            improve_pct = ""
            if r.improvement_ratio is not None:
                improve_pct = f"{(r.improvement_ratio * 100):.2f}%"
            cpu = f"{fmt_cpu_set(r.cpu_set)} (c{r.cores_per_task})"
            lines.append(
                f"| {r.work_scale} | {r.repeats} | {cpu} | {r.baseline_mean_s:.6f} | {r.prio_mean_s:.6f} | {improve_pct} | {r.delta_mean_s:.6f} | {r.created_at} |\n"
            )
        lines.append("\n")
        return "".join(lines)

    path.parent.mkdir(parents=True, exist_ok=True)
    parts: List[str] = []
    parts.append("# zhang2：runtime_compare 实验汇总\n\n")
    parts.append("说明：每行是一组实验配置（work_scale + repeats + cpu_set + cores_per_task）的聚合统计。\n\n")
    for title, rows in sections:
        parts.append(render(title, rows))
    path.write_text("".join(parts), encoding="utf-8")


def _locate_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "cli.py").exists() and (parent / "__main__.py").exists():
            return parent
    raise RuntimeError("Cannot locate repo root from script path.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build zhang2 runtime_compare results tables from summary.json files.")
    ap.add_argument(
        "--root",
        default="experiment/zhang2实验结果汇总",
        help="Root directory containing suites (default: experiment/zhang2实验结果汇总)",
    )
    ap.add_argument("--platform", default="zhang2", help="Platform label written into tables (default: zhang2)")
    args = ap.parse_args()

    repo_root = _locate_repo_root()
    root_dir = (repo_root / args.root).resolve()
    if not root_dir.exists():
        print(f"Root not found: {root_dir}")
        return 1

    suites = sorted([p for p in root_dir.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name != "tables" and p.name != "scripts"])
    if not suites:
        print(f"No suite directories under: {root_dir}")
        return 1

    tables_dir = root_dir / "tables"
    all_rows: List[Row] = []
    sections: List[Tuple[str, List[Row]]] = []
    for suite_dir in suites:
        rows = collect_rows(args.platform, suite_dir.name, [suite_dir])
        if not rows:
            continue
        sections.append((suite_dir.name, rows))
        all_rows.extend(rows)
        write_csv(tables_dir / f"runtime_results_{suite_dir.name}.csv", rows)

    all_rows.sort(key=lambda r: (r.suite, r.work_scale, r.repeats, r.cpu_set, r.cores_per_task, r.created_at))
    write_csv(tables_dir / "runtime_results_all.csv", all_rows)
    write_markdown(tables_dir / "runtime_results_by_suite.md", sections)
    print(f"Done. suites={len(sections)} rows={len(all_rows)} out={tables_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
