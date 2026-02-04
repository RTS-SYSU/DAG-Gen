# 会话交接：Level‑2（sem/mutex）分段与“图合成”（2026-02-04）

用途：把本窗口围绕“多入边 DAG 的可构造性/语义/Level‑2 规则”讨论后的结论与下一步落地任务整理出来，供新的 Codex 窗口直接接管继续实现。

---

## 0. 目前总体目标（你已经敲定）

要在同一份 C 程序里，用以下 4 类关系构造最终的“学术/算法 DAG（图一）”：

- 线程生命周期关系：`pthread_create`、`pthread_join`
- 同步依赖关系：`sem_post`、`sem_wait`

并采用“图合成”的方式理解与实现：

- 图二：仅由 `create/join` 抽取的基础骨架图（偏生命周期/线程结构）
- 图三：仅由 `sem_post/sem_wait` 抽取的同步依赖补边图（支持 fan-in、多入边）
- 图一：在图二基础上加入图三的边（边类型区分），得到完整拓扑

> 结论：仅用 `create/join` 不能表达多入边；引入 `sem_post/sem_wait` 后可表达任意 DAG 的依赖约束（至少对 benchmark/任务级 DAG）。

---

## 1. DAG 语义分层（用于对齐学术/工业）

本窗口把“边语义混淆”的问题梳理清楚，并形成分层共识：

1) **计算/任务 DAG（目标图）**：节点是任务/段，边是 precedence（前驱完成后继才可开始）。学术论文图更接近这一层。
2) **同步证据图**：`sem_post/sem_wait`（后续还会加更多同步原语）提供 happens-before 的证据，可用于推导/补全计算 DAG 的边。
3) **生命周期/载体图**：`create/join` 主要反映线程/资源管理结构，不等价于算法依赖，但可用于线程分组/解释并发窗口。

在你当前“图合成”规则里：
- 图二主要对应第 3 层（生命周期图）
- 图三主要对应第 2 层（同步证据）
- 图一希望逼近第 1 层（计算 DAG）

---

## 2. Level‑1 已有能力（基于 create/join）

现状（已完成）：
- Level‑1 / Stage‑1：只把 `pthread_create*` / `pthread_join*` 当 cut points，生成 `segments_stage1.json` + 段级 DAG。
- 段级测时、LPF、prio 插桩、baseline/prio 对照实验与批量实验归档体系已存在（详见：
  - `mycallyplus_v1/文档/新会话快速上手_段级实验.md`
  - `mycallyplus_v1/文档/代码段切割方法/README_代码段切割与优先级插桩_Level1.md`
  - `mycallyplus_v1/文档/会话交接_自动化工具与测时统一_2026-02-01.md`
  - `mycallyplus_v1/文档/会话交接_多DAG构造与实验流程_2026-02-03.md`
）

关键约束（已明确）：
- 同一个 `pthread_t` **不能被 join 两次**；因此仅依赖 `create/join` 的表达能力偏树/单父结构，无法表达 fan-in。

---

## 3. Level‑2 的新增方向（本窗口敲定）

### 3.1 Level‑2 不止 sem_post/sem_wait：还要纳入 mutex

你提出：Level‑2 规则不止 `post/wait`，还需要把 **mutex** 纳入：
- `pthread_mutex_lock`
- `pthread_mutex_unlock`
- 并把“同一把锁的 lock→unlock 之间”视为一个代码段（临界区段）

### 3.2 “不同粒度”同时支持（结构粒度 vs 研究粒度）

你决定同时支持两种粒度（两种视图）：

1) **结构粒度（不合并）**：同步/生命周期语句作为独立段
   - 优点：依赖锚点与边类型清晰，便于查看/对齐 DAG 结构（合成图一更直观）
2) **研究粒度（合并/折叠）**：把同步/生命周期语句按规则并入相邻 compute 段或折叠为粗节点
   - 优点：更接近“任务级 DAG”，便于调度研究（LPF/HELF/WCET 等）

> 重要结论：是否“把 create/join 单独成段”不必二选一；保持独立段对结构与可追溯性更好，而研究时可通过折叠视图获得粗粒度图。

---

## 4. 需要实现的 Level‑2 规则（建议先定一个最小可落地版本）

为避免语义膨胀，建议 Level‑2 先落地一个“保守可实现”的版本（后续再增强）：

### 4.1 sem_post/sem_wait 的段与边

- cut points：识别 `sem_wait(...)` / `sem_post(...)` 所在行，作为独立段（结构粒度）。
- 配对/连边（用于图三与图合成）：
  - 基准程序侧约束：使用全局 `sem_t` 变量，调用形态稳定为 `sem_wait(&dep_X)` / `sem_post(&dep_Y)`（一行一句）。
  - 工具侧：以 `&dep_*`（同一个 sem 对象）为 key，将 `post` 视为对该对象的“生产许可”，`wait` 视为“消费许可”，据此推导依赖边。
  - 先支持：同一函数内、一行一句、形态可解析的地址参数（复杂表达式先跳过并 warning）。

### 4.2 mutex 段（临界区段）

- cut points：识别 `pthread_mutex_lock(&m)` / `pthread_mutex_unlock(&m)`。
- 段规则（建议最小版本）：
  - 仅处理“同一函数内、同一 mutex 对象、非嵌套”的 lock/unlock 配对。
  - 生成 `critical_section` 段（建议先包含 lock/unlock 行，或至少输出两种范围以便折叠）。
  - 遇到嵌套/跨函数：先标 warning，退化为普通 compute（避免破坏稳定性）。
- 边语义（建议先不强行变成 precedence DAG 边）：
  - mutex 更像资源互斥约束，不天然等价于算法依赖；
  - Level‑2 初期建议先输出“临界区段 + 耗时统计”，把“互斥关系”作为附加信息（可选做资源冲突图），不要直接混进图一的 precedence 边。

---

## 5. 基准程序落地状态（zhang1）

已创建占位文件：
- `mycallyplus_v1/源文件/zhang1/zhang1.c`（当前为空文件，用于后续实现 benchmark DAG 程序）

近期要做的基准程序方向（已讨论但未落码）：
- 图(a) Laplace/菱形网格 DAG：用 `sem_post/sem_wait` 表达多入边依赖，`create/join` 提供生命周期骨架与线程分组
- 图(c) stencil 类 DAG：顶层可“同时启动”多个入度为 0 的节点（仍在同一 C 文件内实现，不需要多个 C 文件）

代码风格约束（必须遵守）：
- `mycallyplus_v1/文档/代码风格_ScratchDAG_线程DAG基准程序.md`

---

## 6. 下一窗口建议的落地任务清单（按优先级）

1) **补齐 `zhang1.c`**：实现一个可编译、可运行的 DAG 基准程序
   - 同时包含：`pthread_create/join` + `sem_post/sem_wait`
   - （可选）加入可控的 `pthread_mutex_lock/unlock` 临界区段用于 Level‑2 验证
   - 代码要求：一行一句 create/join/wait/post/lock/unlock；线程句柄显式命名；每节点有 compute

2) **实现 Level‑2 结构粒度切段**：在现有 Level‑1 的切段/段级 DAG 流程上扩展 cut points
   - 新增：`sem_post/sem_wait`、`pthread_mutex_lock/unlock` 的识别与段划分
   - 输出：新增 `segments_stage2.json` / `dag_stage2_seg.json`（或在现有结构内增量扩展并标记 kind）

3) **实现“折叠视图”**：把结构粒度段折叠成研究粒度段（用于调度/LPF）
   - 保持两套输出：结构视图（用于合成图/可视化）+ 折叠视图（用于调度/测时/插桩）

4) **实现图合成输出**：在图二基础上加图三边，产出图一（带边类型）

---

## 7. 交接给新窗口的关键路径（直接贴路径即可）

- 交接文档（背景）：`mycallyplus_v1/文档/会话交接_多DAG构造与实验流程_2026-02-03.md`
- Level‑1 快速上手：`mycallyplus_v1/文档/新会话快速上手_段级实验.md`
- Level‑1 规格：`mycallyplus_v1/文档/代码段切割方法/README_代码段切割与优先级插桩_Level1.md`
- ScratchDAG 友好代码风格：`mycallyplus_v1/文档/代码风格_ScratchDAG_线程DAG基准程序.md`
- Level‑1 代码入口（切段/测时/调度/插桩）：`mycallyplus_v1/level1/`
- 新基准程序占位：`mycallyplus_v1/源文件/zhang1/zhang1.c`

