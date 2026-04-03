# zhang2 调度 Trace — 第二轮采集

## 方法依据

- `实验文档/约定术语.md` → **§调度 Trace 分析法**（MU 段前后时间戳、`WORK_SCALE=100`、绑核、`taskset -c 6,7`）
- 权重与拓扑：`实验文档/权值调整实验.md` → **第一轮权重调整方案**（与 `源文件/zhang2/zhang2.c` 中 C1–C15 一致）

## 环境

| 项 | 值 |
|----|-----|
| 采集时间 | 2026-04-03T14:20 前后（本目录 `run_all_traces.py` 单次执行） |
| 内核 | Linux 5.10.160 aarch64 |
| CPU 亲和 | 6, 7（2 核） |
| 编译 | `gcc -O0 -pthread -DWORK_SCALE=100` |
| SCHED_FIFO | FIFO / zhao2020 / heft / t_level / wcet_first 通过 **sudo taskset** 运行 |

## 单次 TOTAL（ms）

来自本目录 `zhang2_all_traces.json`（同一时刻的六次独立运行）。

| 算法 | TOTAL (ms) |
|------|------------|
| CFS | 684.3 |
| wcet_first | 722.7 |
| FIFO | 725.4 |
| heft | 739.1 |
| zhao2020 | 753.2 |
| t_level | 785.1 |

## 本目录文件

| 文件 | 说明 |
|------|------|
| `run_all_traces.py` | 生成 trace 源码、编译、运行、写出 json |
| `zhang2_all_traces.json` | 各算法 trace 列表 + total |
| `zhang2_六种调度策略时间线对比.md` | 基于本轮 json：ASCII 时间线 + Trace 表 + Phase + 结论 |
| `zhang2_<algo>_trace.c` | 生成的插桩源码 |
| `zhang2_<algo>_trace` | 可执行文件 |

## 与第一轮的关系

- **数据独立**：勿与 `权重实验分析（第一轮）/` 下的 json 或 md 数字混用。
- 定性对比两套 md 时，请注明「第一轮 / 第二轮」及各自采集时间。
