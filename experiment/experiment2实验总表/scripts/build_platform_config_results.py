#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

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


def collect_rows(platform: str, roots: Iterable[Path]) -> List[Row]:
    rows: List[Row] = []
    for root in roots:
        for summary_path in sorted(root.rglob("summary.json")):
            try:
                data = _load_summary(summary_path)
                base_stats = data["baseline"]["stats"]
                prio_stats = data["prio"]["stats"]
                b_mean, b_total, b_max, b_min = _stats_to_vals(base_stats)
                p_mean, p_total, p_max, p_min = _stats_to_vals(prio_stats)
                cpu_set = data.get("cpu_set")
                cpu_set_str = ",".join(str(x) for x in cpu_set) if isinstance(cpu_set, list) else str(cpu_set)
                rows.append(
                    Row(
                        platform=platform,
                        created_at=str(data.get("created_at", "")),
                        work_scale=int(data.get("work_scale", 0)),
                        repeats=int(data.get("repeats", 0)),
                        cpu_set=cpu_set_str,
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
                # best-effort: skip malformed summaries
                continue
    rows.sort(key=lambda r: (r.work_scale, r.repeats, r.created_at))
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
                "baseline_total_s",
                "baseline_max_s",
                "baseline_min_s",
                "prio_mean_s",
                "prio_total_s",
                "prio_max_s",
                "prio_min_s",
                "delta_mean_s",
                "improvement_ratio",
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
                    f"{r.baseline_total_s:.9f}",
                    f"{r.baseline_max_s:.9f}",
                    f"{r.baseline_min_s:.9f}",
                    f"{r.prio_mean_s:.9f}",
                    f"{r.prio_total_s:.9f}",
                    f"{r.prio_max_s:.9f}",
                    f"{r.prio_min_s:.9f}",
                    f"{r.delta_mean_s:.9f}",
                    "" if r.improvement_ratio is None else f"{r.improvement_ratio:.9f}",
                    r.cpu_set,
                    r.cores_per_task,
                    r.created_at,
                    r.out_dir,
                ]
            )


def write_markdown(path: Path, vm_rows: List[Row], rk_rows: List[Row]) -> None:
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

    def render(platform_title: str, rows: List[Row]) -> str:
        lines = []
        lines.append(f"## {platform_title}\n")
        lines.append(
            "| work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement |\n"
        )
        lines.append(
            "|---:|---:|:---|---:|:---|:---|---:|:---|:---|---:|\n"
        )
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
    parts = []
    parts.append("# experiment2：实验配置与结果（按平台）\n\n")
    parts.append("说明：每行是一组实验配置（work_scale + repeats + CPU 核集合）的聚合统计；`total` 为该组 runs 的总耗时（按 mean×repeats 估算）。\n\n")
    parts.append(render("虚拟机 (VM)", vm_rows))
    parts.append(render("板子 (RK3588S)", rk_rows))
    path.write_text("".join(parts), encoding="utf-8")


def main() -> int:
    p = Path(__file__).resolve()
    mycally_root: Optional[Path] = None
    for parent in p.parents:
        if parent.name == "mycallyplus_v1":
            mycally_root = parent
            break
    if mycally_root is None:
        raise RuntimeError("Cannot locate mycallyplus_v1 root from script path.")
    base_dir = mycally_root / "experiment"

    vm_root = base_dir / "experiment2虚拟机实验结果汇总"
    rk_root = base_dir / "experiment2（rk3588）实验结果"

    # fallbacks: also include raw experiment2 runs if needed
    raw_root = base_dir / "experiment2"

    vm_roots = [p for p in [vm_root] if p.exists()]
    rk_roots = [p for p in [rk_root] if p.exists()]
    if not vm_roots:
        vm_roots = [raw_root] if raw_root.exists() else []

    vm_rows = collect_rows("vm", vm_roots)
    rk_rows = collect_rows("rk3588", rk_roots)

    out_root = base_dir / "experiment2实验总表"
    tables_dir = out_root / "tables"

    write_csv(tables_dir / "config_results_vm.csv", vm_rows)
    write_csv(tables_dir / "config_results_rk3588.csv", rk_rows)
    write_csv(tables_dir / "config_results_all.csv", vm_rows + rk_rows)
    write_markdown(tables_dir / "config_results_by_platform.md", vm_rows, rk_rows)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
