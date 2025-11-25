#!/usr/bin/env bash
set -euo pipefail

# 切换到脚本所在目录，确保相对路径正确
cd "$(dirname "$0")"

# 启动 mycallyplus GUI（直接运行脚本）
python3 run_gui.py
