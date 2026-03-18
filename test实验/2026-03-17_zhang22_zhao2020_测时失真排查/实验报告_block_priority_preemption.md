# 块边界动态降优先级抢占实验报告

## 1. 实验目标

本实验用于验证一个关键问题：

- 当线程 A 正在执行；
- 并且在进入下一个代码块前，把自己的实时优先级从较高值降到较低值；
- 此时若线程 B 已经就绪或被唤醒，且其优先级高于 A；

那么 B 是否会立即抢占 A，使 A 暂停，待 B 运行结束或阻塞后再继续。

这个问题直接关系到当前“按代码块设置优先级”的方案是否能够在运行时形成近似的块级调度效果。


## 2. 实验结论

结论是：

- 会抢占。
- 在本次实际运行中，A 在块边界把优先级从 `90` 降到 `70`；
- 随后 A 通过 `sem_post()` 唤醒优先级为 `80` 的 B；
- B 在 A 继续执行前立即获得 CPU；
- A 直到 B 完成后才恢复执行。

因此，可以确认：

- Linux 内核真正调度的仍然是线程；
- 但如果在“块边界”动态修改线程优先级，就可以把“块优先级”映射为线程在不同阶段的调度地位；
- 这种机制可以产生你所关心的“某个块切换后，另一个线程因为优先级更高而抢占”的效果。


## 3. 实验文件

本次新增的最小化验证程序位于：

- `/home/chove/Desktop/ScratchDAG/中间结果/zhang22/pipeline/instrument/level2/effective_line_merge/zhao2020/ab_preempt_test.c`

编译产物位于：

- `/home/chove/Desktop/ScratchDAG/中间结果/zhang22/pipeline/instrument/level2/effective_line_merge/zhao2020/ab_preempt_test`

依赖的优先级设置接口来自：

- `/home/chove/Desktop/ScratchDAG/level1/prio_runtime.h`


## 4. 实验设计

### 4.1 线程与优先级设置

实验中有 3 个线程：

- `main`：设置为 `SCHED_FIFO 60`
- `A`：先设置为 `SCHED_FIFO 90`，运行第一段后降到 `SCHED_FIFO 70`
- `B`：设置为 `SCHED_FIFO 80`

优先级关系为：

- 初始阶段：`A(90) > B(80) > main(60)`
- 降级后：`B(80) > A(70) > main(60)`

### 4.2 同步关系

为了让现象足够清晰，实验使用了一个信号量：

- B 启动后先阻塞在 `sem_wait(&sem_start_b)`
- A 在完成第一段工作后，先把自己降级到 `70`
- 然后由 A 调用 `sem_post(&sem_start_b)` 唤醒 B

这样可以精确观察：

- A 降级之后
- B 被唤醒变为 runnable
- 调度器到底先让谁继续执行

### 4.3 消除干扰的方法

实验做了两个重要控制：

- 所有线程绑定到 `CPU0`
- 使用 `SCHED_FIFO`

单核绑定保证不会出现 A 和 B 分别跑在不同核上的情况，从而让“抢占”现象变得可直接观测。


## 5. 核心代码逻辑

实验程序的关键逻辑是：

### 5.1 线程 A

1. 设为 `FIFO 90`
2. 执行 `block_A1`
3. 降到 `FIFO 70`
4. `sem_post()` 唤醒 B
5. 尝试继续执行 `block_A2`

### 5.2 线程 B

1. 设为 `FIFO 80`
2. 阻塞等待 `sem_start_b`
3. 被 A 唤醒后执行 `block_B1`

如果 A 降级后不会被抢占，那么日志顺序应接近：

```text
A after prio set -> A returned from sem_post -> A block_A2 start -> B ready
```

如果 A 降级后会被抢占，那么日志顺序应接近：

```text
A after prio set -> B ready -> B run -> A returned from sem_post
```


## 6. 实际运行结果

本次实际运行得到的关键日志如下：

```text
[   2004495 ns] thread=A     policy=FIFO   prio=70 phase=drop     after prio set, about to wake B
[   2007585 ns] thread=B     policy=FIFO   prio=80 phase=ready    woken and runnable
[   2008188 ns] thread=B     policy=FIFO   prio=80 phase=run      start block B1
[   4808587 ns] thread=B     policy=FIFO   prio=80 phase=run      end block B1
[   4868083 ns] thread=A     policy=FIFO   prio=70 phase=drop     returned from sem_post
[   4870114 ns] thread=A     policy=FIFO   prio=70 phase=block_A2 start
```

从这几行可以得到非常明确的判断：

1. A 在唤醒 B 之前，优先级已经成功降到 `70`
2. B 被唤醒后，当前优先级是 `80`
3. B 的 `ready` 和 `start block B1` 都发生在 A 的 `returned from sem_post` 之前
4. A 没有在 `sem_post()` 之后继续执行，而是先被 B 抢占

也就是说：

- 抢占确实发生了
- 触发点正是“块边界降优先级 + 唤醒一个更高优先级线程”


## 7. 对当前 zhang22 / zhao2020 的含义

这次实验验证的不是 `zhang22` 的完整业务流程，而是其中最关键的调度机制：

- 内核层：调度对象仍是线程
- 策略层：你可以在代码块边界修改线程优先级
- 效果层：不同代码块会对应线程在该阶段的不同调度地位

因此，对你当前方案更准确的表述是：

- “分析调度单位”是代码块
- “执行调度单位”仍然是线程
- 但通过块边界的动态 `pthread_setschedparam(SCHED_FIFO)`，可以让线程在不同块上体现不同优先级

换句话说：

- 这不是内核原生的“块调度”
- 但它是一种可以逼近块级优先级策略的实现方式


## 8. 与前面 zhang22 实验的关系

此前对 `zhang22` 的实际插桩代码观察到：

- `source_instrumented.c` 中已经不是“每线程只设一次优先级”
- 而是每个块前都插入了 `l1_set_thread_prio_fifo(...)`

因此，当前 `zhang22 / zhao2020` 的插桩运行时，确实具备本实验所验证的这种能力：

- 某线程在进入下一块时改变优先级
- 若该改变导致别的 runnable 线程优先级更高
- 那么别的线程可以抢占当前线程

不过也要注意：

- 抢占是否实际发生，仍取决于是否存在“更高优先级且已就绪”的线程
- 如果其他线程仍在阻塞，或者优先级仍低于当前线程，那么当前线程不会被打断


## 9. 复现实验命令

编译命令：

```bash
gcc -O0 -pthread -I /home/chove/Desktop/ScratchDAG/level1 \
  /home/chove/Desktop/ScratchDAG/中间结果/zhang22/pipeline/instrument/level2/effective_line_merge/zhao2020/ab_preempt_test.c \
  -o /home/chove/Desktop/ScratchDAG/中间结果/zhang22/pipeline/instrument/level2/effective_line_merge/zhao2020/ab_preempt_test
```

运行命令：

```bash
/home/chove/Desktop/ScratchDAG/中间结果/zhang22/pipeline/instrument/level2/effective_line_merge/zhao2020/ab_preempt_test
```


## 10. 最终结论

本实验已经验证：

- 在 `SCHED_FIFO` 下；
- 若线程 A 在代码块切换点把自己的优先级降到低于线程 B；
- 且 B 在该时刻变为 runnable；

那么 B 会抢占 A。

因此，你当前“以代码块为分析单位、以线程为执行载体、在块边界动态调整线程优先级”的方案，在机制上是成立的，并且确实能够产生块级优先级所期望的运行时抢占效果。
