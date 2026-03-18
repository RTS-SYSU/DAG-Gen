#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import statistics
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TIMING_JSON = ROOT / "中间结果" / "zhang22" / "pipeline" / "timing" / "level2" / "effective_line_merge" / "timing.json"
TIMING_COMPILE_ERR = ROOT / "中间结果" / "zhang22" / "pipeline" / "timing" / "level2" / "effective_line_merge" / "logs" / "compile.stderr.log"
SEGMENTS_JSON = ROOT / "中间结果" / "zhang22" / "pipeline" / "blocks" / "level2" / "effective_line_merge" / "segments.json"
SOURCE_ORIGINAL = ROOT / "中间结果" / "zhang22" / "pipeline" / "instrument" / "level2" / "effective_line_merge" / "zhao2020" / "source_original.c"
CALIBRATION_JSON = ROOT / "test实验" / "2026-03-17_zhang22权重标定" / "results" / "summary.json"
OUT_DIR = ROOT / "test实验" / "2026-03-17_zhang22块时间验证" / "results"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def interp(weight: float, pts):
    if weight <= pts[0][0]:
        return pts[0][1] * weight / pts[0][0]
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        if x1 <= weight <= x2:
            t = (weight - x1) / (x2 - x1)
            return y1 + t * (y2 - y1)
    x1, y1 = pts[-2]
    x2, y2 = pts[-1]
    t = (weight - x1) / (x2 - x1)
    return y1 + t * (y2 - y1)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not TIMING_JSON.exists():
        payload = {
            "status": "timing_stage_failed",
            "timing_json_exists": False,
            "compile_stderr": TIMING_COMPILE_ERR.read_text(encoding="utf-8", errors="replace") if TIMING_COMPILE_ERR.exists() else "",
        }
        (OUT_DIR / "summary.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        lines = [
            "# zhang22 Block Timing Validation",
            "",
            "- status: timing_stage_failed",
            "- current pipeline timing stage did not produce timing.json on the updated zhang22 source.",
            "",
            "## Compile Error",
            "",
            "```text",
            payload["compile_stderr"].rstrip(),
            "```",
            "",
            "## Conclusion",
            "",
            "- The current block timing calculation workflow is not valid on the updated zhang22 source, because the timing instrumentation step cannot compile successfully.",
            "- Therefore, current block timing values cannot yet be treated as trustworthy scheduling inputs for this source version.",
        ]
        (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(str(OUT_DIR))
        return 0

    timing = read_json(TIMING_JSON)["weights"]
    segments = read_json(SEGMENTS_JSON)["segments"]
    source_text = SOURCE_ORIGINAL.read_text(encoding="utf-8")
    source_lines = source_text.splitlines()
    consts = {m.group(1): float(m.group(2)) for m in re.finditer(r"#define\s+(C\d+)\s+([0-9.]+)", source_text)}
    calib = read_json(CALIBRATION_JSON)
    pts = [(float(x["weight"]), float(x["per_call_mean_s"])) for x in calib["busy_calibration"]]
    base_struct_s = float(calib["zhang22_compare"]["busy0"]["stats"]["mean_s"]) / 14.0

    rows = []
    ratios = []
    for seg in segments:
        seg_id = seg["seg_id"]
        sl = int(seg["start_line"])
        el = int(seg["end_line"])
        text = " ".join(line.strip() for line in source_lines[sl - 1 : el])
        busy_consts = re.findall(r"busy_wait_seconds\((C\d+)\)", text)
        if len(busy_consts) != 1:
            continue
        c_name = busy_consts[0]
        c_val = consts[c_name]
        pipeline_avg_ns = int(timing[seg_id]["avg_ns"])
        expected_compute_s = interp(c_val, pts)
        expected_total_ns = int(round((expected_compute_s + base_struct_s) * 1e9))
        ratio = pipeline_avg_ns / expected_total_ns if expected_total_ns > 0 else 0.0
        ratios.append(ratio)
        rows.append(
            {
                "seg_id": seg_id,
                "busy_const": c_name,
                "busy_weight": c_val,
                "pipeline_avg_ns": pipeline_avg_ns,
                "expected_compute_ns": int(round(expected_compute_s * 1e9)),
                "expected_total_ns": expected_total_ns,
                "pipeline_vs_expected_ratio": ratio,
            }
        )

    with (OUT_DIR / "validation.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    summary = {
        "rows": rows,
        "ratio_mean": statistics.mean(ratios),
        "ratio_median": statistics.median(ratios),
        "ratio_min": min(ratios),
        "ratio_max": max(ratios),
    }
    (OUT_DIR / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# zhang22 Block Timing Validation",
        "",
        "- current pipeline timing output was compared against calibrated busy cost per block.",
        f"- ratio_mean: {summary['ratio_mean']:.6f}",
        f"- ratio_median: {summary['ratio_median']:.6f}",
        f"- ratio_min: {summary['ratio_min']:.6f}",
        f"- ratio_max: {summary['ratio_max']:.6f}",
        "",
        "| seg_id | Cx | pipeline_avg_ns | expected_total_ns | ratio |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows:
        lines.append(
            f"| {row['seg_id']} | {row['busy_const']}={row['busy_weight']} | {row['pipeline_avg_ns']} | {row['expected_total_ns']} | {row['pipeline_vs_expected_ratio']:.6f} |"
        )
    (OUT_DIR / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(str(OUT_DIR))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
