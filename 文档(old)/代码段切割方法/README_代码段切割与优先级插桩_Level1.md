# Level-1 代码段切割与优先级插桩（端到端流程）

本文档说明：如何从“标准 DAG”派生“代码段 DAG”，如何对代码段测时、计算最长路径优先（LPF）优先级，并将优先级插桩生成对照实验结果。

适用范围：当前实现为 **Level-1 / Stage-1**（只处理 `pthread_create`/`pthread_join` 作为 cut points），后续阶段（条件节点、热点段）不在本文覆盖。

---

## 0. 关键原则（本实现的口径）

1. **代码段（Segment）是源代码行号区间**：`[start_line, end_line]`。
2. Stage-1 只把两类调用作为切段边界：
   - `pthread_create*`
   - `pthread_join*`
3. **段级 DAG = 在标准 DAG 上做合并**：
   - 段级节点来自 `segments_stage1.json`
   - 段级边只表达依赖（顺序边 + create/join 语义边）
4. **源文件不允许被原地改写**：
   - 所有插桩/对照实验均在 `中间结果/<base>/level1/experiments/.../project/` 的工程副本中完成
5. **程序总时间测量不改源代码**：
   - 通过链接期 `-Wl,--wrap=main`（`wrap_main.c`）包裹 `main`，输出 `PROGRAM_TOTAL_NS=...` 到 `stderr`。

---

## 1. 目录结构（Level-1 专用）

所有 Level-1 产物统一落在：

`mycallyplus_v1/中间结果/<base>/level1/`

其中：

- `stage1/`：段定义 + 段级 DAG
- `timing/`：段级测时结果
- `schedule/`：LPF 调度输出（优先级文件）
- `experiments/`：对照实验（baseline vs prio）与对比报告

---

## 2. 输入与 base 取值

### 2.1 输入文件

- 源代码：`*.c`
- expand：`*.233r.expand`

### 2.2 base 规则

优先使用源代码文件名（不带扩展）作为 `<base>`；若缺失源文件则使用 expand 的前缀（去掉 `.233r.expand`）。

例如：

- `cpu4_thread10_fifo.c` / `cpu4_thread10_fifo.c.233r.expand` → `<base>=cpu4_thread10_fifo`

---

## 3. Step A：生成标准 DAG（legacy）

入口：`mycallyplus_v1.generation.legacy`

建议命令（示例）：

```bash
PYTHONPATH=. python3 -m mycallyplus_v1.generation.legacy \
  --threads-only \
  --source-file mycallyplus_v1/源文件/<proj>/<proj>.c \
  --output-base mycallyplus_v1 \
  --force \
  --level1-stage1 \
  mycallyplus_v1/源文件/<proj>/<proj>.c.233r.expand
```

> `--source-file` 必须提供：用于生成 `mycalls_meta_internal.json`（含行号），否则无法切段。

### 3.1 标准 DAG 输出文件（输入基础）

目录：`mycallyplus_v1/中间结果/<base>/生成dag图/`

- `dag.dot/png`：标准 DAG（线程视图）
- `functions_full.json`：解析后的函数表（包含 `mycalls`、`myinfo` 等）
- `functions_ranges.json`：函数体范围（Level-1 使用 `level1_start_line/level1_end_line`）
- `debug/mycalls_meta_internal.json`：调用点源代码行号（extern==0 的调用）

### 3.2 `functions_ranges.json` 是如何得到的（详细）

文件路径：

`mycallyplus_v1/中间结果/<base>/生成dag图/functions_ranges.json`

它的目的：为 Level-1 切段提供“每个函数在源代码中的可切范围”，避免把段边界落到函数体外（例如落在 `}` 之后）导致插桩宏出现在函数外。

#### 3.2.1 触发时机（什么时候生成）

当你运行 `mycallyplus_v1.generation.legacy` 且满足：

- 传入 `--source-file <xxx.c>` 且文件存在
- 源文件后缀为 `.c`

legacy 会在导出 `functions_full.json` / debug 文件后，额外导出 `functions_ranges.json`。

实现位置：

- `mycallyplus_v1/generation/legacy.py`（导出 `functions_ranges.json`）
- `mycallyplus_v1/core/func_ranges.py`（实际解析源代码得到范围）

#### 3.2.2 输入是什么

`functions_ranges.json` 的输入有两部分：

1) 源代码文本：`--source-file` 指向的 `.c` 文件  
2) 函数名集合：来自 legacy 解析出来的 `functions` 表（也就是 `functions_full.json` 顶层 key 集合）

注意：`functions` 表里会包含 `busy_wait_seconds@instance1` 这类实例名，以及编译器插入的 `__stack_chk_fail*` 节点名，解析时会做归一化/过滤（见下一节）。

#### 3.2.3 核心算法（源代码定位 + `{}` 配对）

实现模块：`mycallyplus_v1/core/func_ranges.py`

对每个函数名 `name`：

1) 名称归一化

- `xxx@instanceN` → `xxx`（例如 `busy_wait_seconds@instance1` 归一化为 `busy_wait_seconds`）
  - 输出仍保留原始 `name`，并额外记录 `base_name`（归一化后名称），便于与 DAG/实例对应
- `__stack_chk_fail*`：直接忽略（不纳入 ranges，也不计入 missing）

2) 定位函数定义

在“去掉注释与字符串字面量”的源码文本中查找 `base_name(` 的位置，并向后扫描：

- 若参数列表结束后遇到 `{`：判定为函数定义
- 若先遇到 `;`：判定为声明/原型（不是定义），继续找下一个匹配

3) 确定函数体结束行（`end_line`）

从 `{` 开始做 brace depth 计数（`{` +1，`}` -1），depth 回到 0 的 `}` 所在行就是函数体结束行。

4) 计算 Level-1 的安全切段范围（用于插桩）

为了避免把插桩点放在 `{`/`}` 外侧，额外计算：

- `first_stmt_line`：`{` 后第一个非空白/非 `{}` token 所在行（best-effort）
- `last_stmt_line`：函数体内最后一个 `;` 或 `}` 的行（best-effort）

最终给 Level-1 用的范围：

- `level1_start_line = first_stmt_line`（若缺失则 fallback `body_start_line`）
- `level1_end_line = last_stmt_line`（若缺失则 fallback `end_line`）

#### 3.2.4 输出字段含义

每个函数条目包括：

- `name`：functions 表中的原始名称（可能带 `@instanceN`）
- `base_name`：归一化后用于源文件查找的名称
- `start_line`：函数签名行（`base_name(` 首次出现行）
- `body_start_line`：函数体 `{` 所在行
- `first_stmt_line`：函数体内第一条语句行（best-effort）
- `end_line`：函数体匹配 `}` 所在行
- `last_stmt_line`：函数体内最后一条语句行（best-effort）
- `last_return_line`：最后一个 `return` 行（best-effort）
- `level1_start_line / level1_end_line`：Level-1 切段与插桩使用的最终范围

`missing`：只列出“functions 表里存在但源文件找不到定义”的用户函数（`@instance` 会映射到 `base_name`，编译器插入函数会忽略）。

---

## 4. Step B：Stage-1 切段（生成 segments + 段级 DAG）

### 4.1 关键输入

- `生成dag图/functions_ranges.json`：每个函数的可切范围
- `生成dag图/debug/mycalls_meta_internal.json`：create/join 的行号
- `生成dag图/functions_full.json`：create/join 的绑定关系（包含链式创建的句柄映射）

### 4.2 输出文件

目录：`mycallyplus_v1/中间结果/<base>/level1/stage1/`

- `segments_stage1.json`：段定义（段节点列表）
- `dag_stage1_seg.json`：段级 DAG（节点=段，边=intra/create/join）
- `dag_stage1_seg.dot`：段级 DAG dot

### 4.3 生成逻辑摘要

1) 对每个函数 `f`，取范围 `[level1_start_line, level1_end_line]`  
2) 仅以 `pthread_create*`、`pthread_join*` 为 cut points，按行号切分 compute 段与单行 cut 段  
3) 段级边：
- `intra`：同一函数内段顺序边
- `create`：create 段 → entry 函数第一个段
- `join`：entry 函数最后一个段 → join 段

段级 `seg_id` 命名：
- compute：`THR:<func>#<idx>@<start>-<end>`
- create：`CRT:<func>#<idx>@L<line>`
- join：`JON:<func>#<idx>@L<line>`

### 4.4 `segments_stage1.json` 是如何得到的（详细）

生成模块：`mycallyplus_v1/level1/segment_dag.py`

输入：

- `生成dag图/functions_ranges.json`（函数范围：`level1_start_line/level1_end_line`）
- `生成dag图/debug/mycalls_meta_internal.json`（create/join 行号）
- `生成dag图/functions_full.json`（create/join 绑定与链式创建句柄映射）

生成步骤（对每个函数 `f`）：

1) 取函数切段范围 `[level1_start_line, level1_end_line]`
2) 在该函数的 `mycalls_meta_internal` 中筛出 `pthread_create*`、`pthread_join*` 的 `line`
3) 按行号排序，依次切分：
   - 若 `cur <= line-1`：输出 compute 段 `[cur, line-1]`
   - 输出 cut 段 `[line, line]`（kind=create 或 join）
   - `cur = line + 1`
4) 收尾：若 `cur <= end`：输出 compute 段 `[cur, end]`

输出段字段：

- `seg_id`：段 id（节点名）
- `function`：所属函数
- `kind`：`compute/create/join`
- `start_line/end_line`：段行号区间
- `cut_node`：若为 create/join 段，记录标准 DAG 节点名（例如 `main/pthread_join21`）

### 4.5 `dag_stage1_seg.json` 是如何得到的（详细）

生成模块：`mycallyplus_v1/level1/segment_dag.py`

它以 `segments_stage1.json` 的段为节点，补三类边：

1) `intra`（函数内顺序边）
- 每个函数内 segments 按行号排序串联：`S0->S1->S2...`

2) `create`（线程创建边）
- 利用 `functions_full.json` 的 `mycalls` 结构：legacy 会把 `pthread_createX` 后紧跟线程入口函数名节点插入序列
- 将 `pthread_createX` 所在段（单行 create 段）连到入口函数的第一个段：`create_seg -> entry_first_seg`

3) `join`（线程等待边）
- 利用 `functions_full.json` 的 `myinfo`：
  - `join_node -> tid_var`（join 句柄绑定）
  - `tid_var -> entry_fn`（可能出现在 main 或链式创建线程函数中）
- 实现上扫描所有函数的 `myinfo` 建全局 `handle_to_entry_fn`，保证 `tc1/tc2/tc3/tc4` 这类链式创建也能解析
- 将入口函数的最后一个段连到 join 段：`entry_last_seg -> join_seg`

输出字段：

- `nodes`：段节点列表（seg_id）
- `edges[*]`：`{src,dst,kind}`，kind 为 `intra/create/join`

---

## 5. Step C：段级测时（独立模块）

入口：`mycallyplus_v1.level1.time_analysis_level1`

建议命令：

```bash
PYTHONPATH=. python3 -m mycallyplus_v1.level1.time_analysis_level1 \
  --base-dir mycallyplus_v1 \
  --base-name <base> \
  --source mycallyplus_v1/源文件/<proj>/<proj>.c
```

### 5.1 输出文件

目录：`mycallyplus_v1/中间结果/<base>/level1/timing/<project>/`

- `time_result_seg.json`：`seg_id -> {total_ns,count,avg_ns,min_ns,max_ns}`
- `time_analysis_level1.log`：插桩/跳过段/告警记录
- `trace/trace.<tid>.csv`：原始事件日志（每线程一个文件）

> 说明：该测时是“段内 BEGIN/END”测得的段耗时，用于后续 LPF。

---

## 6. Step D：LPF（Longest Path First）计算段优先级

入口：`mycallyplus_v1.level1.lpf_segment`

建议命令：

```bash
PYTHONPATH=. python3 -m mycallyplus_v1.level1.lpf_segment \
  --base-dir mycallyplus_v1 \
  --base-name <base> \
  --project <project> \
  --prio-max 80
```

### 6.1 权重口径

- `create/join` 段：权重 = 0（避免 join 等待时间影响优先级推导）
- compute 段：权重 = `time_result_seg.json[seg_id].total_ns`

### 6.2 汇点（Sink）

以 `main` 的最后一个段作为汇点（你确认的口径）。

### 6.3 输出文件

目录：`mycallyplus_v1/中间结果/<base>/level1/schedule/lpf_segment/`

- `schedule_seg.json`：`seg_id -> priority`

---

## 7. Step E：优先级插桩 + 对照实验对比（baseline vs prio）

入口：`mycallyplus_v1.level1.instrument_prio_level1`

建议命令：

```bash
PYTHONPATH=. python3 -m mycallyplus_v1.level1.instrument_prio_level1 \
  --base-dir mycallyplus_v1 \
  --base-name <base> \
  --source mycallyplus_v1/源文件/<proj>/<proj>.c
```

### 7.1 对照实验约束（你确认的口径）

- **baseline**：源代码保持一致（不插入段优先级切换），仅通过 `--wrap=main` 输出程序总时间
- **prio**：在源代码副本内对每个 compute 段起始行插入一次 `pthread_setschedparam(SCHED_FIFO, prio)`（权重为 0 的段不插入）
- 输出总时间：`stderr` 打印一行 `PROGRAM_TOTAL_NS=...`

### 7.2 程序总时间测量（不改源代码）

通过链接参数与 wrapper：

- `wrap_main.c`：`__wrap_main()` 调用 `PROG_BEGIN()` 后转调 `__real_main()`
- `prog_timer.c`：`PROG_BEGIN()` 注册 `atexit(PROG_END)`，退出时打印 `PROGRAM_TOTAL_NS=...`

### 7.3 输出文件

目录：`mycallyplus_v1/中间结果/<base>/level1/experiments/lpf_segment_<timestamp>/<project>/`

- `baseline/project/...`：对照组工程副本（源代码不改）
- `prio/project/...`：实验组工程副本（插入优先级切换）
- `compare.json`：对比结果（baseline_total_ns/prio_total_ns/delta）

---

## 8. 一键跑到底（GUI）

GUI：时间分析区子功能 `段级时间分析（Level-1）`

输入来自状态区：
- 源文件 `.c`
- expand 文件 `.expand`

一键流水线（固定顺序）：

`legacy生成(带--source-file) -> level1 stage1 -> 段级测时 -> LPF段优先级 -> 优先级插桩对比`

默认展示：段级 DAG 的 png 图（`level1/stage1/dag_stage1_seg.png`）。

---

## 9. 常见问题（阶段 1 已知限制）

1) 段不嵌套：runtime 使用 TLS 单槽（后续阶段需扩展为栈）
2) 多行语句（create/join 跨多行）暂不处理
3) 控制语句行插桩：无法安全插入时会跳过并记录 warning
4) SCHED_FIFO 权限：无 root/CAP_SYS_NICE 时可能 EPERM，GUI 会弹窗提示
