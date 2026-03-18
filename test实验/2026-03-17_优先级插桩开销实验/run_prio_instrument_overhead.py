#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import statistics
import subprocess
import textwrap
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PROGRAM_TOTAL_NS_RE = re.compile(r"PROGRAM_TOTAL_NS=(\d+)")
PRIO_FAIL_RE = re.compile(r"L1_PRIO_SET_FAILED")


@dataclass
class Variant:
    name: str
    source_path: Path
    insert_lines: List[int]
    priorities: List[int]
    family: str
    helper_mode: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def feature_insert_at(lines: Sequence[str]) -> int:
    feature_def_re = re.compile(r"^\s*#\s*define\s+_(GNU|DEFAULT|POSIX|XOPEN|BSD|SVID)_SOURCE\b")
    insert_at = 0
    for i, line in enumerate(lines):
        if feature_def_re.match(line):
            insert_at = i + 1
            continue
        break
    return insert_at


def inject_include_and_calls(source_text: str, *, insertions: Dict[int, List[int]]) -> str:
    lines0 = source_text.splitlines(keepends=True)
    insert_at = feature_insert_at(lines0)
    lines = lines0[:insert_at] + ['#include "prio_runtime.h"\n'] + lines0[insert_at:]
    shifted = {line_no + 1: list(prios) for line_no, prios in insertions.items()}

    out: List[str] = []
    for idx in range(1, len(lines) + 1):
        prios = shifted.get(idx, [])
        if prios:
            indent = re.match(r"[ \t]*", lines[idx - 1]).group(0)
            for prio in prios:
                out.append(f"{indent}l1_set_thread_prio_fifo({prio});\n")
        out.append(lines[idx - 1])
    return "".join(out)


def parse_program_total_ns(stdout: str, stderr: str) -> int:
    matches = PROGRAM_TOTAL_NS_RE.findall(f"{stdout}\n{stderr}")
    if not matches:
        raise RuntimeError("missing PROGRAM_TOTAL_NS in program output")
    return int(matches[-1])


def run_cmd(
    cmd: Sequence[str],
    *,
    cwd: Path,
    cpu_set: Iterable[int] | None = None,
) -> subprocess.CompletedProcess[str]:
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


def compile_variant(variant: Variant, out_bin: Path, work_scale: int) -> None:
    root = repo_root()
    helper_dir = root / "level1"
    cmd = [
        "gcc",
        "-O0",
        "-g",
        "-std=c11",
        "-pthread",
        f"-DWORK_SCALE={work_scale}",
        "-I",
        str(variant.source_path.parent),
        "-I",
        str(helper_dir),
        str(variant.source_path),
        str(helper_dir / "wrap_main.c"),
        str(helper_dir / "prog_timer.c"),
        "-Wl,--wrap=main",
        "-lm",
        "-o",
        str(out_bin),
    ]
    proc = run_cmd(cmd, cwd=variant.source_path.parent)
    if proc.returncode != 0:
        raise RuntimeError(f"compile failed for {variant.name}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


def stats(values: Sequence[float]) -> Dict[str, float]:
    xs = list(values)
    return {
        "n": float(len(xs)),
        "min_s": min(xs) if xs else 0.0,
        "max_s": max(xs) if xs else 0.0,
        "mean_s": statistics.mean(xs) if xs else 0.0,
        "median_s": statistics.median(xs) if xs else 0.0,
        "stdev_s": statistics.pstdev(xs) if len(xs) >= 2 else 0.0,
    }


def make_standalone_template() -> str:
    return textwrap.dedent(
        """\
        #define _GNU_SOURCE
        #include <math.h>
        #include <pthread.h>
        #include <sched.h>
        #include <stdint.h>
        #include <stdio.h>
        #include <stdlib.h>
        #include <string.h>
        #include <time.h>

        #ifndef WORK_SCALE
        #define WORK_SCALE 600
        #endif

        #define MAT_N 32
        static double mat_a[MAT_N][MAT_N];
        static double mat_b[MAT_N][MAT_N];
        static double mat_c[MAT_N][MAT_N];

        static void init_matrices(void) {
          for (int i = 0; i < MAT_N; ++i) {
            for (int j = 0; j < MAT_N; ++j) {
              mat_a[i][j] = (double)(i + j + 1);
              mat_b[i][j] = (double)(i * 2 + j + 3);
              mat_c[i][j] = 0.0;
            }
          }
        }

        static void busy_work(int units) {
          for (int r = 0; r < units * WORK_SCALE; ++r) {
            for (int i = 0; i < MAT_N; ++i) {
              for (int j = 0; j < MAT_N; ++j) {
                double accum = 0.0;
                for (int k = 0; k < MAT_N; ++k) {
                  accum += mat_a[i][k] * mat_b[k][j];
                }
                mat_c[i][j] = accum;
              }
            }
          }
        }

        int main(void) {
          cpu_set_t cpu_set;
          CPU_ZERO(&cpu_set);
          CPU_SET(0, &cpu_set);
          sched_setaffinity(0, sizeof(cpu_set), &cpu_set);

          init_matrices();
          busy_work(4);
          busy_work(4);
          busy_work(4);
          busy_work(4);
          printf("standalone_checksum=%0.3f\\n", mat_c[0][0]);
          return 0;
        }
        """
    )


def write_runtime_header(dst_dir: Path, helper_mode: str) -> None:
    if helper_mode == "probe":
        text = textwrap.dedent(
            """\
            #pragma once
            #include <pthread.h>
            #include <sched.h>
            #include <string.h>

            static inline void l1_set_thread_prio_fifo(int prio) {
                (void)prio;
                int policy = 0;
                struct sched_param sp;
                memset(&sp, 0, sizeof(sp));
                if (pthread_getschedparam(pthread_self(), &policy, &sp) != 0) {
                    return;
                }
                (void)pthread_setschedparam(pthread_self(), policy, &sp);
            }
            """
        )
    elif helper_mode == "real":
        text = (repo_root() / "level1" / "prio_runtime.h").read_text(encoding="utf-8")
    else:
        raise ValueError(f"unknown helper_mode: {helper_mode}")
    (dst_dir / "prio_runtime.h").write_text(text, encoding="utf-8")


def build_standalone_variants(work_dir: Path, helper_mode: str) -> List[Variant]:
    src_dir = work_dir / "sources"
    src_dir.mkdir(parents=True, exist_ok=True)
    write_runtime_header(src_dir, helper_mode)
    baseline_text = make_standalone_template()
    baseline_path = src_dir / "standalone_baseline.c"
    baseline_path.write_text(baseline_text, encoding="utf-8")

    variants = [Variant("standalone_baseline", baseline_path, [], [], "standalone", helper_mode)]
    plans = [
        ("standalone_main_once", {50: [99]}),
        ("standalone_phase_4sites", {50: [99], 51: [98], 52: [97], 53: [96]}),
    ]
    for name, insertions in plans:
        path = src_dir / f"{name}.c"
        path.write_text(inject_include_and_calls(baseline_text, insertions=insertions), encoding="utf-8")
        lines: List[int] = []
        prios: List[int] = []
        for line_no, values in insertions.items():
            for value in values:
                lines.append(line_no)
                prios.append(value)
        variants.append(Variant(name, path, lines, prios, "standalone", helper_mode))
    return variants


def build_zhang22_variants(work_dir: Path, helper_mode: str) -> List[Variant]:
    root = repo_root()
    src_dir = work_dir / "sources"
    src_dir.mkdir(parents=True, exist_ok=True)
    write_runtime_header(src_dir, helper_mode)
    zhang22_text = (root / "源文件" / "zhang22" / "zhang22.c").read_text(encoding="utf-8")
    baseline_path = src_dir / "zhang22_baseline.c"
    baseline_path.write_text(zhang22_text, encoding="utf-8")

    variants = [Variant("zhang22_baseline", baseline_path, [], [], "zhang22", helper_mode)]

    segments_path = root / "中间结果" / "zhang22" / "pipeline" / "blocks" / "level2" / "effective_line_merge" / "segments.json"
    seg_data = json.loads(segments_path.read_text(encoding="utf-8"))
    segment_lines = [
        int(seg["start_line"])
        for seg in seg_data.get("segments", [])
        if isinstance(seg, dict) and isinstance(seg.get("start_line"), int)
    ]
    segment_prios = list(range(99, 99 - len(segment_lines), -1))

    plans = [
        ("zhang22_main_entry_only", {132: [99]}),
        ("zhang22_worker_entries_only", {98: [91], 113: [90], 125: [89]}),
        ("zhang22_main_segments_only", {132: [99], 169: [98], 172: [97], 177: [96], 181: [95], 185: [94], 189: [93], 192: [92]}),
        ("zhang22_all_segments", {line_no: [prio] for line_no, prio in zip(segment_lines, segment_prios)}),
    ]
    for name, insertions in plans:
        path = src_dir / f"{name}.c"
        path.write_text(inject_include_and_calls(zhang22_text, insertions=insertions), encoding="utf-8")
        lines: List[int] = []
        prios: List[int] = []
        for line_no, values in insertions.items():
            for value in values:
                lines.append(line_no)
                prios.append(value)
        variants.append(Variant(name, path, lines, prios, "zhang22", helper_mode))
    return variants


def run_variant(
    variant: Variant,
    *,
    bin_dir: Path,
    repeats: int,
    work_scale: int,
    cpu_set: Iterable[int],
) -> Dict:
    out_bin = bin_dir / variant.name
    compile_variant(variant, out_bin, work_scale)
    runs: List[Dict] = []
    values: List[float] = []
    fail_counts: List[int] = []

    for idx in range(repeats):
        proc = run_cmd([str(out_bin)], cwd=out_bin.parent, cpu_set=cpu_set)
        total_ns = parse_program_total_ns(proc.stdout, proc.stderr)
        fail_count = len(PRIO_FAIL_RE.findall(proc.stderr))
        values.append(total_ns / 1e9)
        fail_counts.append(fail_count)
        runs.append(
            {
                "iter": idx + 1,
                "returncode": proc.returncode,
                "program_total_ns": total_ns,
                "time_s": total_ns / 1e9,
                "prio_fail_count": fail_count,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )

    return {
        "variant": variant.name,
        "family": variant.family,
        "insert_count": len(variant.insert_lines),
        "insert_lines": variant.insert_lines,
        "priorities": variant.priorities,
        "helper_mode": variant.helper_mode,
        "work_scale": work_scale,
        "repeats": repeats,
        "stats": stats(values),
        "avg_prio_fail_count": statistics.mean(fail_counts) if fail_counts else 0.0,
        "runs": runs,
    }


def write_report(out_dir: Path, results: List[Dict]) -> None:
    by_name = {item["variant"]: item for item in results}
    baselines = {
        "standalone": by_name["standalone_baseline"]["stats"]["mean_s"],
        "zhang22": by_name["zhang22_baseline"]["stats"]["mean_s"],
    }
    lines = [
        "# Priority Instrumentation Overhead Report",
        "",
        f"- generated_at: {subprocess.check_output(['date', '-Iseconds'], text=True).strip()}",
        f"- host: {subprocess.check_output(['hostname'], text=True).strip()}",
        f"- helper_mode: {results[0]['helper_mode'] if results else 'unknown'}",
        "- note: `probe` mode keeps the instrumentation call path but reapplies the current scheduling policy/priority, so it measures insertion cost without intended scheduling benefit.",
        "",
        "## Summary",
        "",
        "| variant | family | insert_count | mean_s | median_s | stdev_s | delta_vs_baseline_s | overhead_ratio | avg_prio_fail_count |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        base = baselines[item["family"]]
        mean_s = item["stats"]["mean_s"]
        delta = mean_s - base
        ratio = delta / base if base > 1e-12 else 0.0
        lines.append(
            f"| {item['variant']} | {item['family']} | {item['insert_count']} | {mean_s:.6f} | {item['stats']['median_s']:.6f} | {item['stats']['stdev_s']:.6f} | {delta:.6f} | {ratio:.4f} | {item['avg_prio_fail_count']:.2f} |"
        )
    lines.extend(["", "## Insertions", ""])
    for item in results:
        lines.append(f"- `{item['variant']}`: lines={item['insert_lines']} priorities={item['priorities']} helper_mode={item['helper_mode']}")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--work-scale-standalone", type=int, default=400)
    parser.add_argument("--work-scale-zhang22", type=int, default=10)
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--cpu-list", default="0,1,2,3")
    parser.add_argument("--helper-mode", choices=["probe", "real"], default="probe")
    args = parser.parse_args()

    root = repo_root()
    work_root = root / "test实验" / "2026-03-17_优先级插桩开销实验"
    exp_dir = work_root / "results"
    if exp_dir.exists():
        shutil.rmtree(exp_dir)
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "bin").mkdir(exist_ok=True)

    cpu_set = [int(x) for x in args.cpu_list.split(",") if x.strip()]
    results: List[Dict] = []

    for variant in build_standalone_variants(exp_dir, args.helper_mode):
        results.append(
            run_variant(
                variant,
                bin_dir=exp_dir / "bin",
                repeats=args.repeats,
                work_scale=args.work_scale_standalone,
                cpu_set=[cpu_set[0]],
            )
        )

    for variant in build_zhang22_variants(exp_dir, args.helper_mode):
        results.append(
            run_variant(
                variant,
                bin_dir=exp_dir / "bin",
                repeats=args.repeats,
                work_scale=args.work_scale_zhang22,
                cpu_set=cpu_set,
            )
        )

    (exp_dir / "summary.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    with (exp_dir / "runs.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["variant", "family", "iter", "time_s", "program_total_ns", "prio_fail_count", "returncode"])
        for item in results:
            for run in item["runs"]:
                writer.writerow(
                    [
                        item["variant"],
                        item["family"],
                        run["iter"],
                        f"{run['time_s']:.9f}",
                        run["program_total_ns"],
                        run["prio_fail_count"],
                        run["returncode"],
                    ]
                )

    write_report(exp_dir, results)
    print(str(exp_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
