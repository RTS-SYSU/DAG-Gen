#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


EXCLUDED_ALGOS = {"lpf"}
ALGO_ORDER = ["cpf", "heft", "t_level", "wcet_first", "zhao2020"]


@dataclass(frozen=True)
class Row:
    zhang: str
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


def _algo_sort_key(algo_name: str) -> Tuple[int, str]:
    try:
        return (ALGO_ORDER.index(algo_name), algo_name)
    except ValueError:
        return (len(ALGO_ORDER), algo_name)


def _sort_rows(rows: List[Row]) -> List[Row]:
    return sorted(
        rows,
        key=lambda r: (
            r.zhang,
            r.work_scale,
            r.repeats,
            _algo_sort_key(r.algo_name),
            r.cpu_set,
            r.cores_per_task,
            r.created_at,
        ),
    )


def _filter_and_dedup_rows(rows: List[Row]) -> List[Row]:
    latest: Dict[Tuple[str, str, int, int, str], Row] = {}
    for row in rows:
        if row.algo_name in EXCLUDED_ALGOS:
            continue
        key = (row.platform, row.zhang, row.work_scale, row.repeats, row.algo_name)
        prev = latest.get(key)
        if prev is None or row.created_at > prev.created_at:
            latest[key] = row
    return _sort_rows(list(latest.values()))


def _group_rows_for_plots(rows: List[Row]) -> List[Tuple[Tuple[str, int, int], List[Row]]]:
    grouped: Dict[Tuple[str, int, int], List[Row]] = {}
    for row in rows:
        key = (row.zhang, row.work_scale, row.repeats)
        grouped.setdefault(key, []).append(row)
    result: List[Tuple[Tuple[str, int, int], List[Row]]] = []
    for key in sorted(grouped.keys(), key=lambda item: (item[0], item[1], item[2])):
        result.append((key, _sort_rows(grouped[key])))
    return result


def _sanitize_filename_component(text: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", text.strip())
    value = value.strip("_")
    return value or "unknown"


def _ensure_matplotlib():
    try:
        import matplotlib

        matplotlib.use("Agg")
        from matplotlib import pyplot as plt
    except ImportError as exc:
        raise RuntimeError(
            "需要安装 matplotlib 才能生成统计图，请先执行 `python3 -m pip install matplotlib`。"
        ) from exc
    return plt


CSV_HEADER = [
    "platform",
    "zhang",
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


def collect_rows(zhang_dir: Path, platform: str) -> List[Row]:
    rows: List[Row] = []
    zhang = zhang_dir.name

    for summary_path in sorted(zhang_dir.rglob("summary.json")):
        try:
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            base_stats = data["baseline"]["stats"]
            prio_stats = data["prio"]["stats"]
            b_mean, b_total, b_max, b_min = _stats_to_vals(base_stats)
            p_mean, p_total, p_max, p_min = _stats_to_vals(prio_stats)
            rows.append(
                Row(
                    zhang=zhang,
                    platform=platform,
                    algo_name=_algo_name_from_summary(data),
                    created_at=str(data.get("created_at", "")),
                    work_scale=int(data.get("work_scale", 0)),
                    repeats=int(data.get("repeats", 0)),
                    cpu_set=_cpu_set_str(data.get("cpu_set")),
                    cores_per_task=int(data.get("cores_per_task", 0)),
                    baseline_mean_s=b_mean,
                    prio_mean_s=p_mean,
                    improvement_ratio=(
                        None
                        if data.get("improvement_ratio") is None
                        else float(data["improvement_ratio"])
                    ),
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
        except Exception as e:
            print(f"  WARN: skip {summary_path}: {e}")
            continue

    return _sort_rows(rows)


def _row_to_csv(r: Row) -> list:
    return [
        r.platform,
        r.zhang,
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


def write_csv(path: Path, rows: List[Row]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(CSV_HEADER)
        for r in rows:
            w.writerow(_row_to_csv(r))


def _fmt_cpu_set(cpu_set: str) -> str:
    parts = [p.strip() for p in cpu_set.split(",") if p.strip().isdigit()]
    if not parts:
        return cpu_set
    nums = sorted({int(p) for p in parts})
    if nums == list(range(nums[0], nums[-1] + 1)):
        return f"{nums[0]}-{nums[-1]}"
    return ",".join(str(n) for n in nums)


def write_markdown(
    path: Path,
    grouped: List[Tuple[str, List[Row]]],
    platform: str,
) -> None:
    lines: List[str] = []
    lines.append(f"# 第四次实验结果统计（{platform}）\n\n")
    lines.append(
        "说明：按 summary.json 汇总，total=mean×n，"
        "improvement=(baseline−prio)/baseline（正值表示 prio 更快）；"
        "已排除 lpf，并且同一 zhang + work_scale + repeats + 算法只保留 created_at 最新的一条。\n\n"
    )

    for zhang, rows in grouped:
        lines.append(f"## {zhang}\n\n")
        lines.append(
            "| 算法名 | work_scale | repeats | cpu | "
            "baseline mean (s) | prio mean (s) | improvement | "
            "delta (s) | baseline min/max (s) | prio min/max (s) | created_at |\n"
        )
        lines.append(
            "|:---|---:|---:|:---|---:|---:|---:|---:|:---|:---|:---|\n"
        )
        for r in rows:
            improve = (
                ""
                if r.improvement_ratio is None
                else f"{(r.improvement_ratio * 100):.2f}%"
            )
            cpu = f"{_fmt_cpu_set(r.cpu_set)} (c{r.cores_per_task})"
            b_range = f"{r.baseline_min_s:.6f} / {r.baseline_max_s:.6f}"
            p_range = f"{r.prio_min_s:.6f} / {r.prio_max_s:.6f}"
            lines.append(
                f"| {r.algo_name} | {r.work_scale} | {r.repeats} | {cpu} | "
                f"{r.baseline_mean_s:.6f} | {r.prio_mean_s:.6f} | {improve} | "
                f"{r.delta_mean_s:.6f} | {b_range} | {p_range} | {r.created_at} |\n"
            )
        lines.append("\n")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(lines), encoding="utf-8")


def write_figures(fig_root: Path, grouped_rows: List[Tuple[Tuple[str, int, int], List[Row]]], platform: str) -> int:
    plt = _ensure_matplotlib()
    fig_count = 0
    for (zhang, work_scale, repeats), rows in grouped_rows:
        if not rows:
            continue
        algo_labels = [r.algo_name for r in rows]
        baseline_vals = [r.baseline_mean_s for r in rows]
        prio_vals = [r.prio_mean_s for r in rows]
        x = list(range(len(rows)))
        width = 0.38

        fig, ax = plt.subplots(figsize=(10, 5.5))
        ax.bar([i - width / 2 for i in x], baseline_vals, width=width, label="baseline")
        ax.bar([i + width / 2 for i in x], prio_vals, width=width, label="prio")
        ax.set_xticks(x)
        ax.set_xticklabels(algo_labels)
        ax.set_ylabel("mean runtime (s)")
        ax.set_xlabel("algorithm")
        ax.set_title(
            f"platform={platform} | dag={zhang} | ws={work_scale} | r={repeats}"
        )
        ax.legend()
        ax.grid(axis="y", linestyle="--", alpha=0.35)
        fig.tight_layout()

        out_dir = fig_root / zhang
        out_dir.mkdir(parents=True, exist_ok=True)
        out_name = (
            f"{_sanitize_filename_component(platform)}_"
            f"{_sanitize_filename_component(zhang)}_ws{work_scale}_r{repeats}.png"
        )
        fig.savefig(out_dir / out_name, dpi=160)
        plt.close(fig)
        fig_count += 1
    return fig_count


def main() -> int:
    script_dir = Path(__file__).resolve().parent
    out_dir = script_dir.parent / "tables"
    fig_dir = out_dir / "figures"

    source_root = Path(
        "/home/firefly/Desktop/ScratchDAG/tools/runtime_compare"
        "/实验结果/第四次实验结果/rk3588"
    )

    if not source_root.exists():
        print(f"Source not found: {source_root}")
        return 1

    platform = "rk3588"
    zhang_dirs = sorted(
        [p for p in source_root.iterdir() if p.is_dir() and p.name.startswith("zhang")]
    )
    if not zhang_dirs:
        print(f"No zhangX dirs under: {source_root}")
        return 1

    all_rows: List[Row] = []
    grouped: List[Tuple[str, List[Row]]] = []

    for zhang_dir in zhang_dirs:
        rows = _filter_and_dedup_rows(collect_rows(zhang_dir, platform))
        if not rows:
            print(f"  WARN: no rows from {zhang_dir}")
            continue
        grouped.append((zhang_dir.name, rows))
        all_rows.extend(rows)
        csv_path = out_dir / f"runtime_results_{zhang_dir.name}.csv"
        write_csv(csv_path, rows)
        print(f"  wrote {csv_path.name}  ({len(rows)} rows)")

    all_rows = _sort_rows(all_rows)
    write_csv(out_dir / "runtime_results_all.csv", all_rows)
    write_markdown(out_dir / "runtime_results_by_zhang.md", grouped, platform)
    fig_count = write_figures(fig_dir, _group_rows_for_plots(all_rows), platform)

    print(
        f"\nDone. zhangs={len(grouped)} total_rows={len(all_rows)} "
        f"figures={fig_count} out={out_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
