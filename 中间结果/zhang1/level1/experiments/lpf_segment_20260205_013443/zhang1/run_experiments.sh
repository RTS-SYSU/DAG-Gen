#!/usr/bin/env bash
# Auto-generated runner: compile & run baseline/prio in this experiment, log runtimes.
# Usage:
#   sudo bash run_experiments.sh
#   sudo WORK_SCALE=50000 bash run_experiments.sh
#   sudo REPEATS=10 bash run_experiments.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$ROOT_DIR"
BASE_PROJ="$PROJECT_DIR/baseline/project/zhang1"
PRIO_PROJ="$PROJECT_DIR/prio/project/zhang1"

if [[ ! -d "$BASE_PROJ" || ! -d "$PRIO_PROJ" ]]; then
  echo "Missing baseline/prio under $PROJECT_DIR" >&2
  exit 1
fi

BIN_DIR="$PROJECT_DIR/bin"
OUT_DIR="$PROJECT_DIR/experiment"
mkdir -p "$BIN_DIR" "$OUT_DIR"

# Editable defaults (can also be overridden via env WORK_SCALE / REPEATS)
WORK_SCALE_DEFAULT=25000
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
