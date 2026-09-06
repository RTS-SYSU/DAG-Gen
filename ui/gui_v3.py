# -*- coding: utf-8 -*-
"""
Compatibility entry point for the legacy ``mycallyplus.ui.gui_v3`` path.
The implementation is reused from ``gui.py``.
"""

from __future__ import annotations

from .gui import *  # noqa: F401,F403


def main() -> None:
    from .gui import main as _main
    _main()


if __name__ == "__main__":
    main()
