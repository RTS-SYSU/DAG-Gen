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
   - 同步导出 `circle.txt` 到 `中间结果/<base>/配置文件/circle.txt`（供 PipeDAG/互斥锁/信号量使用；失败不阻塞 DAG 生成，但会导致后续步骤缺输入）。
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
11. **模块化实验（PipeDAG）**
    - 打开固定流水线子功能栏：`collector -> blocks -> timing -> schedule -> instrument`。  
    - 产物统一写入 `中间结果/<base>/pipeline/`，与旧流程并存隔离。
12. **过滤dot文件**  
    - 调用 `filter_dot.py`（手动选择 DOT）。
13. **选择dot文件 / 选择配置文件**  
    - 支持直接加载已有 DOT/配置目录。配置目录优先 `中间结果/<base>/配置文件/`，兼容旧 `配置文件/<base>/`。

## 3.2 状态区
- 显示：源文件、expand 文件、当前 DOT、当前 TXT、配置文件目录。
- 每次按钮成功执行后都会更新状态。

## 3.3 画布展示
- Graphviz 渲染生成 PNG 后，通过 Tkinter 图像控件展示。
- 支持鼠标拖拽、滚轮缩放。
- 某些功能（互斥锁信息）会在新窗口显示文本。

## 3.4 常见联动
- **circle.txt**：由“生成dag图”（自动导出）或“查看条件节点”导出 → 互斥锁/信号量按钮依赖；PipeDAG 的 `collector` 也需要它。
- **time_result.json**：时间分析完成后 → 调度算法（Longest Path）使用。
- **长路径插桩**：调度算法子功能将依赖 longest_path.json + time_result + mycalls_meta_internal。

## 3.5 模块化实验（PipeDAG）
### 入口与目标
- 左侧主按钮 `模块化实验` 进入 PipeDAG 子功能栏。
- 不新开页面，沿用现有单窗口 GUI；旧流程按钮全部保留。
- 目标是固定执行链路并支持规则/算法可插拔。

### 子功能顺序
1. `生成分块信息`
2. `level1 分块`
3. `level2 分块`
4. `level3 分块`
5. `分块测时`
6. `调度算法`（二级按钮按算法 registry 动态生成）
7. `优先级插装`
8. `返回主流程`

### 从零开始（手动回归）建议点击顺序
以 `zhang2.c` 为例，每次想从“空中间结果”验证全链路时：
1. 手动删除目录：`中间结果/zhang2/`（确保没有旧产物干扰）
2. `选择源文件` → 选择 `源文件/zhang2/zhang2.c`
3. `生成expand文件`
4. `生成dag图`（会生成 `dag.dot/png`，并同步导出 `circle.txt`）
5. `模块化实验`：
   - `生成分块信息`
   - `level2 分块`（推荐 rule: `effective_line_merge`）
   - `分块测时`
   - `调度算法`（选择一个算法，例如 `cpf`）
   - `优先级插装`（选择“通用插装”更适合 level2/3；level1 可用“专用插装”）

### 状态区增强
- 在原有状态区（源文件/Expand/DOT/配置）基础上新增 PipeDAG 上下文：
  - `level`
  - `rule`
  - `view(single)`
  - `algo`
- 新增“最近产物”快捷入口按钮：
  - `block_info`
  - `segments`
  - `timing`
  - `schedule`
  - `source_original`
  - `source_instrumented`
- 快捷入口仅在目标文件存在时可点击。

### 输入/输出与门禁
- `生成分块信息`
  - 输入：当前源文件 + `生成dag图` 相关产物
  - 输出：`中间结果/<base>/pipeline/block_info.json`
- `levelX 分块`
  - 前置：`pipeline/block_info.json`
  - 输出：`pipeline/blocks/<level>/<rule>/segments.json`、`dag_seg.json`
- `分块测时`
  - 前置：存在至少一个可用分块目标（`segments.json` + `dag_seg.json`）
  - 输出：`pipeline/timing/<level>/<rule>/timing.json`
- `调度算法`
  - 前置：存在至少一个可用测时目标（`timing.json` + `dag_seg.json`）
  - 输出：`pipeline/schedule/<level>/<rule>/<algo>/schedule.json`
- `优先级插装`
  - 前置：存在至少一个 `schedule.json`
  - 输出：`pipeline/instrument/<...>/source_original.c`、`source_instrumented.c`
- 门禁行为：
  - 不满足前置时按钮置灰。
  - 执行前再次检查；若缺失，弹窗显示缺失文件绝对路径。

### 覆盖写入与失败处理
- PipeDAG 默认覆盖写入，不保留历史版本。
- 各阶段 `*_meta.json` 在执行中写 `status=running`，成功写 `success`，异常写 `failed` 并记录错误。
- 失败时允许半成品落盘，便于排障与重跑。
- 重新运行成功时会清理旧的 `error` 字段，避免“成功但仍显示旧报错”的困扰（对排障信息请以最新的 `status`/输入文件存在性为准）。

详细参数与目录路径请参阅《04_数据流与存储机制》与 《06_时间分析与调度》。***
