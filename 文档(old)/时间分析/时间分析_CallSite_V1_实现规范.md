
# MyCallyPlus 时间分析机制说明（最新）

本文聚合了时间分析相关的实现规则与使用方式，仅保留一份文档，便于维护。

## 1. 目标与范围
- 基于 `mycalls_meta_internal.json` 中的调用点信息，对 C 源代码逐调用点插桩计时。
- 支持条件内调用：`if/while/for` 条件里的函数会被就地包裹计时，保持原有布尔语义。
- 仅限 `.c` 文件；当前不处理头文件插桩。

## 2. 输入与输出
- 输入：`mycalls_meta_internal.json`，键为调用点唯一名（如 `threadtask2/pthread_create5`），字段含 `file/line/col/extern`。
- 插桩产物：`中间结果/<basename>/时间分析/<项目>/` 内的修改后源码、`time_stat.c/h`、可执行 `app`。
- 结果：
  - `time_result.json`：按调用点键统计 `total_ns/count/avg_ns/max_ns/min_ns`（单位均为纳秒 ns）。
  - `mycalls_meta_internal.json` 回写计时字段：`miss`（计时失败标记）、`executed`（运行是否触达）、`skip_reason`。
  - `thread_time_summary.json`：按顶层键（线程/任务入口）汇总 `miss=false` 的 `total_ns/count`。

## 3. 插桩规则
- 定位：按 JSON 中的 `file/line` 找到语句结束（括号深度 + 分号）。
- 条件内调用：将调用替换为 GNU 语句表达式包裹，示例：
  ```c
  if ((__extension__({ uint64_t t = now_ns();
    __auto_type r = pthread_create(...);
    time_account("threadtask2/pthread_create5", now_ns() - t);
    r;
  })) != 0) { ... }
  ```
  结果保持原返回值，计时必执行。
- 普通调用：在语句前插入 `TA_BEGIN`，后插入 `TA_END` 记录耗时；变量名基于调用点键生成安全标识。
- 去重：若同一调用点已存在 `TA_BEGIN` 标记则跳过。
- 自动补充 `#include "time_stat.h"  // TA_INCLUDE`。

## 4. 运行与回写
- 自动拷贝 `time_stat.c/h`，编译为 `app`（`gcc -O2 -std=c11 -pthread -I. -Iinclude`），运行后生成 `time_result.json`。
- 回写规则：
  - 找到匹配键（优先 JSON 原键，兼容 `func@file:line`），写入计时字段（单位 ns），`miss=false`，`executed=true`。
  - 插桩但未执行：`miss=true`，`executed=false`，计时字段为 0。
  - 未插桩（文件缺失/非 C 等）：`miss=true`，`executed=false`，`skip_reason=not_instrumented`。
- 线程汇总：按顶层键聚合 `miss=false` 的 `total_ns/count`，输出 `thread_time_summary.json`。

## 5. 时间统计库（time_stat）
- 提供 `now_ns()`（CLOCK_MONOTONIC 纳秒）与 `time_account(key, dur_ns)`。
- 内部用 `pthread_mutex` 保护，进程退出时自动生成 `time_result.json`。

## 6. 开发/调试提示
- 插桩按行号降序执行，避免前插导致行偏移。
- 条件内包裹使用 GNU 语句表达式；若需纯 C11，可改用临时变量重写条件。
- 如需细化 `skip_reason`，可在插桩阶段对未插入的调用点设置原因（例如定位失败）。

---

## 7. 本次会话的落地成果（实现清单）

对应实现主要在：
- 插桩与运行：`mycallyplus/time_analysis.py`
- GUI 入口：`mycallyplus/ui/gui.py`

已实现的功能点：
- **GUI 按钮：时间分析**
  - GUI 左侧新增“7. 时间分析”，点击后出现 2 个子按钮：选中源代码文件、选中 JSON 文件（`mycalls_meta_internal.json`）。
  - 两个文件都选中后自动执行：复制工程→插桩→编译→运行→回写 JSON→生成线程汇总→写日志。
- **输出目录规范（覆盖模式）**
  - 插桩工程输出到：`mycallyplus/中间结果/<basename>/时间分析/<project>/`（自动覆盖旧输出）。
  - 运行生成：`time_result.json`（单位 ns）。
  - 回写到：原始 `mycalls_meta_internal.json`（与 `extern` 平级增加计时字段）。
  - 线程汇总输出到：与 `mycalls_meta_internal.json` 同目录下的 `thread_time_summary.json`。
  - 日志输出到：`mycallyplus/中间结果/<basename>/生成dag图/debug/time_analysis.log`（失败也会落盘）。
- **逐调用点统计（不按函数名合并）**
  - 统计 key 与变量命名均基于 JSON 的调用点键名（例如 `threadtask2/pthread_create5`），确保同名函数不同调用点分别统计。
- **条件内调用的插桩（不改变判断语义）**
  - 对 `if/while/for` 的“条件括号内”调用：用 GNU 语句表达式 `__extension__({ ... })` 包裹，返回原返回值并保证只求值一次。
  - 对控制语句同一行但在条件括号外的独立语句（如 `perror(...)`）：使用 `do { ...; CALL; ... } while (0);` 包裹，兼容 `void` 返回。
- **线程耗时汇总**
  - 只按 `mycalls_meta_internal.json` 的顶层键（线程/任务入口）汇总，统计口径：仅累计 `miss=false` 的 `total_ns/count`。
- **辅助功能：生成 expand 文件**
  - GUI 在“选择 expand 文件”附近新增“生成 expand 文件”按钮：根据状态区源文件调用 gcc 生成 `.expand` 并存入 `配置文件/<源文件名>/`，自动覆盖并更新状态区。

---

## 8. 实现原理（C 插桩核心算法）

### 8.1 输入结构（mycalls_meta_internal.json）
- JSON 为多层结构（顶层常为线程/函数入口，如 `main`、`threadtask1` 等）。
- 叶子节点为调用点：键名形如 `threadtask2/pthread_create5`，字段含 `file/line/col/extern`，并会被回写计时字段。

### 8.2 插桩定位
- 对每个调用点，按 `file/line` 在源码中定位起始行。
- 以“括号深度 + 分号”扫描确定语句结束行：
  - 从 `line-1` 开始向下扫描；
  - 遇到 `(` 深度 +1，遇到 `)` 深度 -1；
  - 当读到 `;` 且深度为 0，认为语句结束。

### 8.3 插桩模板
- 普通语句调用：在语句前插入：
  - `// TA_BEGIN: <file>:<line> <func>`
  - `; /* TA_PAD */`（保证是合法语句，避免 case/label 附近声明报错）
  - `uint64_t <var> = now_ns();`
- 在语句后插入：
  - `// TA_END: ...`
  - `time_account("<json_key>", now_ns() - <var>);`
- 条件括号内调用：将 `func(...)` 替换为：
  - `(__extension__({ uint64_t t=now_ns(); __auto_type r=func(...); time_account(key, now_ns()-t); r; }))`
- 控制语句同一行、条件括号外的独立语句：替换为：
  - `do { uint64_t t=now_ns(); func(...); time_account(key, now_ns()-t); } while (0);`

### 8.4 去重与安全过滤
- 去重：若附近已存在 `TA_BEGIN: <file>:<line> <func>`，视为该调用点已插桩，跳过。
- 跳过编译器内部符号（避免跨函数边界破坏源码）：`__stack_chk*`、`__builtin_*`。

---

## 9. 编译/运行与回写逻辑

### 9.1 工程拷贝与覆盖
- 复制源文件所在目录到 `中间结果/<basename>/时间分析/<project>/`，用于“可重复、可覆盖”的插桩构建。

### 9.2 include 插入规则（_GNU_SOURCE 兼容）
- 若源码顶部有 `_GNU_SOURCE/_DEFAULT_SOURCE/...` 这类特性宏，`time_stat.h` 会插在这些宏之后、其他系统头之前，避免出现 `CPU_ZERO/CPU_SET` 等宏失效导致链接错误。

### 9.3 编译与运行
- 编译命令：`gcc -O2 -std=c11 -pthread -I. -Iinclude -o app <all .c> -lm -ldl`
- 运行：`./app`，进程退出时由 `time_stat.c` 的 destructor 自动落盘 `time_result.json`。

### 9.4 回写字段定义（当前版本）
- `total_ns/count/avg_ns/max_ns/min_ns`：单位 ns。
- `miss`：
  - 找到统计条目 → `miss=false`
  - 未找到统计条目 → `miss=true`
- `executed`：
  - 找到统计条目 → `executed=true`
  - 未找到统计条目 → `executed=false`
- `skip_reason`：
  - 未插桩（例如文件缺失/非 C）→ `not_instrumented`
  - 已插桩但未执行 → 空字符串（可按需进一步细分）

---

## 10. 已知限制与后续方向
- 目前 `time_analysis` 仅对 `.c` 插桩与自动编译运行；`.cpp` 会被跳过并在日志中提示。
- 复杂表达式/宏/模板等场景仍可能定位不准；建议逐步引入更强的定位策略（例如 AST/clang）或增加 `skip_reason` 细分规则。
