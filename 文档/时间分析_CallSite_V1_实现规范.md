
# 📘 MyCallyPlus 时间分析（Call‑Site Instrumentation）实现规范 · V1

> 依据用户确认：  
> 1) 结束计时紧跟调用语句的下一行（无空行）；  
> 2) **逐调用点统计**（不做按函数名合并）；  
> 3) 编译失败即中断并报错（严格模式）；  
> 4) 复杂表达式中的调用 **一律跳过**；  
> 5) 生成 **JSON** 结果文件。

本规范用于驱动 Codex 生成完整的“按 **函数调用点** 插桩”的时间分析工具。V1 不使用 AST，仅做文本级语句边界判定；不处理递归/宏内联/复杂表达式包裹。

---

## 0. 目标与范围

- **目标**：依据 `mycalls_meta_internal.json` 中的 `(file, line, func)` 定位到 **函数调用语句**，在调用语句 **前一行** 和 **该语句结束后的下一行** 插入计时代码，统计 **该调用点** 的耗时。
- **范围**：C 语言源代码（`.c`）。头文件插桩不在 V1 范围。多线程运行下统计同样有效（运行时代码已加锁）。
- **不做**：递归正确性、内联函数、宏展开语义保持、复杂表达式内的调用（赋值、条件、return/for/while/switch 三目等）。

---

## 1. 输入 / 输出

### 1.1 输入：`mycalls_meta_internal.json`

示例：
```json
{
  "threadtask2/ludcmp17": { "file": "main.c", "line": 53, "col": 5, "extern": 0, "func": "ludcmp" },
  "threadtask2/free15":   { "file": "main.c", "line": 51, "col": 5, "extern": 0, "func": "free"  }
}
```

必需字段：
- `file`: 源文件名或相对路径（以项目根为基准）。
- `line`: 调用 **起始行**（1-based）。
- `func`: 被调用函数名（用于键名与可读性）。
- `col`: 可忽略；若存在，可用于 disambiguate，但 V1 不强制依赖。

### 1.2 输出：目录结构（建议）

```
instrumented_build/
  <project files after instrumentation>
  time_stat.c
  time_stat.h
  app                    # 编译生成
  time_result.json       # 统计结果（最终产物）
```

### 1.3 输出：`time_result.json` 结构

逐调用点键名：`"<func>@<basename>:<line>"`  
示例：
```json
{
  "ludcmp@main.c:53": { "total_ns": 123456789, "count": 3, "avg_ns": 41152263, "max_ns": 50000000, "min_ns": 30000000 },
  "free@main.c:51":   { "total_ns": 10000,     "count": 1, "avg_ns": 10000,    "max_ns": 10000,   "min_ns": 10000   }
}
```
- **不做函数级聚合**；保持每个调用点独立。

---

## 2. 插桩语义与文本模板

### 2.1 插入位置（严格约定）
- **BEGIN**：插在 **调用语句的起始行** 之前一行。
- **END**：插在 **调用语句结束行的下一行**（无空行）。
- 跨行调用时，必须通过括号深度 + `;` 定位该语句的 **真正结束行**。

### 2.2 生成文本

设：
- `file` = `main.c`，`line` = `53`，`func` = `ludcmp`
- `key_str` = `"ludcmp@main.c:53"`
- 变量名：`__ta_t0_main_c_53_<seq>`（`<seq>` 为同文件内递增序号，避免同一行多次插入冲突）

**BEGIN 段：**
```c
// TA_BEGIN: main.c:53 ludcmp
uint64_t __ta_t0_main_c_53_1 = now_ns();
```

**END 段：**
```c
// TA_END: main.c:53 ludcmp
time_account("ludcmp@main.c:53", now_ns() - __ta_t0_main_c_53_1);
```

**文件级 include（若未包含过）：**
```c
#include "time_stat.h"  // TA_INCLUDE
```

### 2.3 Idempotency（避免重复插桩）
- 若目标文件相应位置附近已存在 `// TA_BEGIN:` / `// TA_END:` 标记，视为已插桩，**跳过**。
- 文件顶部若已存在 `// TA_INCLUDE`，则不再重复插入 include。

---

## 3. 调用语句边界判定（无 AST）

### 3.1 求语句结束行 `stmt_end_line`
- 从 `i0 = line - 1`（0-based）开始扫描到 EOF：
  - 维护 `depth`：遇 `(` → `depth++`；遇 `)` → `depth--`；
  - 当读到 `';'` 且 `depth == 0`，记当前行为 `stmt_end_line`，**终止**。

> **注意**：这样可以正确处理实参换行、嵌套括号等常见跨行调用。

### 3.2 V1 复杂表达式过滤（**一律跳过**）
若 `i0..stmt_end_line` 范围内满足任一：
- 以 `if|while|for|switch|return` 开头（忽略前导空白）。
- 存在明显的赋值痕迹：`=` 出现在分号前，且不在字符串/字符字面量内（可做简化处理）。
- 存在三目 `?`。

则：**跳过该调用点，记录 warning**（但构建继续）。

---

## 4. 运行时支持库（必须自动拷贝）

### 4.1 `time_stat.h`
```c
#ifndef TIME_STAT_H
#define TIME_STAT_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

uint64_t now_ns(void);
void time_account(const char* key, uint64_t dur_ns);

#ifdef __cplusplus
}
#endif

#endif
```

### 4.2 `time_stat.c`
```c
#define _GNU_SOURCE
#include "time_stat.h"
#include <time.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

typedef struct {
    char key[160];
    unsigned long long total_ns;
    unsigned long long count;
    unsigned long long max_ns;
    unsigned long long min_ns;
} stat_item;

static stat_item *g_stats = NULL;
static size_t g_cap = 0, g_sz = 0;
static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;
static int g_dumped = 0;

static void ensure_cap(void) {
    if (g_sz < g_cap) return;
    size_t nc = g_cap ? g_cap * 2 : 256;
    stat_item *np = (stat_item*)realloc(g_stats, nc * sizeof(stat_item));
    if (!np) exit(2);
    for (size_t i = g_cap; i < nc; ++i) {
        np[i].key[0] = 0;
        np[i].total_ns = np[i].count = np[i].max_ns = 0;
        np[i].min_ns = ~0ull;
    }
    g_stats = np; g_cap = nc;
}

uint64_t now_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;
}

static stat_item* get_slot(const char* key) {
    for (size_t i = 0; i < g_sz; ++i) {
        if (strcmp(g_stats[i].key, key) == 0) return &g_stats[i];
    }
    ensure_cap();
    strncpy(g_stats[g_sz].key, key, sizeof(g_stats[g_sz].key) - 1);
    g_stats[g_sz].key[sizeof(g_stats[g_sz].key) - 1] = 0;
    g_stats[g_sz].total_ns = 0;
    g_stats[g_sz].count = 0;
    g_stats[g_sz].max_ns = 0;
    g_stats[g_sz].min_ns = ~0ull;
    return &g_stats[g_sz++];
}

void time_account(const char* key, uint64_t dur_ns) {
    pthread_mutex_lock(&g_mu);
    stat_item* s = get_slot(key);
    s->total_ns += dur_ns;
    s->count += 1;
    if (dur_ns > s->max_ns) s->max_ns = dur_ns;
    if (dur_ns < s->min_ns) s->min_ns = dur_ns;
    pthread_mutex_unlock(&g_mu);
}

static void dump_json(void) {
    if (g_dumped) return;
    g_dumped = 1;
    FILE *fp = fopen("time_result.json", "w");
    if (!fp) return;
    fprintf(fp, "{\n");
    for (size_t i = 0; i < g_sz; ++i) {
        unsigned long long avg = g_stats[i].count ? (g_stats[i].total_ns / g_stats[i].count) : 0ull;
        fprintf(fp,
            "  \"%s\": {\"total_ns\": %llu, \"count\": %llu, \"avg_ns\": %llu, \"max_ns\": %llu, \"min_ns\": %llu}%s\n",
            g_stats[i].key,
            g_stats[i].total_ns,
            g_stats[i].count,
            avg,
            g_stats[i].max_ns,
            (g_stats[i].min_ns == ~0ull ? 0ull : g_stats[i].min_ns),
            (i + 1 == g_sz) ? "" : ","
        );
    }
    fprintf(fp, "}\n");
    fclose(fp);
}

__attribute__((destructor))
static void at_exit_dump(void) { dump_json(); }
```

- 生成文件：工作目录下 `time_result.json`（工具应在 `instrumented_build/` 下运行）
- 线程安全：使用 `pthread_mutex`
- 复杂度：O(#call‑sites)

---

## 5. 插桩器算法（Codex 必须实现）

以 Python 为实现语言（建议），核心步骤：

1. **读取 JSON**：解析为列表 `[ {file, line, func, key}, ... ]`，其中 `key = f"{func}@{basename}:{line}"`。
2. **按文件分组**：`{ file: [records...] }`。
3. **对每个文件**：
   - 读取源文件为 `lines`；
   - 若未 `#include "time_stat.h"  // TA_INCLUDE`，则在 **首个非空/非注释** 行前插入；
   - 将该文件的记录按 `line` **降序** 排序；
   - 逐条处理：
     - `i0 = line - 1`；若 `TA_BEGIN`/`TA_END` 附近存在，**跳过**；
     - 自 `i0` 起用 **括号深度 + 分号** 策略求 `stmt_end_line`；若未找到，**警告并跳过**；
     - 做 **复杂表达式过滤**（if/while/for/switch/return 开头；存在 `=`；存在 `?`）；若命中，**警告并跳过**；
     - 生成唯一变量名 `__ta_t0_<sanitized_basename>_<line>_<seq>`；
     - 在 `i0` 之前 `insert(BEGIN)`；在 `stmt_end_line + 2` 处 `insert(END)`（注意前一次插入引起的下标偏移）；
   - 将修改后的内容写入 `instrumented_build/<same path>`。
4. **复制运行时库**：`time_stat.c/h` 到 `instrumented_build/`。
5. **编译**（严格模式）：
   - `gcc -O2 -std=c11 -pthread *.c -o app`（必要时加入项目其余 .c）。
   - 任意编译失败 → **中断并报错**（退出码非零）。
6. **运行**：在 `instrumented_build/` 下执行 `./app`，生成 `time_result.json`；如进程退出码非零 → 报错并中止。
7. **结束**：打印 `time_result.json` 路径。

### 5.1 重要实现细节
- **行号漂移**：同一文件需按 **行号降序** 插入，避免前面插入影响后续位置。
- **字符串/字符字面量**：复杂表达式检测时的 `=`/`?` 判断可做最小化：粗略忽略字符串/字符常量（例如先删除引号中的内容）；以降低误报。
- **文件路径**：`basename = os.path.basename(file)` 用于 `key`；插入标签使用原始 `file:line` 便于读者映射。

---

## 6. 错误处理与日志

- **编译失败**：立即中止；输出失败命令、编译器返回码与 stderr 的前 200 行。
- **未找到语句结束**：warning（记录：file, line, func），继续处理其它调用点。
- **复杂表达式**：warning（记录：file, line, func, reason），继续处理其它调用点。
- **重复插桩**：info（记录：file, line, func）。
- **成功统计**：info（插桩点数量、生成的 app 路径、time_result.json 路径）。

---

## 7. 自检清单（交付前的快速测试）

1. **单行调用**：`foo();` → 插桩在前后各一行。
2. **跨行调用**：参数多行换行 → 正确定界至分号。  
3. **同一行多语句**：`a(); b();` → JSON 有两条记录时，能分别插入且不冲突。
4. **复杂表达式**：`x = foo(); if (bar()) {}` → 被跳过且有 warning。
5. **重复执行插桩器**：不重复插入（靠 `TA_BEGIN/END` & `TA_INCLUDE` 标记）。
6. **生成 JSON**：`time_result.json` 字段完整，avg = total/count。

---

## 8. 编译与运行命令（示例）

在 `instrumented_build/`：
```bash
gcc -O2 -std=c11 -pthread *.c -o app
./app
# 生成 instrumented_build/time_result.json
```

如原项目需要其它 `.c` 文件参与编译，工具应允许通过参数或从原目录收集统一拷贝/编译。

---

## 9. 示例（用户给出的片段）

原始：
```c
printf("task6结束\n");
pthread_join(thread2, NULL);
pthread_join(thread3, NULL);
free(task_arg1);
free(task_arg2);
ludcmp(arg);                // line = 53
printf("task7结束\n");
```

插桩后（仅对 `ludcmp@main.c:53`）：
```c
printf("task6结束\n");
pthread_join(thread2, NULL);
pthread_join(thread3, NULL);
free(task_arg1);
free(task_arg2);

// TA_BEGIN: main.c:53 ludcmp
uint64_t __ta_t0_main_c_53_1 = now_ns();

ludcmp(arg);

// TA_END: main.c:53 ludcmp
time_account("ludcmp@main.c:53", now_ns() - __ta_t0_main_c_53_1);

printf("task7结束\n");
```

---

> **交付要求**：Codex 按本规范输出：  
> 1) 插桩器（Python，含 CLI）；  
> 2) `time_stat.c/h`；  
> 3) 自动编译/运行流程；  
> 4) `time_result.json` 生成；  
> 5) 日志与错误处理；  
> 6) 自检用最小示例。
