from __future__ import annotations

"""Unified command-line entry point.

Subcommands:
- generate: Generation stage (default, backward-compatible), arguments passed through to legacy.main()
- describe: Visualization stage, launches dag_describe GUI; supports --open <PATH> to open directly

Maintains backward compatibility: when no subcommand is given, behavior is equivalent to generate.
"""

import os
import sys
import shlex
from pathlib import Path
from typing import List, Optional

from . import legacy


def _run_describe(argv: List[str]) -> int:
    """Launch the visualization viewer (integrates test/dag_describe.py).

    Supported arguments:
      --open <PATH>  Optional, points to circle.txt / .dot / config directory
    Other arguments are ignored (interaction is handled by the GUI).
    """
    # Parse --open
    open_path: Optional[str] = None
    i = 0
    while i < len(argv):
        if argv[i] == "--open" and i + 1 < len(argv):
            open_path = argv[i + 1]
            i += 2
        else:
            i += 1

    # Pass PATH to the GUI module via environment variable to avoid conflicts with its internal argparse
    if open_path:
        os.environ["MYCALLYPRO_OPEN_PATH"] = str(Path(open_path).expanduser().resolve())

    # Launch GUI as a module, with working directory set to the project root (parent of mycallypro)
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
    """Unified CLI entry point.

    Compatible: when no subcommand is given, behaves the same as generate (passes through to legacy).
    New: describe subcommand launches interactive visualization.
    """
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        # No arguments: fall through to legacy (backward compatibility)
        original_argv = sys.argv[:]
        sys.argv = [original_argv[0]]
        try:
            return legacy.main()
        finally:
            sys.argv = original_argv

    subcmd = argv[0]
    if subcmd in ("generate", "gen"):
        # Pass remaining arguments through to legacy
        passthrough = argv[1:]
        original_argv = sys.argv[:]
        sys.argv = [original_argv[0]] + passthrough
        try:
            return legacy.main()
        finally:
            sys.argv = original_argv

    if subcmd in ("describe", "view", "viz"):
        return _run_describe(argv[1:])

    # Unknown subcommand: treat as legacy arguments for backward compatibility
    original_argv = sys.argv[:]
    sys.argv = [original_argv[0]] + argv
    try:
        return legacy.main()
    finally:
        sys.argv = original_argv
