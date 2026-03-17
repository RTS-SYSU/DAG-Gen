"""mycally – modular call graph generator with thread-aware extensions."""

import sys as _sys

from .cli import main

# Backward-compat package alias used across legacy imports.
# Running `python3 -m ScratchDAG` imports this package first, so subsequent
# `import mycallyplus_v1.*` resolves to the same package tree.
_sys.modules.setdefault("mycallyplus_v1", _sys.modules[__name__])

__all__ = ["main"]
