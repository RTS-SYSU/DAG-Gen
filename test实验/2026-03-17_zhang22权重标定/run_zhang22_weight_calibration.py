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
from pathlib import Path
from typing import Dict, List, Sequence


PROGRAM_TOTAL_NS_RE = re.compile(r"PROGRAM_TOTAL_NS=(\d+)")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


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


def compile_c(src: Path, out_bin: Path, work_scale: int) -> None:
    root = repo_root()
    helper = root / "level1"
    cmd = [
        "gcc",
        "-O0",
        "-g",
        "-std=c11",
        "-pthread",
        f"-DWORK_SCALE={work_scale}",
        str(src),
        str(helper / "wrap_main.c"),
        str(helper / "prog_timer.c"),
        "-Wl,--wrap=main",
        "-lm",
        "-o",
        str(out_bin),
    ]
    proc = run_cmd(cmd, cwd=src.parent)
    if proc.returncode != 0:
        raise RuntimeError(f"compile failed: {src}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")


def stats(xs: Sequence[float]) -> Dict[str, float]:
    vals = list(xs)
    return {
        "n": float(len(vals)),
        "min_s": min(vals) if vals else 0.0,
        "max_s": max(vals) if vals else 0.0,
        "mean_s": statistics.mean(vals) if vals else 0.0,
        "median_s": statistics.median(vals) if vals else 0.0,
        "stdev_s": statistics.pstdev(vals) if len(vals) >= 2 else 0.0,
    }


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_busy_harness(out_path: Path) -> None:
    text = textwrap.dedent(
        """\
        #define _GNU_SOURCE
        #include <sched.h>
        #include <stdint.h>
        #include <stdio.h>

        #ifndef WORK_SCALE
        #define WORK_SCALE 1000
        #endif

        #ifndef BUSY_WEIGHT
        #define BUSY_WEIGHT 1.0
        #endif

        #ifndef BUSY_REPEATS
        #define BUSY_REPEATS 1
        #endif

        static volatile double g_busy_sink = 0.0;

        static void pin_cpu0(void) {
          cpu_set_t cpu_set;
          CPU_ZERO(&cpu_set);
          CPU_SET(0, &cpu_set);
          sched_setaffinity(0, sizeof(cpu_set), &cpu_set);
        }

        static void busy_wait_seconds(double seconds) {
          int units = (int)(seconds * WORK_SCALE + 0.5);
          if (units < 1)
            units = 1;

          double x = 1.000001;
          double y = 0.999999;
          double z = 1.0000003;
          double acc = 0.0;

          for (int r = 0; r < units; ++r) {
            for (int i = 0; i < 512; ++i) {
              x = x * 1.0000001 + y * 0.9999999 + z * 0.0000001;
              y = y * 1.0000002 + z * 0.9999998 + x * 0.0000002;
              z = z * 1.0000003 + x * 0.9999997 + y * 0.0000003;
              acc += x * y + z;
            }
          }

          g_busy_sink += acc;
        }

        int main(void) {
          pin_cpu0();
          for (int i = 0; i < BUSY_REPEATS; ++i) {
            busy_wait_seconds(BUSY_WEIGHT);
          }
          printf("busy_sink=%0.6f\\n", g_busy_sink);
          return 0;
        }
        """
    )
    write_text(out_path, text)


def build_zhang22_busy0(src_path: Path) -> None:
    original = (repo_root() / "源文件" / "zhang22" / "zhang22.c").read_text(encoding="utf-8")
    patched = original.replace(
        textwrap.dedent(
            """\
            static void busy_wait_seconds(double seconds) {
              int units = (int)(seconds * WORK_SCALE + 0.5);
              if (units < 1)
                units = 1;

              double x = 1.000001;
              double y = 0.999999;
              double z = 1.0000003;
              double acc = 0.0;

              for (int r = 0; r < units; ++r) {
                for (int i = 0; i < 512; ++i) {
                  x = x * 1.0000001 + y * 0.9999999 + z * 0.0000001;
                  y = y * 1.0000002 + z * 0.9999998 + x * 0.0000002;
                  z = z * 1.0000003 + x * 0.9999997 + y * 0.0000003;
                  acc += x * y + z;
                }
              }

              g_busy_sink += acc;
              mat_c[0][0] = g_busy_sink;
            }
            """
        ),
        textwrap.dedent(
            """\
            static void busy_wait_seconds(double seconds) {
              (void)seconds;
              g_busy_sink += 1.0;
              mat_c[0][0] = g_busy_sink;
            }
            """
        ),
        1,
    )
    if original == patched:
        raise RuntimeError("failed to patch busy_wait_seconds in zhang22.c")
    write_text(src_path, patched)


def run_binary(bin_path: Path, repeats: int, cpu_set: Sequence[int]) -> List[Dict]:
    runs: List[Dict] = []
    for i in range(repeats):
        proc = run_cmd([str(bin_path)], cwd=bin_path.parent, cpu_set=cpu_set)
        total_ns = parse_total_ns(proc.stderr)
        runs.append(
            {
                "iter": i + 1,
                "returncode": proc.returncode,
                "time_s": total_ns / 1e9,
                "program_total_ns": total_ns,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
            }
        )
    return runs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--busy-work-scale", type=int, default=500)
    parser.add_argument("--busy-repeats", type=int, default=5)
    parser.add_argument("--weights", default="1,2,5,10,20,50,100")
    parser.add_argument("--zhang22-work-scale", type=int, default=5)
    parser.add_argument("--zhang22-repeats", type=int, default=8)
    parser.add_argument("--cpu-list", default="0,1,2,3")
    args = parser.parse_args()

    root = repo_root()
    exp_dir = root / "test实验" / "2026-03-17_zhang22权重标定" / "results"
    if exp_dir.exists():
        shutil.rmtree(exp_dir)
    (exp_dir / "src").mkdir(parents=True, exist_ok=True)
    (exp_dir / "bin").mkdir(parents=True, exist_ok=True)

    cpu_list = [int(x) for x in args.cpu_list.split(",") if x.strip()]

    # Busy harness calibration
    harness_src = exp_dir / "src" / "busy_harness.c"
    build_busy_harness(harness_src)
    weight_results: List[Dict] = []
    for weight in [float(x) for x in args.weights.split(",") if x.strip()]:
        out_bin = exp_dir / "bin" / f"busy_w_{str(weight).replace('.', '_')}"
        cmd = [
            "gcc",
            "-O0",
            "-g",
            "-std=c11",
            "-pthread",
            f"-DWORK_SCALE={args.busy_work_scale}",
            f"-DBUSY_WEIGHT={weight}",
            f"-DBUSY_REPEATS={args.busy_repeats}",
            str(harness_src),
            str(root / "level1" / "wrap_main.c"),
            str(root / "level1" / "prog_timer.c"),
            "-Wl,--wrap=main",
            "-lm",
            "-o",
            str(out_bin),
        ]
        proc = run_cmd(cmd, cwd=harness_src.parent)
        if proc.returncode != 0:
            raise RuntimeError(f"compile busy harness failed for weight={weight}\n{proc.stderr}")
        runs = run_binary(out_bin, repeats=args.zhang22_repeats, cpu_set=[cpu_list[0]])
        mean_s = statistics.mean(r["time_s"] for r in runs)
        weight_results.append(
            {
                "weight": weight,
                "busy_repeats": args.busy_repeats,
                "per_call_mean_s": mean_s / args.busy_repeats,
                "total_stats": stats([r["time_s"] for r in runs]),
                "runs": runs,
            }
        )

    # Zhang22 current vs busy0
    zhang22_src = root / "源文件" / "zhang22" / "zhang22.c"
    zhang22_busy0_src = exp_dir / "src" / "zhang22_busy0.c"
    build_zhang22_busy0(zhang22_busy0_src)
    zhang22_current_bin = exp_dir / "bin" / "zhang22_current"
    zhang22_busy0_bin = exp_dir / "bin" / "zhang22_busy0"
    compile_c(zhang22_src, zhang22_current_bin, args.zhang22_work_scale)
    compile_c(zhang22_busy0_src, zhang22_busy0_bin, args.zhang22_work_scale)
    current_runs = run_binary(zhang22_current_bin, repeats=args.zhang22_repeats, cpu_set=cpu_list)
    busy0_runs = run_binary(zhang22_busy0_bin, repeats=args.zhang22_repeats, cpu_set=cpu_list)

    summary = {
        "busy_calibration": weight_results,
        "zhang22_compare": {
            "work_scale": args.zhang22_work_scale,
            "current": {
                "stats": stats([r["time_s"] for r in current_runs]),
                "runs": current_runs,
            },
            "busy0": {
                "stats": stats([r["time_s"] for r in busy0_runs]),
                "runs": busy0_runs,
            },
        },
    }
    (exp_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    with (exp_dir / "busy_calibration.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["weight", "busy_repeats", "per_call_mean_s", "total_mean_s", "total_stdev_s"])
        for item in weight_results:
            w.writerow([
                item["weight"],
                item["busy_repeats"],
                f"{item['per_call_mean_s']:.9f}",
                f"{item['total_stats']['mean_s']:.9f}",
                f"{item['total_stats']['stdev_s']:.9f}",
            ])

    current_mean = summary["zhang22_compare"]["current"]["stats"]["mean_s"]
    busy0_mean = summary["zhang22_compare"]["busy0"]["stats"]["mean_s"]
    busy_share = 1.0 - (busy0_mean / current_mean) if current_mean > 1e-12 else 0.0

    lines = [
        "# zhang22 Weight Calibration Report",
        "",
        f"- generated_at: {subprocess.check_output(['date', '-Iseconds'], text=True).strip()}",
        f"- host: {subprocess.check_output(['hostname'], text=True).strip()}",
        f"- busy_work_scale: {args.busy_work_scale}",
        f"- zhang22_work_scale: {args.zhang22_work_scale}",
        f"- calibration_repeats: {args.zhang22_repeats}",
        "",
        "## Busy Calibration",
        "",
        "| weight | per_call_mean_s | per_call_mean_ms | total_mean_s | stdev_s |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in weight_results:
        lines.append(
            f"| {item['weight']} | {item['per_call_mean_s']:.9f} | {item['per_call_mean_s']*1000:.6f} | {item['total_stats']['mean_s']:.9f} | {item['total_stats']['stdev_s']:.9f} |"
        )
    lines.extend([
        "",
        "## zhang22 Current vs busy=0",
        "",
        f"- current mean: `{current_mean:.6f} s`",
        f"- busy=0 mean: `{busy0_mean:.6f} s`",
        f"- estimated compute share: `{busy_share:.4%}`",
        f"- estimated structural share: `{(busy0_mean / current_mean) if current_mean > 1e-12 else 0.0:.4%}`",
        "",
        "## Interpretation",
        "",
        "- `busy=0` 版本保留线程、锁、信号量、join、affinity，只把计算节点替换为空计算，因此它近似表示结构底噪。",
        "- `busy_calibration` 给出单个 `busy_wait_seconds(weight)` 调用在当前实现下的平均时间，可作为后续块权重重建的计算成本映射。",
    ])
    (exp_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(exp_dir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
