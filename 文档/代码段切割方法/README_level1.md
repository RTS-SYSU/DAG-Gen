# Level-1（代码段级）实现记录与待完善项

本文档用于记录 Level-1（代码段/Segment）从“标准 DAG”派生“段级 DAG”的实现约定、以及后续需要完善的边界情况。随着实现迭代，请持续补充本文件。

## 当前已实现（阶段 1：create/join）

### 1) 段级 DAG（基于标准 DAG 合并）
- 入口：`generation/legacy.py --level1-stage1`（需同时提供 `--source-file`）
- 输出目录：`mycallyplus_v1/中间结果/<base>/level1/stage1/`
  - `segments_stage1.json`
  - `dag_stage1_seg.json`
  - `dag_stage1_seg.dot`
- 段范围来源：`mycallyplus_v1/中间结果/<base>/生成dag图/functions_ranges.json`
  - `level1_start_line = first_stmt_line`（fallback: `body_start_line`）
  - `level1_end_line = last_stmt_line`（fallback: `end_line`）
- create/join 语义边：
  - create 段 -> entry_fn 的第一个段
  - entry_fn 的最后一个段 -> join 段
  - 不使用 `__stack_chk_fail*` 作为尾节点（源代码不存在，无法插桩）

### 2) 段命名（可读）
- 执行段（compute）：`THR:<func>#<idx>@<start>-<end>`
- create 段：`CRT:<func>#<idx>@L<line>`
- join 段：`JON:<func>#<idx>@L<line>`

## 时间测量（独立模块）
- 模块：`mycallyplus_v1/level1/time_analysis_level1.py`
- 输出目录：`mycallyplus_v1/中间结果/<base>/level1/timing/<project>/`

## 待完善项（必须记录，后续逐步解决）

1. **段不嵌套假设**
   - 当前 runtime 使用 TLS 单槽，默认每线程不会嵌套段。
   - 若未来引入更细粒度切割（条件/热点），可能出现嵌套，需要改为栈结构或计数器。

2. **多行语句 cut point**
   - 当前阶段 1 默认 create/join 是单行 `[line,line]`。
   - 若 `pthread_create/join` 跨多行，建议把 cut 段扩展到分号结束行（需要括号深度扫描）。
   - 当前实现暂不处理（插桩阶段跳过/告警）。

3. **控制语句行插桩**
   - 若段边界落在 `if/for/while/switch` 控制行，宏插入可能改变语义或导致编译问题。
   - 当前策略：跳过并记录 warning。
   - 改进方向：自动移动边界到最近的“普通语句行”或改用块级插桩策略。

4. **trace 输出策略**
   - 推荐：每线程一个 trace 文件，减少锁开销与扰动。
   - 备选：单文件 + mutex（实现更简单但扰动更大）。

5. **与段级 DAG 的加权融合**
   - 将 `time_result_seg.json` 写回 `dag_stage1_seg.json`（node weight）并导出 `dag_stage1_seg_weighted.dot/png`。
