# CLI 使用说明

## 基本用法

```bash
python3 tools/runtime_compare/main.py --cli <操作> [选项]
```

## 操作命令

### 1. 从配置文件加载任务

```bash
python3 tools/runtime_compare/main.py --cli --config tasks.json [--wait]
```

- `--config <文件>`: 指定配置文件路径
- `--wait`: 等待所有任务完成（否则在后台运行）

示例：
```bash
# 加载并等待完成
python3 tools/runtime_compare/main.py --cli --config experiment/tasks_2026-02-01.json --wait

# 加载后在后台运行
python3 tools/runtime_compare/main.py --cli --config experiment/tasks_2026-02-01.json
```

### 2. 添加单个任务

```bash
python3 tools/runtime_compare/main.py --cli --add-task task.json [--wait]
```

- `--add-task <文件>`: 包含单个任务配置的 JSON 文件

### 3. 列出所有任务

```bash
python3 tools/runtime_compare/main.py --cli --list
```

显示所有任务的状态、阶段、CPU 分配等信息。

### 4. 查看系统状态

```bash
python3 tools/runtime_compare/main.py --cli --status
```

显示：
- 在线 CPU 列表
- 空闲 CPU 数量
- 排队模式状态
- 任务统计（运行中、等待中、已完成、失败）

### 5. 取消任务

```bash
python3 tools/runtime_compare/main.py --cli --cancel <task_id>
```

- `--cancel <task_id>`: 要取消的任务 ID（只能取消 queued 状态的任务）

## 通用选项

- `--base-dir <路径>`: 指定项目根目录（默认自动检测）
- `--queue-mode`: 启用单并发排队模式（所有任务串行执行）

## 配置文件格式

### 多任务配置

```json
{
  "tasks": [
    {
      "baseline_c": "/path/to/baseline1.c",
      "prio_c": "/path/to/prio1.c",
      "work_scale": 25000,
      "repeats": 3,
      "cores_per_task": 4,
      "cpu_list": [4, 5, 6, 7],
      "use_sudo": false
    },
    {
      "baseline_c": "/path/to/baseline2.c",
      "prio_c": "/path/to/prio2.c",
      "work_scale": 50000,
      "repeats": 5,
      "cores_per_task": 2,
      "use_sudo": false
    }
  ],
  "queue_mode": false
}
```

### 单任务配置（用于 --add-task）

```json
{
  "tasks": [
    {
      "baseline_c": "/path/to/baseline.c",
      "prio_c": "/path/to/prio.c",
      "work_scale": 25000,
      "repeats": 3,
      "cores_per_task": 4,
      "cpu_list": [4, 5, 6, 7],
      "use_sudo": false
    }
  ]
}
```

## 使用场景

### 场景 1：离线环境批量执行

1. 在 GUI/Web 界面配置好任务，自动导出配置文件
2. 在离线环境中使用 CLI 加载配置：

```bash
python3 tools/runtime_compare/main.py --cli --config experiment/tasks_2026-02-01.json --wait
```

### 场景 2：自动化脚本

```bash
#!/bin/bash
# 生成配置文件
python3 generate_tasks.py > tasks.json

# 执行任务
python3 tools/runtime_compare/main.py --cli --config tasks.json --wait

# 检查结果
python3 tools/runtime_compare/main.py --cli --status
```

### 场景 3：监控任务状态

```bash
# 定期检查状态
watch -n 5 'python3 tools/runtime_compare/main.py --cli --status'
```

## 日志

CLI 模式的日志保存在：
```
experiment/logs/cli.log
```

同时也会输出到标准输出。

## 注意事项

1. **CPU 核心分配**：
   - 如果指定了 `cpu_list`，优先使用指定的核心
   - 否则从空闲核心中自动分配
   - 确保 `cores_per_task` 不超过可用核心数

2. **排队模式**：
   - 启用 `--queue-mode` 后，所有任务串行执行
   - 适合需要严格隔离的场景

3. **sudo 权限**：
   - 如果 `use_sudo: true`，需要 root 权限或配置免密 sudo
   - 否则可能无法写入某些目录

4. **任务取消**：
   - 只能取消 `queued` 状态的任务
   - 正在运行的任务无法取消
