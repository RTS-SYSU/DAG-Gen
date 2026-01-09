# 03. GUI 按键与交互

> 基于 `ui/gui.py` 的统一 GUI。左侧“操作”按钮驱动各功能；状态区显示当前文件；画布用于展示 PNG 或文本结果。

## 3.1 主按钮（按顺序）
1. **选择源文件**  
   - 选择 `.c` 或 `.cpp`。若需要 expand，可在后续使用“生成expand文件”。
2. **选择expand文件**  
   - 选择已有 `.c.233r.expand`；状态区记录路径；复制到 `中间结果/<base>/rtl文件/`。
3. **生成expand文件**  
   - 基于当前源文件调用 `gcc -fdump-rtl-expand -c`，输出到源文件目录，再复制到 `中间结果/<base>/rtl文件/`。
4. **生成dag图**  
   - 调用 `legacy --threads-only --output-base <root>`（若已选择 dot 则直接渲染）。  
   - 从 `中间结果/<base>/配置文件/<base>_threads.dot` → `中间结果/<base>/生成dag图/dag.dot` → `dot` 渲染 `dag.png`。
5. **查看条件节点**  
   - `legacy --conditions-only` + `--output-base`。  
   - `中间结果/<base>/配置文件/<base>_full.dot` → `中间结果/<base>/查看条件节点/conditions.dot/png`。
6. **生成源码调用图**  
   - 需要源/expand；调用 legacy（`--extern-only --source-file ...`）。  
   - 输出 `dag_source_only.dot` → `dag_source_only_filt.dot/png` 于 `中间结果/<base>/生成源码调用图/`。
7. **查看互斥锁**  
   - 依赖 `circle.txt`（`中间结果/<base>/配置文件/circle.txt`）。  
   - 在画布上显示互斥锁图（Graphviz）或文本信息。
8. **生成信号量图**  
   - 同上；生成 `original/tarjan/threads.png` 到 `中间结果/<base>/生成信号量图/`。
9. **时间分析**  
   - 分两步：选择源代码（插桩工程根）与 `mycalls_meta_internal.json`。  
   - 调用 `time_analysis.run_time_analysis()`，结果位于 `中间结果/<base>/时间分析/<project>/`。
10. **调度算法**  
    - 子功能：“生成最长路径”已实现（dot + time_result）。  
    - 输出 `中间结果/<base>/调度算法/longest_path/`（或更多策略子目录）。
11. **过滤dot文件**  
    - 调用 `filter_dot.py`（手动选择 DOT）。
12. **选择dot文件 / 选择配置文件**  
    - 支持直接加载已有 DOT/配置目录。配置目录优先 `中间结果/<base>/配置文件/`，兼容旧 `配置文件/<base>/`。

## 3.2 状态区
- 显示：源文件、expand 文件、当前 DOT、当前 TXT、配置文件目录。
- 每次按钮成功执行后都会更新状态。

## 3.3 画布展示
- Graphviz 渲染生成 PNG 后，通过 Tkinter 图像控件展示。
- 支持鼠标拖拽、滚轮缩放。
- 某些功能（互斥锁信息）会在新窗口显示文本。

## 3.4 常见联动
- **circle.txt**：由“生成配置文件”或条件节点功能生成 → 互斥锁/信号量按钮依赖。
- **time_result.json**：时间分析完成后 → 调度算法（Longest Path）使用。
- **长路径插桩**：调度算法子功能将依赖 longest_path.json + time_result + mycalls_meta_internal。

详细参数与目录路径请参阅《04_数据流与存储机制》与 《06_时间分析与调度》。***
