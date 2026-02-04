# Runtime Compare Tool

用于对比 baseline 和 prio 版本 C 程序的运行时间工具。

## 功能特性

- **多界面支持**：GUI、Web、CLI 三种模式
- **CPU 隔离**：每个任务独占一组 CPU 核心，避免干扰
- **自动配置导出**：GUI/Web 模式自动导出 JSON 配置文件，支持离线 CLI 控制
- **灵活的任务管理**：支持并行执行、排队模式、任务取消
- **详细的结果记录**：生成 summary.json、runs.csv、run.log 和 run_results.txt

## 快速开始

### Web 模式（推荐用于远程设备，如 RK3588）

```bash
# 启动 Web 服务器
python3 tools/runtime_compare/main.py --web --host 0.0.0.0 --port 5000

# 然后在浏览器中访问 http://<ip>:5000
# 支持任务配置、实时监控、配置文件管理等功能
```

详细说明参见 [Web UI 使用说明](WebUI使用说明.md)

### CLI 模式（推荐用于离线环境）

```bash
# 从配置文件加载任务
python3 tools/runtime_compare/main.py --cli --config tasks.json --wait

# 查看任务列表
python3 tools/runtime_compare/main.py --cli --list

# 查看系统状态
python3 tools/runtime_compare/main.py --cli --status
```

详细说明参见 [CLI 使用说明](CLI使用说明.md)

### GUI 模式

```bash
# 启动 GUI（待实现）
python3 tools/runtime_compare/main.py --gui
```

## 配置文件格式

参见 `example_config.json`：

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
  ],
  "queue_mode": true
}
```

## 输出结果

每个任务的结果保存在：
```
tools/runtime_compare/实验结果/<config_name>/<timestamp>_ws<work_scale>_r<repeats>/
├── summary.json          # 统计结果和元信息
├── runs.csv              # 每次运行的耗时表
├── run.log               # 完整输出日志
├── run_results_*.txt     # 三段式文本报告（与 run.sh 格式一致）
├── baseline/             # baseline 编译结果
└── prio/                 # prio 编译结果
```

配置文件保存在：
```
tools/runtime_compare/配置文件/
└── <config_name>.json    # 任务配置文件
```

## 更多文档

- [文档索引](文档索引.md) - 所有文档的索引和导航
- [架构文档](架构文档.md) - 系统架构和模块说明
- [CLI 使用说明](CLI使用说明.md) - 命令行模式详细说明
- [Web UI 使用说明](WebUI使用说明.md) - Web 界面使用指南
- [路径说明](路径说明.md) - 文件路径和目录结构
- [工作进度](工作进度.md) - 开发进度和待办事项
