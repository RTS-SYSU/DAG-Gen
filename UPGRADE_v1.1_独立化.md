# Mycallyplus v1.1 升级说明 - 完全独立化

**升级日期**: 2025-10-30  
**版本**: v1.0 → v1.1  
**主要变更**: 将所有输出目录从 `mycallypro/` 迁移到 `mycallyplus/`，实现完全独立

---

## 📋 升级概述

### 变更动机

原先 mycallyplus 的输出文件（配置文件、中间结果、dag图等）默认保存在 `mycallypro/` 目录下，这导致：
1. mycallyplus 项目不完全独立
2. 与 mycallypro 项目产生不必要的耦合
3. 用户可能混淆两个项目的输出

### 升级目标

将 mycallyplus 改为**完全独立**的项目，所有输出文件保存在自己的目录下：
- ✅ 配置文件目录：`mycallyplus/配置文件/`
- ✅ 中间结果目录：`mycallyplus/中间结果/`
- ✅ DAG图输出目录：`mycallyplus/dag图/`
- ✅ 源文件目录：`mycallyplus/源文件/`

---

## 🔧 代码修改清单

### 1. GUI 代码修改

#### 1.1 `mycallyplus/ui/gui_v3.py`

**修改位置**: Line 91

```python
# 修改前
self.base_dir = Path(__file__).resolve().parent.parent.parent / "mycallypro"

# 修改后
self.base_dir = Path(__file__).resolve().parent.parent
```

**说明**: 将工作路径从 `mycallypro/` 改为 `mycallyplus/`

---

#### 1.2 `mycallyplus/ui/gui.py`

**修改位置**: Line 118

```python
# 修改前
self.base_dir = Path(__file__).resolve().parent.parent.parent / "mycallypro"

# 修改后
self.base_dir = Path(__file__).resolve().parent.parent
```

**修改位置**: 多处注释（Line 1171, 1187, 1222, 1238, 1273, 1291）

```python
# 修改前注释
# 调用 legacy，指定output_base为mycallypro目录
# legacy 会生成在 mycallypro/配置文件/<basename>/...

# 修改后注释
# 调用 legacy，指定output_base为mycallyplus目录
# legacy 会生成在 mycallyplus/配置文件/<basename>/...
```

---

### 2. Legacy 生成逻辑修改

#### 2.1 `mycallyplus/generation/legacy.py`

**修改位置**: Line 1484-1486

```python
# 修改前
# 如果没有指定output_base，默认使用mycallypro目录
if not hasattr(config, 'output_base') or not config.output_base:
    config.output_base = str(Path(__file__).parent)

# 修改后
# 如果没有指定output_base，默认使用mycallyplus目录
if not hasattr(config, 'output_base') or not config.output_base:
    config.output_base = str(Path(__file__).parent.parent)
```

**说明**: 
- 修改前：`Path(__file__).parent` 指向 `mycallyplus/generation/`
- 修改后：`Path(__file__).parent.parent` 指向 `mycallyplus/`

---

### 3. 文档修改

#### 3.1 `mycallyplus/FULL_FEATURE_GUIDE_CN.md`

**修改内容**:

1. **§1 总体架构**: 
   - base 的取值从 `mycallypro/` 改为 `mycallyplus/`

2. **§2 CLI 子命令**:
   - `--output-base` 推荐值从 `mycallypro/` 改为 `mycallyplus/`

3. **§7 输出文件清单**:
   - 示例路径从 `<base>=mycallypro/` 改为 `<base>=mycallyplus/`

---

## 📂 目录结构变化

### 修改前

```
cally/
├── mycallypro/           ← 原输出目录
│   ├── 配置文件/
│   ├── 中间结果/
│   └── dag图/
├── mycallyplus/          ← 源代码
│   ├── core/
│   ├── generation/
│   ├── ui/
│   └── visualization/
```

### 修改后

```
cally/
├── mycallypro/           ← 保持不变（独立项目）
│   └── ...
├── mycallyplus/          ← 完全独立
    ├── core/
    ├── generation/
    ├── ui/
    ├── visualization/
    ├── 配置文件/         ← 新增：输出目录
    ├── 中间结果/         ← 新增：临时文件
    ├── dag图/            ← 新增：可视化图片
    └── 源文件/           ← 新增：编译生成的RTL文件
```

---

## 🎯 影响范围

### 对用户的影响

#### GUI 用户
- ✅ **无需修改任何操作流程**
- ✅ 输出文件自动保存到 `mycallyplus/` 目录
- ✅ 与 mycallypro 项目完全隔离

#### CLI 用户
- ⚠️ 如果之前未指定 `--output-base`，输出位置会变化
- ✅ 建议显式指定 `--output-base mycallyplus/`
- ✅ 或者直接使用默认值（自动指向 `mycallyplus/`）

#### 开发者
- ✅ 项目依赖关系更清晰
- ✅ 便于独立测试和部署
- ✅ 减少与 mycallypro 的耦合

---

## 🚀 使用示例

### GUI 使用（推荐）

```bash
cd /home/chove/桌面/cally
python -m mycallyplus

# 输出自动保存到：
# - mycallyplus/配置文件/<basename>/
# - mycallyplus/中间结果/<basename>/
# - mycallyplus/dag图/图N/
```

### CLI 使用

```bash
cd /home/chove/桌面/cally

# 方式1: 使用默认输出路径（推荐）
python -m mycallyplus generate file.c.233r.expand --threads-only
# → 输出到 mycallyplus/配置文件/file/

# 方式2: 显式指定输出路径
python -m mycallyplus generate file.c.233r.expand \
    --output-base mycallyplus/ \
    --export-txt
# → 输出到 mycallyplus/配置文件/file/
```

---

## ✅ 验证测试

### 1. 测试 GUI

```bash
cd /home/chove/桌面/cally
python -m mycallyplus

# 操作步骤：
# 1. 选择源文件
# 2. 生成dag图
# 3. 检查输出路径
```

**预期结果**:
```
mycallyplus/
├── 配置文件/
│   └── <basename>/
│       ├── <basename>_threads.dot
│       └── <basename>.c.233r.expand
└── 中间结果/
    └── <basename>/
        └── 生成dag图/
            ├── dag.dot
            └── dag.png
```

### 2. 测试 CLI

```bash
cd /home/chove/桌面/cally

# 测试默认输出
python -m mycallyplus generate 测试示例/produce5/main.c.233r.expand

# 检查文件
ls -la mycallyplus/配置文件/main/
```

**预期输出**:
```
mycallyplus/配置文件/main/
├── main.dot
├── main.c.233r.expand
└── (其他生成文件)
```

---

## 🔄 迁移指南

### 如果您之前使用过 v1.0

#### 选项 1: 清理旧文件（推荐）

```bash
cd /home/chove/桌面/cally

# 备份 mycallypro 输出（如果需要）
cp -r mycallypro/配置文件 mycallypro/配置文件.backup
cp -r mycallypro/中间结果 mycallypro/中间结果.backup
cp -r mycallypro/dag图 mycallypro/dag图.backup

# 清理旧输出（可选）
rm -rf mycallypro/配置文件
rm -rf mycallypro/中间结果
rm -rf mycallypro/dag图
```

#### 选项 2: 迁移文件到新位置

```bash
cd /home/chove/桌面/cally

# 将旧输出迁移到 mycallyplus
mv mycallypro/配置文件 mycallyplus/配置文件
mv mycallypro/中间结果 mycallyplus/中间结果
mv mycallypro/dag图 mycallyplus/dag图
```

---

## 📝 注意事项

### 1. 与 mycallypro 的关系

- ✅ **mycallypro 项目保持不变**
- ✅ mycallyplus 不会影响 mycallypro 的任何文件
- ✅ 两个项目完全独立，互不干扰

### 2. 配置文件兼容性

- ✅ 所有配置文件格式保持不变
- ✅ 旧的 `circle.txt` 可直接使用
- ✅ DOT 文件格式完全兼容

### 3. 磁盘空间

- ⚠️ 如果同时使用两个项目，会占用更多磁盘空间
- 💡 建议定期清理不需要的中间结果文件

---

## 🐛 故障排查

### 问题 1: 找不到输出文件

**症状**: GUI 提示"未找到生成的DOT文件"

**解决**:
```bash
# 检查 mycallyplus 目录是否存在
ls -la mycallyplus/

# 手动创建目录
mkdir -p mycallyplus/配置文件
mkdir -p mycallyplus/中间结果
mkdir -p mycallyplus/dag图
```

### 问题 2: 权限错误

**症状**: "Permission denied" 错误

**解决**:
```bash
# 检查目录权限
ls -la mycallyplus/

# 修复权限
chmod -R u+w mycallyplus/
```

### 问题 3: 旧文件冲突

**症状**: 文件已存在但内容不一致

**解决**:
```bash
# 使用 --clean 选项重新生成
python -m mycallyplus generate file.expand --clean

# 或手动删除旧文件
rm -rf mycallyplus/配置文件/<basename>
```

---

## 📊 性能影响

- ✅ **无性能影响**: 仅改变输出路径，不影响处理速度
- ✅ **磁盘I/O**: 与之前完全相同
- ✅ **内存使用**: 无变化

---

## 🎉 升级完成

恭喜！您已成功升级到 Mycallyplus v1.1。

### 快速验证

```bash
cd /home/chove/桌面/cally
python -m mycallyplus

# 检查是否正常工作
ls -la mycallyplus/配置文件/
ls -la mycallyplus/中间结果/
ls -la mycallyplus/dag图/
```

### 获取帮助

如有问题，请参考：
- `mycallyplus/README.md` - 项目说明
- `mycallyplus/QUICK_START.md` - 快速入门
- `mycallyplus/FULL_FEATURE_GUIDE_CN.md` - 完整功能指南

---

**升级完成时间**: 2025-10-30  
**下一版本计划**: v1.2 - 性能优化与批处理支持
