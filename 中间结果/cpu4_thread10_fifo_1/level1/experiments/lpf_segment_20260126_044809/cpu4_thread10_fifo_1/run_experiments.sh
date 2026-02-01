#!/usr/bin/env bash
# Auto-generated runner: compile & run baseline/prio in this experiment, log runtimes.
# Usage:
#   sudo bash run_experiments.sh
#   sudo WORK_SCALE=50000 bash run_experiments.sh
#   sudo REPEATS=10 bash run_experiments.sh
#
# Output:
#   experiment/run_results_<timestamp>_ws<workscale>_r<repeats>[_N].txt
# The output file is never overwritten (suffix _N is appended on collision).

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$ROOT_DIR"
BASE_PROJ="$PROJECT_DIR/baseline/project/cpu4_thread10_fifo_1"
PRIO_PROJ="$PROJECT_DIR/prio/project/cpu4_thread10_fifo_1"

if [[ ! -d "$BASE_PROJ" || ! -d "$PRIO_PROJ" ]]; then
  echo "Missing baseline/prio under $PROJECT_DIR" >&2
  exit 1
fi

BIN_DIR="$PROJECT_DIR/bin"
OUT_DIR_DEFAULT="$PROJECT_DIR/experiment"

# Editable defaults (can also be overridden via env WORK_SCALE / REPEATS)
WORK_SCALE_DEFAULT=100
REPEATS_DEFAULT=5

WS_VALUE="${WORK_SCALE:-$WORK_SCALE_DEFAULT}"
REPEATS="${REPEATS:-$REPEATS_DEFAULT}"
if ! [[ "$REPEATS" =~ ^[0-9]+$ ]] || [[ "$REPEATS" -lt 1 ]]; then
  echo "Invalid REPEATS=$REPEATS (must be integer >= 1)" >&2
  exit 1
fi

TS="$(date -Iseconds)"
TS_SAFE="${TS//:/-}"
WS_SAFE="${WS_VALUE//[^A-Za-z0-9._-]/_}"
base_name="run_results_${TS_SAFE}_ws${WS_SAFE}_r${REPEATS}"
OUT_FILE_PLACEHOLDER="${base_name}.txt"

compile_proj() {
  local src_dir="$1"
  local bin_path="$2"
  local sources=()
  while IFS= read -r -d '' f; do
    sources+=("$f")
  done < <(find "$src_dir" -maxdepth 1 -name '*.c' -print0)
  if [[ "${#sources[@]}" -eq 0 ]]; then
    echo "No .c files in $src_dir" >&2
    return 1
  fi
  gcc -O2 -g -std=c11 -DWORK_SCALE="$WS_VALUE" -pthread \
    -Wl,--wrap=main \
    "${sources[@]}" -o "$bin_path" -lm
}

tmp_dir="$(mktemp -d "/tmp/${base_name}_XXXX")"
cleanup() { rm -rf "$tmp_dir"; }
trap cleanup EXIT
BIN_DIR="$tmp_dir/bin"
mkdir -p "$BIN_DIR"
if mkdir -p "$OUT_DIR_DEFAULT" 2>/dev/null; then
  OUT_DIR="$OUT_DIR_DEFAULT"
else
  OUT_DIR="$HOME/run_results_cpu4_thread10_fifo_1"
  mkdir -p "$OUT_DIR"
  echo "WARNING: cannot write to $OUT_DIR_DEFAULT, using $OUT_DIR instead" >&2
fi
# verify writable; fallback to tmp if not
if ! (echo test >"$OUT_DIR/.writetest" 2>/dev/null); then
  OUT_DIR="$HOME/run_results_cpu4_thread10_fifo_1"
  mkdir -p "$OUT_DIR"
  echo "WARNING: cannot write to $OUT_DIR_DEFAULT, using $OUT_DIR instead" >&2
else
  rm -f "$OUT_DIR/.writetest"
fi
OUT_FILE="$OUT_DIR/${OUT_FILE_PLACEHOLDER}"
idx=1
while [[ -e "$OUT_FILE" ]]; do
  OUT_FILE="$OUT_DIR/${base_name}_${idx}.txt"
  idx=$((idx+1))
done
if mkdir -p "$OUT_DIR_DEFAULT" 2>/dev/null; then
  OUT_DIR="$OUT_DIR_DEFAULT"
else
  OUT_DIR="$tmp_dir/experiment"
  mkdir -p "$OUT_DIR"
  echo "WARNING: cannot write to $OUT_DIR_DEFAULT, using $OUT_DIR instead" >&2
fi

run_once() {
  local label="$1"
  local iter="$2"
  local bin="$3"
  local log_file="$tmp_dir/${label}_${iter}.log"
  local rc prog_ns
  set +e
  "$bin" >"$log_file" 2>&1
  rc=$?
  set -e
  prog_ns="$(python3 - <<PY
import re, sys, pathlib
txt = pathlib.Path("$log_file").read_text(errors="ignore")
matches = re.findall(r"PROGRAM_TOTAL_NS=(\\d+)", txt)
if matches:
    print(matches[-1])
    sys.exit(0)
print("ERROR: missing PROGRAM_TOTAL_NS in $log_file", file=sys.stderr)
sys.exit(1)
PY
)" || prog_ns="-1"
  printf "%s" "$prog_ns" >"$tmp_dir/${label}_${iter}.prog_ns"
  printf "%s" "$rc" >"$tmp_dir/${label}_${iter}.rc"
}

emit_summary() {
  python3 - <<'PY'
import os, statistics
tmp_dir = os.environ["TMP_DIR"]
repeats = int(os.environ["REPEATS"])
def load(label):
    prog=[]
    rcs=[]
    for i in range(1, repeats+1):
        with open(os.path.join(tmp_dir, f"{label}_{i}.prog_ns"), "r") as f:
            prog.append(int(f.read().strip()))
        with open(os.path.join(tmp_dir, f"{label}_{i}.rc"), "r") as f:
            rcs.append(int(f.read().strip()))
    return prog, rcs
def stats(ns):
    s=[x/1e9 for x in ns]
    return {
        "min_s": min(s),
        "max_s": max(s),
        "mean_s": statistics.mean(s),
        "times_s": s,
    }
base_prog, base_rc = load("baseline")
prio_prog, prio_rc = load("prio")
base = stats(base_prog)
prio = stats(prio_prog)
print("=== PAIRED RESULTS (program-reported time, seconds) ===")
print("run\tbaseline\tprio\tdelta(prio-baseline)")
for i in range(repeats):
    b = base["times_s"][i]
    p = prio["times_s"][i]
    print(f"{i+1}\t{b:.6f}\t{p:.6f}\t{(p-b):+.6f}")
print()
print("=== BASELINE STATS (program time) ===")
print(f"times_s={ [round(x,6) for x in base['times_s']] }")
print(f"mean={base['mean_s']:.6f}s min={base['min_s']:.6f}s max={base['max_s']:.6f}s rcs={base_rc}")
print()
print("=== PRIO STATS (program time) ===")
print(f"times_s={ [round(x,6) for x in prio['times_s']] }")
print(f"mean={prio['mean_s']:.6f}s min={prio['min_s']:.6f}s max={prio['max_s']:.6f}s rcs={prio_rc}")
if base['mean_s'] > 1e-12:
    improve = (base['mean_s'] - prio['mean_s']) / base['mean_s']
    print(f"\nrelative_delta (baseline->prio) = {improve:.4f}")
else:
    print("\nrelative_delta (baseline->prio) = n/a (baseline too small)")
PY
}

emit_details() {
  echo
  echo "=== LOGS (raw program output) ==="
  for i in $(seq 1 "$REPEATS"); do
    ns="$(cat "$tmp_dir/baseline_${i}.prog_ns")"
    rc="$(cat "$tmp_dir/baseline_${i}.rc")"
    prog_s="$(python3 - <<PY
ns=int("$ns")
print(f"{ns/1e9:.6f}")
PY
)"
    echo
    echo "----- [baseline] run #$i (program=${prog_s}s, rc=${rc}) -----"
    cat "$tmp_dir/baseline_${i}.log"
  done
  for i in $(seq 1 "$REPEATS"); do
    ns="$(cat "$tmp_dir/prio_${i}.prog_ns")"
    rc="$(cat "$tmp_dir/prio_${i}.rc")"
    prog_s="$(python3 - <<PY
ns=int("$ns")
print(f"{ns/1e9:.6f}")
PY
)"
    echo
    echo "----- [prio] run #$i (program=${prog_s}s, rc=${rc}) -----"
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

if grep -qE "rc=([1-9][0-9]*)" "$OUT_FILE"; then
  echo "WARNING: some runs returned non-zero rc; see $OUT_FILE" >&2
fi

echo "Done. Results saved to $OUT_FILE"
