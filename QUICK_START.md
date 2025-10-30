# Mycallyplus 快速入门指南

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /home/chove/桌面/cally/mycallyplus
pip install -r requirements.txt
```

### 2. 三种使用方式

#### 方式一：统一GUI（推荐）

```bash
cd /home/chove/桌面/cally
python -m mycallyplus
```

#### 方式二：命令行生成

```bash
cd /home/chove/桌面/cally
python -m mycallyplus generate 测试示例/produce5/main.c.233r.expand
python -m mycallyplus generate 测试示例/produce5/main.c.233r.expand --threads-only
python -m mycallyplus generate 测试示例/produce5/main.c.233r.expand --conditions-only
```

#### 方式三：独立可视化

```bash
cd /home/chove/桌面/cally
python -m mycallyplus describe
python -m mycallyplus describe --open mycallyplus/配置文件/main/
```

---

## 📖 统一GUI使用教程

### 工作流程

```
1. 选择源文件
   ↓
2. 生成DAG（三种模式可选）
   ↓ (自动加载)
3. 可视化分析
   ├─ 查看原始图
   ├─ 分析互斥锁
   └─ 分析信号量
```

### 详细步骤

#### Step 1: 选择源文件

1. 点击"选择源文件"按钮
2. 选择C文件或expand文件
   - **C文件**: 自动调用GCC编译生成expand
   - **expand文件**: 直接使用

状态栏会显示：`源文件：main.c.233r.expand | ...`

#### Step 2: 生成DAG

根据需求选择生成模式：

**A. 生成线程DAG**
- 只显示线程创建和调用关系
- 不包含条件节点
- 最简洁的视图

**B. 生成条件DAG**
- 只显示if/while/switch等条件节点
- 用于分析控制流

**C. 生成完整DAG（推荐）**
- 包含所有调用关系
- 包含线程补边
- 包含条件节点
- 最完整的视图

生成后会自动：
- ✅ 创建配置目录 `mycallyplus/配置文件/<basename>/`
- ✅ 生成DOT文件
- ✅ 渲染为PNG图像
- ✅ 自动显示在画布上
- ✅ 更新状态栏信息

#### Step 3: 生成配置文件（可选）

点击"生成配置文件"按钮：
- 生成 `circle.txt`
- 包含互斥锁和信号量信息
- 用于后续的可视化分析

#### Step 4: 可视化分析

**A. 生成原始图**
- 显示基本的调用关系图
- 无特殊标记

**B. 查看互斥锁**
- 解析circle.txt中的互斥锁信息
- 用颜色框标记lock→unlock覆盖区域
- 子功能：
  - 查看互斥锁图
  - 查看互斥锁信息（文本）

**C. 生成信号量图**
- 添加sem_post→sem_wait虚线边
- 运行Tarjan算法找强连通分量
- 按线程分组显示
- 子功能：
  - 查看原始图
  - 查看Tarjan图（强连通分量）
  - 查看线程图（分组显示）
  - 显示信号量信息
  - 显示线程颜色图例

---

## 💡 使用技巧

### 画布操作

- **拖动**: 鼠标左键拖动画布
- **缩放**: 鼠标滚轮放大/缩小
- **浏览**: 自动调整滚动区域

### 文件组织

生成的文件会自动保存在：

```
mycallyplus/
├── 配置文件/           # 最终输出
│   └── <basename>/
│       ├── dag_full.dot
│       ├── circle.txt
│       └── *.png
│
├── 中间结果/           # 临时文件
│   └── <basename>/
│       └── debug/
│
├── dag图/             # 可视化输出
│   └── 图1/, 图2/...
│
└── 源文件/            # 编译生成的expand
```

### 快捷工作流

#### 工作流1：快速生成和查看

```
1. 选择源文件
2. 生成完整DAG
   ↓ (自动显示)
3. 完成！
```

#### 工作流2：深度分析

```
1. 选择源文件
2. 生成完整DAG
3. 生成配置文件
4. 查看互斥锁
5. 生成信号量图
   ├─ 切换各种视图
   └─ 查看详细信息
```

#### 工作流3：仅查看已有配置

```
1. 点击"选择配置文件"
2. 选择配置文件夹
3. 生成原始图
4. 查看互斥锁/信号量
```

---

## 🔍 示例演示

### 示例1：分析produce5项目

```bash
cd /home/chove/桌面/cally
python -m mycallyplus
```

1. 选择源文件: `测试示例/produce5/main.c.233r.expand`
2. 点击"生成完整DAG"
3. 点击"生成配置文件"
4. 点击"生成信号量图"
5. 使用子功能查看各种视图

结果：
- ✅ DOT文件: `mycallyplus/配置文件/main/dag_full.dot`
- ✅ 配置文件: `mycallyplus/配置文件/main/circle.txt`
- ✅ 图像: `mycallyplus/dag图/图1/*.png`

### 示例2：命令行批处理

```bash
# 生成多个文件的DAG
for file in 测试示例/produce5/*.expand; do
    python -m mycallyplus generate "$file" --threads-only
done
```

### 示例3：查看已有配置

```bash
# 启动独立查看器
python -m mycallyplus describe --open mycallyplus/配置文件/main/
```

---

## 🐛 故障排查

### 问题1：模块导入失败

**症状**: `ModuleNotFoundError: No module named 'mycallyplus'`

**解决**:
```bash
# 确保在正确的目录
cd /home/chove/桌面/cally
python -m mycallyplus
```

### 问题2：GCC编译失败

**症状**: "GCC未生成expand文件"

**解决**:
- 检查系统是否安装GCC: `gcc --version`
- 直接使用expand文件而不是C文件
- 手动编译: `gcc -fdump-rtl-expand -O2 -c file.c`

### 问题3：Graphviz错误

**症状**: "Graphviz 错误"

**解决**:
```bash
# 安装Graphviz
sudo apt-get install graphviz  # Ubuntu/Debian
brew install graphviz           # macOS

# 验证安装
dot -V
```

### 问题4：图像不显示

**症状**: 画布空白

**解决**:
- 检查文件权限
- 查看是否有错误弹窗
- 检查 `配置文件/` 和 `dag图/` 目录

---

## 📚 进阶用法

### 自定义配置

编辑 `circle.txt` 手动添加互斥锁/信号量信息：

```
互斥量
main/pthread_mutex_lock5 mutex mutex1 42 main.c
main/pthread_mutex_unlock7 mutex mutex1 56 main.c

信号量
thread1/sem_post3 sem sem1 23 thread.c
thread2/sem_wait5 sem sem1 89 thread.c
```

### 批量处理脚本

```bash
#!/bin/bash
# 批量生成DAG

for dir in 测试示例/*/; do
    for expand in "$dir"*.expand; do
        [ -f "$expand" ] || continue
        echo "Processing: $expand"
        python -m mycallyplus generate "$expand"
    done
done
```

---

## 📞 获取帮助

### 查看文档

- `README.md` - 完整说明
- `PROJECT_COMPLETION.md` - 项目总结
- 本文档 - 快速入门

### 运行测试

```bash
python test_mycallyplus.py
```

---

## ✨ 最佳实践

1. **始终使用完整路径**: 避免相对路径问题
2. **先生成再分析**: 按照工作流顺序操作
3. **保存重要结果**: 配置文件可以重复使用
4. **定期清理**: 删除不需要的中间文件
5. **使用版本控制**: 对重要的circle.txt配置进行版本管理

---

**祝您使用愉快！** 🎉

如有问题或建议，请查看项目文档或运行测试脚本。
