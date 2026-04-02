#!/bin/bash
# ================================================
# ScratchDAG 60秒CPU核心测试Demo
# 用于观察特定核心的负载情况
# ================================================

echo "=== ScratchDAG 60秒CPU测试Demo ==="
echo "此任务将运行60秒，用于观察CPU核心负载"
echo "建议使用 taskset -c 6,7 ./cpu_test_60s.sh 来绑定到核心 6,7"
echo ""

if [ "$1" = "--help" ] || [ "$1" = "-h" ]; then
  echo "用法:"
  echo "  ./cpu_test_60s.sh          # 运行在所有可用核心"
  echo "  taskset -c 6,7 ./cpu_test_60s.sh  # 绑定到核心 6,7"
  exit 0
fi

echo "测试开始时间: $(date)"
echo "将运行 60 秒..."
echo "按 Ctrl+C 可提前终止"
echo ""

# 记录开始时间
start_time=$(date +%s)
end_time=$((start_time + 60))

counter=0
while [ $(date +%s) -lt $end_time ]; do
  counter=$((counter + 1))
  # 执行CPU密集型操作
  dd if=/dev/zero of=/dev/null bs=4M count=8 2>/dev/null
  # 每5秒打印一次状态
  if [ $((counter % 5)) -eq 0 ]; then
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    echo "已运行 ${elapsed} 秒... (第 $counter 次循环)"
  fi
done

echo ""
echo "测试完成时间: $(date)"
echo "总共运行了 60 秒"
echo "g_test_counter = $counter"
echo ""
echo "你可以观察 htop 中对应核心的进度条变化。"
echo "建议下次使用: taskset -c 6,7 ./cpu_test_60s.sh"
