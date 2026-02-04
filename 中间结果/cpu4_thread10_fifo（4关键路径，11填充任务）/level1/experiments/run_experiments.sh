#!/usr/bin/env bash
# 自动选取最新的 Level-1 实验（lpf_segment_*），编译并运行 baseline/prio 副本，输出对比结果。
# 用法示例：
#   sudo bash run_experiments.sh
#   sudo WORK_SCALE=50000 EXP_NAME=lpf_segment_20260126_003151 bash run_experiments.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 允许通过环境变量指定实验目录名；未指定则选最新 lpf_segment_* 目录
EXP_NAME="${EXP_NAME:-}"
if [[ -z "$EXP_NAME" ]]; then
  EXP_NAME="$(ls -1dt "$ROOT_DIR"/lpf_segment_* 2>/dev/null | head -n1 | xargs -n1 basename)"
fi
if [[ -z "$EXP_NAME" || ! -d "$ROOT_DIR/$EXP_NAME" ]]; then
  echo "No experiment directory found. Set EXP_NAME or ensure lpf_segment_* exists." >&2
  exit 1
fi

EXP_DIR="$ROOT_DIR/$EXP_NAME"
PROJECT_DIR="$EXP_DIR"/cpu4_thread10_fifo
BASE_PROJ="$PROJECT_DIR/baseline/project/cpu4_thread10_fifo"
PRIO_PROJ="$PROJECT_DIR/prio/project/cpu4_thread10_fifo"

if [[ ! -d "$BASE_PROJ" || ! -d "$PRIO_PROJ" ]]; then
  echo "Missing baseline/prio project directories under $PROJECT_DIR" >&2
  exit 1
fi

BIN_DIR="$PROJECT_DIR/bin"
OUT_DIR="$PROJECT_DIR/experiment"
mkdir -p "$BIN_DIR" "$OUT_DIR"

# 工作量参数：未指定 WORK_SCALE 时使用源代码默认 25000
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
  # 编译目录内全部 .c
  local sources=()
  while IFS= read -r -d '' f; do
    # 跳过 wrap_main/prog_timer（优先级实验副本可能包含）
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

echo "Selected experiment: $EXP_NAME"
echo "Compiling with WORK_SCALE=${WS_VALUE} ..."
compile_proj "$BASE_PROJ" "$BIN_DIR/app_baseline"
compile_proj "$PRIO_PROJ" "$BIN_DIR/app_prio"

echo "Running baseline/prio ..."
{
  echo "=== RUN at $TS (WORK_SCALE=${WS_VALUE}) ==="
  echo "[baseline]"
  "$BIN_DIR/app_baseline"
  echo
  echo "[prio]"
  "$BIN_DIR/app_prio"
} > "$OUT_FILE"

echo "Done. Results saved to $OUT_FILE"
