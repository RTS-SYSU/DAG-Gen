# Mycallyplus 功能实现与输入输出说明（完整指南）

适用版本：v1.0（2025-10-27）

本指南面向希望深入理解 Mycallyplus 的开发者与使用者，系统说明每个功能的实现逻辑、输入输出、文件读写与保存位置，以及与 CLI/GUI 的对应关系。所有路径均以项目根目录（包含 mycallyplus/、mycallypro/）为参考。

- 主要入口：`mycallyplus/cli.py`
- GUI：`mycallyplus/ui/gui.py`（统一工作台），`mycallyplus/ui/gui_v3.py`（状态区驱动简化版）
- 可视化查看器：`mycallyplus/visualization/viewer.py`
- 生成核心（legacy流水线）：`mycallyplus/generation/legacy.py`
- 现代化内核与数据结构：`mycallyplus/core/*`、`mycallyplus/generation/*`

---

## 1. 总体架构与数据流

- 阶段A（生成）：从 GCC RTL expand（或 C 源文件）解析 → 构建调用图 → 输出 DOT 与 circle.txt → 生成中间调试快照
- 阶段B（可视化）：加载 DOT 与 circle.txt → 生成原始图/互斥锁图/信号量图（含 Tarjan 强连通分量与线程分组）
- 统一入口：
  - GUI：`python -m mycallyplus` 或 `python -m mycallyplus gui`
  - 生成：`python -m mycallyplus generate <expand>`（参数透传到 legacy）
  - 查看：`python -m mycallyplus describe [--open <PATH>]`

目录组织（核心）：
- `mycallyplus/core/`：解析器、数据模型、控制流与线程补边（现代化接口）
- `mycallyplus/generation/`：legacy 生成流水线、渲染与导出封装
- `mycallyplus/visualization/`：查看器（原始图/互斥锁/信号量/Tarjan）
- `mycallyplus/ui/`：统一 GUI（整合"生成 + 可视化"）
- 输出：
  - 配置输出：`<base>/配置文件/<basename>/`（DOT、circle.txt、expand等）
  - 中间结果：`<base>/中间结果/<basename>/`（debug JSON、临时 DOT/PNG、日志等）
  - 可视化图片：`<base>/dag图/图N/…`（通过 `info.json` 做目录映射）

base 的取值：
- GUI/推荐：`mycallyplus/`（GUI 在调用 legacy 时通过 `--output-base` 指定）
- 纯 CLI 未传 `--output-base`：默认 `mycallyplus/generation/`

---

## 2. CLI 子命令与行为

位置：`mycallyplus/cli.py`

- `gui`（默认无参数也等价）
  - 启动统一 GUI（`ui/gui_v3.py` 的 `main()`）
- `describe [--open <PATH>]`
  - 启动可视化查看器（`visualization/viewer.py` 的 `main()`）
  - `--open` 路径可指向配置目录、`.dot` 或 `circle.txt` 文件
- `generate <expand> [options]`
  - 参数透传给 `generation/legacy.py:main()`
  - 典型选项：
    - `--threads-only`：只输出线程调用图（无条件节点）
    - `--conditions-only`：只输出条件节点图（if/while/switch）
    - `--export-txt`：导出 `circle.txt`（作为布尔开关使用）
    - `--output-base <DIR>`：指定输出根目录（推荐 `mycallyplus/`）
    - 冗余模式：`--smart`、`--clean`、`--force`（见 §4.3）

输出位置规则（无 `--output-base` 时）：
- 配置文件与中间结果默认写入 `mycallyplus/generation/` 下的对应目录。

---

## 3. 统一 GUI（生成 + 可视化）

位置：`mycallyplus/ui/gui.py`

按钮与对应实现：
- 选择源文件（C 或 expand）
  - C 文件：临时调用 gcc 生成 expand（`-O0 -fdump-rtl-expand -c`），并拷贝到 `中间结果/<basename>/rtl文件/`
  - expand 文件：直接拷贝到 `中间结果/<basename>/rtl文件/`
- 生成 dag 图（线程视图）
  - 调用 legacy：`--threads-only --output-base <base>`
  - 从 `<base>/配置文件/<basename>/<basename>_threads.dot` 复制到 `中间结果/<basename>/生成dag图/dag.dot`，并渲染 `dag.png`
- 查看条件节点（完整视图）
  - 调用 legacy：`--conditions-only --output-base <base>`
  - 从 `<base>/配置文件/<basename>/<basename>_full.dot` 复制为 `中间结果/<basename>/查看条件节点/conditions.dot` 并渲染 `conditions.png`
- 生成配置文件（circle.txt）
  - 调用 legacy：`--export-txt --output-base <base>`
  - 从 `<base>/配置文件/<basename>/circle.txt` 复制为 `中间结果/<basename>/配置文件/circle.txt`
- 生成原始图 / 查看互斥锁 / 生成信号量图
  - 在 `中间结果/<basename>/…` 目录下生成/展示 `original.png`、`mutex.png`、`semaphore.png/tarjan.png/threads.png`

状态栏同时显示：expand 文件名、配置目录、当前 DOT/TXT。

注意：`gui_v3.py` 为简化的七按钮版本，互斥锁/信号量图的生成逻辑更直接，适合作为流程演示。

---

## 4. 生成阶段（legacy 流水线）

位置：`mycallyplus/generation/legacy.py`

### 4.1 解析与建模

- 解析输入：GCC RTL expand（`.expand`）
  - 通过正则识别：函数头、`(call ...)` 目标、`(symbol_ref …)` 引用
  - 记录到 `functions[func]`：`calls`、`refs`、`mycalls`、`myinfo`
- 条件前缀识别：`if/`、`while/`、`switchK/`
  - 预读阶段扫描 `jump_insn`、`code_label`、`label_ref` 等，生成 `functions_pre`
  - 将条件上下文以前缀方式写入 `mycalls`，用于后续渲染（虚线标记）
- 线程补边（create/join → tail→join）
  - 在 `myinfo` 中记录 `thread_id→task_function`、`join_node→thread_id`，并缓存每个 task 的 `tail`
  - join 边解析：`thread_map.resolve_join_edges()`
  - 源码兜底：若 RTL 无法配对，`source_binder.bind_from_source()` 解析 C 源函数，按 handle 归一化配对 create/join
- 反向索引：`build_callee_info()`

中间快照（保存到 `中间结果/<basename>/debug/`）：
- `post_parse.json`：初次解析与线程预览
- `control_prefix.json`：条件前缀探测结果
- `post_callee_info.json`：构建反向索引后快照
- 同时按时间戳写入对应的 `.dot` 快照（如 full/threads/conditions）

### 4.2 渲染 DOT

- full_call_graph（完整图，包含条件节点虚线、线程补边）
- conditions_call_graph（仅条件节点，函数→条件节点顺序连边）
- 线程模式：当 `--threads-only` 时不额外处理条件节点

输出命名（当指定 `--output-base <base>`）：
- `配置文件/<basename>/<basename>_threads.dot`（`--threads-only`）
- `配置文件/<basename>/<basename>_full.dot`（`--conditions-only`）
- 未指定模式时为 `<basename>.dot`

同时复制：
- expand 原文件 → `配置文件/<basename>/`
- 源代码（若 `--source-file` 提供）→ `配置文件/<basename>/`

### 4.3 冗余处理模式

- `--clean`：第一次调用时清空旧的 `配置文件/<basename>/` 与 `中间结果/<basename>/`，再重建
- `--smart`（配合 `--output-base`）
  - 若 `circle.txt` 比输入 expand 更新，则跳过生成（置 `_skip_generation` 标志）
- `--force`：与 `--smart` 联用，强制重新生成

### 4.4 导出 circle.txt

位置：`generation/exporters.py`

- 入口：`export_circle_txt(functions, expand_file, output_path, source_file=None)`
- 规则：扫描 `mycalls` 中的同步原语调用，生成带可选源码位置信息的条目
- 输出格式（分两段）：
  - 段1：`互斥量`
    - 每行：`<node> mutex <id> [line] [file]`
  - 段2：`信号量`
    - 每行：`<node> sem <id> [line] [file]`
- 变量名与编号：
  - 尝试在 expand 附近的 `symbol_ref` 中提取变量名（不以 pthread_/sem_ 开头）
  - 默认变量名分别为 `mutex`/`sem`；编号按变量名分组递增，如 `mutex1`、`sem2`

---

## 5. 可视化阶段（describe）

位置：`mycallyplus/visualization/viewer.py`

- 输入：配置目录（含 `.dot` 与可选 `circle.txt`）或单独的 `.dot`/`.txt`
- 原始图
  - 直接 DOT→PNG 到 `dag图/图N/原始图.png`
- 互斥锁
  - 解析 `circle.txt` 的 “互斥量” 部分，按 `idx` 成对（lock/unlock）
  - 在 NetworkX 图上计算 `covered = descendants(lock) ∩ ancestors(unlock) ∪ {lock,unlock}`
  - 以子图 cluster 着色显示，输出 `dag图/图N/mutex.png`
  - 可切换查看文本信息（包含行号/文件）
- 信号量
  - 解析 “信号量” 部分，添加 `sem_post→sem_wait` 虚线边（带 label）
  - Tarjan 强连通分量：对非平凡 SCC 上色，输出 `tarjan.png`
  - 线程分组：按节点前缀（如 `threadX_`，否则归于 `main`）生成 cluster，输出 `threads.png`
  - 默认显示 `threads.png`，子工具栏可切换视图/信息/颜色图例
- 输出落盘策略
  - 第一次加载某配置目录时分配 `dag图/图N/` 文件夹，并写入 `info.json` 做路径映射；后续再次打开复用原目录

---

## 6. 输入读取方式（细节）

- expand 解析：正则匹配函数头/调用/引用；在 `mycalls` 中按顺序保留调用序列与条件前缀；线程 create/join 的句柄/任务名称通过 RTL 或源码兜底配对
- 源码绑定（兜底）：
  - 从 expand 里提取源文件路径；读取 C 源文本；在目标函数体代码块内用轻量级正则匹配 `pthread_create`/`pthread_join`
  - 句柄归一化规则：`&var`/数组元素/结构成员/指针解引用/变量名归一
- circle.txt 解析：按两段标题（“互斥量”“信号量”）分块，行内字段依次为 node、类型、编号、可选行号、文件；互斥锁按编号配对 lock/unlock
- DOT 解析：首选 `networkx.nx_pydot.read_dot`，失败时回退到 `pydot`

---

## 7. 输出文件清单与位置

以 `<base>=mycallyplus/`、`<b>=<basename>` 为例（GUI/推荐模式）：
- 配置输出（供查看器或复用）
  - `<base>/配置文件/<b>/<b>_threads.dot`
  - `<base>/配置文件/<b>/<b>_full.dot`
  - `<base>/配置文件/<b>/circle.txt`
  - `<base>/配置文件/<b>/<原expand>`、`<base>/配置文件/<b>/<源c文件>`（可选）
- 中间结果（调试与渲染临时）
  - `<base>/中间结果/<b>/debug/*_{post_parse|control_prefix|post_callee_info}.{json,dot}`
  - `<base>/中间结果/<b>/{生成dag图,查看条件节点,生成原始图,查看互斥锁图,生成信号量图}/*.dot|*.png`
  - `<base>/中间结果/<b>/{logs,temp,images}/…`
- 可视化图片（按配置目录映射）
  - `<base>/dag图/图N/{原始图.png, mutex.png, tarjan.png, threads.png}`

纯 CLI 未指定 `--output-base` 时，`<base>` 缺省为 `mycallyplus/generation/`。

---

## 8. 常见问题与建议

- Graphviz 未安装或 `dot` 命令不可用 → 安装 `graphviz` 并验证 `dot -V`
- gcc 无法生成 expand → 手动加编译选项，或直接提供 `.expand`
- 未找到输出文件 → 确认是否传入了 `--output-base`（GUI 会自动指定为 `mycallypro/`）
- circle.txt 行号/文件为空 → 可能 expand 无足够信息；可手动补充或调整源码以便匹配
- 大图性能 → 建议优先用 `--threads-only` 预览，再切换完整视图

---

## 9. 代码参考（关键文件）

- CLI 入口：`mycallyplus/cli.py`
- Legacy 生成：`mycallyplus/generation/legacy.py`
- 导出器：`mycallyplus/generation/exporters.py`
- 源码配对：`mycallyplus/generation/source_binder.py`
- 现代化模型/渲染：`mycallyplus/core/*`, `mycallyplus/generation/renderer.py`
- 查看器：`mycallyplus/visualization/viewer.py`
- 统一 GUI：`mycallyplus/ui/gui.py`、`mycallyplus/ui/gui_v3.py`

如需补充示例或生成脚本，请在 `mycallyplus/QUICK_START.md` 的基础上扩展。

