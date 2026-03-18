#!/usr/bin/env python3
from __future__ import annotations

import json
import shutil
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parents[1]

SOURCE_ORIGINAL = (
    BASE_DIR
    / "中间结果"
    / "zhang22"
    / "pipeline"
    / "instrument"
    / "level2"
    / "effective_line_merge"
    / "zhao2020"
    / "source_original.c"
)
SOURCE_INSTRUMENTED = (
    BASE_DIR
    / "中间结果"
    / "zhang22"
    / "pipeline"
    / "instrument"
    / "level2"
    / "effective_line_merge"
    / "zhao2020"
    / "source_instrumented.c"
)

PROG_TIMER_DIR = BASE_DIR / "tools" / "runtime_compare" / "testdata" / "laplace_phi4_baseline"
RUNTIME_MAIN = BASE_DIR / "tools" / "runtime_compare" / "main.py"

WORK_SCALE = 100
REPEATS = 10
GROUP_COUNT = 5

OUT_ROOT = ROOT / "runtime_compare_strict_batch5"
PREPARED_ROOT = OUT_ROOT / "prepared_sources"
RESULTS_ROOT = OUT_ROOT / "runtime_results"
CONFIG_DIR = OUT_ROOT / "configs"
SUMMARY_PATH = OUT_ROOT / "batch_summary.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def summarize(vals: list[float]) -> dict:
    return {
        "count": len(vals),
        "mean": statistics.fmean(vals),
        "min": min(vals),
        "max": max(vals),
        "stddev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def prepare_sources() -> tuple[Path, Path]:
    baseline_dir = PREPARED_ROOT / "baseline_zhao2020_strict"
    prio_dir = PREPARED_ROOT / "prio_zhao2020_strict"
    if PREPARED_ROOT.exists():
        shutil.rmtree(PREPARED_ROOT)
    baseline_dir.mkdir(parents=True, exist_ok=True)
    prio_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(SOURCE_ORIGINAL, baseline_dir / "source_original.c")
    shutil.copy2(SOURCE_INSTRUMENTED, prio_dir / "source_instrumented.c")
    for helper_name in ("wrap_main.c", "prog_timer.c", "prog_timer.h"):
        helper_src = PROG_TIMER_DIR / helper_name
        shutil.copy2(helper_src, baseline_dir / helper_name)
        shutil.copy2(helper_src, prio_dir / helper_name)
    return baseline_dir / "source_original.c", prio_dir / "source_instrumented.c"


def make_config(baseline_c: Path, prio_c: Path) -> dict:
    return {
        "tasks": [
            {
                "baseline_c": str(baseline_c.resolve()),
                "prio_c": str(prio_c.resolve()),
                "work_scale": WORK_SCALE,
                "repeats": REPEATS,
                "cores_per_task": 2,
                "cpu_list": [0, 1],
                "use_sudo": False,
            }
        ],
        "queue_mode": True,
    }


def newest_summary() -> Path:
    summaries = sorted(RESULTS_ROOT.rglob("summary.json"), key=lambda p: p.stat().st_mtime_ns)
    if not summaries:
        raise RuntimeError("summary.json not found")
    return summaries[-1]


def run_one_group(group_idx: int, baseline_c: Path, prio_c: Path) -> dict:
    config_path = CONFIG_DIR / f"runtime_task_group_{group_idx:02d}.json"
    write_json(config_path, make_config(baseline_c, prio_c))
    stdout_path = OUT_ROOT / f"group_{group_idx:02d}.stdout.log"
    stderr_path = OUT_ROOT / f"group_{group_idx:02d}.stderr.log"
    cmd = [
        "python3",
        str(RUNTIME_MAIN),
        "--cli",
        "--results-root",
        str(RESULTS_ROOT),
        "--config",
        str(config_path),
        "--no-resume",
        "--wait",
    ]
    proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    stdout_path.write_text(proc.stdout or "", encoding="utf-8")
    stderr_path.write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"group {group_idx} failed: {proc.stderr[-500:]}")

    summary_path = newest_summary()
    summary = read_json(summary_path)

    baseline_times = [float(x) for x in summary["baseline"]["times_s"]]
    prio_times = [float(x) for x in summary["prio"]["times_s"]]
    parsed_ok = all(bool(run.get("parsed_from_program_output", run.get("parsed_from_stdout"))) for run in summary["runs"])
    if not parsed_ok:
        raise RuntimeError(f"group {group_idx} has non-program-output timing parse")

    return {
        "group": group_idx,
        "summary_path": str(summary_path),
        "baseline_mean_s": float(summary["baseline"]["stats"]["mean_s"]),
        "prio_mean_s": float(summary["prio"]["stats"]["mean_s"]),
        "improvement_ratio_pct": (float(summary["baseline"]["stats"]["mean_s"]) - float(summary["prio"]["stats"]["mean_s"]))
        / float(summary["baseline"]["stats"]["mean_s"])
        * 100.0,
        "baseline_times_s": baseline_times,
        "prio_times_s": prio_times,
        "affinity_rewritten_in_source": summary.get("affinity_rewritten_in_source", {}),
        "all_runs_parsed_from_program_output": parsed_ok,
    }


def main() -> int:
    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    RESULTS_ROOT.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    baseline_c, prio_c = prepare_sources()

    groups: list[dict] = []
    for idx in range(1, GROUP_COUNT + 1):
        groups.append(run_one_group(idx, baseline_c, prio_c))

    baseline_means = [g["baseline_mean_s"] for g in groups]
    prio_means = [g["prio_mean_s"] for g in groups]
    improvements = [g["improvement_ratio_pct"] for g in groups]

    batch_summary = {
        "work_scale": WORK_SCALE,
        "repeats": REPEATS,
        "group_count": GROUP_COUNT,
        "prepared_sources": {
            "baseline": str(baseline_c),
            "prio": str(prio_c),
        },
        "groups": groups,
        "cross_group_summary": {
            "baseline_mean_s": summarize(baseline_means),
            "prio_mean_s": summarize(prio_means),
            "improvement_ratio_pct": summarize(improvements),
        },
    }
    write_json(SUMMARY_PATH, batch_summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
