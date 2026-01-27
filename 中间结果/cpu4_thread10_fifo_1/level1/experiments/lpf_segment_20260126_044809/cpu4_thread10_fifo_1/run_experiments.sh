#!/usr/bin/env bash
# Auto-generated runner: compile & run baseline/prio in this experiment, log runtimes.
# Usage:
#   sudo bash run_experiments.sh
#   sudo WORK_SCALE=50000 bash run_experiments.sh

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
OUT_DIR="$PROJECT_DIR/experiment"
mkdir -p "$BIN_DIR" "$OUT_DIR"

WS_DEFAULT=10000
WS_VALUE="${WORK_SCALE:-$WS_DEFAULT}"
TS="$(date -Iseconds)"
TS_SAFE="${TS//:/-}"
WS_LABEL="${WS_VALUE:-default}"
WS_SAFE="${WS_LABEL//[^A-Za-z0-9._-]/_}"
base_name="run_results_${TS_SAFE}_ws${WS_SAFE}"
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
  gcc -DWORK_SCALE="$WS_VALUE" -pthread "${sources[@]}" -o "$bin_path"
}

run_and_measure() {
  local title="$1"
  shift
  local start end dur
  start=$(date +%s%N)
  "$@"
  end=$(date +%s%N)
  dur=$((end - start))
  printf "[%s runtime] %.3f s (%d ns)\n" "$title" "$(echo "scale=3; $dur/1000000000" | bc)" "$dur"
}

echo "Running experiment at $ROOT_DIR (WORK_SCALE=${WS_VALUE})"
compile_proj "$BASE_PROJ" "$BIN_DIR/app_baseline"
compile_proj "$PRIO_PROJ" "$BIN_DIR/app_prio"

{ 
  echo "=== RUN at $TS (WORK_SCALE=${WS_VALUE}) ==="
  echo "[baseline]"
  run_and_measure "baseline" "$BIN_DIR/app_baseline"
  echo
  echo "[prio]"
  run_and_measure "prio" "$BIN_DIR/app_prio"
} > "$OUT_FILE"

echo "Done. Results saved to $OUT_FILE"
