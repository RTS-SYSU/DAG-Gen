# -*- coding: utf-8 -*-
"""
兼容入口：保持对旧路径 mycallyplus.ui.gui_v3 的支持，实际复用 gui.py。
"""

from __future__ import annotations

from .gui import *  # noqa: F401,F403


def main() -> None:
    from .gui import main as _main
    _main()


if __name__ == "__main__":
    main()
