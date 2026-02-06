# S02 Level‑2 有效代码行合并规则实现

## 1. 阶段目标
- 将 Level‑2 分块规则调整为“按最近有效代码行（跳过空行与注释）”判定合并。
- 维持既有输入输出接口，保证 zhang1 可复现。

## 2. 输入与依赖
- 规则文档：`mycallyplus_v1/文档/代码段切割方法/level2级分块.md`
- 代码实现：`mycallyplus_v1/level2/segment_dag_level2.py`
- 验证样例：`mycallyplus_v1/源文件/zhang1/zhang1.c`
- 数据输入：
  - `mycallyplus_v1/中间结果/zhang1/生成dag图/functions_full.json`
  - `mycallyplus_v1/中间结果/zhang1/生成dag图/functions_ranges.json`
  - `mycallyplus_v1/中间结果/zhang1/生成dag图/debug/mycalls_meta_internal.json`
  - `mycallyplus_v1/中间结果/zhang1/level2/merge_post_wait/circle.txt`

## 3. 实现与改动
- 文件：`mycallyplus_v1/level2/segment_dag_level2.py`
- 新增内容：
  - `_line_has_effective_code`：识别有效代码行（排除空行、`//`、`/*...*/`）。
  - `_build_effective_line_neighbors`：为每个函数构建 `prev_effective_line` / `next_effective_line`。
- 规则改动：
  - 合并规则从“段邻接判定”改为“有效代码行邻接判定”：
    - create/sem_post：若上一条有效代码是 unlock，删除 unlock 的切线。
    - join/sem_wait：若下一条有效代码是 lock，删除 lock 前切线。
- 线程首尾补线：
  - 入口：首调用非 lock/wait 时记录入口补线（加入切线集合并在输出标记）。
  - 出口：尾调用非 unlock/post/create 时在函数末尾切线。
- 输出扩展：
  - `segments_level2.json` 增加 `entry_cut_applied`、`exit_cut_applied`。

## 4. 结果与产物路径
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/segments_level2.json`
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.json`
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.dot`
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.png`

## 5. 验证方法与结论
- 语法检查：
  - `python3 -m py_compile mycallyplus_v1/level2/segment_dag_level2.py`
- 运行流程：
  - `python3 -m mycallyplus_v1.level2.merge_post_wait_dag --base-dir mycallyplus_v1 --base-name zhang1`
  - `python3 -m mycallyplus_v1.level2.segment_dag_level2 --base-dir mycallyplus_v1 --base-name zhang1 --source-file mycallyplus_v1/源文件/zhang1/zhang1.c`
  - `dot -Tpng mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.dot -o mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.png`
- 结论：
  - 产物成功生成，规则切换到“有效代码行相邻”后可复现输出。

## 6. 风险与问题
- 同一物理行多同步原语场景仍未纳入（本阶段约束）。
- 多行宏与复杂注释块在极端写法下可能需要进一步词法级处理。

## 7. 下一步
- S03：对比新旧分块结果差异，形成规则回归样例集。
- 补充最小化测试输入（含空行/注释跨越的合并场景）。
