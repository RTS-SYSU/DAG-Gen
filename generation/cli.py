from __future__ import annotations

"""统一命令行入口。

子命令：
- generate: 生成阶段（默认，向后兼容），参数透传给 legacy.main()
- describe: 可视化阶段，启动 dag_describe GUI；支持 --open <PATH> 直接打开

保持对旧用法的兼容：无子命令时，行为等同于 generate。
"""

import os
import sys
import shlex
from pathlib import Path
from typing import List, Optional

from . import legacy


def _run_describe(argv: List[str]) -> int:
    """启动可视化（整合 test/dag_describe.py）。

    支持参数：
      --open <PATH>  可选，指向 circle.txt / .dot / 配置目录
    其余参数忽略（交互由GUI完成）。
    """
    # 解析 --open
    open_path: Optional[str] = None
    i = 0
    while i < len(argv):
        if argv[i] == "--open" and i + 1 < len(argv):
            open_path = argv[i + 1]
            i += 2
        else:
            i += 1

    # 将 PATH 通过环境变量传给 GUI 模块，避免与其内部 argparse 冲突
    if open_path:
        os.environ["MYCALLYPRO_OPEN_PATH"] = str(Path(open_path).expanduser().resolve())

    # 以模块方式启动 GUI，工作目录设为项目根（mycallypro 的父目录）
    project_root = Path(__file__).resolve().parent
    work_dir = project_root.parent

    cmd = [sys.executable, "-m", "test.dag_describe"]
    try:
        import subprocess
        proc = subprocess.run(
            cmd,
            cwd=str(work_dir),
        )
        return proc.returncode
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        sys.stderr.write(f"ERROR: Failed to launch viewer: {exc}\n")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """统一 CLI 入口。

    兼容：无子命令时等同 generate（透传给 legacy）。
    新增：describe 子命令启动交互式可视化。
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        # 无参数，直接走 legacy（向后兼容）
        original_argv = sys.argv[:]
        sys.argv = [original_argv[0]]
        try:
            return legacy.main()
        finally:
            sys.argv = original_argv

    subcmd = argv[0]
    if subcmd in ("generate", "gen"):
        # 透传余下参数给 legacy
        passthrough = argv[1:]
        original_argv = sys.argv[:]
        sys.argv = [original_argv[0]] + passthrough
        try:
            return legacy.main()
        finally:
            sys.argv = original_argv

    if subcmd in ("describe", "view", "viz"):
        return _run_describe(argv[1:])

    # 未知子命令：为兼容旧用法，视为 legacy 参数
    original_argv = sys.argv[:]
    sys.argv = [original_argv[0]] + argv
    try:
        return legacy.main()
    finally:
        sys.argv = original_argv
