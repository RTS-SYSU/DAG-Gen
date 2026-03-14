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
    platform: str
    created_at: str
    work_scale: int
    repeats: int
    cpu_set: str
    cores_per_task: int

    baseline_mean_s: float
    baseline_total_s: float
    baseline_max_s: float
    baseline_min_s: float

    prio_mean_s: float
    prio_total_s: float
    prio_max_s: float
    prio_min_s: float

    delta_mean_s: float
    improvement_ratio: Optional[float]

    out_dir: str


@dataclass(frozen=True)
class AlgoRow:
    algo: str
    row: Row


PREFERRED_ALGO_ORDER = ["cpf", "lpf", "heft", "zhao2020"]


def _algo_sort_key(name: str) -> Tuple[int, str]:
    try:
        return (PREFERRED_ALGO_ORDER.index(name), name)
    except ValueError:
        return (1_000_000, name)


def _safe_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _load_summary(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


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


def collect_rows(platform: str, roots: Iterable[Path], *, min_repeats: int = 0) -> List[Row]:
    rows: List[Row] = []
    for root in roots:
        for summary_path in sorted(root.rglob("summary.json")):
            try:
                data = _load_summary(summary_path)
                base_stats = data["baseline"]["stats"]
                prio_stats = data["prio"]["stats"]
                b_mean, b_total, b_max, b_min = _stats_to_vals(base_stats)
                p_mean, p_total, p_max, p_min = _stats_to_vals(prio_stats)
                repeats = int(data.get("repeats", 0))
                if repeats < int(min_repeats):
                    continue
                rows.append(
                    Row(
                        platform=platform,
                        created_at=str(data.get("created_at", "")),
                        work_scale=int(data.get("work_scale", 0)),
                        repeats=repeats,
                        cpu_set=_cpu_set_str(data.get("cpu_set")),
                        cores_per_task=int(data.get("cores_per_task", 0)),
                        baseline_mean_s=b_mean,
                        baseline_total_s=b_total,
                        baseline_max_s=b_max,
                        baseline_min_s=b_min,
                        prio_mean_s=p_mean,
                        prio_total_s=p_total,
                        prio_max_s=p_max,
                        prio_min_s=p_min,
                        delta_mean_s=_safe_float(data.get("delta_mean_s")),
                        improvement_ratio=(None if data.get("improvement_ratio") is None else float(data["improvement_ratio"])),
                        out_dir=str(summary_path.parent),
                    )
                )
            except Exception:
                continue
    rows.sort(key=lambda r: (r.work_scale, r.repeats, r.cpu_set, r.cores_per_task, r.created_at))
    return rows


def write_csv(path: Path, rows: List[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
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


def write_csv_long_with_algo(path: Path, rows: List[AlgoRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "algo",
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
        for ar in rows:
            r = ar.row
            w.writerow(
                [
                    ar.algo,
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


def write_csv_wide_by_algo(path: Path, rows: List[AlgoRow], algos: List[str]) -> None:
    """
    Pivot long rows into a wide table keyed by (work_scale,repeats,cpu_set,cores_per_task).
    For each algo, export: baseline_mean_s / prio_mean_s / improvement_ratio / delta_mean_s / created_at.
    """

    def key(r: Row) -> Tuple[int, int, str, int]:
        return (r.work_scale, r.repeats, r.cpu_set, r.cores_per_task)

    by_key: Dict[Tuple[int, int, str, int], Dict[str, AlgoRow]] = {}
    for ar in rows:
        by_key.setdefault(key(ar.row), {})[ar.algo] = ar

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        header: List[str] = ["platform", "work_scale", "repeats", "cpu_set", "cores_per_task"]
        for algo in algos:
            header.extend(
                [
                    f"{algo}_baseline_mean_s",
                    f"{algo}_prio_mean_s",
                    f"{algo}_improvement_ratio",
                    f"{algo}_delta_mean_s",
                    f"{algo}_created_at",
                ]
            )
        w.writerow(header)

        for k in sorted(by_key.keys()):
            work_scale, repeats, cpu_set, cores_per_task = k
            # platform might differ across rows; pick from first available
            platform = ""
            row_out: List[str] = [platform, str(work_scale), str(repeats), cpu_set, str(cores_per_task)]
            for algo in algos:
                ar = by_key[k].get(algo)
                if ar is None:
                    row_out.extend(["", "", "", "", ""])
                    continue
                r = ar.row
                platform = r.platform or platform
                row_out.extend(
                    [
                        f"{r.baseline_mean_s:.9f}",
                        f"{r.prio_mean_s:.9f}",
                        "" if r.improvement_ratio is None else f"{r.improvement_ratio:.9f}",
                        f"{r.delta_mean_s:.9f}",
                        r.created_at,
                    ]
                )
            row_out[0] = platform
            w.writerow(row_out)


def write_markdown(path: Path, title: str, sections: List[Tuple[str, List[Row]]]) -> None:
    def fmt_hms(total_s: float) -> str:
        if total_s != total_s:  # NaN
            return ""
        total_s_i = int(round(total_s))
        h = total_s_i // 3600
        m = (total_s_i % 3600) // 60
        s = total_s_i % 60
        if h > 0:
            return f"{h:d}:{m:02d}:{s:02d}"
        return f"{m:d}:{s:02d}"

    def fmt_cpu_set(cpu_set: str) -> str:
        parts = [p.strip() for p in cpu_set.split(",") if p.strip().isdigit()]
        if not parts:
            return cpu_set
        nums = sorted({int(p) for p in parts})
        if not nums:
            return cpu_set
        if nums == list(range(nums[0], nums[-1] + 1)):
            return f"{nums[0]}-{nums[-1]}"
        return ",".join(str(n) for n in nums)

    def render(title: str, rows: List[Row]) -> str:
        lines: List[str] = []
        lines.append(f"## {title}\n\n")
        lines.append(
            "| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |\n"
        )
        lines.append("|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|\n")
        for r in rows:
            improve_pct = ""
            if r.improvement_ratio is not None:
                improve_pct = f"{(r.improvement_ratio * 100):.2f}%"
            cpu = f"{fmt_cpu_set(r.cpu_set)} (c{r.cores_per_task})"
            lines.append(
                f"| {r.work_scale} | {r.repeats} | {cpu} | {r.baseline_mean_s:.6f} | {fmt_hms(r.baseline_total_s)} | "
                f"{r.baseline_min_s:.6f}/{r.baseline_max_s:.6f} | {r.prio_mean_s:.6f} | {fmt_hms(r.prio_total_s)} | "
                f"{r.prio_min_s:.6f}/{r.prio_max_s:.6f} | {improve_pct} |\n"
            )
        lines.append("\n")
        return "".join(lines)

    path.parent.mkdir(parents=True, exist_ok=True)
    parts: List[str] = []
    parts.append(f"# {title}：实验配置与结果（按算法）\n\n")
    parts.append(
        "说明：每行是一组实验配置（work_scale + repeats + CPU 核集合 + cores_per_task）的聚合统计；"
        "`total` 为该组 runs 的总耗时（按 mean×n 估算）。\n\n"
    )
    for sec_title, rows in sections:
        parts.append(render(sec_title, rows))
    path.write_text("".join(parts), encoding="utf-8")


def _locate_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "cli.py").exists() and (parent / "__main__.py").exists():
            return parent
    raise RuntimeError("Cannot locate repo root from script path.")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build zhang1 config results tables from summary.json files.")
    ap.add_argument(
        "--root",
        default="experiment/zhang1实验结果汇总",
        help="Root directory containing direct child groups (default: experiment/zhang1实验结果汇总)",
    )
    ap.add_argument("--platform", default="zhang1", help="Platform label written into CSV (default: zhang1)")
    ap.add_argument(
        "--min-repeats",
        type=int,
        default=0,
        help="Only include runs with repeats >= N (default: 0, include all).",
    )
    ap.add_argument(
        "--ignore-dir",
        action="append",
        default=["tables", "scripts", "web_tasks"],
        help="Ignore direct child directory names under root (can repeat). Default: tables,scripts,web_tasks",
    )
    args = ap.parse_args()

    repo_root = _locate_repo_root()
    root_dir = (repo_root / args.root).resolve()
    if not root_dir.exists():
        print(f"Root not found: {root_dir}")
        return 1

    ignore = set(args.ignore_dir or [])
    group_dirs = [p for p in root_dir.iterdir() if p.is_dir() and not p.name.startswith(".") and p.name not in ignore]
    group_dirs.sort(key=lambda p: _algo_sort_key(p.name))

    tables_dir = root_dir / "tables"
    sections: List[Tuple[str, List[Row]]] = []
    all_rows: List[Row] = []
    all_algo_rows: List[AlgoRow] = []
    for group_dir in group_dirs:
        rows = collect_rows(args.platform, [group_dir], min_repeats=int(args.min_repeats))
        if not rows:
            continue
        sections.append((group_dir.name, rows))
        all_rows.extend(rows)
        all_algo_rows.extend([AlgoRow(algo=group_dir.name, row=r) for r in rows])
        write_csv(tables_dir / f"config_results_{group_dir.name}.csv", rows)

    all_rows.sort(key=lambda r: (r.work_scale, r.repeats, r.cpu_set, r.cores_per_task, r.created_at))
    write_csv(tables_dir / "config_results_all.csv", all_rows)
    write_markdown(tables_dir / "config_results_by_algo.md", args.platform, sections)

    all_algo_rows.sort(
        key=lambda ar: (
            _algo_sort_key(ar.algo),
            ar.row.work_scale,
            ar.row.repeats,
            ar.row.cpu_set,
            ar.row.cores_per_task,
            ar.row.created_at,
        )
    )
    write_csv_long_with_algo(tables_dir / "config_results_all_long.csv", all_algo_rows)
    write_csv_wide_by_algo(
        tables_dir / "config_results_compare_algos_wide.csv",
        all_algo_rows,
        sorted([title for title, _ in sections], key=_algo_sort_key),
    )

    print(f"Done. groups={len(sections)} rows={len(all_rows)} out={tables_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
