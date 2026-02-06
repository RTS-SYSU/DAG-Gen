from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Tuple


def _load_schedule(path: Path) -> Dict[str, int]:
    data = json.loads(path.read_text(encoding="utf-8"))
    prios = data.get("priorities", {})
    if not isinstance(prios, dict):
        raise ValueError("schedule_thread.json: priorities must be dict")
    return {str(k): int(v) for k, v in prios.items()}


def _feature_insert_at(lines: List[str]) -> int:
    feature_def_re = re.compile(r"^\s*#\s*define\s+_(GNU|DEFAULT|POSIX|XOPEN|BSD|SVID)_SOURCE\b")
    insert_at = 0
    for i, ln in enumerate(lines):
        if feature_def_re.match(ln):
            insert_at = i + 1
            continue
        break
    return insert_at


def instrument_prio_program_timing_and_segment_priorities(
    source_c: Path,
    *,
    segments_json: Path,
    priorities: Dict[str, int],
    out_c: Path,
) -> List[str]:
    warnings: List[str] = []
    lines0 = source_c.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    insert_at = _feature_insert_at(lines0)
    lines = lines0[:insert_at] + ['#include "prio_runtime.h"\n'] + lines0[insert_at:]

    seg_data = json.loads(segments_json.read_text(encoding="utf-8"))
    segments = seg_data.get("segments", [])

    # include insertion shift by +1 after feature-test macros
    include_shift = 1

    # line_no -> chosen priority (deduplicated)
    inserts_prio: Dict[int, int] = {}

    for seg in segments:
        if not isinstance(seg, dict):
            continue
        seg_id = seg.get("seg_id")
        kind = seg.get("kind")
        start_line = seg.get("start_line")
        if not isinstance(seg_id, str) or kind != "compute" or not isinstance(start_line, int):
            continue
        prio = priorities.get(seg_id)
        if prio is None:
            continue
        ins_line = start_line + include_shift
        prev = inserts_prio.get(ins_line)
        if prev is None or prio > prev:
            inserts_prio[ins_line] = prio

    out: List[str] = []
    for i in range(1, len(lines) + 1):
        prio = inserts_prio.get(i)
        if prio is not None:
            indent = re.match(r"[ \t]*", lines[i - 1]).group(0)  # type: ignore[union-attr]
            out.append(f"{indent}l1_set_thread_prio_fifo({prio});\n")
        out.append(lines[i - 1])
    out_c.write_text("".join(out), encoding="utf-8")
    return warnings


def _write_experiment_runner(
    *,
    exp_dir: Path,
    project_name: str,
    work_scale_default: int = 25000,
) -> None:
    """Emit a helper script inside the experiment dir to run baseline/prio repeatedly and log runtimes."""
    script_path = exp_dir / "run_experiments.sh"
    # NOTE: Do NOT use Python f-string for this template, because the script embeds
    # Python code that itself uses `{...}` formatting and would be accidentally
    # interpolated by the outer f-string.
    content = """#!/usr/bin/env bash
# Auto-generated runner: compile & run baseline/prio in this experiment, log runtimes.
# Usage:
#   sudo bash __SCRIPT_NAME__
#   sudo WORK_SCALE=50000 bash __SCRIPT_NAME__
#   sudo REPEATS=10 bash __SCRIPT_NAME__

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$ROOT_DIR"
BASE_PROJ="$PROJECT_DIR/baseline/project/__PROJECT_NAME__"
PRIO_PROJ="$PROJECT_DIR/prio/project/__PROJECT_NAME__"

if [[ ! -d "$BASE_PROJ" || ! -d "$PRIO_PROJ" ]]; then
  echo "Missing baseline/prio under $PROJECT_DIR" >&2
  exit 1
fi

BIN_DIR="$PROJECT_DIR/bin"
OUT_DIR="$PROJECT_DIR/experiment"
mkdir -p "$BIN_DIR" "$OUT_DIR"

# Editable defaults (can also be overridden via env WORK_SCALE / REPEATS)
	WORK_SCALE_DEFAULT=__WORK_SCALE_DEFAULT__
	REPEATS_DEFAULT=1
	
	WS_VALUE="${WORK_SCALE:-$WORK_SCALE_DEFAULT}"
	REPEATS="${REPEATS:-$REPEATS_DEFAULT}"
	if ! [[ "$REPEATS" =~ ^[0-9]+$ ]] || [[ "$REPEATS" -lt 1 ]]; then
	  echo "Invalid REPEATS=$REPEATS (must be integer >= 1)" >&2
	  exit 1
	fi
	
	TS="$(date -Iseconds)"
	TS_SAFE="${TS//:/-}"
	WS_LABEL="${WS_VALUE:-default}"
	WS_SAFE="${WS_LABEL//[^A-Za-z0-9._-]/_}"
	base_name="run_results_${TS_SAFE}_ws${WS_SAFE}_r${REPEATS}"
	OUT_FILE="$OUT_DIR/${base_name}.txt"
	idx=1
	while [[ -e "$OUT_FILE" ]]; do
	  OUT_FILE="$OUT_DIR/${base_name}_${idx}.txt"
	  idx=$((idx+1))
	done
	
	compile_proj() {
	  local src_dir="$1"
	  local bin_path="$2"
	  local sources=()
	  while IFS= read -r -d '' f; do
	    case "$(basename "$f")" in
	      wrap_main.c|prog_timer.c) continue ;;
	    esac
	    sources+=("$f")
	  done < <(find "$src_dir" -maxdepth 1 -name '*.c' -print0)
	  if [[ "${#sources[@]}" -eq 0 ]]; then
	    echo "No .c files in $src_dir" >&2
	    return 1
	  fi
	  gcc -O2 -g -std=c11 -DWORK_SCALE="$WS_VALUE" -pthread "${sources[@]}" -o "$bin_path" -lm
	}
	
	tmp_dir="$(mktemp -d "/tmp/${base_name}_XXXX")"
	cleanup() { rm -rf "$tmp_dir"; }
	trap cleanup EXIT
	
	run_once() {
	  local label="$1"
	  local iter="$2"
	  local bin="$3"
	  local log_file="$tmp_dir/${label}_${iter}.log"
	  local start end dur rc
	  start=$(date +%s%N)
	  set +e
	  "$bin" >"$log_file" 2>&1
	  rc=$?
	  set -e
	  end=$(date +%s%N)
	  dur=$((end - start))
	  printf "%s" "$dur" >"$tmp_dir/${label}_${iter}.ns"
	  printf "%s" "$rc" >"$tmp_dir/${label}_${iter}.rc"
	}
	
	emit_summary() {
	  python3 - <<'PY'
	import os, statistics
	tmp_dir = os.environ["TMP_DIR"]
	repeats = int(os.environ["REPEATS"])
	def load(label):
	    ns=[]
	    rcs=[]
	    for i in range(1, repeats+1):
	        with open(os.path.join(tmp_dir, f"{label}_{i}.ns"), "r") as f:
	            ns.append(int(f.read().strip()))
	        with open(os.path.join(tmp_dir, f"{label}_{i}.rc"), "r") as f:
	            rcs.append(int(f.read().strip()))
	    return ns, rcs
	def stats(ns):
	    s=[x/1e9 for x in ns]
    return {
        "min_s": min(s),
        "max_s": max(s),
        "mean_s": statistics.mean(s),
        "times_s": s,
    }
base_ns, base_rc = load("baseline")
prio_ns, prio_rc = load("prio")
base = stats(base_ns)
prio = stats(prio_ns)
print("=== SUMMARY (wall-time measured by script) ===")
print(f"baseline: mean={base['mean_s']:.6f}s min={base['min_s']:.6f}s max={base['max_s']:.6f}s rcs={base_rc}")
print(f"prio:     mean={prio['mean_s']:.6f}s min={prio['min_s']:.6f}s max={prio['max_s']:.6f}s rcs={prio_rc}")
print(f"baseline_times_s: {[round(x, 9) for x in base['times_s']]}")
print(f"prio_times_s:     {[round(x, 9) for x in prio['times_s']]}")
if base['mean_s'] > 1e-12:
    improve = (base['mean_s'] - prio['mean_s']) / base['mean_s']
    print(f"improvement_ratio (baseline->prio): {improve:.4f}")
else:
    print("improvement_ratio (baseline->prio): n/a (baseline too small)")
	PY
	}
	
	emit_details() {
	  echo
	  echo "=== DETAILS (per-run full output) ==="
	  for i in $(seq 1 "$REPEATS"); do
	    ns="$(cat "$tmp_dir/baseline_${i}.ns")"
	    rc="$(cat "$tmp_dir/baseline_${i}.rc")"
	    wall_s="$(python3 - <<PY
	ns=int("$ns")
	print(f"{ns/1e9:.6f}")
	PY
	)"
	    echo
	    echo "----- [baseline] run #$i (wall=${wall_s}s, rc=${rc}) -----"
	    cat "$tmp_dir/baseline_${i}.log"
	  done
	  for i in $(seq 1 "$REPEATS"); do
	    ns="$(cat "$tmp_dir/prio_${i}.ns")"
	    rc="$(cat "$tmp_dir/prio_${i}.rc")"
	    wall_s="$(python3 - <<PY
	ns=int("$ns")
	print(f"{ns/1e9:.6f}")
	PY
	)"
	    echo
	    echo "----- [prio] run #$i (wall=${wall_s}s, rc=${rc}) -----"
	    cat "$tmp_dir/prio_${i}.log"
	  done
	}
	
	echo "Running experiment at $ROOT_DIR (WORK_SCALE=${WS_VALUE}, REPEATS=${REPEATS})"
	compile_proj "$BASE_PROJ" "$BIN_DIR/app_baseline"
	compile_proj "$PRIO_PROJ" "$BIN_DIR/app_prio"

for i in $(seq 1 "$REPEATS"); do
  run_once "baseline" "$i" "$BIN_DIR/app_baseline"
  run_once "prio" "$i" "$BIN_DIR/app_prio"
done

	{
	  echo "=== RUN at $TS (WORK_SCALE=${WS_VALUE}, REPEATS=${REPEATS}) ==="
	  echo "BASE_PROJ=$BASE_PROJ"
	  echo "PRIO_PROJ=$PRIO_PROJ"
  echo "baseline_bin=$BIN_DIR/app_baseline"
  echo "prio_bin=$BIN_DIR/app_prio"
  echo
  export TMP_DIR="$tmp_dir"
  export REPEATS
	  emit_summary
	  emit_details
	} > "$OUT_FILE"

echo "Done. Results saved to $OUT_FILE"
"""
    content = textwrap.dedent(content).lstrip()
    # Some template lines may start with literal TABs; strip them so bash heredocs terminate correctly.
    content = "\n".join(ln.lstrip("\t") for ln in content.splitlines()) + "\n"
    content = (
        content.replace("__SCRIPT_NAME__", script_path.name)
        .replace("__PROJECT_NAME__", str(project_name))
        .replace("__WORK_SCALE_DEFAULT__", str(int(work_scale_default)))
    )
    script_path.write_text(content, encoding="utf-8")
    script_path.chmod(script_path.stat().st_mode | 0o111)


def _compile(src_dir: Path) -> Path:
    sources = sorted(str(p) for p in src_dir.rglob("*.c"))
    cmd = [
        "gcc",
        "-O2",
        "-std=c11",
        "-pthread",
        "-I.",
        "-o",
        "app",
        *sources,
        "-Wl,--wrap=main",
        "-lm",
        "-ldl",
    ]
    proc = subprocess.run(cmd, cwd=str(src_dir), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-500:])
    return src_dir / "app"


def _run_once(app: Path) -> Tuple[Optional[int], str, str]:
    proc = subprocess.run([str(app)], cwd=str(app.parent), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr[-500:])
    stderr = proc.stderr or ""
    # Parse PROGRAM_TOTAL_NS from stderr
    total_ns = None
    for ln in stderr.splitlines():
        if ln.startswith("PROGRAM_TOTAL_NS="):
            try:
                total_ns = int(ln.split("=", 1)[1].strip())
            except Exception:
                total_ns = None
    return total_ns, proc.stdout or "", stderr


def main() -> int:
    ap = argparse.ArgumentParser(description="Instrument thread priorities (LPF) and compare runtime once.")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"))
    ap.add_argument("--base-name", required=True)
    ap.add_argument("--source", required=True, type=Path, help="Baseline fifo.c source")
    ap.add_argument("--project-name", default=None, help="Output project name under 时间分析_level1_prio/")
    ap.add_argument("--schedule", type=Path, default=None, help="schedule_thread.json path (default derived from base)")
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name
    source_c = args.source.resolve()
    project_name = args.project_name or source_c.stem

    schedule_path = args.schedule or (base_dir / "中间结果" / base_name / "level1" / "schedule" / "lpf_segment" / "schedule_seg.json")
    priorities = _load_schedule(schedule_path)

    segments_json = base_dir / "中间结果" / base_name / "level1" / "stage1" / "segments_stage1.json"

    ts = time.strftime("%Y%m%d_%H%M%S")
    out_root = base_dir / "中间结果" / base_name / "level1" / "experiments" / f"lpf_segment_{ts}" / project_name
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # Baseline build
    src_root = source_c.parent
    base_proj = out_root / "baseline" / "project" / src_root.name
    prio_proj = out_root / "prio" / "project" / src_root.name
    shutil.copytree(src_root, base_proj)
    shutil.copytree(src_root, prio_proj)

    # Inject runtime for program timing
    (base_proj / "prog_timer.h").write_text((base_dir / "level1" / "prog_timer.h").read_text(encoding="utf-8"), encoding="utf-8")
    (base_proj / "prog_timer.c").write_text((base_dir / "level1" / "prog_timer.c").read_text(encoding="utf-8"), encoding="utf-8")
    (base_proj / "wrap_main.c").write_text((base_dir / "level1" / "wrap_main.c").read_text(encoding="utf-8"), encoding="utf-8")
    (prio_proj / "prog_timer.h").write_text((base_dir / "level1" / "prog_timer.h").read_text(encoding="utf-8"), encoding="utf-8")
    (prio_proj / "prog_timer.c").write_text((base_dir / "level1" / "prog_timer.c").read_text(encoding="utf-8"), encoding="utf-8")
    (prio_proj / "wrap_main.c").write_text((base_dir / "level1" / "wrap_main.c").read_text(encoding="utf-8"), encoding="utf-8")

    # Inject prio runtime header
    (prio_proj / "prio_runtime.h").write_text((base_dir / "level1" / "prio_runtime.h").read_text(encoding="utf-8"), encoding="utf-8")

    # Baseline: keep source identical (measure total time via wrap_main.c)
    warn_base: List[str] = []

    # Prio: rename主源文件以区分，且只在该副本中加优先级切换（wrap_main.c 处理总时间）
    prio_src_orig = prio_proj / source_c.name
    prio_src_new = prio_proj / f"{source_c.stem}_prio{source_c.suffix}"
    if prio_src_orig.exists():
        prio_src_orig.rename(prio_src_new)
    prio_c = prio_src_new if prio_src_new.exists() else prio_src_orig
    warn_prio = instrument_prio_program_timing_and_segment_priorities(
        prio_c, segments_json=segments_json, priorities=priorities, out_c=prio_c
    )
    warnings = warn_base + warn_prio

    app_base = _compile(base_proj)
    app_prio = _compile(prio_proj)
    ns_base, out_base, err_base = _run_once(app_base)
    ns_prio, out_prio, err_prio = _run_once(app_prio)
    prio_failed = "L1_PRIO_SET_FAILED" in err_prio

    report = {
        "base_name": base_name,
        "baseline_total_ns": ns_base,
        "prio_total_ns": ns_prio,
        "delta_total_ns": (ns_prio - ns_base) if (ns_prio is not None and ns_base is not None) else None,
        "schedule": str(schedule_path),
        "prio_set_failed": prio_failed,
        "warnings": warnings,
        "baseline_stderr_tail": err_base[-500:],
        "prio_stderr_tail": err_prio[-500:],
    }
    report_path = out_root / "compare.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {report_path}")

    # Emit helper runner script under level1/experiments/
    _write_experiment_runner(
        exp_dir=out_root,
        project_name=src_root.name,
        work_scale_default=25000,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
