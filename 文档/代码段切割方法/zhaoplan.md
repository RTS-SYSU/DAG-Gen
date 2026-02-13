# 集成 `zhao2020` 新调度算法（RTSS 2020 CPC + EA）

## 摘要
目标是在现有 `pipeline schedule -> schedule.json.priorities -> instrument` 链路中新增一个算法 `zhao2020`，实现论文 *“DAG Scheduling and Analysis on Multiprocessor Systems: Exploitation of Parallelism and Dependency”* 的核心调度策略：
- Algorithm 1：CPC 模型构造（providers + F/G）
- Algorithm 2：EA 规则优先级分配（Rule 1/2/3* + nested CPC 递归）

输出仍以 `priorities(1..99)` 为主，保证与 GUI、插装、后续 pipeline 完全兼容。

## 对外接口/行为变化
- 新增 `--algo zhao2020`（GUI 调度算法列表会自动出现，因为 GUI 动态读取 `algo_registry`）
- `schedule.json` 增加 `meta`（可选调试信息，不影响下游）：`critical_path/providers/F/G`

## 需要新增/修改的文件
- 新增：`pipeline/algo/zhao2020.py`
- 修改：`pipeline/algo_registry.py`（注册 `"zhao2020": Zhao2020BlockAlgo()`）
- 修改：`pipeline/algo/__init__.py`（导出 `Zhao2020BlockAlgo`）

## 设计细节（实现必须按此落地，避免二义性）

### 1) 输入解析（与现有算法保持一致）
- `segments_json["segments"]`：取 `seg_id` 列表作为节点集 `V`
- `dag_json["edges"]`：取 `src/dst` 作为边集 `E`
- `timing_json["weights"][seg_id]["total_ns"]` 作为节点权重 `Cj`（缺失则按 `0`）

### 2) 关键路径 `λ*`（Longest complete path by WCET）
- 目标：得到一条最长路径用于 CPC providers 构造
- 处理多源/多汇：
  - 内部构造虚拟 `__vsrc__` 连到所有 source（入度 0）
  - 构造虚拟 `__vsink__` 接所有 sink（出度 0）
  - 虚拟节点权重为 0
  - 计算最长路径后，输出时移除虚拟节点
- 计算方法：DAG DP（逆拓扑）+ `next_choice` 回溯，tie-break 用 `seg_id` 字典序保证可复现

### 3) Algorithm 1：CPC 模型构造（严格按论文公式）
实现 `_build_cpc_model(dag, critical_path)` 返回：
- `providers: [{idx, nodes(list), F(set), G(set)}]`
- `consumers_all: V \\ critical_set`

步骤：
- Step 1 providers：
  - 按 `critical_path` 顺序分段
  - 对连续节点满足 `pre(v_{j+1}) == {v_j}` 则归入同一 provider，否则新开 provider
- Step 2 consumers（维护可变集合 `V¬`）：
  - 初始化 `V_not = V \\ critical_set`
  - 对每个 provider `θi*`（从早到晚）：
    - 令 `head_next = head(θ_{i+1}*)`（若不存在则 `F=∅, G=∅`）
    - `F(θi*) = anc(head_next) ∩ V_not`
    - `G(θi*) = ⋃_{vj ∈ F(θi*)} ( C(vj) ∩ V_not )`
      - `C(vj)` 定义为：不在 `anc(vj)` 且不在 `des(vj)` 的节点集合（排除自身）
      - `anc/des` 用 DFS + memo 缓存（对每个节点只算一次）
    - `V_not = V_not \\ F(θi*)`
  - 注意：`F/G` 均不包含 critical 节点

### 4) Algorithm 2：EA 优先级分配（Rule 1/2/3* + nested CPC）
在 `Zhao2020BlockAlgo.compute()` 内调用 `_ea_priority_assignment(dag, wcet, cpc_model, prio_max=99)`：
- 初始化：`p=99`，`priorities={}`
- Rule 1（CPFE）：critical/path/provider 节点优先级最高
  - 按 `critical_path` 从头到尾赋值：`priorities[v]=p; p=max(1,p-1)`
- Rule 2：越早 provider 的 consumer group `F(θi*)` 越先分配（因此天然高于后面的组）
  - 依次处理 `F(θ1*), F(θ2*), ...`
- Rule 3*（组内最长局部路径优先 + 递归）：
  - 对一个 consumer group 的剩余节点集合 `S`：
    1. 构造诱导子图 `G[S]`
    2. 找“最长局部路径” `λve`：
       - 计算 `best_end[v]`（子图内到 v 的最长路径长度）
       - 在子图 sinks（子图内无后继）里选 `ve` 使 `best_end[ve]` 最大（tie-break seg_id）
       - 通过 `best_pred` 回溯出路径 `λve`
    3. 嵌套判定（对应 Algorithm 2 line 10）：
       - 若 `λve` 上存在节点 `x` 使其在子图内 `in_degree(x) > 1`：
         - 以 `λve` 作为子图的 critical path，调用 `CPC(G[S], λve)` 得到内层 CPC
         - 递归运行 `EA` 给子图内所有未分配节点赋优先级
         - 返回（该 consumer group 剩余部分由递归完全处理）
       - 否则（独立路径）：
         - 按路径顺序给 `λve` 中节点赋值：`priorities[v]=p; p=max(1,p-1)`
         - `S = S \\ λve` 继续循环
  - 兜底：任何因异常未分配到优先级的节点，按 `seg_id` 字典序填充（确保 `priorities` 覆盖 `V`）

### 5) 输出格式（保持 pipeline 契约）
`schedule.json` 至少包含：
- `schema_version`
- `base_name`
- `algo_name: "zhao2020"`
- `priorities: {seg_id: int}`
- `meta`（调试用）：
  - `critical_path`
  - `providers: [{idx, nodes, F_size, G_size, F_sample, G_sample}]`（避免 meta 太大；也可先输出完整 F/G 便于调试）

## 测试与验收（实现后必须跑）

### A) 静态检查
```bash
python3 -m py_compile pipeline/algo/zhao2020.py pipeline/algo_registry.py pipeline/algo/__init__.py
```

### B) CLI 可用性
```bash
PYTHONPATH=/home/chove/桌面 python3 -m mycallyplus_v1.pipeline list --level level2
```
应能看到 `zhao2020`。

### C) zhang1 回归
1. `schedule`：
```bash
PYTHONPATH=/home/chove/桌面 python3 -m mycallyplus_v1.pipeline --base-dir /home/chove/桌面/mycallyplus_v1 \\
  schedule --base-name zhang1 --level level2 --rule effective_line_merge --algo zhao2020
```
验收点：
- 产物存在：`中间结果/zhang1/pipeline/schedule/level2/effective_line_merge/zhao2020/schedule.json`
- `priorities` 数量等于 segments 数量，且值都在 `1..99`

2. `instrument`（通用）：
```bash
PYTHONPATH=/home/chove/桌面 python3 -m mycallyplus_v1.pipeline --base-dir /home/chove/桌面/mycallyplus_v1 \\
  instrument --base-name zhang1 --level level2 --rule effective_line_merge --algo zhao2020 --mode generic
```
验收点：
- `source_instrumented.c` 中插装条数与 segments 数一致（或至少 priorities 覆盖的 seg 数一致）

## 假设与默认值
- 默认以 `dag_seg.json` 为调度 DAG 输入（你现有 pipeline 即如此）
- 默认优先级范围固定为 `1..99`（与现有 validate/插装一致）
- 暂不集成论文的 `(α,β)` 响应时间分析（只做调度优先级分配）
