# 代码风格：ScratchDAG 友好的线程‑DAG 基准程序（Level‑1/Stage‑1）

本文定义“适合 ScratchDAG（以及 Level‑1/Stage‑1：仅以 `pthread_create`/`pthread_join` 为切点）”的 C 语言线程程序代码风格。目标是：**容易建图、容易切段、容易插桩、容易对比实验**。

---

## 0. 适用范围与不追求的东西

- 适用：pthread 线程 DAG（create/join 表达依赖），用于你们的 stage‑1 切段/段级测时/LPF/插桩实验。
- 不追求：工程化封装、极致抽象、动态任务生成、复杂通用框架。

---

## 1. 总原则（ScratchDAG 友好）

### 1.1 拓扑只用 create/join 显式表达

- DAG 的依赖边 **只能**通过 `pthread_create(...)` 与 `pthread_join(...)` 出现。
- `pthread_create/join` 尽量保持“一条语句一行”，不要放进宏/多行语句里，避免行号切段不稳定。

### 1.2 每个节点 = 一个线程函数（命名稳定）

- 每个 DAG 节点写成独立的线程入口函数：
  - `static void *task_A(void *arg);`
  - `static void *task_B(void *arg);`
- 不用函数指针表/数组索引动态选择入口函数（会影响可追踪性）。

### 1.3 每个线程函数里必须有 compute 段

- 不允许出现“纯同步/纯 create/join”的空线程。
- 每个线程函数至少调用一次统一的计算函数（如 `busy_wait_seconds(weight)`），保证段级测时与优先级分配有意义。

### 1.4 不使用 pthread_t 数组（便于映射与建图）

- 线程句柄用显式变量命名：`static pthread_t tA, tB, tC;`
- 避免：`pthread_t threads[N];`、`threads[i]`、循环 join。

### 1.5 计算负载统一走一个 busy 计算函数

- 保留一个统一的计算函数（建议签名固定）：
  - `static void busy_wait_seconds(double seconds);`
- 负载倍率用宏 `WORK_SCALE` 控制：
  - `#ifndef WORK_SCALE` / `#define WORK_SCALE ...`
  - 编译时用 `-DWORK_SCALE=<n>` 覆盖
- 每个节点的“权重”用 `#define` 或常量表达（例如 `#define A_W 10.0`），确保拓扑与权重都可读。

### 1.6 避免复杂控制流包裹 create/join

- 避免在 `if/for/while/switch` 内部出现 create/join（会增加切段与插桩风险）。
- 如果必须创建多个线程，优先手写展开成多条 `pthread_create` 语句（固定次数）。

### 1.7 参数传递尽量简单

- 优先使用 `arg` 未使用或仅传入简单结构体指针（且结构体定义清晰）。
- 避免深层嵌套结构、复杂生命周期管理，减少插桩边界“不安全”的概率。

---

## 2. 推荐的骨架结构（模板思路）

### 2.1 头部与宏

- 头部：`pthread.h`、必要时 `sched.h`、`errno.h`、`string.h`、`time.h`。
- `WORK_SCALE` 宏入口：
  - `#ifndef WORK_SCALE`
  - `#define WORK_SCALE 25000`
  - `#endif`
- 节点权重：`#define A_W ...`、`#define B_W ...` …

### 2.2 全局线程句柄

- `static pthread_t tA, tB, tC, ...;`（不用数组）

### 2.3 线程函数形态（建议固定顺序）

每个线程函数尽量长得像：

- 1) `busy_wait_seconds(W_A);`
- 2) `pthread_create(&tX, NULL, task_X, NULL);`（可选）
- 3) `busy_wait_seconds(W_A2);`（可选）
- 4) `return NULL;`

这样可以让 stage‑1 的 compute/create/join 段切割更稳定，也方便后续在 compute 段边界插桩。

### 2.4 main 的职责（就做“调度/收尾”）

- `main()` 只负责：
  - 创建 DAG 入口节点（若需要）
  - 等待关键节点结束（用 `pthread_join`）
- **不强制**“所有 join 集中 main / main 固定写 affinity / 先 filler 再关键链”：
  - 这些属于“实验策略”，不是 scratchdag 代码风格硬约束

---

## 3. 常见反模式（请避免）

- `pthread_t th[N]; for(i) pthread_create(&th[i], ...)`（数组+循环）
- `#define START_T(x) pthread_create(...)`（create 藏在宏里）
- create/join 写成多行或一行多个语句（行号切段不稳定）
- 线程函数只有 create/join 没有 compute（无可测权重）
- 复杂控制流包裹 create/join（难插桩、难稳定复现）

---

## 4. 与实验策略的关系（备注）

如果你的目标是“制造 baseline FIFO 与 prio/LPF 的差异”，可以在遵守上述风格的前提下再加策略：

- 关键链 + 填充任务（制造争用）
- 选择性 join 位置（控制并发窗口）
- 权重分布设计（让 LPF 更有优势）

但这些属于“如何构造特殊 DAG 的内容”，不属于 scratchdag 代码风格本身。

