#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import os
import re
import shutil
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BASE_DIR = ROOT.parents[1]
SOURCE = BASE_DIR / "源文件" / "zhang22" / "zhang22.c"
SEGMENTS_JSON = BASE_DIR / "中间结果" / "zhang22" / "pipeline" / "blocks" / "level2" / "effective_line_merge" / "segments.json"

WORK_SCALE = 10
REPEATS = 10

OUT_DIR = ROOT / "total_time_compare"
SEG_PROJECT = OUT_DIR / "segment_project"
MAIN_PROJECT = OUT_DIR / "main_timer_project"
RUNTIME_RESULTS = OUT_DIR / "runtime_results"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_program_total_ns(text: str) -> int:
    m = re.findall(r"PROGRAM_TOTAL_NS=(\d+)", text)
    if not m:
        raise RuntimeError("missing PROGRAM_TOTAL_NS")
    return int(m[-1])


def load_segments() -> list[dict]:
    data = read_json(SEGMENTS_JSON)
    return list(data.get("segments", []))


def inject_segtrace(source_text: str, segments: list[dict]) -> str:
    lines = source_text.splitlines(keepends=True)
    before: dict[int, list[str]] = {}
    after: dict[int, list[str]] = {}
    for seg in segments:
        start = int(seg["start_line"])
        end = int(seg["end_line"])
        seg_id = str(seg["seg_id"])
        before.setdefault(start, []).append(f'SEG_BEGIN("{seg_id}");\n')
        after.setdefault(end, []).append(f'SEG_END("{seg_id}");\n')

    src_lines = list(lines)
    rendered: list[str] = []
    feature_inserted = False
    include_inserted = False
    for idx, line in enumerate(src_lines, start=1):
        if not include_inserted:
            rendered.append(line)
            if line.startswith("#define _GNU_SOURCE"):
                feature_inserted = True
                continue
            if feature_inserted:
                rendered.append('#include "segtrace.h"\n')
                include_inserted = True
                feature_inserted = False
            continue
        if idx in before:
            for item in sorted(before[idx]):
                rendered.append(item)
        rendered.append(line)
        if idx in after:
            for item in sorted(after[idx]):
                rendered.append(item)
    if not include_inserted:
        rendered.insert(0, '#include "segtrace.h"\n')
    rendered_text = "".join(rendered)
    rendered_text = rendered_text.replace(
        "int main(void) {\n",
        'int main(void) {\n  const char *__seg_dir = getenv("SEGTRACE_DIR");\n  if (__seg_dir && __seg_dir[0])\n    segtrace_init(__seg_dir);\n',
        1,
    )
    return rendered_text


def inject_main_timer(source_text: str) -> str:
    include = """
#include <stdint.h>

static uint64_t my_now_ns(void) {
  struct timespec ts;
#ifdef CLOCK_MONOTONIC_RAW
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
#else
  clock_gettime(CLOCK_MONOTONIC, &ts);
#endif
  return (uint64_t)ts.tv_sec * 1000000000ULL + (uint64_t)ts.tv_nsec;
}
"""
    if "#include <time.h>\n" in source_text and "static uint64_t my_now_ns(void)" not in source_text:
        source_text = source_text.replace("#include <time.h>\n", "#include <time.h>\n" + include, 1)
    source_text = source_text.replace("int main(void) {\n", "int main(void) {\n  uint64_t __prog_t0_ns = my_now_ns();\n", 1)
    source_text = source_text.replace("  return 0;\n}\n", '  fprintf(stderr, "PROGRAM_TOTAL_NS=%llu\\n", (unsigned long long)(my_now_ns() - __prog_t0_ns));\n  return 0;\n}\n', 1)
    return source_text


def setup_projects() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    SEG_PROJECT.mkdir(parents=True, exist_ok=True)
    MAIN_PROJECT.mkdir(parents=True, exist_ok=True)
    RUNTIME_RESULTS.mkdir(parents=True, exist_ok=True)

    source_text = SOURCE.read_text(encoding="utf-8")
    seg_source = inject_segtrace(source_text, load_segments())
    main_source = inject_main_timer(source_text)

    (SEG_PROJECT / "zhang22_segtrace.c").write_text(seg_source, encoding="utf-8")
    (SEG_PROJECT / "segtrace.c").write_text((BASE_DIR / "level1" / "segtrace.c").read_text(encoding="utf-8"), encoding="utf-8")
    (SEG_PROJECT / "segtrace.h").write_text((BASE_DIR / "level1" / "segtrace.h").read_text(encoding="utf-8"), encoding="utf-8")
    (MAIN_PROJECT / "zhang22_main_timer.c").write_text(main_source, encoding="utf-8")


def compile_c(project_dir: Path, output_name: str, sources: list[str]) -> Path:
    bin_path = project_dir / output_name
    cmd = ["gcc", "-O0", "-g", "-std=c11", "-pthread", f"-DWORK_SCALE={WORK_SCALE}", *sources, "-o", str(bin_path), "-lm", "-ldl"]
    proc = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True)
    (project_dir / f"{output_name}.compile.log").write_text("CMD: " + " ".join(cmd) + "\n" + proc.stdout + proc.stderr, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"compile failed for {output_name}: {proc.stderr[-400:]}")
    return bin_path


def run_segment_program(bin_path: Path) -> dict:
    trace_root = SEG_PROJECT / "trace_runs"
    trace_root.mkdir(parents=True, exist_ok=True)
    segment_runs: list[dict] = []
    for idx in range(1, REPEATS + 1):
        run_dir = trace_root / f"run_{idx:02d}"
        run_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        env["SEGTRACE_DIR"] = str(run_dir)
        proc = subprocess.run([str(bin_path)], cwd=str(SEG_PROJECT), env=env, capture_output=True, text=True)
        (run_dir / "stdout.log").write_text(proc.stdout or "", encoding="utf-8")
        (run_dir / "stderr.log").write_text(proc.stderr or "", encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(f"segment program failed at run {idx}: {proc.stderr[-400:]}")
        seg_sum = 0
        seg_by_id: dict[str, int] = {}
        for trace_file in sorted(run_dir.glob("trace.*.csv")):
            for row in csv.reader(trace_file.read_text(encoding="utf-8").splitlines()):
                seg_id = row[1].strip('"')
                dur = int(row[4])
                seg_sum += dur
                seg_by_id[seg_id] = seg_by_id.get(seg_id, 0) + dur
        segment_runs.append({"run": idx, "segment_sum_ns": seg_sum, "segments": seg_by_id})
    return {"runs": segment_runs}


def run_main_timer_program(bin_path: Path) -> dict:
    runs: list[dict] = []
    for idx in range(1, REPEATS + 1):
        proc = subprocess.run([str(bin_path)], cwd=str(MAIN_PROJECT), capture_output=True, text=True)
        (MAIN_PROJECT / f"run_{idx:02d}.stdout.log").write_text(proc.stdout or "", encoding="utf-8")
        (MAIN_PROJECT / f"run_{idx:02d}.stderr.log").write_text(proc.stderr or "", encoding="utf-8")
        if proc.returncode != 0:
            raise RuntimeError(f"main timer program failed at run {idx}: {proc.stderr[-400:]}")
        runs.append({"run": idx, "program_total_ns": parse_program_total_ns(proc.stderr or "")})
    return {"runs": runs}


def run_runtime_tool() -> tuple[Path, dict]:
    config = {
        "tasks": [
            {
                "baseline_c": str((MAIN_PROJECT / "zhang22_main_timer.c").resolve()),
                "prio_c": str((MAIN_PROJECT / "zhang22_main_timer.c").resolve()),
                "work_scale": WORK_SCALE,
                "repeats": REPEATS,
                "cores_per_task": 2,
                "cpu_list": [0, 1],
                "use_sudo": False,
            }
        ],
        "queue_mode": True,
    }
    config_path = OUT_DIR / "runtime_task.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
    cmd = [
        "python3",
        str(BASE_DIR / "tools" / "runtime_compare" / "main.py"),
        "--cli",
        "--results-root",
        str(RUNTIME_RESULTS),
        "--config",
        str(config_path),
        "--wait",
    ]
    proc = subprocess.run(cmd, cwd=str(BASE_DIR), capture_output=True, text=True)
    (OUT_DIR / "runtime_compare.stdout.log").write_text(proc.stdout or "", encoding="utf-8")
    (OUT_DIR / "runtime_compare.stderr.log").write_text(proc.stderr or "", encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"runtime compare failed: {proc.stderr[-400:]}")
    summary_files = sorted(RUNTIME_RESULTS.rglob("summary.json"))
    if not summary_files:
        raise RuntimeError("runtime compare summary.json not found")
    summary_path = summary_files[-1]
    return summary_path, read_json(summary_path)


def summarize_numbers(values: list[int | float]) -> dict:
    vals = [float(v) for v in values]
    return {
        "count": len(vals),
        "mean": statistics.fmean(vals),
        "min": min(vals),
        "max": max(vals),
        "stddev": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def main() -> int:
    setup_projects()
    seg_bin = compile_c(SEG_PROJECT, "app_segtrace", ["zhang22_segtrace.c", "segtrace.c"])
    main_bin = compile_c(MAIN_PROJECT, "app_main_timer", ["zhang22_main_timer.c"])

    segment_data = run_segment_program(seg_bin)
    main_timer_data = run_main_timer_program(main_bin)
    runtime_summary_path, runtime_summary = run_runtime_tool()

    segment_sums = [row["segment_sum_ns"] for row in segment_data["runs"]]
    main_totals = [row["program_total_ns"] for row in main_timer_data["runs"]]
    runtime_baseline_ns = [int(round(float(x) * 1e9)) for x in runtime_summary["baseline"]["times_s"]]

    report = {
        "work_scale": WORK_SCALE,
        "repeats": REPEATS,
        "paths": {
            "source": str(SOURCE),
            "segment_project": str(SEG_PROJECT),
            "main_project": str(MAIN_PROJECT),
            "runtime_summary": str(runtime_summary_path),
        },
        "segment_trace": {
            "runs": segment_data["runs"],
            "summary_ns": summarize_numbers(segment_sums),
        },
        "main_timer": {
            "runs": main_timer_data["runs"],
            "summary_ns": summarize_numbers(main_totals),
        },
        "runtime_tool_baseline": {
            "times_ns": runtime_baseline_ns,
            "summary_ns": summarize_numbers(runtime_baseline_ns),
            "summary_json": runtime_summary,
        },
    }
    (OUT_DIR / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
