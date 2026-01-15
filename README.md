# ScratchDAG (formerly mycallyplus_v1)

ScratchDAG is a toolkit to build and explore call graphs for C/C++ projects, run time analysis via automatic instrumentation, and experiment with scheduling strategies (longest-path, CPC). It ships with GUI and CLI, outputs DOT/PNG/JSON, and keeps artifacts organized for comparison.

## What it does
- Graphs: parse GCC RTL `.expand` or source; export thread/full DOT/PNG and circle.txt.
- Visualization: GUI/viewer for original, threads, conditions, mutex, semaphore, Tarjan, thread clusters.
- Time analysis: auto-instrument `.c` via `mycalls_meta_internal.json`, compile/run → `time_result.json`, `thread_trace.json`, `metrics.json`.
- Scheduling: longest-path, CPC priorities, CPC priority-aware instrumentation, metrics comparison.
- DOT filtering: clean symbol names for readability.

## Quick start
1. Install deps: `pip install -r requirements.txt` (Python 3.8+, gcc, graphviz `dot`).
2. Launch GUI: `PYTHONPATH=. python3 -m mycallyplus_v1`
3. CLI samples:  
   - Thread DAG: `PYTHONPATH=. python3 -m mycallyplus_v1.generation.legacy --threads-only --output-base mycallyplus_v1 path/to/file.expand`  
   - Time analysis: `PYTHONPATH=. python3 -m mycallyplus_v1.time_analysis --source path/to/src.c --meta path/to/mycalls_meta_internal.json`

## GUI flow (high level)
- Pick source / expand / dot / config.
- Generate DAG / conditions / source-only graph.
- Mutex / semaphore views (need circle.txt).
- Time analysis: source + meta → copy, instrument, build, run → `中间结果/<base>/时间分析/<project>/`.
- Scheduling:
  - Longest path: `dag.dot` + `time_result.json` → `调度算法/longest_path/`
  - CPC analysis: `dag.dot` + `time_result.json` + `longest_path.json` → `调度算法/cpc/`
  - CPC priority instrumentation: source + meta + CPC `schedule.json` → `时间分析_cpc/<project>/` + `调度算法/cpc分析结果/`
  - Metrics compare: two metrics JSON → PNGs in `调度算法/compare/<timestamp>/`
- Filter DOT: output `_filt.dot/png` under `中间结果/过滤dot/`.

## Outputs (key paths)
- `中间结果/<base>/配置文件/`: `<base>_threads.dot`, `<base>_full.dot`, circle.txt, expand/src copies
- `中间结果/<base>/生成dag图/`: `dag.dot/png`, debug (`mycalls_meta_internal.json`, etc.)
- `中间结果/<base>/时间分析/<project>/`: instrumented src, `time_result.json`, `thread_trace.json`, `metrics.json`, `dag_weighted.dot`
- `中间结果/<base>/时间分析_cpc/<project>/`: CPC run; `time_result_prio.json`, `metrics_prio.json`, `dag_weighted_prio.dot`, optional `sched_diag.json`
- `中间结果/<base>/调度算法/<strategy>/`: e.g., `longest_path/`, `cpc/`, `cpc分析结果/`, `compare/<timestamp>/`

## Scheduling notes
- CPC priorities come from `schedule.json.priorities`. Instrumentation sets priority once per thread prefix (first hit) via `ta_set_priority(SCHED_FIFO)`; without root/CAP_SYS_NICE, calls may be denied (EPERM) and only add overhead.
- Longest-path/CPC DOTs add weights/tooltips and `prio=` labels; JSON/TXT record schedules.

## Requirements
- Graphviz `dot` on PATH; gcc with `-fdump-rtl-expand` if you need expand files.
- For priority to take effect: run as root or grant `CAP_SYS_NICE` to the built app.

## Troubleshooting
- Priority has no effect / time increases: likely EPERM on `pthread_setschedparam`; check `sched_diag.json`, run with `CAP_SYS_NICE`, or move priority set to thread entry.
- `time_result.json` empty: see `time_analysis.log`, ensure `.c` files are present and instrumented.
- DOT render fails: install Graphviz and check `dot -V`.
