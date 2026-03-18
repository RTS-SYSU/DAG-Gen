#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Sequence

PROGRAM_TOTAL_NS_RE = re.compile(r"PROGRAM_TOTAL_NS=(\d+)")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pipeline.algo.zhao2020 import Zhao2020BlockAlgo
from pipeline.instrument_levelx import instrument_prio_all_segments_by_start_line

OUT_DIR = ROOT / "test实验" / "2026-03-17_zhang22重加权实验" / "results"
SRC_ORIGINAL = ROOT / "中间结果" / "zhang22" / "pipeline" / "instrument" / "level2" / "effective_line_merge" / "zhao2020" / "source_original.c"
SRC_CURRENT = ROOT / "中间结果" / "zhang22" / "pipeline" / "instrument" / "level2" / "effective_line_merge" / "zhao2020" / "source_instrumented.c"
SEGMENTS_JSON = ROOT / "中间结果" / "zhang22" / "pipeline" / "blocks" / "level2" / "effective_line_merge" / "segments.json"
DAG_JSON = ROOT / "中间结果" / "zhang22" / "pipeline" / "blocks" / "level2" / "effective_line_merge" / "dag_seg.json"
SCHEDULE_CURRENT = ROOT / "中间结果" / "zhang22" / "pipeline" / "schedule" / "level2" / "effective_line_merge" / "zhao2020" / "schedule.json"
REWEIGHT_TABLE = ROOT / "test实验" / "2026-03-17_zhang22权重标定" / "results" / "zhang22_reweight_table.json"
HELPER_DIR = ROOT / "level1"

WORK_SCALE = 5
REPEATS = 10
GROUPS = 5
CPU_SET = [0, 1, 2, 3]


def read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def run_cmd(cmd: Sequence[str], *, cwd: Path, cpu_set: Sequence[int] | None = None) -> subprocess.CompletedProcess[str]:
    def preexec() -> None:
        if cpu_set is not None:
            os.sched_setaffinity(0, set(cpu_set))

    return subprocess.run(
        list(cmd),
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
        preexec_fn=preexec,
    )


def parse_total_ns(stderr: str) -> int:
    matches = PROGRAM_TOTAL_NS_RE.findall(stderr or "")
    if not matches:
        raise RuntimeError("missing PROGRAM_TOTAL_NS")
    return int(matches[-1])


def compile_one(src: Path, out_bin: Path) -> None:
    cmd = [
        "gcc",
        "-O0",
        "-g",
        "-std=c11",
        "-pthread",
        f"-DWORK_SCALE={WORK_SCALE}",
        "-I",
        str(src.parent),
        "-I",
        str(HELPER_DIR),
        str(src),
        str(HELPER_DIR / "wrap_main.c"),
        str(HELPER_DIR / "prog_timer.c"),
        "-Wl,--wrap=main",
        "-lm",
        "-o",
        str(out_bin),
    ]
    proc = run_cmd(cmd, cwd=src.parent)
    if proc.returncode != 0:
        raise RuntimeError(f"compile failed for {src}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


def run_bin(bin_path: Path) -> Dict:
    proc = run_cmd([str(bin_path)], cwd=bin_path.parent, cpu_set=CPU_SET)
    total_ns = parse_total_ns(proc.stderr)
    return {
        "returncode": proc.returncode,
        "time_s": total_ns / 1e9,
        "program_total_ns": total_ns,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }


def summarize(xs: Sequence[float]) -> Dict[str, float]:
    vals = list(xs)
    return {
        "count": len(vals),
        "mean_s": statistics.fmean(vals),
        "min_s": min(vals),
        "max_s": max(vals),
        "stddev_s": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def build_reweighted_schedule() -> Dict:
    dag_json = read_json(DAG_JSON)
    segments_json = read_json(SEGMENTS_JSON)
    rows = read_json(REWEIGHT_TABLE)
    timing_json = {
        "schema_version": "1.0",
        "base_name": "zhang22",
        "level": "level2",
        "rule_name": "effective_line_merge",
        "view": "single",
        "repeats": 1,
        "weights": {
            row["seg_id"]: {
                "total_ns": int(row["suggested_weight_ns"]),
                "count": 1,
                "avg_ns": int(row["suggested_weight_ns"]),
                "min_ns": int(row["suggested_weight_ns"]),
                "max_ns": int(row["suggested_weight_ns"]),
            }
            for row in rows
        },
    }
    algo = Zhao2020BlockAlgo()
    return algo.compute(dag_json=dag_json, segments_json=segments_json, timing_json=timing_json)


def prepare_sources() -> Dict[str, Path]:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    src_dir = OUT_DIR / "src"
    bin_dir = OUT_DIR / "bin"
    src_dir.mkdir(parents=True, exist_ok=True)
    bin_dir.mkdir(parents=True, exist_ok=True)

    baseline_src = src_dir / "baseline.c"
    baseline_src.write_text(SRC_ORIGINAL.read_text(encoding="utf-8"), encoding="utf-8")
    (src_dir / "prio_runtime.h").write_text((HELPER_DIR / "prio_runtime.h").read_text(encoding="utf-8"), encoding="utf-8")

    current_src = src_dir / "prio_current.c"
    current_src.write_text(SRC_CURRENT.read_text(encoding="utf-8"), encoding="utf-8")

    reweight_src = src_dir / "prio_reweight.c"
    reweight_src.write_text(SRC_ORIGINAL.read_text(encoding="utf-8"), encoding="utf-8")
    reweight_schedule = build_reweighted_schedule()
    instrument_prio_all_segments_by_start_line(
        reweight_src,
        segments_json=SEGMENTS_JSON,
        priorities={str(k): int(v) for k, v in reweight_schedule["priorities"].items()},
        out_c=reweight_src,
    )

    write_json(OUT_DIR / "reweighted_schedule.json", reweight_schedule)
    return {
        "baseline": baseline_src,
        "current": current_src,
        "reweight": reweight_src,
    }


def main() -> int:
    sources = prepare_sources()
    current_schedule = read_json(SCHEDULE_CURRENT)
    reweight_schedule = read_json(OUT_DIR / "reweighted_schedule.json")

    changed = {
        seg_id: {
            "old": int(current_schedule["priorities"][seg_id]),
            "new": int(reweight_schedule["priorities"][seg_id]),
        }
        for seg_id in current_schedule["priorities"]
        if int(current_schedule["priorities"][seg_id]) != int(reweight_schedule["priorities"][seg_id])
    }

    bins = {name: OUT_DIR / "bin" / f"{name}.bin" for name in sources}
    for name, src in sources.items():
        compile_one(src, bins[name])

    groups: List[Dict] = []
    baseline_means: List[float] = []
    current_means: List[float] = []
    reweight_means: List[float] = []

    for g in range(1, GROUPS + 1):
        group_runs: Dict[str, List[Dict]] = {"baseline": [], "current": [], "reweight": []}
        for _ in range(REPEATS):
            for name in ("baseline", "current", "reweight"):
                group_runs[name].append(run_bin(bins[name]))
        group_summary = {
            "group": g,
            "baseline": summarize([x["time_s"] for x in group_runs["baseline"]]),
            "current": summarize([x["time_s"] for x in group_runs["current"]]),
            "reweight": summarize([x["time_s"] for x in group_runs["reweight"]]),
            "improve_current_pct": (statistics.fmean(x["time_s"] for x in group_runs["baseline"]) - statistics.fmean(x["time_s"] for x in group_runs["current"])) / statistics.fmean(x["time_s"] for x in group_runs["baseline"]) * 100.0,
            "improve_reweight_pct": (statistics.fmean(x["time_s"] for x in group_runs["baseline"]) - statistics.fmean(x["time_s"] for x in group_runs["reweight"])) / statistics.fmean(x["time_s"] for x in group_runs["baseline"]) * 100.0,
        }
        groups.append(group_summary)
        baseline_means.append(group_summary["baseline"]["mean_s"])
        current_means.append(group_summary["current"]["mean_s"])
        reweight_means.append(group_summary["reweight"]["mean_s"])

    summary = {
        "work_scale": WORK_SCALE,
        "repeats_per_group": REPEATS,
        "groups": GROUPS,
        "cpu_set": CPU_SET,
        "priority_changes": changed,
        "group_results": groups,
        "cross_group": {
            "baseline": summarize(baseline_means),
            "current": summarize(current_means),
            "reweight": summarize(reweight_means),
            "improve_current_pct": summarize([g["improve_current_pct"] for g in groups]),
            "improve_reweight_pct": summarize([g["improve_reweight_pct"] for g in groups]),
        },
    }
    write_json(OUT_DIR / "summary.json", summary)

    lines = [
        "# zhang22 Reweight Experiment",
        "",
        f"- generated_at: {subprocess.check_output(['date', '-Iseconds'], text=True).strip()}",
        f"- host: {subprocess.check_output(['hostname'], text=True).strip()}",
        f"- work_scale: {WORK_SCALE}",
        f"- repeats_per_group: {REPEATS}",
        f"- groups: {GROUPS}",
        "",
        "## Priority Changes",
        "",
        f"- changed_count: {len(changed)}",
    ]
    for seg_id, pair in changed.items():
        lines.append(f"- `{seg_id}`: {pair['old']} -> {pair['new']}")
    lines.extend([
        "",
        "## Cross-group Means",
        "",
        f"- baseline mean: `{summary['cross_group']['baseline']['mean_s']:.6f} s`",
        f"- current-schedule prio mean: `{summary['cross_group']['current']['mean_s']:.6f} s`",
        f"- reweighted-schedule prio mean: `{summary['cross_group']['reweight']['mean_s']:.6f} s`",
        f"- current improvement vs baseline: `{summary['cross_group']['improve_current_pct']['mean_s']:.2f}%`",
        f"- reweight improvement vs baseline: `{summary['cross_group']['improve_reweight_pct']['mean_s']:.2f}%`",
    ])
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
