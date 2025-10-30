# Mycallyplus - 统一调用图生成与可视化工具

## 概述

Mycallyplus 是 mycallypro 和 dag_describe 的整合版本，提供统一的调用图生成和可视化功能。

## 目录结构

```
mycallyplus/
├── __init__.py              # 包初始化
├── __main__.py              # 模块入口
├── cli.py                   # 命令行接口
├── requirements.txt         # 依赖清单
│
├── core/                    # 核心功能模块
│   ├── __init__.py
│   ├── parser.py            # RTL解析器
│   ├── model.py             # 数据模型
│   ├── control_flow.py      # 控制流分析
│   ├── threads.py           # 线程分析
│   └── thread_map.py        # 线程映射
│
├── generation/              # 生成模块
│   ├── __init__.py
│   ├── legacy.py            # 主生成逻辑
│   ├── builder.py           # DAG构建
│   ├── renderer.py          # DOT渲染
│   ├── exporters.py         # 导出器
│   └── source_binder.py     # 源码绑定
│
├── visualization/           # 可视化模块
│   ├── __init__.py
│   └── viewer.py            # 可视化查看器
│
├── ui/                      # 用户界面
│   ├── __init__.py
│   ├── gui.py               # 统一GUI（整合生成+可视化）
│   └── generation_gui.py    # 原生成GUI（备份）
│
├── 配置文件/                # 生成的配置输出
├── 中间结果/                # 临时文件
└── 源文件/                  # 源代码存放
```

## 使用方法

### CLI 命令

```bash
# 启动统一GUI（默认）
python -m mycallyplus
python -m mycallyplus gui

# 命令行生成DAG
python -m mycallyplus generate <expand文件> [选项]
python -m mycallyplus generate file.c.233r.expand --threads-only
python -m mycallyplus generate file.c.233r.expand --conditions-only
python -m mycallyplus generate file.c.233r.expand --smart  # 智能模式
python -m mycallyplus generate file.c.233r.expand --clean  # 清理重建

# 启动独立可视化查看器
python -m mycallyplus describe
python -m mycallyplus describe --open 配置文件/main/
python -m mycallyplus describe --open 配置文件/main/dag_full.dot
```

### 统一GUI功能

#### 主功能区（10个按钮）

**生成功能（5个）：**
1. **选择源文件** - 选择C或expand文件
2. **生成线程DAG** - 生成线程调用图（`--threads-only`）
3. **生成条件DAG** - 生成条件节点图（`--conditions-only`）
4. **生成完整DAG** - 生成完整调用图
5. **生成配置文件** - 导出circle.txt配置

**可视化功能（5个）：**
6. **使用默认配置(dag1)** - 快速加载默认配置
7. **选择配置文件** - 选择配置文件夹
8. **生成原始图** - 显示原始调用图
9. **查看互斥锁** - 互斥锁分析
10. **生成信号量图** - 信号量分析与Tarjan强连通分量

#### 动态子功能区

- **互斥锁子功能**：查看图 | 查看信息
- **信号量子功能**：原始图 | Tarjan图 | 线程图 | 信息 | 颜色图例

#### 特点

- **自动联动**：生成后直接加载到可视化区
- **状态栏**：同时显示源文件和配置路径
- **交互式画布**：支持拖动、缩放

## 功能特性

### 生成功能
- 从C文件或expand文件生成调用图
- 支持线程补边分析
- 条件节点提取（if/while/switch）
- 互斥锁和信号量识别
- 智能冗余处理（--smart/--clean/--force）

### 可视化功能
- 原始调用图展示
- 互斥锁覆盖区域可视化
- 信号量配对与环检测
- Tarjan强连通分量分析
- 线程颜色标记与分组

## 当前状态

### ✅ 已完成
- ✅ 工程化目录结构（core/generation/visualization/ui）
- ✅ 核心模块整合完成
- ✅ CLI命令行接口（gui/generate/describe子命令）
- ✅ 统一GUI完整实现（10个主功能按钮全部可用）
- ✅ 生成功能集成（5个按钮）
- ✅ 可视化功能集成（5个按钮）
- ✅ 依赖配置（requirements.txt）
- ✅ 所有模块导入测试通过

### 🧪 测试状态
运行测试脚本验证：
```bash
python test_mycallyplus.py
```

所有4项测试通过：
- ✅ 目录结构
- ✅ 模块导入
- ✅ CLI功能
- ✅ GUI类（10个方法）

## 依赖

- Python 3.7+
- networkx >= 2.6
- pillow >= 9.0.0
- pydot >= 1.4.2 (可选)
- Graphviz (系统工具)

## 安装

```bash
# 进入项目目录
cd mycallyplus

# 安装依赖
pip install -r requirements.txt

# 确保系统安装了Graphviz
sudo apt-get install graphviz  # Ubuntu/Debian
brew install graphviz           # macOS
```

## 与原项目的关系

- **mycallypro** 和 **test/** 保持不变，作为独立项目继续使用
- **mycallyplus** 是整合版本，独立运行，不依赖其他两个项目
- 所有配置和输出相对于 mycallyplus 目录

## 后续开发

1. 补充 GUI 可视化功能的完整实现
2. 添加单元测试
3. 完善文档和使用示例
4. 性能优化
5. 添加更多导出格式支持
