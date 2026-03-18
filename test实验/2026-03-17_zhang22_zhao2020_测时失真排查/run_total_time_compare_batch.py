#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SINGLE_RUN = ROOT / "run_total_time_compare.py"
BATCH_ROOT = ROOT / "total_time_compare_batch5"
GROUP_COUNT = 5


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize(vals: list[float]) -> dict:
    return {
        "count": len(vals),
        "mean": statistics.fmean(vals),
        "min": min(vals),
        "max": max(vals),
        "stddev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def main() -> int:
    if BATCH_ROOT.exists():
        shutil.rmtree(BATCH_ROOT)
    BATCH_ROOT.mkdir(parents=True, exist_ok=True)

    groups: list[dict] = []
    for idx in range(1, GROUP_COUNT + 1):
        subprocess.run(["python3", str(SINGLE_RUN)], cwd=str(ROOT.parents[0]), check=True)
        src_dir = ROOT / "total_time_compare"
        dst_dir = BATCH_ROOT / f"group_{idx:02d}"
        shutil.copytree(src_dir, dst_dir)
        report = read_json(dst_dir / "report.json")
        groups.append(
            {
                "group": idx,
                "path": str(dst_dir),
                "segment_mean_ns": float(report["segment_trace"]["summary_ns"]["mean"]),
                "main_mean_ns": float(report["main_timer"]["summary_ns"]["mean"]),
                "runtime_mean_ns": float(report["runtime_tool_baseline"]["summary_ns"]["mean"]),
                "runtime_summary": str(report["paths"]["runtime_summary"]),
            }
        )

    segment_means = [g["segment_mean_ns"] for g in groups]
    main_means = [g["main_mean_ns"] for g in groups]
    runtime_means = [g["runtime_mean_ns"] for g in groups]
    main_runtime_gap_pct = [
        abs(g["main_mean_ns"] - g["runtime_mean_ns"]) / g["main_mean_ns"] * 100.0
        for g in groups
    ]
    seg_main_ratio = [g["segment_mean_ns"] / g["main_mean_ns"] for g in groups]

    summary = {
        "group_count": GROUP_COUNT,
        "groups": groups,
        "cross_group_summary": {
            "segment_mean_ns": summarize(segment_means),
            "main_mean_ns": summarize(main_means),
            "runtime_mean_ns": summarize(runtime_means),
            "main_runtime_gap_pct": summarize(main_runtime_gap_pct),
            "segment_over_main_ratio": summarize(seg_main_ratio),
        },
    }
    (BATCH_ROOT / "batch_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
