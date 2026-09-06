from __future__ import annotations

"""Unified command-line entry point.

Subcommands:
- generate: Generation stage (default, backward-compatible), arguments passed through to legacy.main()
- describe: Visualization stage, launches viewer GUI; supports --open <PATH> to open directly
- gui: Launch the unified GUI workbench

Maintains backward compatibility: when no subcommand is given, launches the unified GUI.
"""

import os
import sys
import shlex
from pathlib import Path
from typing import List, Optional

from .runtime_env import PACKAGE_NAME


def _import_legacy_module():
    """Import legacy generator implemented inside mycallyplus."""
    from .generation import legacy  # type: ignore
    return legacy


def _run_gui() -> int:
    """Launch the unified GUI workbench."""
    try:
        # Use the GUI main interface (originally v3)
        from .ui.gui import main as gui_main
        gui_main()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        msg = str(exc)
        sys.stderr.write(f"ERROR: Failed to launch GUI: {msg}\n")
        if "ImageTk" in msg and "PIL" in msg:
            sys.stderr.write(
                "HINT: The current Python environment is missing Pillow Tk support.\n"
                f"1) Preferred: run without sudo: python3 -m {PACKAGE_NAME}\n"
                "2) Install dependency: python3 -m pip install pillow\n"
                "3) If you must run with sudo, also install pillow in the root environment.\n"
            )
        return 1


def _run_describe(argv: List[str]) -> int:
    """Launch the visualization viewer (using the internal viewer).

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

    # Pass PATH to the GUI module via environment variable
    if open_path:
        os.environ["MYCALLYPRO_OPEN_PATH"] = str(Path(open_path).expanduser().resolve())

    # Launch the viewer GUI
    try:
        from .visualization.viewer import main as viewer_main
        viewer_main()
        return 0
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        sys.stderr.write(f"ERROR: Failed to launch viewer: {exc}\n")
        return 1


def _run_pipeline(argv: List[str]) -> int:
    try:
        from .pipeline.cli import main as pipeline_main

        return int(pipeline_main(argv))
    except KeyboardInterrupt:
        return 130
    except Exception as exc:
        sys.stderr.write(f"ERROR: Failed to run pipeline: {exc}\n")
        return 1


def main(argv: Optional[List[str]] = None) -> int:
    """Unified CLI entry point.

    No arguments or gui subcommand: launch unified GUI
    generate: Generate DAG (command-line mode)
    describe: Visualize DAG (standalone viewer)
    """
    if argv is None:
        argv = sys.argv[1:]

    # No arguments: launch GUI
    if not argv:
        return _run_gui()

    subcmd = argv[0]

    # GUI subcommand
    if subcmd in ("gui", "ui"):
        return _run_gui()

    # Generate subcommand
    if subcmd in ("generate", "gen"):
        legacy = _import_legacy_module()
        passthrough = argv[1:]
        original_argv = sys.argv[:]
        sys.argv = [original_argv[0]] + passthrough
        try:
            return legacy.main()
        finally:
            sys.argv = original_argv

    # Visualization subcommand
    if subcmd in ("describe", "view", "viz"):
        return _run_describe(argv[1:])

    # Modular pipeline subcommand
    if subcmd in ("pipeline", "pipe"):
        return _run_pipeline(argv[1:])

    # Unknown subcommand: treat as generate arguments (backward compatibility)
    legacy = _import_legacy_module()
    original_argv = sys.argv[:]
    sys.argv = [original_argv[0]] + argv
    try:
        return legacy.main()
    finally:
        sys.argv = original_argv
