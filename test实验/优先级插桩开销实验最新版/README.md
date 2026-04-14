# 优先级插桩开销实验

这个实验只测量这一行代码的时间开销：

```c
l1_set_thread_prio_fifo(76);
```

方法很直接：

1. 在这行代码前调用一次 `clock_gettime(CLOCK_MONOTONIC_RAW, &t0)`
2. 执行 `l1_set_thread_prio_fifo(76);`
3. 在这行代码后调用一次 `clock_gettime(CLOCK_MONOTONIC_RAW, &t1)`
4. 计算 `t1 - t0`，得到这一次调用的耗时
5. 正式测量 `101` 次
6. 丢弃第 `1` 次测量结果，只对后面 `100` 次做统计

为了降低抖动，程序启动后会把当前线程绑定到 `CPU0`。

## 文件

- `bench_prio_call_overhead.c`: 实验程序
- `Makefile`: 编译和运行命令

## 编译

```bash
make
```

## 运行

真实 `prio_runtime.h` 内部会调用 `pthread_setschedparam(..., SCHED_FIFO, ...)`，需要 `root/sudo` 权限：

```bash
sudo ./bench_prio_call_overhead
```

或者：

```bash
make run
```

## 输出

程序会输出：

- `101` 次单次测量结果，单位 `ns`
- 第 `1` 次结果会标记为 `discarded from stats`
- 后面 `100` 次的平均值 `avg_ns`
- 最小值 `min_ns`
- 最大值 `max_ns`

程序还会把结果写入当前目录下的 `prio_call_overhead_results.csv`。

其中 `avg_ns` 就是按当前实验方法得到的 `l1_set_thread_prio_fifo(76);` 平均开销。
