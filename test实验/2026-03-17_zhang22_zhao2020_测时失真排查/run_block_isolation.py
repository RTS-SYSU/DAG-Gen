#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import statistics
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "block_isolation_harness.c"
BIN = ROOT / "block_isolation_harness"
OUT_DIR = ROOT / "results"

WORK_SCALE = 80
REPEATS = 20
WEIGHTS = [1, 5, 10, 20, 50]

BLOCKS = {
    "mutex": {
        "source_ref": "worker_c0#001@125-127",
        "source_lines": "125-127",
        "helper_weight": 0.0,
        "modes": ["other-only", "busy-only", "full-block"],
    },
    "sem": {
        "source_ref": "worker_c2#002@101-104",
        "source_lines": "101-104",
        "helper_weight": 1.0,
        "modes": ["other-only", "busy-only", "full-block"],
    },
    "join": {
        "source_ref": "main#004@177-180",
        "source_lines": "177-180",
        "helper_weight": 1.0,
        "modes": ["other-only", "busy-only", "full-block"],
    },
}

ZHANG22_TIMING = {
    "mutex": 205,
    "sem": 175,
    "join": 94061,
}


def compile_binary() -> None:
    cmd = [
        "gcc",
        "-O2",
        "-g",
        "-std=c11",
        "-pthread",
        f"-DWORK_SCALE={WORK_SCALE}",
        str(SRC),
        "-o",
        str(BIN),
        "-lm",
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))


def summarize(values: list[int]) -> dict:
    mean = statistics.fmean(values)
    stddev = statistics.pstdev(values) if len(values) > 1 else 0.0
    return {
        "count": len(values),
        "mean_ns": mean,
        "min_ns": min(values),
        "max_ns": max(values),
        "stddev_ns": stddev,
    }


def run_one(block: str, mode: str, weight: int, helper_weight: float) -> dict:
    proc = subprocess.run(
        [str(BIN), block, mode, str(weight), str(REPEATS), str(helper_weight)],
        cwd=str(ROOT),
        check=True,
        text=True,
        capture_output=True,
    )
    rows: list[int] = []
    for line in proc.stdout.splitlines():
        parts = next(csv.reader([line]))
        rows.append(int(parts[-1]))
    summary = summarize(rows)
    payload = {
        "block": block,
        "mode": mode,
        "weight": weight,
        "helper_weight": helper_weight,
        "work_scale": WORK_SCALE,
        "repeats": REPEATS,
        "durations_ns": rows,
        "summary": summary,
        "stderr": proc.stderr.strip(),
    }
    path = OUT_DIR / f"{block}_{mode}_w{weight}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    compile_binary()

    matrix: dict[str, dict[str, dict[int, dict]]] = {}
    for block, cfg in BLOCKS.items():
        matrix[block] = {}
        for mode in cfg["modes"]:
            matrix[block][mode] = {}
            for weight in WEIGHTS:
                payload = run_one(block, mode, weight, cfg["helper_weight"])
                matrix[block][mode][weight] = payload

    report = {
        "work_scale": WORK_SCALE,
        "repeats": REPEATS,
        "weights": WEIGHTS,
        "blocks": BLOCKS,
        "zhang22_timing_avg_ns": ZHANG22_TIMING,
        "results": matrix,
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
