# zhang22 三口径总时间对照实验报告

## 1. 本轮实验做了什么

围绕 `zhang22`，比较 3 种时间口径：

1. 所有分块时间求和
2. `main` 内总时间
3. runtime 工具解析到的 `PROGRAM_TOTAL_NS`

本轮先对 runtime 做了增量修复：

- 保留原有 fallback 逻辑
- 仅把内部时间解析从“只扫 stdout”改成“同时扫 stdout + stderr”

对应修改文件：

- `/home/chove/Desktop/ScratchDAG/tools/runtime_compare/utils/time_parse.py`
- `/home/chove/Desktop/ScratchDAG/tools/runtime_compare/core/task_runner.py`
- `/home/chove/Desktop/ScratchDAG/tools/c_runtime_compare_gui.py`

这次实验的 runtime 已经成功解析到程序内部时间，不再回退到 wall-clock。


## 2. 实验产物

实验脚本：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/run_total_time_compare.py`

结果目录：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare`

结构化结果：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare/report.json`

本轮 runtime 结果：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare/runtime_results/runtime_task/2026-03-17T19-10-39+08-00_ws10_r10/summary.json`

参数：

- `WORK_SCALE = 10`
- `repeats = 10`

注意：

- 这次三口径已统一为 `-O0` 编译口径，避免之前 `-O2` vs runtime `-O0` 的失配。


## 3. 三种时间口径的真实结果

根据 `report.json`：

- 分块累计时间均值：`530,148,436.9 ns`
- `main` 内总时间均值：`237,611,978.9 ns`
- runtime 工具 baseline 均值：`229,172,548.8 ns`

换算后约为：

- 分块累计：`530.148 ms`
- `main` 内总时间：`237.612 ms`
- runtime：`229.173 ms`


## 4. 单次样本

前 3 次运行：

1. 第 1 次
   - 分块累计：`555,205,292 ns`
   - `main` 内总时间：`246,166,522 ns`
   - runtime：`221,757,339 ns`
2. 第 2 次
   - 分块累计：`527,081,203 ns`
   - `main` 内总时间：`240,752,653 ns`
   - runtime：`232,480,977 ns`
3. 第 3 次
   - 分块累计：`527,032,349 ns`
   - `main` 内总时间：`243,373,491 ns`
   - runtime：`247,113,778 ns`


## 5. runtime 修复是否生效

已生效。

在最新 runtime `summary.json` 中：

- `parsed_from_stdout = true`

并且 `log_text` 里可直接看到：

```text
[stderr]
PROGRAM_TOTAL_NS=239398224
```

说明 runtime 这次确实拿到了程序内部时间，而不是 wall-clock fallback。


## 6. 结果解释

### 6.1 `main` 内总时间和 runtime 很接近

均值分别为：

- `237.612 ms`
- `229.173 ms`

差值约：

- `8.439 ms`

相对 `main` 内总时间的偏差约：

- `3.55%`

这说明：

- runtime 的内部时间解析现在已经基本正确
- 用它来评估调度算法效果是可信的


### 6.2 分块累计时间明显大于程序总时间

分块累计均值：

- `530.148 ms`

而 `main` 内总时间均值：

- `237.612 ms`

分块累计约为程序总时间的：

- `2.23` 倍

这不是测量错误，而是并发程序中的正常现象：

- 多个线程上的 segment 可以并行执行
- 分块累计是“所有线程忙碌时间的总和”
- 程序总时间是 `makespan`

两者本来就不是同一个量


### 6.3 这轮实验真正说明了什么

本轮实验回答了两个问题：

1. runtime 工具能不能被修到正确解析内部总时间？
   - 可以
   - 这轮已经成功

2. 所有分块时间加起来是否等于程序总运行时间？
   - 不等于
   - 而且在 `zhang22` 这轮上明显更大


## 7. 对调度算法评价的含义

这轮结果进一步确认：

- 调度算法效果应看 `main` 内总时间 / runtime 成功解析到的 `PROGRAM_TOTAL_NS`
- 不应看“所有分块时间求和”

因为：

- 调度算法优化的是程序完成时间
- 不是所有线程工作时间的算术和

分块累计时间更适合：

- 做权重分析
- 看局部块的耗时组成
- 看关键路径候选

但它不适合作为最终效果指标。


## 8. 当前结论

本轮在修好 runtime 内部时间解析后，三口径关系已经清楚：

1. runtime 工具现在是正确的
   - 已成功解析 `PROGRAM_TOTAL_NS`
   - 与 `main` 内总时间仅差约 `3.55%`

2. `main` 内总时间可以作为最稳的主指标

3. 分块累计时间不等于程序总时间
   - 在 `zhang22` 这轮里约为总时间的 `2.23` 倍
   - 所以后续不能再把它当 makespan 使用


## 9. 一句话结论

修复后的 runtime 已能正确读取程序内部总时间；在 `zhang22` 上，真正应关注的是 `main` 内总时间或 runtime 解析到的 `PROGRAM_TOTAL_NS`，而不是所有分块时间之和。
