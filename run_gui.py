#!/usr/bin/env python3
"""启动 mycallyplus GUI 的可执行入口（无需 python -m）。"""

import os
import sys


def main() -> int:
    # 确保本目录在 sys.path，便于直接运行此文件
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
    from mycallyplus.cli import main as cli_main
    return cli_main(["gui"])


if __name__ == "__main__":
    sys.exit(main())
