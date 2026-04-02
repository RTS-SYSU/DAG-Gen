#!/bin/bash
# 测时版本编译和运行脚本（runtime v2.0）
# 在测时目录下执行

echo "编译测时版本..."

# 编译 baseline_FIFO (实时FIFO调度)
gcc -O2 -g -std=c11 -pthread -I"/home/firefly/Desktop/ScratchDAG/level1" baseline_FIFO.c -o baseline_FIFO -lm
if [ $? -eq 0 ]; then echo "✓ baseline_FIFO 编译完成"; else echo "✗ baseline_FIFO 编译失败"; fi

# 编译 baseline_CFS (默认CFS公平调度)
gcc -O2 -g -std=c11 -pthread -I"/home/firefly/Desktop/ScratchDAG/level1" baseline_CFS.c -o baseline_CFS -lm
if [ $? -eq 0 ]; then echo "✓ baseline_CFS 编译完成"; else echo "✗ baseline_CFS 编译失败"; fi

# 编译 prio (动态优先级插桩版本)
gcc -O2 -g -std=c11 -pthread -I"/home/firefly/Desktop/ScratchDAG/level1" prio.c -o prio -lm
if [ $? -eq 0 ]; then echo "✓ prio 编译完成"; else echo "✗ prio 编译失败"; fi

echo ""
echo "运行测试..."
echo "=== baseline_FIFO ==="
./baseline_FIFO 2>&1 | tail -5
echo ""
echo "=== baseline_CFS ==="
./baseline_CFS 2>&1 | tail -5
echo ""
echo "=== prio ==="
./prio 2>&1 | tail -5
echo ""
echo "测时完成！（runtime v2.0）"
