# experiment2：单平台实验结果统计指南

本指南用于“只跑一个平台（VM 或 RK3588S）”时，按 `experiment/experiment2实验总表/tables/` 现有格式统计并产出表格。

> 补充：仓库内 `experiment/zhang1实验结果汇总`、`experiment/zhang2实验结果汇总` 也遵循同一套“单平台表结构/字段口径”（尤其是 `total = mean × n`），只是目录分组维度不同（按 `algo` 或按 `suite`）。

## 1. 统计对象与粒度

- **统计粒度**：每一行代表一组“实验配置”的聚合结果，配置由以下字段唯一确定：
  - `work_scale`：负载规模
  - `repeats`：重复次数（runs 数）
  - `cpu_set`：绑核集合（例如 `0,1,2,3`）
  - `cores_per_task`：每任务使用核心数（例如 `4`）
- **对比对象**：同一配置下的两种方案
  - `baseline`
  - `prio`

> 说明：`total_s` 在表里按 `mean_s × repeats(n)` 估算（当前脚本就是这样算的）。

## 2. 数据来源（你需要准备什么）

当前汇总脚本会在实验结果目录里递归查找 `summary.json`，因此单平台统计时，你只要确保你的平台实验结果都落在某个根目录下，并且每次 run 的目录里包含 `summary.json`。

推荐目录（仓库内默认约定）：

- VM：`experiment/experiment2虚拟机实验结果汇总/`
- RK3588S：`experiment/experiment2（rk3588）实验结果/`

脚本位置：

- `experiment/experiment2实验总表/scripts/build_platform_config_results.py`

### 2.1 `summary.json` 至少应包含的字段（脚本会读取）

脚本读取（或推导）的信息包括：

- 元信息
  - `created_at`
  - `work_scale`
  - `repeats`
  - `cpu_set`（可为数组或字符串；数组会被转成逗号分隔字符串）
  - `cores_per_task`
- 统计值
  - `baseline.stats.mean_s / max_s / min_s / n`
  - `prio.stats.mean_s / max_s / min_s / n`
  - `delta_mean_s`
  - `improvement_ratio`（可空）

其中提升比例定义为：

`improvement(%) = (baseline_mean_s - prio_mean_s) / baseline_mean_s × 100%`

## 3. 单平台输出应该长什么样（CSV 与 Markdown）

### 3.1 CSV（单平台汇总表）

单平台 CSV 推荐命名为：

- VM：`experiment/experiment2实验总表/tables/config_results_vm.csv`
- RK3588S：`experiment/experiment2实验总表/tables/config_results_rk3588.csv`

列名与顺序（与现有表一致）：

```
platform,work_scale,repeats,
baseline_mean_s,baseline_total_s,baseline_max_s,baseline_min_s,
prio_mean_s,prio_total_s,prio_max_s,prio_min_s,
delta_mean_s,improvement_ratio,
cpu_set,cores_per_task,created_at,out_dir
```

字段含义要点：

- `platform`：建议固定为 `vm` 或 `rk3588`（与现有表一致，便于合并）
- `*_mean_s/max_s/min_s`：来自 `summary.json` 中对应方案的统计
- `*_total_s`：`mean_s × n`（n 通常等于 `repeats`）
- `delta_mean_s`：通常为 `prio_mean_s - baseline_mean_s`（以你的生成逻辑为准；汇总表只是原样抄入）
- `improvement_ratio`：`(baseline_mean_s - prio_mean_s) / baseline_mean_s`（0~1）
- `out_dir`：该行数据对应的 `summary.json` 所在目录路径

### 3.2 Markdown（单平台展示表，答辩/汇报更友好）

现有跨平台 Markdown 为：

- `experiment/experiment2实验总表/tables/config_results_by_platform.md`

单平台情况下，你有两种做法（任选其一）：

1) **继续生成跨平台文件，但只使用其中某个平台的 section**  
   直接从 `config_results_by_platform.md` 里复制你需要的平台表格到汇报材料。

2) **单独维护一个单平台 Markdown 文件**（推荐用于长期只跑一个平台时）  
   建议文件名：
   - `experiment/experiment2实验总表/tables/config_results_vm.md`
   - 或 `experiment/experiment2实验总表/tables/config_results_rk3588.md`

表头字段建议保持与现有一致（便于横向对比时直接拼接）：

- `work_scale | repeats | cpu | baseline mean (s) | baseline total | baseline min/max (s) | prio mean (s) | prio total | prio min/max (s) | improvement`

## 3.3 参考实现：zhang1/zhang2 的“目录结构 + 产物清单”（保持一致的格式）

`zhang1/zhang2/zhang3` 的汇总目录本质上也是“单平台统计”，表结构与本指南一致；区别在于它们会把结果按不同维度拆分成多份表，方便汇报：

### A) 配置结果表（config_results_*）：按 `algo` 分组

目录结构示例（以 zhang2 为例）：

- `experiment/zhang2实验结果汇总/<algo>/<run>/summary.json`
  - `<algo>`：`cpf` / `lpf` / `heft` / `zhao2020`（以及某些实验会有 `web_tasks` 作为单独组）
- 汇总表输出目录：`experiment/zhang2实验结果汇总/tables/`
- 汇总脚本（示例）：`experiment/zhang1实验结果汇总/scripts/build_zhang1_config_results.py`

产物文件（zhang1/zhang2 保持一致）：

- `config_results_<algo>.csv`
- `config_results_all.csv`
- `config_results_all_long.csv`（多一列 `algo`，便于筛选/透视）
- `config_results_compare_algos_wide.csv`（同一配置下对比多个 `algo`）
- `config_results_by_algo.md`（按 `algo` 分段的 Markdown 展示表）

#### A.1 算法顺序（固定规则）

为保证不同平台（如 `zhang1/zhang2/zhang3`）的表格可直接对齐比较，**算法（`algo`）顺序固定为**：

- `cpf`, `lpf`, `heft`, `zhao2020`

该顺序的来源与实现位置：

- `experiment/zhang1实验结果汇总/scripts/build_zhang1_config_results.py` 中的 `PREFERRED_ALGO_ORDER`

该顺序会同时影响三类产物：

- `config_results_by_algo.md`：章节（分段）顺序
- `config_results_all_long.csv`：长表按 `algo` 分组排序
- `config_results_compare_algos_wide.csv`：宽表列展开顺序

如果某次实验目录下出现不在上述列表中的 `algo`（例如把某个 suite 也单独作为一组目录），会被排在最后（并按名称稳定排序），以避免影响四算法对齐。

#### A.2 分类规则：如何从 `summary.json` 得到 `algo` 并落盘成目录

在理想情况下，你的实验输出目录已经按算法分好了目录：

- `.../<algo>/<run>/summary.json`

但在某些情况下（例如先按 suite 产出在 `web_tasks/<run>/summary.json`），`summary.json` **未显式包含 `algo` 字段**。这时可以按以下规则从 `summary.json` 推断算法并进行分类：

1) **优先从 `baseline.c_file` / `prio.c_file` 推断**
   - 若路径包含 `.../effective_line_merge/<algo>/...`，则取 `<algo>` 作为算法名。
2) **回退从 `baseline.compile_cmd` / `prio.compile_cmd` 推断**
   - 解析编译命令中的 include 路径，若出现 `.../baseline/<algo>/...` 或 `.../prio/<algo>/...`，则取 `<algo>`。

落盘方式（以 `zhang1` 为例）：

- 输入：`experiment/zhang1实验结果汇总/web_tasks/<run>/summary.json`
- 输出：`experiment/zhang1实验结果汇总/<algo>/<run>/summary.json`

仓库内提供了对应的分类脚本（默认复制，保留原始 `web_tasks` 不动）：

```bash
python3 experiment/zhang1实验结果汇总/scripts/classify_web_tasks_by_algo.py --dry-run
python3 experiment/zhang1实验结果汇总/scripts/classify_web_tasks_by_algo.py
```

如需“移动”而不是“复制”（会把 `web_tasks/<run>` 迁移到 `<algo>/<run>`）：

```bash
python3 experiment/zhang1实验结果汇总/scripts/classify_web_tasks_by_algo.py --mode move
```

其中 `config_results_all_long.csv` 的列名与顺序（与现有表一致）：

```
algo,platform,work_scale,repeats,
baseline_mean_s,prio_mean_s,improvement_ratio,delta_mean_s,
baseline_total_s,prio_total_s,
baseline_min_s,baseline_max_s,prio_min_s,prio_max_s,
cpu_set,cores_per_task,created_at,out_dir
```

### B) runtime_compare 汇总表（runtime_results_*）：按 `suite` 分组

目录结构示例（以 zhang2 为例）：

- `experiment/zhang2实验结果汇总/<suite>/<run>/summary.json`
  - `<suite>`：例如 `web_tasks`
- 汇总表输出目录：`experiment/zhang2实验结果汇总/tables/`
- 汇总脚本（示例）：`experiment/zhang2实验结果汇总/scripts/build_zhang2_runtime_results.py`

产物文件：

- `runtime_results_<suite>.csv`
- `runtime_results_all.csv`
- `runtime_results_by_suite.md`

`runtime_results_all.csv` 的列名与顺序（与现有表一致）：

```
suite,platform,work_scale,repeats,
baseline_mean_s,prio_mean_s,improvement_ratio,delta_mean_s,
baseline_total_s,prio_total_s,
baseline_min_s,baseline_max_s,prio_min_s,prio_max_s,
cpu_set,cores_per_task,created_at,out_dir
```

## 4. 生成流程（单平台怎么做最省事）

最省事的做法是：**仍然运行现有脚本生成所有表，然后只取你需要的平台文件**。

在仓库根目录执行：

```
python3 experiment/experiment2实验总表/scripts/build_platform_config_results.py
```

生成产物位置：

- 单平台 CSV：
  - `experiment/experiment2实验总表/tables/config_results_vm.csv`
  - `experiment/experiment2实验总表/tables/config_results_rk3588.csv`
- 合并表（跨平台）：
  - `experiment/experiment2实验总表/tables/config_results_all.csv`
- 跨平台 Markdown：
  - `experiment/experiment2实验总表/tables/config_results_by_platform.md`

当你只跑一个平台时：

- 只把对应平台的 `config_results_*.csv` 当作“最终汇总表”
- `config_results_all.csv` / 另一个平台 CSV 可以忽略（为空也没关系）

## 5. 单平台统计时的“检查清单”

- 每个 run 目录都生成了 `summary.json`
- `summary.json` 里 `baseline.stats.n` 与 `prio.stats.n` 与你期望的 `repeats` 一致
- 同一配置（`work_scale/repeats/cpu_set/cores_per_task`）不会混入不同实验批次的脏数据（必要时用目录分批，或清理旧结果）
- 汇总后的 `improvement_ratio` 为正值且量级合理（prio 比 baseline 更快时应为正）
