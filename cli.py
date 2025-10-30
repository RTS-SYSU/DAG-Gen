from __future__ import annotations

"""统一命令行入口。

子命令：
- generate: 生成阶段（默认，向后兼容），参数透传给 legacy.main()
- describe: 可视化阶段，启动 viewer GUI；支持 --open <PATH> 直接打开
- gui: 启动统一GUI工作台

保持对旧用法的兼容：无子命令时，启动统一GUI。
"""

import os
import sys
import shlex
from pathlib import Path
from typing import List, Optional


def _import_legacy_module():
    """Import legacy generator, fallback to mycallypro when packaged module missing."""
    try:
        from .generation import legacy  # type: ignore
    except Exception:
        from mycallypro import legacy  # type: ignore
    return legacy


def _run_gui() -> int:
    """启动统一GUI工作台"""
    try:
        # 使用新的v3 GUI
        from .ui.gui_v3 import main as gui_main
        gui_main()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        sys.stderr.write(f"ERROR: Failed to launch GUI: {exc}\n")
        return 1


def _run_describe(argv: List[str]) -> int:
    """启动可视化（使用内部viewer）。

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

    # 将 PATH 通过环境变量传给 GUI 模块
    if open_path:
        os.environ["MYCALLYPRO_OPEN_PATH"] = str(Path(open_path).expanduser().resolve())

    # 启动viewer GUI
    try:
        from .visualization.viewer import main as viewer_main
        viewer_main()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        sys.stderr.write(f"ERROR: Failed to launch viewer: {exc}\n")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """统一 CLI 入口。

    无参数或 gui 子命令：启动统一GUI
    generate：生成DAG（命令行模式）
    describe：可视化DAG（独立查看器）
    """
    if argv is None:
        argv = sys.argv[1:]

    # 无参数：启动GUI
    if not argv:
        return _run_gui()

    subcmd = argv[0]
    
    # GUI 子命令
    if subcmd in ("gui", "ui"):
        return _run_gui()
    
    # 生成子命令
    if subcmd in ("generate", "gen"):
        legacy = _import_legacy_module()
        passthrough = argv[1:]
        original_argv = sys.argv[:]
        sys.argv = [original_argv[0]] + passthrough
        try:
            return legacy.main()
        finally:
            sys.argv = original_argv

    # 可视化子命令
    if subcmd in ("describe", "view", "viz"):
        return _run_describe(argv[1:])

    # 未知子命令：视为 generate 参数（向后兼容）
    legacy = _import_legacy_module()
    original_argv = sys.argv[:]
    sys.argv = [original_argv[0]] + argv
    try:
        return legacy.main()
    finally:
        sys.argv = original_argv
