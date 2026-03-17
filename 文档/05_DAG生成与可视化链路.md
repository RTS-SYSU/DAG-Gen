# DAG 生成与可视化链路

## 1. 上游输入

当前项目的典型上游输入有两类：

- GCC 产生的 RTL `.expand`
- 与 `.expand` 对应的 `.c` 源文件

在生成链路里，`.expand` 是主输入，源码主要用于：

- 提取函数范围
- create/join 绑定兜底
- 补充源码行号信息

## 2. `generation/legacy.py` 的核心职责

`generation/legacy.py` 完成了五件事情：

1. 解析 RTL，构建函数调用信息。
2. 识别条件上下文，形成带前缀的调用节点。
3. 识别线程创建与汇合，补齐线程边。
4. 导出 DOT、debug JSON、函数范围、`circle.txt`。
5. 在输出目录下组织统一的中间结果结构。

## 3. 解析阶段

### 3.1 函数、调用、引用

解析器通过正则识别：

- 函数头：`;; Function ...`
- 调用：`(call ...)`
- 符号引用：`(symbol_ref ...)`

这些信息会被写入 `functions` 字典，并保留 `mycalls` 顺序。

### 3.2 条件前缀

项目会把 `if`、`while`、`switch` 这类控制流上下文编码进节点名或路径前缀，使导出的图不仅表示“谁调用谁”，还保留一定的执行上下文信息。

这也是 viewer 可以单独渲染条件节点图的原因。

## 4. 线程边构建

线程图不是从 RTL 里“天然存在”的，而是由项目补出来的：

- `pthread_create` 节点连到线程入口函数首段。
- 线程尾节点连到对应的 `pthread_join` 节点。

实现上依赖三种信息：

1. `myinfo` 中记录的线程句柄到任务函数映射。
2. 线程任务的 `tail` 节点。
3. 当 RTL 无法可靠配对时，使用 `generation/source_binder.py` 从 C 源函数内扫描 `pthread_create` / `pthread_join`。

## 5. `circle.txt` 的作用

`circle.txt` 是整个项目里非常关键的同步原语配置文件，供两个模块共同消费：

- `visualization/viewer.py`
- `level2/segment_dag_level2.py` / `pipeline.collector.py`

其内容分两段：

- `互斥量`
- `信号量`

记录每个同步节点对应的编号、源码位置和文件信息，用来：

- 在可视化中把 lock/unlock、post/wait 成对显示。
- 在 Level-2 中恢复 `sem_post -> sem_wait` 的跨线程依赖。

## 6. 生成产物

legacy 生成链路的关键产物包括：

- `中间结果/<base>/生成dag图/dag.dot`
- `中间结果/<base>/生成dag图/functions_full.json`
- `中间结果/<base>/生成dag图/functions_ranges.json`
- `中间结果/<base>/生成dag图/debug/mycalls_meta_internal.json`
- `中间结果/<base>/配置文件/circle.txt`

后续 Level-1、Level-2、pipeline collector 都以这些文件为标准输入。

## 7. viewer 可视化链路

`visualization/viewer.py` 消费 DOT 与 `circle.txt` 后，会生成几类视图：

- 原始图
- 互斥锁图
- 信号量图
- Tarjan 强连通分量图
- 线程分组图

其核心工作包括：

- 读取 DOT 到 `networkx` 图
- 解析 `circle.txt`
- 为 `sem_post -> sem_wait` 叠加虚线边
- 计算 SCC 并高亮
- 按线程前缀或推断结果做 cluster 着色

## 8. 这一层的边界

需要特别区分两种图：

- legacy 输出的函数/调用级 DAG
- Level-1 / Level-2 输出的分段 DAG

viewer 主要面向前者。分块 DAG 的可视化则更多由 `level1/segment_dag.py`、`level2/segment_dag_level2.py`、`pipeline/runner.py` 自己导出 DOT 完成。

