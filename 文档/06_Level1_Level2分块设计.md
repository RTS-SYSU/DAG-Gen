# Level-1 / Level-2 分块设计

## 1. 分块阶段的输入前提

分块并不是直接从源码开始，而是建立在 legacy 产物之上：

- `functions_full.json`
- `functions_ranges.json`
- `debug/mycalls_meta_internal.json`
- `circle.txt`
- 原始 `dag.dot`

其中：

- `functions_ranges.json` 决定函数可分块区间。
- `mycalls_meta_internal.json` 提供同步原语所在行和调用顺序。
- `circle.txt` 提供信号量配对关系。

## 2. Level-1: `create/join` 分块

实现位置：

- `level1/segment_dag.py`

### 2.1 核心规则

Level-1 只关心两类切点：

- `pthread_create`
- `pthread_join`

每个函数按源码行被切成多段：

- 普通计算段：`compute`
- 创建点段：`create`
- 汇合点段：`join`

### 2.2 段 ID 设计

Level-1 用可读性很强的 ID 前缀表达段语义：

- `THR:` -> 普通计算段
- `CRT:` -> create 段
- `JON:` -> join 段

这有利于后续调度结果、日志和可视化直接回读语义。

### 2.3 DAG 边类型

Level-1 输出的边主要有：

- `intra`：同函数内顺序边
- `create`：创建段 -> 线程入口首段
- `join`：线程尾段 -> join 段

## 3. Level-2: 有效代码行 + 同步原语分块

实现位置：

- `level2/segment_dag_level2.py`
- `level2/merge_post_wait_dag.py`

### 3.1 相比 Level-1 的扩展

Level-2 在 `create/join` 基础上新增三类规则：

- `sem_post` / `sem_wait`
- `pthread_mutex_lock` / `pthread_mutex_unlock`
- “有效代码行相邻”的切线合并

### 3.2 切线规则

代码中实现的规则可概括为：

- `create`、`sem_post`：在该行之后切。
- `join`、`sem_wait`：在该行之前切。
- `lock`：在该行之前切。
- `unlock`：在该行之后切。

### 3.3 互斥区保护

Level-2 会先用 `mycalls_meta_internal.json` 的有序调用序列把 `lock/unlock` 配成区间，然后删除所有会把段切进临界区内部的切线。

因此 Level-2 的段类型除了 `compute` 外，还会标记：

- `mutex_cs`

### 3.4 有效代码行相邻合并

Level-2 不是简单看“物理相邻行”，而是先跳过：

- 空行
- 行注释
- 块注释

然后再判断：

- `create/sem_post` 的前一条有效代码是不是 `unlock`
- `join/sem_wait` 的后一条有效代码是不是 `lock`

如果满足条件，就撤销对应切线，实现跨同步语句的合并。

### 3.5 线程入口/出口补线

对于 `main` 和所有线程入口函数，Level-2 还会根据首尾调用点决定是否记录入口/出口切线：

- 首个调用不是 `lock/wait` 时，记录入口补线。
- 最后调用不是 `unlock/post/create` 时，记录出口补线。

当前实现以规则记录和边界处理为主，不额外制造空段。

## 4. `sem_post -> sem_wait` 图合成

`level2/merge_post_wait_dag.py` 负责把信号量配对信息转成图边。

流程是：

```text
读取原始 dag.dot
-> 解析 circle.txt 中的 post/wait 对
-> 增加 sem_dep 边
-> 输出 dag_level2_sem.dot/json
```

随后 `segment_dag_level2.py` 再把这些节点映射回段级边。

## 5. pipeline 中的封装

在 `pipeline` 中，上述分块被包装成 rule：

- `Level1Stage1Rule`
- `Level2EffectiveLineRule`

封装后统一输出到：

```text
中间结果/<base>/pipeline/blocks/<level>/<rule>/
```

包含：

- `segments.json`
- `dag_seg.json`
- `dag_seg.dot`
- `dag_seg.png`
- `rule_meta.json`

## 6. Level-3 现状

`pipeline/rules/level3_placeholder_rule.py` 目前只是占位实现，说明项目架构已经预留三级分块，但实际可用的仍是 Level-1 和 Level-2。

