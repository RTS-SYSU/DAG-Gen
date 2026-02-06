# Level-2 分块规则（双层结构）

## 文档用途
- 实现方默认优先读取 **B. 本轮变更**；若 B 未覆盖，再读取 **A. 稳定规则**。

## A. 稳定规则（长期有效）

### A1 输入与数据源
- `中间结果/<base>/生成dag图/functions_full.json`
- `中间结果/<base>/生成dag图/functions_ranges.json`
- `中间结果/<base>/生成dag图/debug/mycalls_meta_internal.json`
- `中间结果/<base>/level2/merge_post_wait/circle.txt`（缺失时回退到 `中间结果/<base>/配置文件/circle.txt`）

### A2 基础切线规则
- 块节点：`create`、`join`、`sem_wait`、`sem_post`、`pthread_mutex_lock`、`pthread_mutex_unlock`。
- `create` / `sem_post`：在行后画线。
- `join` / `sem_wait`：在行前画线。
- `pthread_mutex_lock`：在 lock 行前画线。
- `pthread_mutex_unlock`：在 unlock 行后画线。

### A3 线程首尾补线规则
- “第一个函数/最后一个函数”指线程中第一个/最后一个调用节点（按 `mycalls_meta_internal.json` 的有序键序列）。
- 每个线程函数开始时：若第一个调用不是 `lock`、`wait`，在函数开始处画线。
- 每个线程函数结束时：若最后一个调用不是 `unlock`、`post`、`create`，在函数结束处画线。

### A4 分段类型判定
- 段区间覆盖任一 lock 起始行：`mutex_cs`。
- 其他：`compute`。

### A5 边构造规则
- `intra`：函数内相邻段依赖。
- `create`：create 所在段 -> 线程入口函数首段。
- `join`：线程入口函数末段 -> join 所在段。
- `sem_dep`：`circle.txt` 中 post/wait 配对映射到段边。

### A6 不处理项
- 同一物理行同时命中多个同步原语的冲突场景暂不处理。
- 宏封装 API 识别暂不处理（仅原生 pthread/sem 名称）。

### A7 行范围字段释义（functions_ranges.json）
- `last_stmt_line`（推荐）：
  - 函数体内“最后一条有效语句”的行号，通常不包含右花括号 `}`。
  - 适合作为分段上界，避免把 `}` 等语法收尾混进最后一个段。
- `level1_end_line`（次选）：
  - Level-1 规则下的函数末端行号（用于兼容旧流程）。
  - 在大多数情况下可用，但语义不如 `last_stmt_line` 直接。
- `end_line`（最后兜底，不推荐）：
  - 函数定义的结束行，通常就是 `}` 所在行。
  - 若直接用于分段上界，容易让 `return`/`}` 进入同一尾段，产生你说的“多出块”现象。
- 推荐上界优先级：
  - `last_stmt_line` > `level1_end_line` > `end_line`。

## B. 本轮变更（仅本轮生效/高频）

### B1 变更背景
- 现状问题：合并规则若按“line±1”判断，会受空行与注释干扰。
- 本轮目标：将合并判定升级为“最近有效代码行”。

### B2 变更条目
1. 新增“有效代码行”语义：
   - 非空且非注释行；注释含 `//` 与 `/*...*/`。
2. 合并规则改为按有效代码行邻接：
   - 出现 `create`、`sem_post`：若上一条有效代码是 `unlock`，删除该 `unlock` 的切线（与 lock 块合并）。
   - 出现 `join`、`sem_wait`：若下一条有效代码是 `lock`，删除该 `lock` 的前切线（与 lock 块合并）。
3. 保持“基础切线规则”和“边构造规则”不变。

### B3 本轮验收点
- [x] 基础切线仍按 A2 执行。
- [x] 空行与注释不会阻断合并判定。
- [x] `create/sem_post` 与 `join/sem_wait` 合并规则按“有效代码行邻接”生效。
- [x] `zhang1` 可重新产出 `segments_level2.json / dag_level2_seg.json / dot / png`。

### B4 对实现文件影响范围
- 目标文件：`mycallyplus_v1/level2/segment_dag_level2.py`
- 关键点：
  - 有效代码行识别函数
  - `prev_effective_line` / `next_effective_line` 邻接表
  - 合并规则从“段邻接”切换为“有效代码行邻接”

### B5 回滚策略
- 若本轮规则导致结果不可用，回滚到“按 line±1 判定”的上一版合并逻辑。
- 回滚后仅保留 A 节稳定规则，不带 B 节新增邻接语义。

## C. 实现读取顺序（给 agent）
1. **Step1**：先读 B 节（本轮变更）。
2. **Step2**：B 节未覆盖的基础语义，回查 A 节。
3. **Step3**：未收到口令 `同步文档` / `阶段收敛` / `会话交接`，不更新其他文档。

## D. 版本标记
- 最近更新时间：2026-02-06
- 本轮负责人：
- 关联阶段号：S02
