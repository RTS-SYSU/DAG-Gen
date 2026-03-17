from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .constants import META_FAILED, META_RUNNING, META_SUCCESS


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    ensure_parent(path)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def update_meta(meta_path: Path, status: str, *, step: Optional[str] = None, error: Optional[str] = None, extra: Optional[Dict[str, Any]] = None) -> None:
    data: Dict[str, Any] = {}
    if meta_path.exists():
        try:
            data = read_json(meta_path)
            if not isinstance(data, dict):
                data = {}
        except Exception:
            data = {}
    data["status"] = status
    if step is not None:
        data["step"] = step
    if error is not None:
        data["error"] = error
    else:
        # When a step is re-run successfully, clear any stale error left from previous failures.
        if status in (META_RUNNING, META_SUCCESS) and "error" in data:
            data.pop("error", None)
    if extra:
        data.update(extra)
    write_json(meta_path, data)


def mark_running(meta_path: Path, *, step: str, extra: Optional[Dict[str, Any]] = None) -> None:
    update_meta(meta_path, META_RUNNING, step=step, extra=extra)


def mark_success(meta_path: Path, *, step: str, extra: Optional[Dict[str, Any]] = None) -> None:
    update_meta(meta_path, META_SUCCESS, step=step, extra=extra)


def mark_failed(meta_path: Path, *, step: str, error: str, extra: Optional[Dict[str, Any]] = None) -> None:
    update_meta(meta_path, META_FAILED, step=step, error=error, extra=extra)
