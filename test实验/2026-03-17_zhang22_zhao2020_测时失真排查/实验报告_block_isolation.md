# zhang22 代表块隔离实验报告

## 1. 实验目标

本轮不再全量分析 `zhang22` 的所有块，而是从中抽取 3 个代表块，分别做：

- `other-only`：去掉 `busy_wait_seconds(Cx)`，只测块中其他语句
- `busy-only`：只测该块对应的 `busy_wait_seconds(Cx)`
- `full-block`：保留块原始结构，测完整块

实验目的：

1. 验证 `busy` 本身是否会随权值正常放大
2. 验证完整块是否可近似拆成“其他语句时间 + busy 时间”
3. 对比独立小程序与 `zhang22` 中已有 `pipeline timing` 结果，判断差异来源


## 2. 选取的 3 个代表块

### 块 A：纯 mutex + busy

来源：

- `/home/chove/Desktop/ScratchDAG/源文件/zhang22/zhang22.c:125`

对应代码：

```c
pthread_mutex_lock(&mutex_07);
busy_wait_seconds(C6);
pthread_mutex_unlock(&mutex_07);
```

### 块 B：sem_wait + busy

来源：

- `/home/chove/Desktop/ScratchDAG/源文件/zhang22/zhang22.c:101`

对应代码：

```c
pthread_mutex_lock(&mutex_02);
sem_wait(&sem_02);
busy_wait_seconds(C2);
pthread_mutex_unlock(&mutex_02);
```

### 块 C：join + busy

来源：

- `/home/chove/Desktop/ScratchDAG/源文件/zhang22/zhang22.c:177`

对应代码：

```c
pthread_mutex_lock(&mutex_09);
pthread_join(thread_c0, NULL);
busy_wait_seconds(C10);
pthread_mutex_unlock(&mutex_09);
```


## 3. 实验实现

实验目录：

- `/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查`

关键文件：

- 源码：`/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/block_isolation_harness.c`
- 批跑脚本：`/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/run_block_isolation.py`
- 汇总结果：`/home/chove/Desktop/ScratchDAG/test实验/2026-03-17_zhang22_zhao2020_测时失真排查/results/summary.json`

实现要点：

1. 独立程序仍保留原块结构
2. `busy_wait_seconds()` 使用与 `zhang22` 同类矩阵乘法
3. 为防止 `-O2` 把 `busy` 优化空，加入：

```c
static volatile double g_sink = 0.0;
```

并在 busy 末尾累加到 `g_sink`

4. 运行时固定 affinity 到 CPU `0,1`
5. 编译选项仍使用 `-O2`

本轮参数：

- `WORK_SCALE = 80`
- `repeats = 20`
- 扫描权值：`1, 5, 10, 20, 50`


## 4. 核心结果

### 4.1 块 A：mutex + busy

独立程序均值：

- `other-only`
  - `w1 = 51 ns`
  - `w5 = 46 ns`
  - `w10 = 47 ns`
  - `w20 = 47 ns`
  - `w50 = 46 ns`
- `busy-only`
  - `w1 = 656,621 ns`
  - `w5 = 3,405,569 ns`
  - `w10 = 6,839,715 ns`
  - `w20 = 13,302,419 ns`
  - `w50 = 34,901,901 ns`
- `full-block`
  - `w1 = 653,467 ns`
  - `w5 = 3,328,102 ns`
  - `w10 = 6,221,958 ns`
  - `w20 = 13,115,803 ns`
  - `w50 = 34,688,938 ns`

结论：

- `other-only` 近似常数且极小
- `busy-only` 随权值明显增长
- `full-block` 与 `busy-only` 几乎重合

说明：

- 对这类纯计算块，完整块时间基本由 `busy` 决定
- 该块是可拆解分析的


### 4.2 块 B：sem_wait + busy

独立程序均值：

- `other-only`
  - `w1 = 722,709 ns`
  - `w5 = 702,434 ns`
  - `w10 = 734,795 ns`
  - `w20 = 723,498 ns`
  - `w50 = 731,387 ns`
- `busy-only`
  - `w1 = 695,290 ns`
  - `w5 = 3,338,798 ns`
  - `w10 = 6,907,844 ns`
  - `w20 = 13,556,747 ns`
  - `w50 = 37,584,851 ns`
- `full-block`
  - `w1 = 1,447,564 ns`
  - `w5 = 4,115,730 ns`
  - `w10 = 7,479,151 ns`
  - `w20 = 14,481,277 ns`
  - `w50 = 37,409,944 ns`

对齐 `zhang22` 当前权值 `C2 = 8` 的补测：

- `busy-only @ w8 = 5,199,018 ns`
- `full-block @ w8 = 6,568,118 ns`

结论：

- `other-only` 基本稳定在约 `0.7 ms`
- `busy-only` 能正常放大
- `full-block` 大致等于 `other-only + busy-only`

说明：

- 对这类块，`sem_wait` 形成一个稳定底噪
- 放大倍数主要还是由 `busy` 决定


### 4.3 块 C：join + busy

独立程序均值：

- `other-only`
  - `w1 = 736,484 ns`
  - `w5 = 705,852 ns`
  - `w10 = 757,228 ns`
  - `w20 = 1,252,528 ns`
  - `w50 = 893,560 ns`
- `busy-only`
  - `w1 = 672,655 ns`
  - `w5 = 3,579,239 ns`
  - `w10 = 6,578,178 ns`
  - `w20 = 13,397,931 ns`
  - `w50 = 33,074,602 ns`
- `full-block`
  - `w1 = 1,389,453 ns`
  - `w5 = 4,070,292 ns`
  - `w10 = 7,412,977 ns`
  - `w20 = 14,396,204 ns`
  - `w50 = 33,919,216 ns`

对齐 `zhang22` 当前权值 `C10 = 140` 的补测：

- `other-only @ w140 = 727,287 ns`
- `busy-only @ w140 = 97,539,488 ns`
- `full-block @ w140 = 95,321,342 ns`

结论：

- `join` 带来约 `0.7 ms` 级别固定开销
- 当 `busy` 足够大时，完整块仍主要由 `busy` 主导
- `full-block` 与 `busy-only` 非常接近，说明本实验设置下 `join` 并没有压过 `busy`


## 5. 与 zhang22 现有 pipeline timing 的对照

当前 `zhang22` 的 `pipeline timing` 中对应段均值为：

- `MU:worker_c0#001@125-127`：`205 ns`
- `MU:worker_c2#002@101-104`：`175 ns`
- `MU:main#004@177-180`：`94,061 ns`

来源：

- `/home/chove/Desktop/ScratchDAG/中间结果/zhang22/pipeline/timing/level2/effective_line_merge/timing.json`

对照后可以得到很清楚的结论：

### 5.1 纯计算块在 zhang22 timing 里明显失真

独立实验中：

- `mutex busy-only @ w1 ≈ 656,621 ns`

而 `zhang22` 中对应段只有：

- `205 ns`

这不是正常噪声范围，说明 `zhang22` 现有 timing 结果没有真实反映 `busy` 成本。

### 5.2 sem_wait 块在 zhang22 timing 里也明显失真

独立实验中：

- `sem full-block @ w8 ≈ 6.57 ms`

而 `zhang22` 中对应段只有：

- `175 ns`

这同样说明 `busy` 成本在当前 pipeline timing 里没有被正确保留。

### 5.3 join 块在 zhang22 timing 里看起来“较大”，但仍远小于独立真实计算

独立实验中：

- `join full-block @ w140 ≈ 95.3 ms`

而 `zhang22` 中对应段均值：

- `94,061 ns ≈ 0.094 ms`

这说明：

- 当前 `zhang22` timing 里的大头更像是 `join` 等待波动
- 不是 `C10` 对应的真实计算量


## 6. 本轮最重要的结论

### 结论 1：独立程序里，`busy` 本身是能正常放大的

在加入 `volatile sink` 后：

- `busy-only` 随权值增长明显
- `full-block` 与 `busy-only`/`other-only` 的关系也基本符合预期

这说明：

- 你想要的“按块拆开测”这条思路是成立的
- 问题不在“busy 这个想法本身不可测”

### 结论 2：当前 zhang22 的 pipeline timing 没有测到真实 busy 成本

独立实验和 `zhang22` timing 相差几个数量级，核心原因仍然是：

- `busy_wait_seconds()` 在当前 `pipeline timing` 产物里被 `-O2` 优化空了

本轮之前已经通过反汇编确认过：

```asm
<busy_wait_seconds>:
    retq
```

所以当前 `timing.json` 主要测到的是：

- 锁
- `sem_wait`
- `pthread_join`
- 线程切换和调度波动

而不是 `Cx` 对应的真实计算量。

### 结论 3：用独立块实验可以验证块自身行为，但不能直接替代整程序上下文

本轮独立程序证明了：

- 某些块的本体时间可分解
- `busy` 可正常放大

但它不能直接说明：

- 在完整 `zhang22` 并发上下文里，这个块仍会得到同样结果

原因是：

- `join` / `wait` 的真实等待量依赖前驱何时完成
- 完整程序里还有其它线程、其它 release 时序、其它竞争

所以更准确的说法是：

- 独立实验可以先验证块级时间模型
- 但要验证完整上下文，还需要再把“抗优化 busy”带回 `zhang22`


## 7. 下一步建议

下一步建议不要再调常量，而是优先做下面两件事：

1. 先修 `zhang22` 的 `busy_wait_seconds()`，确保 `pipeline timing` 下不会被 `-O2` 优化空
2. 修完后重新跑：
   - `collect`
   - `blocks`
   - `timing`
   - 再对比这 3 个代表块在 `zhang22` 中的新结果

如果修完以后：

- 代表块在 `zhang22` 里的时间接近独立实验

那么就可以继续做更大范围的块级分析。

如果修完以后仍差很多：

- 那就说明上下文竞争才是主要因素
- 后面需要继续做“独立块 vs 原程序上下文”的更细对照


## 8. 一句话结论

这轮实验已经证明：

- 代表块单独写程序是能测出正常权重放大的
- 当前 `zhang22` 的异常结果，不是因为块级分析思路错了
- 而是因为 `pipeline timing` 里 `busy` 已被优化掉，导致测时口径失真
