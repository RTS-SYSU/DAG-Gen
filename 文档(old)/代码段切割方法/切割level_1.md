下面给你一份**可以直接交给 Codex 开工**的 Level-1 实现方案。目标很明确：**完全基于 JSON 行号切段，create/join 每一个都是独立段，段作为 DAG 节点，边只表示依赖**。我会把目录结构、数据格式、算法、插桩改写、日志格式、DAG 构建与校验、以及你在示例程序上的落地细节都写清楚。

> 说明：你之前上传的部分文件提示“已过期”，但这不影响我给出完整方案。Codex 在实现时只需要你本地的 `cpu4_thread10_fifo.c` 和对应 JSON。

---

# Level-1 实现方案（JSON 驱动切段 + 插桩 + Node-weighted DAG）

## 0. 输入输出与不变量

### 输入文件

1. `src.c`：原始 C 源码，例如 `cpu4_thread10_fifo.c`
2. `functions_full.json`：函数范围（至少包含 start/end 行号）
3. `call_src_full.json`：调用点列表（至少包含 pthread_create/join 的行号与所在函数）
4. 可选：`dag.dot`（已有的函数级/线程级 DAG，可作为参考校验，不是必须）

### 输出文件

1. `src_inst.c`：插桩后的源码
2. `segments.json`：切段结果（每段行区间、类型、插桩策略）
3. `dag_seg.json`：Segment 级 DAG（node 列表 + edge 列表 + 权重）
4. `trace.csv`：运行时测得的段耗时日志
5. `report.json`：可选，汇总统计（每段均值/方差、每线程总时间、等待时间等）

### 必须满足的不变量（写进代码断言）

* 每个 `pthread_create` 是一个独立 Segment（start_line=end_line=该调用行）
* 每个 `pthread_join` 是一个独立 Segment
* Segment 之间在同一线程（同一函数）内按行号顺序串联
* DAG 节点 = Segment；节点权重来自插桩测得 duration
* DAG 边只表示依赖，不带时间

---

## 1. 目录结构建议（Codex 直接照建）

```
scratchdag_level1/
  inputs/
    cpu4_thread10_fifo.c
    functions_full.json
    call_src_full.json
  build/
  out/
  tools/
    gen_segments.py
    instrument_c.py
    run_and_collect.sh
    build_dag.py
    analyze_trace.py
  include/
    segtrace.h
```

---

## 2. JSON 格式要求（最低可用字段）

### 2.1 functions_full.json（函数边界）

必须能拿到函数名和行号区间：

```json
{
  "functions": [
    {"name": "main", "start": 377, "end": 433},
    {"name": "c0_fn", "start": 155, "end": 170}
  ]
}
```

### 2.2 call_src_full.json（cut points）

必须能拿到：callee、行号、所在函数（或至少能映射到函数区间）

```json
{
  "calls": [
    {"callee": "pthread_create", "line": 169, "function": "c0_fn"},
    {"callee": "pthread_join", "line": 409, "function": "main"}
  ]
}
```

如果你当前 JSON 字段名不同，让 Codex 做一个适配层 `normalize_json()` 统一成上面字段。

---

## 3. Level-1 切段：从 JSON 生成 segments.json（核心）

### 3.1 Segment 数据结构（建议）

```json
{
  "segments": [
    {
      "seg_id": "main_S000",
      "function": "main",
      "start_line": 377,
      "end_line": 395,
      "kind": "compute",
      "begin_insert": {"line": 377, "pos": "before"},
      "end_insert": {"line": 395, "pos": "after"}
    },
    {
      "seg_id": "main_S001_join_409",
      "function": "main",
      "start_line": 409,
      "end_line": 409,
      "kind": "join",
      "callee": "pthread_join",
      "begin_insert": {"line": 409, "pos": "before"},
      "end_insert": {"line": 409, "pos": "after"}
    }
  ]
}
```

### 3.2 切段规则（必须严格实现）

对每个函数 `f`：

* 已知函数区间 `[F.start, F.end]`
* 找到该函数内所有 cut points 行号集合：

  * `CreateLines = {l | callee==pthread_create}`
  * `JoinLines = {l | callee==pthread_join}`
  * `CutLines = sort(CreateLines ∪ JoinLines)`

生成 Segment：

1. 在函数入口处设 `cur = F.start`
2. 依次遍历 cut line `l`：

   * 若 `cur <= l-1`：输出 compute 段 `[cur, l-1]`
   * 输出 cut 段 `[l, l]`，kind = create/join（由 callee 判定）
   * 设 `cur = l+1`
3. 遍历结束后：

   * 若 `cur <= F.end`：输出 compute 段 `[cur, F.end]`

### 3.3 关键边界处理（必须做）

* 如果 cut line 恰好是函数第一行：compute 段为空，跳过
* 如果两个 cut line 相邻（l_i+1 == l_{i+1}）：中间 compute 段为空，跳过
* 同一行出现多个 cut（极少，但要防御）：同一行只允许一个 cut 段；若多个，按出现顺序编号成 `line#k`，但你这个 demo 不会发生

### 3.4 seg_id 命名规则（固定，保证可追溯）

建议：

* compute：`{func}_S{idx:03d}_C_{start}_{end}`
* create：`{func}_S{idx:03d}_CREATE_{line}`
* join：`{func}_S{idx:03d}_JOIN_{line}`

这样 trace 中一眼能看懂。

---

## 4. 插桩：基于 segments.json 改写 C 文件生成 src_inst.c

你已经想走“纯文本插入”，可以做到稳定可复现。做法如下：

### 4.1 插桩宏与日志实现（include/segtrace.h）

要求：

* 低开销
* 线程安全
* 不依赖复杂库
* 输出 CSV 行：timestamp_ns, tid, seg_id, event(B/E), duration_ns(仅E)

建议实现：

* 用 `clock_gettime(CLOCK_MONOTONIC_RAW, ...)` 或 `CLOCK_MONOTONIC`
* tid：

  * `syscall(SYS_gettid)` 更好（Linux）
  * 或 `pthread_self()` 也行（但不可读性略差）
* 用 thread-local 存 begin time：`__thread uint64_t seg_t0[SEG_MAX]` 不现实

  * 更简单：BEGIN 时把 t0 写到一个 TLS map：`static __thread uint64_t current_t0; static __thread const char* current_seg;`
  * 但你一个线程可能嵌套段吗？**不会**（你段不嵌套，只顺序），所以 TLS 单槽足够
* 写文件：

  * 为避免锁开销：每线程一个文件 `trace.<tid>.csv`（最稳）
  * 或用 `fprintf` 到同一文件加 mutex（实现简单但扰动更大）

我建议：**每线程一个 trace 文件**，最后再合并。

### 4.2 SEG_BEGIN/SEG_END 的具体展开

在 C 源码中插入的内容建议是：

```c
SEG_BEGIN("main_S001_JOIN_409");
pthread_join(tc0, NULL);
SEG_END("main_S001_JOIN_409");
```

段 ID 用字符串最简单，不用维护整数映射表。

### 4.3 插入点规则（必须严格）

* `begin_insert` 的 `pos=="before"`：在该行文本之前插入一行 `SEG_BEGIN(...)`
* `end_insert` 的 `pos=="after"`：在该行文本之后插入一行 `SEG_END(...)`

### 4.4 instrument_c.py 的实现要求

输入：

* 原始 C 文件
* segments.json

输出：

* 插桩 C 文件

算法（关键点）：

1. 读源文件为 `lines[1..N]`（保留原始换行）
2. 构建两个字典：

   * `insert_before[line] = list_of_begin_macros`
   * `insert_after[line] = list_of_end_macros`
3. 遍历 segments：

   * before at start_line：追加 `SEG_BEGIN("id");`
   * after at end_line：追加 `SEG_END("id");`
4. 生成新文件：

   * for line_no in 1..N:

     * if insert_before[line_no]: 输出它们（按 seg_id 排序，保证确定性）
     * 输出原始行
     * if insert_after[line_no]: 输出它们
5. 额外安全检查：

   * 同一行 after 的 SEG_END 必须在 before 的 SEG_BEGIN 之后输出（你是逐行写，天然满足）
   * 断言：每个 seg_id 必须插入了 exactly 1 个 BEGIN 和 1 个 END

---

## 5. Segment 级 DAG 构建（build_dag.py）

你现在的 DAG 要做两类边：

### 5.1 intra-thread 顺序边（必做）

对每个函数 `f` 的 segment 列表按 start_line 升序：

```
S0 -> S1 -> S2 -> ...
```

这保证“一个线程内顺序”。

### 5.2 create/join 语义边（必做）

这一步需要从 JSON 里得到“create 创建了哪个线程入口函数”与“join 等待的是哪个线程”。

在你这个示例程序里，这通常可以从代码模式解析出来：

* `pthread_create(&tid, ..., <entry_fn>, ...)`
* `pthread_join(tid, ...)`

如果你的 call_src_full.json 已经提取了：

* create 的第三参数（entry function name）
* create 的 tid 变量名（第一个参数里 &tid）
* join 的 tid 变量名

那就能完全 JSON 驱动地建边：

#### create 边

`CREATE_seg(line l in function f)` → `ENTRY_compute_seg(of entry_fn)`
ENTRY 段指 entry_fn 中 start_line 开始的第一个 segment（通常是 compute 段或第一个 cut 段前）

#### join 边

`EXIT_last_seg(of joined thread entry_fn)` → `JOIN_seg(line l in main)`
EXIT_last_seg 指该线程函数的最后一个 segment（通常 end_line 到 return）

> 若 JSON 暂时没有 tid->entry_fn 的映射，你可以先只做 intra-thread 边，依然能跑“线程内段”分析；但要做真正跨线程关键路径，create/join 边最终必须补齐。

---

## 6. 运行与日志汇总

### 6.1 编译运行脚本 run_and_collect.sh

要求：

* 编译插桩后的源码
* 运行多次（例如 30 次）
* 收集 trace 文件到 out/trace_run_k/

建议：

* `-O2` 保持一致
* 关闭多余打印（避免扰动）
* 固定 CPU 亲和性（你已经做了）

### 6.2 analyze_trace.py

输入：

* trace 文件（多线程多文件）
* segments.json
  输出：
* 每个 seg_id：

  * mean duration
  * median
  * stddev
  * p90/p99（可选）
* 每个线程总 compute 时间、总 wait 时间
* main 的各 join 段等待时间排行

然后把 mean duration 写回 `dag_seg.json`，形成 node weight。

---

## 7. 验收标准（Codex 做完你怎么判定它对不对）

### 必须通过的硬检查

1. `segments.json` 中：

   * 每个 pthread_create 行对应一个 kind=create、区间 [l,l] 的 segment
   * 每个 pthread_join 行对应一个 kind=join、区间 [l,l] 的 segment
2. `src_inst.c` 中：

   * 每个 seg_id 恰好出现一次 `SEG_BEGIN("id")` 与一次 `SEG_END("id")`
   * create/join 行被两侧包住
3. trace 中：

   * 每个 seg_id 在每次运行都有配对的 B/E 记录
   * duration 非负，且 join 段明显大于 create 段（常见情况）
4. DAG 中：

   * 节点数 == segments 数
   * intra-thread 边数 == 每线程 segment 数-1 的总和
   * 无环（拓扑排序可通过）

### “正确性直觉”检查（很重要）

* main 的 join 段时间总和 ≈ makespan（近似，取决于程序结构）
* worker 的 compute 段时间稳定
* FIFO vs LPF：join 段的分布发生变化（这是你要的收益证据）

--- 

## 8. 交给 Codex 的工作清单（可以直接复制粘贴）

你把下面这一段作为任务说明给 Codex：

1. 在 `scratchdag_level1/` 创建上述目录结构。
2. 实现 `tools/gen_segments.py`：读取 `inputs/functions_full.json` 与 `inputs/call_src_full.json`，按 Level-1 规则生成 `out/segments.json`。要求每个 pthread_create/pthread_join 行各自生成一个独立 segment，区间 [line,line]。
3. 实现 `include/segtrace.h`：提供 `SEG_BEGIN(id)` 与 `SEG_END(id)` 宏，使用 `clock_gettime(CLOCK_MONOTONIC[_RAW])` 记录纳秒时间戳。每线程输出一个 `trace.<tid>.csv` 到 `out/trace/`，记录字段：run_id, tid, seg_id, begin_ns, end_ns, duration_ns。段不嵌套，允许用 TLS 单槽保存当前段 t0。
4. 实现 `tools/instrument_c.py`：读取 `inputs/cpu4_thread10_fifo.c` 和 `out/segments.json`，按 begin=before start_line、end=after end_line 的规则插入宏，生成 `out/cpu4_thread10_fifo_inst.c`。必须保证每个 seg_id 插入一对 BEGIN/END。
5. 提供 `tools/run_and_collect.sh`：编译插桩程序并运行多次，把 trace 文件收集到 `out/trace_run_k/`。
6. 实现 `tools/analyze_trace.py`：合并多线程 trace，输出每个 seg_id 的 mean/median/std，输出 main 的 join 段等待时间排行，保存 `out/trace_summary.json`。
7. 实现 `tools/build_dag.py`：基于 `segments.json` 生成 Segment DAG 的节点与 intra-thread 边，输出 `out/dag_seg.json`（node-weighted, edge-unweighted）。create/join 语义边如果 JSON 中缺信息可暂时不做，但要预留接口。
8. 写一个 `README.md`：说明如何运行 gen_segments、instrument、build、run、analyze，并给出期望输出示例。

---

如果你愿意把 **functions_full.json 与 call_src_full.json 的字段结构贴一小段**（不用全贴，截取前 30 行就行），我还能把上面“JSON 规范化”部分进一步写死成可直接跑的解析逻辑，避免 Codex 因字段名不一致走偏。
