# zhang22 三口径总时间对照实验报告（5 组）

## 1. 本轮实验说明

在已经修复 runtime 内部时间解析后，围绕同一个 `zhang22` 三口径实验，连续真实运行了 5 组独立批次。

每组都包含：

1. 分块累计时间
2. `main` 内总时间
3. runtime 工具解析到的 `PROGRAM_TOTAL_NS`

批跑脚本：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/run_total_time_compare_batch.py`

批次结果目录：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5`

跨组汇总：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5/batch_summary.json`


## 2. 5 组真实结果

每组均值如下：

| 组别 | 分块累计均值(ns) | main 总时间均值(ns) | runtime 均值(ns) | main-runtime 偏差 | 分块/main 比值 |
|---|---:|---:|---:|---:|---:|
| 1 | 557,248,431 | 247,304,706 | 233,028,260 | 5.77% | 2.253 |
| 2 | 581,288,930 | 235,833,061 | 236,255,952 | 0.18% | 2.465 |
| 3 | 555,055,623 | 241,310,637 | 235,723,906 | 2.32% | 2.300 |
| 4 | 557,617,361 | 233,906,173 | 237,860,444 | 1.69% | 2.384 |
| 5 | 556,402,260 | 239,881,188 | 236,972,100 | 1.21% | 2.319 |

5 组单独 `report.json` 位于：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5/group_01/report.json`
- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5/group_02/report.json`
- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5/group_03/report.json`
- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5/group_04/report.json`
- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/total_time_compare_batch5/group_05/report.json`


## 3. 跨组统计

根据 `batch_summary.json`：

### 分块累计均值

- 跨组均值：`561,522,521.32 ns`
- 最小：`555,055,623.2 ns`
- 最大：`581,288,930.8 ns`
- 标准差：`9,922,367.77 ns`

### main 内总时间均值

- 跨组均值：`239,647,153.46 ns`
- 最小：`233,906,173.9 ns`
- 最大：`247,304,706.8 ns`
- 标准差：`4,668,323.45 ns`

### runtime 均值

- 跨组均值：`235,968,132.86 ns`
- 最小：`233,028,260.9 ns`
- 最大：`237,860,444.3 ns`
- 标准差：`1,635,489.32 ns`

### main-runtime 偏差

- 跨组平均偏差：`2.23%`
- 最小偏差：`0.18%`
- 最大偏差：`5.77%`

### 分块/main 比值

- 跨组平均比值：`2.344`
- 最小比值：`2.253`
- 最大比值：`2.465`


## 4. 结果分析

### 4.1 runtime 的正确性现在是稳定的

5 组中：

- `main` 内总时间和 runtime 均值始终处于同一数量级
- 平均偏差只有 `2.23%`
- 最好一组偏差仅 `0.18%`

这说明：

- runtime 修复后，已经能稳定解析程序内部时间
- 它现在可以作为调度算法效果评估的可信口径


### 4.2 分块累计时间稳定地大于程序总时间

5 组里 `分块/main` 比值都落在：

- `2.253 ~ 2.465`

跨组平均：

- `2.344`

这说明这个现象不是偶然波动，而是稳定结构性现象：

- 分块累计时间不能当程序总时间
- 它更接近“所有线程工作量总和”
- 程序总时间更接近 `makespan`


### 4.3 5 组结果比单组更能说明问题

如果只看 1 组，可能会怀疑：

- 是不是那组刚好抖动
- 是不是某次 runtime 恰好特殊

但 5 组之后结论已经比较硬：

1. `main` 内总时间和 runtime 很接近，而且稳定
2. 分块累计时间始终大很多，而且比例稳定在约 `2.34x`


## 5. 对后续实验的含义

这 5 组真实数据支持下面两个判断：

### 判断 1：调度算法效果应该看哪种时间

应该看：

- `main` 内总时间
- 或 runtime 解析到的 `PROGRAM_TOTAL_NS`

这两者现在已经验证为稳定一致。


### 判断 2：分块时间在后续实验中的角色

分块时间仍然有价值，但用途不是评价调度算法最终效果，而是：

- 分析哪些块重
- 分析关键路径
- 分析等待/同步开销
- 分析权重和分段是否合理

但不能再把：

- 所有分块时间之和

当成程序完成时间来解释。


## 6. 最终结论

基于 5 组真实实验：

1. runtime 修复后已经正确且稳定
   - 与 `main` 内总时间的平均偏差约 `2.23%`

2. `main` 内总时间和 runtime 都可以作为调度算法效果的主指标

3. 分块累计时间稳定地约为程序总时间的 `2.34` 倍
   - 它不是 makespan
   - 不能作为算法优劣的最终评价指标


## 7. 一句话结论

5 组真实结果已经足够说明：后续评价 `zhao2020` 或 FIFO 的效果，应看 `main` 内总时间或 runtime 解析到的 `PROGRAM_TOTAL_NS`；分块累计时间只适合做分析，不适合做最终结论。
