# Code2DAG 升级：通用 create/join 绑定方案

## 问题背景

当前 DAG 生成流程（`generation/legacy.py`）中，`pthread_create` 和 `pthread_join` 的绑定依赖 RTL 寄存器解析：

- `_resolve_symbol_from_reg_history(line_history, "1")` → 从 reg 1 (dx) 提取 start_routine
- `_resolve_symbol_from_reg_history(line_history, "5")` → 从 reg 5 (di) 提取 thread handle
- `preparse_pthread_join_bindings()` → 从 RTL 中匹配 `reg:DI 5 di` 提取 join 的 handle

**这些寄存器编号是 x86_64 的调用约定，在 ARM64 (rk3588) 上完全不适用：**

| 参数 | x86_64 | ARM64 (aarch64) |
|------|--------|-----------------|
| arg0 (thread handle) | reg 5 (di) | reg 0 (x0) |
| arg1 (attr) | reg 4 (si) | reg 1 (x1) |
| arg2 (start_routine) | reg 1 (dx) | reg 2 (x2) |
| arg3 (arg) | reg 2 (cx) | reg 3 (x3) |

导致在 ARM64 上：
- create 的 handle 和 task 解析全部失败（返回空字符串）
- join 的 handle 解析全部失败
- `tail_to_joins` 为空 → 没有 join 补边
- DAG 图中线程之间完全没有 create/join 依赖关系

## 现有代码的问题链路

```
RTL 寄存器解析（平台相关）
    ↓ 失败
myinfo[create_num] = resolved_target
    → create_num = ""（空字符串，所有 create 覆盖同一个 key）
    → join_num = ""（空字符串）
    ↓
build_join_binding_map()
    → handle_to_thread: {"": "最后一个线程"}（被覆盖）
    → handle_to_joins: {"": [所有join节点]}
    ↓
tail_to_joins = {}（空，因为 handle 对不上）
    ↓
append_join_edges() → 无补边输出
```

## 解决方案：行号回源码

### 核心思路

RTL 解析已经为每个节点记录了源码行号（`mycalls_meta_internal.json`），这个信息跨平台稳定。利用行号回到 C 源码，用正则提取 `pthread_create/join` 的参数，用 handle 变量名做配对 key。

### 绑定链路

```
RTL 解析（跨平台稳定的部分）
    ↓
mycalls_meta_internal.json
    → main/pthread_create15: {line: 174}
    → main/pthread_join29:   {line: 188}
    ↓
回到 C 源码对应行
    → 第174行: pthread_create(&thread_c0, NULL, worker_c0, NULL);
    → 第188行: pthread_join(thread_c0, NULL);
    ↓
正则提取参数
    → create: handle="thread_c0", task="worker_c0"
    → join:   handle="thread_c0"
    ↓
用 handle 名配对
    → thread_c0 的 task 尾节点 → main/pthread_join29
```

### 关键正则

```python
CREATE_RE = re.compile(r'pthread_create\s*\(\s*(?:&\s*)?(\w+)')     # 提取 handle
TASK_RE   = re.compile(r'pthread_create\s*\([^,]+,\s*[^,]+,\s*(\w+)')  # 提取 task_fn
JOIN_RE   = re.compile(r'pthread_join\s*\(\s*(\w+)')                 # 提取 handle
```

### 链式 create 支持

部分程序使用链式 create（如 zhang1: main→c0_fn→c1_fn→c2_fn），create 分布在不同函数中，但 join 集中在 main。

解决：全局扫描所有函数的 `mycalls_meta`，收集所有 create/join 节点的行号，统一回源码解析，合并到一个全局 `handle → (create_node, task_fn)` 映射表。

## 验证结果

| 样例 | creates | joins | 匹配 | 状态 |
|------|---------|-------|------|------|
| zhang1 | 3 | 3 | 3 | ✅ 全部匹配（含链式 create） |
| zhang2 | 3 | 3 | 3 | ✅ 全部匹配 |
| zhang3 | 3 | 3 | 3 | ✅ 全部匹配 |
| zhang11 | 3 | 3 | 3 | ✅ 全部匹配（含链式 create） |
| experiment1 | 50 | 50 | 50 | ✅ 全部匹配（含链式 create） |
| experiment2 | 17 | 17 | 17 | ✅ 全部匹配（含链式 create） |

## 需要修改的文件

### `generation/legacy.py`

1. **新增 `_fixup_create_join_bindings_from_source()` 后处理函数**（约第 1221 行）：
   - RTL 第一遍扫描完成后、`build_join_binding_map()` 之前调用
   - 遍历所有函数的 `mycalls_meta`，对每个 `pthread_create`/`pthread_join` 节点：
     - 用行号回到 C 源码，正则提取 handle 和 task_fn
   - 修正三项数据：
     - `myinfo[handle] = task_fn`（create 绑定，用于 join 补边）
     - `myinfo[join_node] = handle`（join 绑定，用于 join 补边）
     - `mycalls` 中的 handle 变量名 → 替换为真正的函数名（用于 create 分叉边）
     - `__create_queue__` 重建为正确的函数名列表

2. **修正 `build_join_binding_map()`**（约第 1048 行）：
   - 区分 create 记录（key 不含 `/`）和 join 记录（key 含 `pthread_join`），避免混淆
   - 过滤 `__source_create_queue__` 等内部 key

3. **调用点**（约第 1914 行）：
   - 在 `instfunctions(functions)` 之后、`build_join_binding_map(functions)` 之前插入：
   - `_fixup_create_join_bindings_from_source(functions, config)`

注意：**未删除**原有的 RTL 寄存器解析代码（`_resolve_symbol_from_reg_history`、`preparse_pthread_join_bindings`），它们在 x86 上仍然会执行，fixup 函数会用源码解析的结果覆盖/修正它们的输出。这样在 x86 上也不会退化。

### 修正的两个问题

| 问题 | 原因 | 修正方式 |
|------|------|----------|
| join 补边缺失 | RTL 寄存器解析在 ARM64 上失败，handle 全部为空字符串，`tail_to_joins` 为空 | fixup 用源码行号提取真实 handle，`build_join_binding_map` 正确构建映射 |
| create 分叉边目标错误 | `resolved_target` 在 ARM64 上是 handle 变量名（如 `thread_c0`）而非函数名（如 `worker_c0`），导致 `has_inline_thread=False` | fixup 将 `mycalls` 和 `__create_queue__` 中的 handle 变量名替换为函数名 |

### `generation/source_binder.py`

- 未修改，但其 `_scan_calls` 函数的正则逻辑被 fixup 函数复用（内联了简化版正则）

## 方案优势

- **跨平台**：不依赖 RTL 寄存器约定，x86/ARM64/RISC-V 都适用
- **跨 GCC 版本**：不依赖 RTL 格式细节，只依赖行号（GCC 始终提供）
- **简单可靠**：正则匹配 POSIX 标准 API 签名，不会变
- **向后兼容**：未删除原有 RTL 解析代码，x86 上不退化
- **改动最小**：新增一个后处理函数 + 修正一个过滤逻辑，不改变 DAG 构建的整体架构

## DAG 验证结果

修改后重新生成的 dag.dot 与修改版（x86 上生成的正确版本）逐行对比：

| 样例 | 对比结果 | join 补边 | create 分叉边 |
|------|----------|-----------|---------------|
| zhang1 | ✅ 完全一致 | `c0_fn/sem_post14 → main/pthread_join29` 等 3 条 | `create → c0_fn/c1_fn/c2_fn`（函数名） |
| zhang2 | ✅ 完全一致 | `worker_c0/unlock3 → main/pthread_join29` 等 3 条 | `create → worker_c0/c1/c2`（函数名） |
| zhang3 | ✅ 完全一致 | `worker_c0/unlock24 → main/pthread_join51` 等 3 条 | `create → worker_c0/c1/c2`（函数名） |

## Pipeline 执行结果

zhang1/2/3 在 DAG 更新后完整跑通 pipeline 6 个阶段：

| 阶段 | zhang1 | zhang2 | zhang3 |
|------|--------|--------|--------|
| collect | ✅ | ✅ | ✅ |
| blocks (level2/effective_line_merge) | ✅ 16 segments | ✅ 14 segments | ✅ 18 segments |
| timing (10 repeats) | ✅ 16 weights | ✅ 14 weights | ✅ 18 weights |
| schedule (6 algos) | ✅ cpf/heft/lpf/t_level/wcet_first/zhao2020 | ✅ | ✅ |
| instrument (6 algos × 3 variants) | ✅ 18 个 .c 文件 | ✅ | ✅ |

每个算法生成 3 个变体：`result/{algo}/`, `result/CFS/`, `result/FIFO/`，以及对应的 `timing/` 版本。

## runtime_compare 结果目录命名升级

### 改动文件

- `tools/runtime_compare/ui/web/api.py`（第 322-331 行）
- `tools/runtime_compare/core/task_runner.py`（第 162-165 行、第 539-545 行）

### 改动内容

**1. batch 文件夹名带参数信息**（`api.py`）

原来：`batch_name = folder_path.name`（如 `zhang3`）

现在：`batch_name = f"{base}_ws{work_scale}_r{repeats}_cpu{cpu_tag}"`（如 `zhang3_ws1000_r10_cpu67`）

**2. batch 文件夹带时间戳，子目录不带**（`task_runner.py`）

原来：
```
zhang3/                          ← batch 无时间
  cpf_2026-04-02T11-07-29+00-00/  ← 子目录带时间
  heft_2026-04-02T11-07-33+00-00/
```

现在：
```
zhang3_ws1000_r10_cpu67_2026-04-02T11-07-10+00-00/  ← batch 带参数+时间
  cpf/                                                ← 子目录干净
  heft/
  CFS/
  FIFO/
```

### 效果

一个 batch 文件夹名就能看出：样例名、work_scale、重复次数、绑定核心、实验时间。子目录只保留算法名，简洁清晰。

## 源码编写规范与测时/分块升级

### 源码编写规范

**mutex 临界区内只放计算节点**，所有同步原语放在 mutex 外面：

```c
// ✅ 正确写法
sem_wait(&sem_01);                   // 同步：在 mutex 外面
pthread_mutex_lock(&mutex_01);
busy_wait_seconds(C1);               // 计算：在 mutex 里面
pthread_mutex_unlock(&mutex_01);
sem_post(&sem_02);                   // 同步：在 mutex 外面

// ❌ 旧写法（zhang2/3 原始版本）
pthread_mutex_lock(&mutex_01);
sem_wait(&sem_01);                   // 同步混在 mutex 里面
busy_wait_seconds(C1);
pthread_mutex_unlock(&mutex_01);
```

好处：
- MU 块内没有阻塞调用，timing 天然准确，不需要跳过逻辑
- 权重与 busy_wait 参数严格线性，偏差收敛到 ±20% 以内

### 分块后处理：SEG 吸收规则

同步原语移到 mutex 外面后，会在两个 MU 块之间产生独立的 `SEG:` 段。通过双向吸收规则消除：

| SEG 段内容 | 吸收方向 | 合并到 | 语义 |
|---|---|---|---|
| `sem_post` | 往上（从 unlock 往下扫） | 前一个 MU 块（扩展 end_line） | "发出信号"是前一个计算的收尾 |
| `pthread_create` | 往上（从 unlock 往下扫） | 前一个 MU 块（扩展 end_line） | "创建线程"是前一个计算的收尾 |
| `sem_wait` | 往下（从 lock 往上扫） | 后一个 MU 块（扩展 start_line） | "等待信号"是后一个计算的前置条件 |
| `pthread_join` | 往下（从 lock 往上扫） | 后一个 MU 块（扩展 start_line） | "等待线程"是后一个计算的前置条件 |

**碰头停止机制：** 两个方向各自只吸收自己类型的原语，遇到对方类型就停止。典型结构：

```
pthread_mutex_unlock(&mutex_01);   ← MU#1 原始结尾
sem_post(&sem_01);                 ← unlock 往下扫，是 post → 吸进 MU#1，继续
sem_post(&sem_02);                 ← 是 post → 吸进 MU#1，继续
sem_wait(&sem_03);                 ← 不是 post/create → 停止！
sem_wait(&sem_04);                 ← lock 往上扫，是 wait → 吸进 MU#2，继续
pthread_mutex_lock(&mutex_02);     ← MU#2 原始开头
```

结果：MU#1 扩展到包含 sem_post，MU#2 扩展到包含 sem_wait，post 和 wait 分属不同段，不会产生依赖环。

**实现要点：** 切点删除时，forward chain（从 unlock 出发）只删除 post/create 行前面的切点；backward chain（从 lock 出发）只删除 wait/join 行前面的切点。两个 chain 各自独立操作，不会越过对方的边界。

吸收后 DAG 节点全是 MU 块，不产生零权重的 SEG 节点。

### 测时规则

MU 块内只有计算，测时探针直接插在 lock 之后、unlock 之前：

```c
pthread_mutex_lock(&mutex_xx);
SEG_BEGIN("MU:xxx");              // ← lock 之后
busy_wait_seconds(Cx);
SEG_END("MU:xxx");                // ← unlock 之前
pthread_mutex_unlock(&mutex_xx);
```

被吸收的 wait/join 在 lock 之前，被吸收的 post/create 在 unlock 之后，都不在探针范围内。

### 改动文件

- `level2/segment_dag_level2.py`：分块后处理，添加 SEG 吸收逻辑
- `level1/time_analysis_level1.py`：测时插桩，SEG_BEGIN 跳过被吸收的 blocker 行
- `pipeline/timing.py`：对未插桩的纯 blocker 段自动填 `avg_ns=0`（兜底）
- `源文件/zhang2/zhang2.c`：同步原语移到 mutex 外面
- `源文件/zhang3/zhang3.c`：同步原语移到 mutex 外面
- `源文件/zhang1/zhang1.c`：已符合规范，无需修改
