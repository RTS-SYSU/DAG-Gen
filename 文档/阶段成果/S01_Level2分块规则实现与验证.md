# S01 Level2分块规则实现与验证

## 1. 阶段目标
- 在现有项目中落地 Level2 分块规则。
- 以 `zhang1` 跑通从分块到分段 DAG 产物生成。
- 将流程接入 GUI 的“段级时间分析（Level-2）”按钮。

## 2. 输入与依赖
- 规则来源：`mycallyplus_v1/文档/代码段切割方法/level2级分块.md`
- 样例程序：`mycallyplus_v1/源文件/zhang1/zhang1.c`
- 数据输入：
  - `mycallyplus_v1/中间结果/<base>/生成dag图/functions_full.json`
  - `mycallyplus_v1/中间结果/<base>/生成dag图/functions_ranges.json`
  - `mycallyplus_v1/中间结果/<base>/生成dag图/debug/mycalls_meta_internal.json`
  - `mycallyplus_v1/中间结果/<base>/level2/merge_post_wait/circle.txt`

## 3. 实现与改动
- 重构 Level2 分块脚本：`mycallyplus_v1/level2/segment_dag_level2.py`
  - 支持 create/post 行后切、join/wait 行前切。
  - 支持 lock 前切、unlock 后切。
  - 支持 create/join 与相邻 lock 块的合并规则。
  - 支持线程入口/出口补线规则（main + 线程入口函数）。
  - 从 `mycalls_meta_internal.json` 使用调用顺序判定首尾调用。
- GUI 接入更新：`mycallyplus_v1/ui/gui.py`
  - Level2 按钮新增 merge_post_wait 调用。
  - 点击按钮自动归档：`functions_full.json`、`mycalls_meta_internal.json`、`circle.txt` 到 `level2/merge_post_wait/`。

## 4. 结果与产物路径
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/segments_level2.json`
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.json`
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.dot`
- `mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.png`
- `mycallyplus_v1/中间结果/zhang1/level2/merge_post_wait/dag_level2_sem.dot`

## 5. 验证方法与结论
- 语法检查：
  - `python3 -m py_compile mycallyplus_v1/level2/segment_dag_level2.py`
  - `python3 -m py_compile mycallyplus_v1/ui/gui.py`
- 运行验证：
  - `python3 -m mycallyplus_v1.level2.segment_dag_level2 --base-dir mycallyplus_v1 --base-name zhang1 --source-file mycallyplus_v1/源文件/zhang1/zhang1.c`
  - `dot -Tpng mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.dot -o mycallyplus_v1/中间结果/zhang1/level2/stage2/dag_level2_seg.png`
- 结果结论：
  - `zhang1` 流程可跑通并产出 Level2 分段 DAG 文件。

## 6. 风险与问题
- 目前“当前开发需求”文件仍是模板内容，未填入本轮明确验收项。
- 个别边界条件（异常路径、宏封装 API）暂未纳入本阶段。

## 7. 下一步
- 先把 `mycallyplus_v1/当前开发需求/需求说明.md` 填成真实需求。
- 进入 S02：按真实需求逐条补齐验证项和回归检查。
