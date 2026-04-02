#!/bin/bash
# ================================================
# ScratchDAG 实验核心隔离脚本
# 功能：将系统任务限制在核心 0-5，预留核心 6-7 专门用于实验
# ================================================

set -e

echo "=== ScratchDAG 实验核心隔离设置 ==="
echo "目标：系统任务 → 核心 0-5，实验专用 → 核心 6-7"
echo ""

# 检查是否以 root 权限运行
if [ "$EUID" -ne 0 ]; then
  echo "错误：请使用 sudo 运行此脚本"
  echo "用法: sudo $0"
  exit 1
fi

echo "正在配置 cpuset..."

# 挂载 cpuset 如果未挂载
if [ ! -d /sys/fs/cgroup/cpuset ]; then
  mount -t cpuset cpuset /sys/fs/cgroup/cpuset 2>/dev/null || true
fi

# 创建系统任务 cpuset
SYSTEM_CGROUP="/sys/fs/cgroup/cpuset/system"
if [ ! -d "$SYSTEM_CGROUP" ]; then
  mkdir -p "$SYSTEM_CGROUP"
fi

# 设置系统任务只能使用核心 0-5
echo "0-5" > "$SYSTEM_CGROUP/cpuset.cpus"
echo "0" > "$SYSTEM_CGROUP/cpuset.mems"

echo "✓ 系统任务已限制在核心 0-5"

# 迁移所有现有进程到系统 cpuset
echo "正在迁移现有进程到系统 cpuset..."
COUNT=0
for pid in $(ps -eo pid); do
  if echo "$pid" > "$SYSTEM_CGROUP/tasks" 2>/dev/null; then
    COUNT=$((COUNT + 1))
  fi
done

echo "✓ 已迁移 $COUNT 个进程到系统 cpuset"

# 显示当前状态
echo ""
echo "=== 当前隔离状态 ==="
echo "系统任务允许的核心: $(cat $SYSTEM_CGROUP/cpuset.cpus)"
echo "实验可用核心: 6,7"
echo ""

echo "=== 使用说明 ==="
echo "1. 运行你的实验程序时使用以下命令绑定到核心 6,7："
echo "   taskset -c 6,7 ./your_program"
echo "   或在代码中添加："
echo "   CPU_ZERO(&set);"
echo "   CPU_SET(6, &set);"
echo "   CPU_SET(7, &set);"
echo "   sched_setaffinity(0, sizeof(set), &set);"
echo ""
echo "2. 恢复所有核心使用权（如果需要）："
echo "   echo 0-7 > /sys/fs/cgroup/cpuset/cpuset.cpus"
echo ""
echo "隔离设置完成！核心 6 和 7 已预留给实验使用。"

# 显示当前 CPU 亲和性状态
echo ""
echo "当前 top 5 进程的 CPU 分布："
ps -eo pid,psr,pcpu,comm --sort=psr | head -n 8
