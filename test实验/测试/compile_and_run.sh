#!/bin/bash
echo "=== ScratchDAG 测试Demo 编译与运行 ==="

echo "编译 small_prio_demo..."
gcc -O2 -g -std=c11 -pthread -I. small_prio_demo.c -o small_prio_demo -lm && echo "✓ small_prio_demo 编译成功" || { echo "✗ 编译失败"; exit 1; }

echo ""
echo "=== 运行测试 ==="
echo "运行 demo (推荐使用 sudo 以设置实时优先级):"
echo "sudo ./small_prio_demo"
echo ""
echo "或者直接运行（优先级设置可能失败）:"
./small_prio_demo 2>&1 | tail -10

echo ""
echo "提示：修改 small_prio_demo.c 中的优先级后重新运行此脚本。"
echo "当前工作目录: $(pwd)"
