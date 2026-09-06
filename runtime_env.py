from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Dict, Optional


PACKAGE_NAME = __name__.split(".", 1)[0]
PROJECT_ROOT = Path(__file__).resolve().parent
PROJECT_PARENT = PROJECT_ROOT.parent


def default_base_dir() -> Path:
    return PROJECT_ROOT


def package_module_name(relative_module: str = "") -> str:
    return PACKAGE_NAME if not relative_module else f"{PACKAGE_NAME}.{relative_module}"


def module_cmd(relative_module: str, *, python_executable: Optional[str] = None) -> list[str]:
    return [python_executable or sys.executable, "-m", package_module_name(relative_module)]


def module_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = dict(os.environ if extra is None else extra)
    pythonpath_parts = [str(PROJECT_PARENT)]
    existing = env.get("PYTHONPATH", "").strip()
    if existing:
        pythonpath_parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
    return env


def looks_like_repo_root(path: Path) -> bool:
    return (path / "cli.py").exists() and (path / "__main__.py").exists()


def locate_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in [cur, *cur.parents]:
        if looks_like_repo_root(parent):
            return parent
    raise RuntimeError(f"Cannot locate repo root from: {start}")
