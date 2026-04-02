# Runtime 工具升级方案 v3.0

## 一、升级概述

本次升级涉及两大方面：
1. Pipeline 插桩环节的目录结构重构
2. runtime_compare 工具的任务模型改造

核心思路：每个算法独立运行、独立统计，不再做 baseline vs prio 对比。runtime_compare 只做统计，实验分析单独进行。

---

## 二、Pipeline 插桩环节重构

### 2.1 当前结构（旧）

```
.../instrument/level2/effective_line_merge/
├── cpf/
│   ├── source_original.c
│   ├── source_instrumented.c
│   ├── instrument_meta.json
│   └── 测时/
│       ├── baseline_CFS.c      ← 每个算法目录都重复
│       ├── baseline_FIFO.c     ← 每个算法目录都重复
│       ├── prio.c
│       └── compile_and_run.sh
├── heft/  (同上)
├── lpf/   (同上)
├── t_level/ (同上)
├── wcet_first/ (同上)
└── zhao2020/ (同上)
```

问题：
- baseline_CFS.c 和 baseline_FIFO.c 在每个算法目录下重复存放
- 没有统一的 CFS/FIFO 对照组目录
- FIFO 插桩 + 测时插桩存在嵌套 `{` 的语法问题

### 2.2 新结构

```
.../instrument/level2/effective_line_merge/
├── result/                        ← 插桩结果（不含测时代码）
│   ├── CFS/CFS.c                 ← source_original.c 拷贝（纯源文件，CFS 调度）
│   ├── FIFO/FIFO.c               ← source_original.c + l1_set_thread_prio_fifo(99)
│   ├── cpf/cpf.c                 ← cpf 优先级插桩
│   ├── heft/heft.c
│   ├── lpf/lpf.c
│   ├── t_level/t_level.c
│   ├── wcet_first/wcet_first.c
│   └── zhao2020/zhao2020.c
└── timing/                        ← 测时版本（在 result 基础上加 main 首尾测时）
    ├── CFS/CFS.c
    ├── FIFO/FIFO.c
    ├── cpf/cpf.c
    ├── heft/heft.c
    ├── lpf/lpf.c
    ├── t_level/t_level.c
    ├── wcet_first/wcet_first.c
    └── zhao2020/zhao2020.c
```

### 2.3 各目录文件说明

| 目录 | 文件来源 | 说明 |
|------|---------|------|
| result/CFS/ | source_original.c 拷贝 | 纯源文件，默认 CFS 公平调度 |
| result/FIFO/ | source_original.c + FIFO 插桩 | 在 main 开头加 `l1_set_thread_prio_fifo(99)` |
| result/{algo}/ | source_instrumented.c | 各算法的优先级插桩版本 |
| timing/CFS/ | result/CFS + 测时插桩 | main 首尾加 clock_gettime |
| timing/FIFO/ | result/FIFO + 测时插桩 | FIFO + 测时，需一次性处理避免语法冲突 |
| timing/{algo}/ | result/{algo} + 测时插桩 | 算法插桩 + 测时 |

### 2.4 instrument.py 改动要点

- 统一在一次插桩中处理 FIFO/优先级设置 + 测时代码的插入顺序，修复当前两次插桩导致的嵌套 `{` 问题
- 新增生成 CFS 和 FIFO 两个对照组目录
- 去掉 instrument_meta.json（未被使用）
- 去掉 compile_and_run.sh（不再需要）
- 文件命名与目录同名（如 `heft/heft.c`），方便对比查看

### 2.5 实验分组

| 分组 | 算法 | 说明 |
|------|------|------|
| 对照组 | CFS | 源文件，默认 Linux CFS 调度 |
| 对照组 | FIFO | 源文件 + 开启 FIFO 实时调度（统一优先级 99） |
| 实验组 | cpf | Critical Path First |
| 实验组 | heft | Heterogeneous Earliest Finish Time |
| 实验组 | lpf | Longest Processing First |
| 实验组 | t_level | T-Level 拓扑层级 |
| 实验组 | wcet_first | WCET 排序 |
| 实验组 | zhao2020 | Zhao 2020 文献算法 |

---

## 三、runtime_compare 工具升级

### 3.1 任务模型改造

旧模型：
- 每个任务包含 `baseline_c` + `prio_c` 两个文件
- 交替运行两个版本，对比结果

新模型：
- 每个任务只有一个 `source_c` 文件 + `algo_name` 标识
- 独立运行，独立统计

### 3.2 批量导入

- 扫描路径：`timing/` 下的 8 个子目录
- 每个子目录找与目录同名的 `.c` 文件
- 共生成 8 个独立任务入队

### 3.3 添加新任务

- 每次只添加一个任务
- 不再区分 prio / baseline
- 选择一个 .c 文件 + 指定算法名即可

### 3.4 消息显示

- 只显示当前任务的运行时间
- 格式示例：`完成: heft mean=0.953s (10 次)`

### 3.5 统计结果存储

每个算法一个 CSV：

```csv
run,time_s,wall_s
1,1.234567,1.240000
2,1.230000,1.235000
...
avg,1.232284,1.237500
min,1.230000,1.235000
max,1.234567,1.240000
```

汇总 CSV（summary_all.csv）：

```csv
algorithm,avg_s,min_s,max_s
CFS,1.500000,1.480000,1.520000
FIFO,1.200000,1.180000,1.220000
cpf,1.050000,1.030000,1.070000
heft,0.950000,0.930000,0.970000
lpf,1.100000,1.080000,1.120000
t_level,0.980000,0.960000,1.000000
wcet_first,1.020000,1.000000,1.040000
zhao2020,0.960000,0.940000,0.980000
```

### 3.6 输出目录结构

```
实验结果/{batch_name}/
├── CFS/
│   ├── runs.csv
│   └── summary.json
├── FIFO/
│   ├── runs.csv
│   └── summary.json
├── cpf/
│   ├── runs.csv
│   └── summary.json
├── heft/
│   ├── runs.csv
│   └── summary.json
├── lpf/
│   ├── runs.csv
│   └── summary.json
├── t_level/
│   ├── runs.csv
│   └── summary.json
├── wcet_first/
│   ├── runs.csv
│   └── summary.json
├── zhao2020/
│   ├── runs.csv
│   └── summary.json
└── summary_all.csv
```

### 3.7 Web UI 功能变更

| 功能 | 旧 | 新 |
|------|----|----|
| 添加任务 | 选 baseline + prio 两个文件 | 选一个文件 + 算法名 |
| 批量导入 | 按算法目录生成 baseline/prio 对 | 扫描 timing/ 下 8 个目录，各一个任务 |
| 消息 | 三栏模式（CFS/FIFO/prio） | 单任务时间 |
| 运行次数 | Web 界面可配置 | 不变 |

---

## 四、实施步骤（分步进行，确保不破坏现有功能）

### 第一步：Pipeline instrument.py 重构
- 修改输出目录结构为 result/ + timing/
- 新增 CFS、FIFO 对照组生成
- 修复 FIFO + 测时双重插桩的语法问题
- 去掉 instrument_meta.json 和 compile_and_run.sh

### 第二步：runtime_compare Task 模型改造
- Task 类新增 source_c / algo_name 字段
- TaskRunner 改为单文件编译运行逻辑
- 保留旧字段的兼容性，过渡期两种模式共存

### 第三步：runtime_compare 统计与输出改造
- 单算法 CSV 输出
- 汇总 summary_all.csv 生成
- 消息格式更新

### 第四步：Web UI 适配
- 添加任务表单改为单文件模式
- 批量导入逻辑适配新目录结构
- 消息显示适配

### 第五步：清理
- 移除旧的 baseline/prio 对比逻辑
- 移除 instrument_meta.json 生成代码
- 移除 compile_and_run.sh 生成代码
