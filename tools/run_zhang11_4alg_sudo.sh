#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

WORK_SCALE="${WORK_SCALE:-100}"
REPEATS="${REPEATS:-20}"
CORES_PER_TASK="${CORES_PER_TASK:-2}"
USE_SUDO="${USE_SUDO:-auto}" # auto|true|false
TIMING_REPEATS="${TIMING_REPEATS:-10}"

SOURCE_C="$ROOT_DIR/源文件/zhang11/zhang11.c"
RTL_FILE="$ROOT_DIR/配置文件/zhang11/zhang11.c.245r.expand"
BASE_NAME="zhang11"
RULE="effective_line_merge"
ALGOS=(LPF FIFO heft zhao2020)

if [[ "$USE_SUDO" == "auto" ]]; then
  if sudo -n true >/dev/null 2>&1; then
    USE_SUDO="true"
  else
    USE_SUDO="false"
  fi
fi

MODE_SUFFIX="nosudo"
if [[ "$USE_SUDO" == "true" ]]; then
  MODE_SUFFIX="sudo"
fi

echo "[zhang11] mode=$MODE_SUFFIX work_scale=$WORK_SCALE repeats=$REPEATS cores=$CORES_PER_TASK"

PYTHONPATH=.. python3 -m mycallyplus_v1 generate \
  --source-file "$SOURCE_C" \
  --output-base "$ROOT_DIR" \
  --export-txt "$ROOT_DIR/中间结果/$BASE_NAME/配置文件/circle.txt" \
  "$RTL_FILE" > "$ROOT_DIR/中间结果/$BASE_NAME/生成dag图/dag.dot"

if command -v dot >/dev/null 2>&1; then
  dot -Tpng "$ROOT_DIR/中间结果/$BASE_NAME/生成dag图/dag.dot" \
    -o "$ROOT_DIR/中间结果/$BASE_NAME/生成dag图/dag.png" || true
fi

PYTHONPATH=.. python3 -m mycallyplus_v1 pipeline collect --base-name "$BASE_NAME" --source "$SOURCE_C" >/dev/null
PYTHONPATH=.. python3 -m mycallyplus_v1 pipeline blocks --base-name "$BASE_NAME" --level level2 --rule "$RULE" --source "$SOURCE_C" >/dev/null
PYTHONPATH=.. python3 -m mycallyplus_v1 pipeline timing --base-name "$BASE_NAME" --level level2 --rule "$RULE" --repeats "$TIMING_REPEATS" >/dev/null

for algo in "${ALGOS[@]}"; do
  PYTHONPATH=.. python3 -m mycallyplus_v1 pipeline schedule --base-name "$BASE_NAME" --level level2 --rule "$RULE" --algo "$algo" >/dev/null
  PYTHONPATH=.. python3 -m mycallyplus_v1 pipeline instrument --base-name "$BASE_NAME" --level level2 --rule "$RULE" --algo "$algo" >/dev/null

  cfg="/tmp/zhang11_${algo}_${MODE_SUFFIX}_ws${WORK_SCALE}_r${REPEATS}.json"
  cat > "$cfg" <<JSON
{
  "tasks": [
    {
      "source_c": "$ROOT_DIR/intermediate_results/$BASE_NAME/pipeline/instrument/level2/$RULE/timing/$algo/$algo.c",
      "algo_name": "$algo",
      "work_scale": $WORK_SCALE,
      "repeats": $REPEATS,
      "cores_per_task": $CORES_PER_TASK,
      "use_sudo": $USE_SUDO
    }
  ],
  "queue_mode": true
}
JSON
  python3 tools/runtime_compare/main.py --cli --config "$cfg" --wait
done

python3 - <<'PY'
import glob, json, os
for algo in ["LPF", "FIFO", "heft", "zhao2020"]:
    roots = sorted(glob.glob(f"tools/runtime_compare/实验结果/zhang11_{algo}_*"))
    if not roots:
        print(algo, "NO_RESULT_ROOT")
        continue
    latest_root = roots[-1]
    runs = sorted(glob.glob(os.path.join(latest_root, "*")))
    if not runs:
        print(algo, "NO_RUN")
        continue
    d = runs[-1]
    s = json.load(open(os.path.join(d, "summary.json"), "r", encoding="utf-8"))
    b = s["baseline"]["stats"]["mean_s"]
    p = s["prio"]["stats"]["mean_s"]
    imp = (b - p) / b * 100 if b else 0.0
    print(f"{algo}: baseline={b:.6f}s prio={p:.6f}s improvement={imp:.4f}% dir={d}")
PY
