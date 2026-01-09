# CPC 调度算法实现说明（MycallyPlus v1）

本文描述 `mycallyplus_v1` 中“CPC分析”子功能的实现逻辑、输入输出与关键算法，便于理解和维护。

## 功能入口
- GUI：左侧“调度算法”→“CPC分析”。
- 依次选择三个文件：
  1) `dag.dot`（DAG 拓扑）
  2) `time_result.json`（节点耗时 total_ns；缺失视为 0）
  3) `longest_path.json`（字段 `path` 作为关键路径 λ*）
- 输出目录：`中间结果/<base>/调度算法/cpc/`
  - `dag_highlight.dot/.png`：节点 label 含 `prio=<n>`，λ* 高亮，tooltip=total_ns
  - `schedule.json`：输入路径、m、provider 段、节点优先级表
  - `schedule.txt`：人读摘要

## 核心函数与文件
- `scheduler.py`
  - `compute_cpc_priorities(nodes, edges, node_weight_ns, longest_path, m=2)`
  - `apply_priorities_to_dot(dot_text, priorities, node_weight_ns, longest_path)`
  - `write_cpc_schedule_json(...)`
- UI 按钮处理：`ui/gui.py::_scheduler_cpc`

## 算法流程（节点级 CPC，含 provider 合并）
1) **输入准备**
   - 解析 `dag.dot` 得到节点/边。
   - 从 `time_result.json` 取 `total_ns` 作为权重，缺失置 0。
   - 从 `longest_path.json.path` 读取 λ*。
   - m 固定为 2（可扩展为参数）。
2) **拓扑检查**
   - `topo_sort_or_cycle` 检测有向环；若有环，CPC 失败并提示。
3) **Provider 划分（沿 λ* 合段）**
   - 顺序扫描 λ*，若下一个关键节点的唯一前驱是当前节点，则并入同一段；
   - 否则切段，新建 provider 段。
4) **优先级分配（整数递减，数值越大优先级越高）**
   - 先按 provider 段顺序分配：段内节点依序递减。
   - 对剩余未分配节点：
     - 在未分配子图中提取“局部最长链”：
       - 对子图拓扑排序，计算到各终点（子图内无后继节点） 的最长路径和；
       - 选择权重和最大的终点回溯整条链。
     - 将该链节点依序分配递减优先级并从子图移除；循环直到子图为空。
   - 若子图检测到环，报错终止。
5) **DOT 标注**
   - 对每个节点：
     - `label` 增加一行 `prio=<n>`（若原有 label 则追加）
     - `tooltip` 写入 `total_ns`
     - 若在 λ* 上则填充/加粗，高亮 λ* 边。
   - 补全原 DOT 未显式声明的节点。
6) **输出写盘**
   - `dag_highlight.dot/.png`、`schedule.json/txt` 写入 `中间结果/<base>/调度算法/cpc/`。

## 与经典 CPC 的差异
- provider 合并规则同论文（关键路径连续、无分叉即合段）。
- 未做线程聚合/映射，纯节点级优先级。
- m 固定为 2，未做多核参数化调度分析。
- consumer 子图的递归 CPC（论文 Rule2/Rule3 的 join 递归）在当前实现简化为“最长链分配”，未继续层层递归，但仍会在含环时失败提示。

## 典型用法
1) 生成 DAG/时间分析/最长路径（已有 GUI 按钮）。
2) 点击“CPC分析”，按提示选择 `dag.dot`、`time_result.json`、`longest_path.json`。
3) 查看输出目录 `调度算法/cpc/` 下的 PNG/JSON/TXT，DOT 节点下方即含 `prio=<n>`。

## 注意事项
- 输入必须是 DAG；有环时会报错并终止。
- 若 `time_result.json` 缺权重，将使用 0，优先级仍会分配，但意义受限。
- λ* 取自 `longest_path.json.path`，若为空则报错。
