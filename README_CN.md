# ScratchDAG（原 mycallyplus_v1）

ScratchDAG 是一套调用图生成、可视化、时间分析与调度实验工具，支持 GUI/CLI，输出 DOT/PNG/JSON，便于对比调试。

## 核心功能
- 调用图：解析 `.expand`/源文件，生成线程/完整 DOT/PNG，导出 circle.txt。
- 可视化：原始图、线程图、条件节点、互斥/信号量、Tarjan、线程分组。
- 时间分析：用 `mycalls_meta_internal.json` 自动插桩 `.c`，编译运行，输出 `time_result.json`、`thread_trace.json`、`metrics.json`。
- 调度实验：最长路径、CPC 优先级分配，CPC 优先级插桩与指标对比。
- DOT 过滤：节点名去噪。

## 快速开始
1. 安装依赖：`pip install -r requirements.txt`（Python 3.8+，需 gcc、graphviz `dot`）  
2. 启动 GUI：`PYTHONPATH=. python3 -m mycallyplus_v1`  
3. CLI 示例：  
   - 线程 DAG：`PYTHONPATH=. python3 -m mycallyplus_v1.generation.legacy --threads-only --output-base mycallyplus_v1 path/to/file.expand`  
   - 时间分析：`PYTHONPATH=. python3 -m mycallyplus_v1.time_analysis --source src.c --meta mycalls_meta_internal.json`

## GUI 流程速览
- 选择源/expand/dot/配置；生成 DAG/条件节点/源码调用图。
- 互斥锁/信号量视图（需 circle.txt）。
- 时间分析：源 + meta → 拷贝、插桩、编译、运行 → 结果存于 `中间结果/<base>/时间分析/<project>/`。
- 调度算法：
  - 最长路径：`dag.dot` + `time_result.json` → `调度算法/longest_path/`
  - CPC 分析：`dag.dot` + `time_result.json` + `longest_path.json` → `调度算法/cpc/`
  - CPC 优先级插桩：源 + meta + CPC `schedule.json` → `时间分析_cpc/<project>/`，并复制到 `调度算法/cpc分析结果/`
  - 指标对比：两份 metrics JSON → 对比图输出到 `调度算法/compare/<timestamp>/`
- 过滤 DOT：输出 `_filt.dot/png`（`中间结果/过滤dot/`）。

## 目录与输出
- `中间结果/<base>/配置文件/`：`<base>_threads.dot`、`<base>_full.dot`、circle.txt、expand/src 备份
- `中间结果/<base>/生成dag图/`：`dag.dot/png`，debug（`mycalls_meta_internal.json` 等）
- `中间结果/<base>/时间分析/<project>/`：插桩源码、`time_result.json`、`thread_trace.json`、`metrics.json`、`dag_weighted.dot`
- `中间结果/<base>/时间分析_cpc/<project>/`：CPC 运行；`time_result_prio.json`、`metrics_prio.json`、`dag_weighted_prio.dot`、可选 `sched_diag.json`
- `中间结果/<base>/调度算法/<strategy>/`：如 `longest_path/`、`cpc/`、`cpc分析结果/`、`compare/<timestamp>/`

## 调度提示
- 优先级来源：`schedule.json.priorities`。插桩时每线程前缀首个调用点设置一次 `ta_set_priority(SCHED_FIFO)`，其余只计时。无 root/CAP_SYS_NICE 可能被 EPERM 拒绝。
- DOT 输出含耗时/优先级标签；JSON/TXT 记录调度结果。

## 常见问题
- 优先级无效/时间变长：多为 EPERM 或设置位置/频率不当。需 root/CAP_SYS_NICE，或改到线程入口。
- `time_result.json` 为空：查 `time_analysis.log`，确认插桩目标为 `.c` 且存在。
- DOT 渲染失败：安装 Graphviz，检查 `dot -V`。

## 关键模块
`generation/legacy.py`、`scheduler.py`、`time_analysis.py`、`time_charts.py`、`ui/gui.py`、`visualization/viewer.py`、`filter_dot.py`。
