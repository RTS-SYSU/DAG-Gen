# mycallypro 架构与代码说明

本文档面向第一次阅读本项目代码的同学，介绍 mycallypro 的总体架构、关键数据结构、处理流程（命令行与 GUI），以及“函数调用图 → 线程调用图”和“节点编号”两项核心语义。阅读本文件后，你可以较快地在代码中定位到相应的实现位置并进行扩展。

## 1. 目标与边界

- 输入：GCC RTL expand 文件（`*.expand`）。
- 输出：Graphviz DOT（全量图或路径视图），以及 PNG 图片（GUI 中渲染）。
- 线程语义：识别 `pthread_create/pthread_join`，为线程任务尾节点补一条 `tail -> pthread_join` 边。
- 节点编号：按“出现顺序”对同名函数的多次调用生成唯一节点名，形如 `caller/<ctx-prefix><callee><N>`。
- 控制流标注：在节点名前附加 `if/`、`while/`、`switchK/`（来自 legacy 解析逻辑）。

## 2. 目录结构

```
mycallypro/
  __init__.py          # 包入口（导出 CLI main）
  __main__.py          # 允许 python3 -m mycallypro 直接运行
  cli.py               # CLI 外壳，转发到 legacy.main（保持兼容）
  legacy.py            # 从 cally/mycally.py 迁移而来（核心语义、编号、线程补边）
  model.py             # 轻量数据模型（现代化接口使用）
  parser.py            # 简化版解析器（现代化接口使用）
  builder.py           # 构建 callee 反向索引（现代化接口使用）
  renderer.py          # 现代化 DOT/路径渲染（用于 UT 与工具内使用）
  threads.py           # 现代化线程补边（用于 UT 与工具内使用）
  exporters.py         # 导出 DOT / circle.txt（与 dag_describe 集成时可用）
  gui.py               # Tk GUI，按钮式流程；调用包入口生成 DOT + PNG
  ARCHITECTURE_CN.md   # 本文档
```

> 说明：当前 GUI 已切换到通过 `python -m mycallypro <expand>` 方式调用 legacy 流水线，以保证生成的 DOT 与原 `mycally.py` 的输出完全一致（包括编号与线程补边）。

## 3. 核心数据结构

对于“现代化接口”（`parser.py / model.py / renderer.py` 等）我们定义了更清晰的类型：

- `Function`：包含 `files / calls / refs / call_sequence / callee_calls / callee_refs` 等字段。
- `CallGraph`：`functions: Dict[str, Function]`；附带线程相关缓存 `thread_edges / thread_create_queue`（若使用现代化线程补边）。
- `RenderOptions`：渲染时的开关（`exclude / no_externs / max_depth / reverse_path`）。

> 注意：`legacy.py` 仍使用原版 `dict` 结构（如 `functions[func]['mycalls'] / ['myinfo']`），这是为了字节级保持兼容性。

## 4. 处理流程

### 4.1 命令行（编号 + 线程补边）

```
python3 -m mycallypro <file.expand>  # 生成全量 DOT（stdout）
python3 -m mycallypro --caller FUNC <expand...>
python3 -m mycallypro --callee FUNC <expand...>
```

CLI 会转发到 `legacy.main()`：

1) 预读 RTL（jump/code/label）→ 识别控制流结构（if/while/switch）；
2) 主读 RTL → 解析 `call` 和 `symbol_ref`；
3) 线程语义：捕获 `pthread_create`（dx=任务入口，di=线程标识）与 `pthread_join`（di=线程标识），在 `myinfo` 中建立映射；
4) 节点编号：在函数内对每一次调用进行自增计数，形成 `caller/<ctx-prefix><callee><N>`；
5) 输出 DOT：
   - 普通边：顺序连线；外部符号 `style=dashed`；
   - 线程补边：找到任务尾 `tail`，输出 `tail -> pthread_join`。

### 4.2 GUI（mycallypro/gui.py）

GUI 点击“生成 dag 图”时，会启动子进程执行 `python3 -m mycallypro <expand>` 获取 DOT，然后调用 `dot` 渲染成 PNG 并展示。

> 这样可以保证 GUI 与命令行的 DOT 完全一致（包括编号与线程补边）。

## 5. 关键语义

### 5.1 节点编号规则

- 在单个函数体内维护 `count`，每遇到一条 `call` 就 `count += 1`；
- 若被调函数不是内部已知函数（即外部符号），仍生成节点并标记 `style=dashed`；
- 节点命名：`<caller>/<ctx-prefix><callee><N>`，`ctx-prefix` 来自 if/while/switch 的识别；
- 这样，即便同一个 `printf`/`sem_post` 被多次调用，也会得到不同编号节点，具备时间序信息。

### 5.2 线程调用图

- 抓取 `pthread_create`：提前捕获 `dx`（任务入口函数名）与 `di`（线程标识），记录 `myinfo[<thread>] = <task>`；并把任务入口加入 `calls`（使线程入口可见）。
- 抓取 `pthread_join`：识别 `di` 的线程标识并在 `myinfo[join_node] = <thread>` 中建立映射；渲染时：取 `<thread> -> <task> -> tail`，输出 `tail -> join_node`。
- 若某些机型的 di 不是显式符号（虚拟栈/寄存器别名），legacy 逻辑会尽力推断；失败时不会崩溃（mycallypro 中已加保护）。

## 6. 代码走读索引

- `legacy.py`：
  - `unit_test()`：内置快照测试（供参考）
  - `full_call_graph()`：编号节点/线程补边/控制流标注的 DOT 输出
  - `main()`：CLI 入口，解析参数、读 RTL、调度输出
- `gui.py`：`MyCallyGUI._build_dag()` 调用 `python -m mycallypro` 生成 DOT → `dot` 渲染 PNG
- `parser.py / builder.py / renderer.py / threads.py`：现代化最小实现（便于后续扩展与 UT）
- `model.py`：数据类型定义（dataclass）

## 7. 常见问题

- GUI 报 "No module named mycallypro"：已在 GUI 中设置子进程工作目录为包父目录；确保以 `~/桌面/cally/` 作为 CWD 或使用 `python3 -m mycallypro.gui` 启动。
- GUI 报 "missing ), unterminated subpattern"：这是正则写法被错误转义导致，`parser.py` 中已修复为原版模式。
- `pthread_join` 映射失败：mycallypro/legacy.py 中已做空安全，缺失映射不会中断渲染，但可能缺少 `tail -> join` 补边。

## 8. 扩展建议

- 若要增强线程句柄匹配精度，可在解析层引入“句柄等价类”（基于虚拟栈偏移/寄存器别名），对 `di` 做归一化后再配对。
- 增加“导出带线程分组的颜色主题”，便于与 dag_describe 的线程可视化风格保持一致。
- 为 `legacy.py` 添加更细粒度的单测（针对 if/while/switch 的复杂嵌套），并逐步迁移到现代化渲染管线。

---

若对本文档或代码结构有任何疑问，欢迎在 `mycallypro` 包内提交 issue/PR 或直接补充注释。

## 9. 本轮已完成的扩展与修复（Changelog）

> 目的：固定当前成果，便于后续继续迭代。

- 线程补边解耦（保留兼容）
  - 新增 `thread_map.resolve_join_edges()`，替换 `legacy.full_call_graph()` 中的内联映射/下钻逻辑；输出顺序与语义保持一致。
  - `legacy` 在解析阶段为每个函数维护 `myinfo["__create_queue__"]`（创建队列）。当 join 的句柄无法从 RTL 确认时，使用队列兜底。兜底策略已从 FIFO 调整为 LIFO（最近创建的更可能先被 join），更符合 while 中“创建-立即 join”的常见写法。

- 源代码补全绑定（RTL 信息不足时的增强）
  - 新增 `source_binder.py`：按如下步骤在源代码层补全 `pthread_create` 与 `pthread_join` 的配对：
    1) 通过 expand 中的 `"xxx.c":line:col` 提示定位源文件与大致函数范围；
    2) 在 owner 函数体内用正则提取 create/join 调用；
    3) 对句柄（第一个实参）做轻量规范化（`&var`/`arr[i]`/`ctx->member`/`*p` 等），建立 HandleID；
    4) 优先按 HandleID 匹配，其次按同函数内 LIFO 兜底。
  - `thread_map.resolve_join_edges()` 在 RTL 匹配失败时会调用 `bind_from_source()`，并把结果缓存在 `myinfo['__source_bind_queue__']` 中逐个消费，随后生成 `tail -> join` 边。

- GUI 统一输出与调用路径
  - 在 `gui.py` 中引入 `PROJECT_ROOT = Path(__file__).resolve().parent.parent`；所有读取/生成/存储目录都锚定到 `PROJECT_ROOT/test/<basename>/`；
  - 调用子进程 `python -m mycallypro` 时，传入 expand 的绝对路径并将 `cwd` 固定为 `PROJECT_ROOT`，避免非 0 退出；
  - 生成的 DOT/PNG 始终落在 `项目根/test/<basename>/`，并在 GUI 画布中显示。
- 调试产物落盘
  - CLI/GUI 每次生成图都会在 `test/<basename>/debug/` 下写入一对 `.dot` 与 `.json`（函数表、myinfo、调用参数等），文件名带时间戳方便排查。

- 文档与注释
  - 增补了 `model.py / parser.py / builder.py / renderer.py / threads.py` 的中文注释与模块说明，明确现代化接口的职责；
  - 新增本文档（`ARCHITECTURE_CN.md`）并补充本轮 Changelog；
  - 提供了“逐步抽函数、不更换容器”的折中重构路线，适合在保持输出完全兼容的前提下逐步提炼代码。

### 9.1 pthread_join 严格识别（重要）

- 只允许将形如 `.../pthread_join` 或 `.../pthread_join<N>` 的节点视作 join 节点：
  - 代码：`thread_map.resolve_join_edges()` 使用正则 `(^|/)pthread_join(\d+)?$` 严格判断。
  - 目的：避免普通调用（例如 `pthread_cond_destroy12`）被误当成 join，导致跨线程误连（历史问题已修复）。

### 9.2 线程绑定优先级（总结）

1. RTL 绑定（若 `myinfo[join_node]` 中已有句柄 → 直接映射至任务入口）
2. LIFO 兜底（`__create_queue__` 取最近创建的任务，更符合“创建即 join”的场景）
3. 源代码补全（`source_binder.bind_from_source()` 在 owner 函数内解析 create/join 参数，构造 HandleID 后匹配；仍不足时用本函数内 LIFO）
4. 生成补边 `tail -> join`（tail 来自任务入口函数的 `myinfo['tail']`）

### 9.3 GUI/CLI 输出与调试产物

- 统一到项目根目录 `test/<basename>/`：
  - DOT：`test/<basename>/dag.dot`
  - PNG：`test/<basename>/dag.png`
  - 调试：`test/<basename>/debug/<timestamp>_full.{dot,json}`（包含函数表、myinfo、入参等）
- CLI 示例：
  - `python3 -m mycallypro test/produce/produce.c.233r.expand`（stdout 为 DOT；同时写 debug 产物）
  - `python3 -m mycallypro --caller main test/produce/produce.c.233r.expand`
  - `python3 -m mycallypro --callee producer test/produce/produce.c.233r.expand`
- GUI：
  - `python3 -m mycallypro.gui`（或在包目录运行 `python3 gui.py`）
  - 读入 expand → 生成 DAG 图；DOT/PNG/Debug 按上述位置落盘。

### 9.4 已知问题与现状

- 源代码补全目前针对“同一函数内”场景，跨函数传递句柄暂不支持（可在下轮迭代增强）。
- 控制流前缀（if/while/switch）的状态机仍在 `legacy.py` 内，已预留 `control_flow.py` 以便后续逐步迁移。

---

## 10. 案例：为何曾出现 `pthread_cond_destroy12 -> watcher/printf3`（已修复）

背景：早期逻辑对 join 的判断不严格，导致 `pthread_cond_destroy12` 被误当成 join 节点，触发了线程尾补边；补边时拿到了 watcher 的尾节点 `watcher/printf3`，因此出现跨线程的误连。

修复：现已改为“严格正则”判断——只有 `.../pthread_join` 或 `.../pthread_join<N>` 才进入绑定逻辑。新版 DOT 不会再出现上述误连。

如何用调试产物定位：

1. 打开 `test/<basename>/debug/<timestamp>_full.dot`，搜索 `pthread_cond_destroy12`；若出现指向其它线程节点的边，则检查本次生成对应的 `_full.json` 中 `functions['main']['myinfo']` 是否有错误的 join 映射（现版本不会进入绑定，值应为空）。
2. 对 join 节点（如 `main/while/pthread_join6`），在 `_full.json` 中查看 `resolve_join_edges()` 的逻辑：
   - 当 `myinfo[join_node]` 有句柄或可从队列/源代码补全得到任务入口时，才会写入 `tail -> join`；
   - 非 join 节点（如 `pthread_cond_destroy12`）不再走这条路径。


### 已知限制
- 源代码补全采用轻量级正则与句柄规范化，适用于“同一函数内”的常见场景；跨函数传递句柄（例如存入全局结构后在另一函数 join）暂不处理；
- 控制流前缀（if/while/switch）仍在 legacy 的状态机内，尚未迁移；
- 若需更强的别名传播（如 `tmp = &thread; join(tmp)`），可在 `source_binder` 内再加一层局部变量赋值的简单跟踪（已预留扩展位置）。

### 下一步建议（可选）
- 节点编号与控制流前缀：在不改变输出的前提下，继续以“抽函数”的方式从 `legacy` 中提炼到 `numbering.py / conditions.py`，每步之后做 DOT 快照对比；
- 句柄匹配增强：在 `source_binder` 中增加简易的赋值传播与更多句柄形态识别（例如 `*(arr+i)`、多级指针等）。
