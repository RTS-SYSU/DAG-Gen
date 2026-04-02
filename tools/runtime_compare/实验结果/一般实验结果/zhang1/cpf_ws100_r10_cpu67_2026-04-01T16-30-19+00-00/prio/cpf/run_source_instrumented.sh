#!/bin/bash
echo "=== 编译并运行 source_instrumented.c ==="

cd "/home/firefly/Desktop/ScratchDAG/中间结果/zhang1/pipeline/instrument/level2/effective_line_merge/cpf"

echo "正在编译..."
gcc -O2 -g -std=c11 -pthread -lrt \
    -I"/home/firefly/Desktop/ScratchDAG/level1" \
    -I. \
    source_instrumented.c \
    -o source_instrumented \
    -lm && echo "✓ 编译成功" || { echo "✗ 编译失败"; exit 1; }

echo "正在运行..."
echo "注意：如果看到 L1_PRIO_SET_FAILED，说明没有root权限，优先级设置未生效"
./source_instrumented 2>&1 | tail -20

echo ""
echo "运行完成。修改优先级后可重新运行此脚本。"
