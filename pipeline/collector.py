from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import CONFIG_DIR_NAME, GEN_DIR_NAME, PIPELINE_DIR_NAME, RESULTS_ROOT_NAME, SCHEMA_VERSION
from .errors import StageError
from .io_utils import mark_failed, mark_running, mark_success, write_json

_MU_LOCK_RE = re.compile(r"(^|/)pthread_mutex_lock(\d+)?$")
_MU_UNLOCK_RE = re.compile(r"(^|/)pthread_mutex_unlock(\d+)?$")


def _parse_sem_pairs(circle_path: Path) -> List[Dict[str, str]]:
    if not circle_path.exists():
        return []
    pairs: Dict[str, Dict[str, Optional[str]]] = {}
    block = None
    for line in circle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        if s == "互斥量":
            block = "mutex"
            continue
        if s == "信号量":
            block = "sem"
            continue
        if block != "sem":
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        node = parts[0]
        idx = parts[2]
        rec = pairs.setdefault(idx, {"post": None, "wait": None})
        if "sem_post" in node:
            rec["post"] = node
        elif "sem_wait" in node:
            rec["wait"] = node
    out: List[Dict[str, str]] = []
    for idx, rec in pairs.items():
        if rec["post"] and rec["wait"]:
            out.append({"idx": idx, "post_node": str(rec["post"]), "wait_node": str(rec["wait"])})
    return out


def _parse_mutex_intervals(internal_meta_path: Path) -> Dict[str, List[Tuple[int, int]]]:
    if not internal_meta_path.exists():
        return {}
    import json

    data = json.loads(internal_meta_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}

    intervals: Dict[str, List[Tuple[int, int]]] = {}
    for fn, meta_map in data.items():
        if not isinstance(fn, str) or not isinstance(meta_map, dict):
            continue
        stack: List[int] = []
        for node, meta in meta_map.items():
            if not isinstance(node, str) or not isinstance(meta, dict):
                continue
            line = meta.get("line")
            if not isinstance(line, int):
                continue
            if _MU_LOCK_RE.search(node):
                stack.append(line)
            elif _MU_UNLOCK_RE.search(node):
                if not stack:
                    continue
                lock_line = stack.pop()
                if lock_line <= line:
                    intervals.setdefault(fn, []).append((lock_line, line))
    for fn in list(intervals.keys()):
        intervals[fn].sort()
    return intervals


def collect_block_info(*, base_dir: Path, base_name: str, source_file: Path) -> Dict:
    results_root = base_dir / RESULTS_ROOT_NAME / base_name
    pipeline_root = results_root / PIPELINE_DIR_NAME
    pipeline_root.mkdir(parents=True, exist_ok=True)
    meta_path = pipeline_root / "block_info_meta.json"
    mark_running(meta_path, step="collector")

    gen_root = results_root / GEN_DIR_NAME
    config_root = results_root / CONFIG_DIR_NAME

    dag_dot = gen_root / "dag.dot"
    functions_full = gen_root / "functions_full.json"
    functions_ranges = gen_root / "functions_ranges.json"
    internal_meta = gen_root / "debug" / "mycalls_meta_internal.json"
    circle_txt = config_root / "circle.txt"

    required = [dag_dot, functions_full, functions_ranges, internal_meta, circle_txt]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        error = f"missing required inputs: {', '.join(missing)}"
        mark_failed(meta_path, step="collector", error=error)
        raise StageError(error)

    sem_pairs = _parse_sem_pairs(circle_txt)
    mutex_intervals = _parse_mutex_intervals(internal_meta)

    derived_dir = pipeline_root / "derived"
    derived_dir.mkdir(parents=True, exist_ok=True)
    if sem_pairs:
        write_json(derived_dir / "sem_pairs.json", {"pairs": sem_pairs})
    if mutex_intervals:
        write_json(derived_dir / "mutex_intervals.json", {"intervals": mutex_intervals})

    block_info = {
        "schema_version": SCHEMA_VERSION,
        "base_name": base_name,
        "source_file": str(source_file.resolve()),
        "inputs": {
            "dag_dot": str(dag_dot),
            "functions_full": str(functions_full),
            "functions_ranges": str(functions_ranges),
            "mycalls_meta_internal": str(internal_meta),
            "circle_txt": str(circle_txt),
        },
        "capabilities": {"has_circle_txt": circle_txt.exists()},
    }
    write_json(pipeline_root / "block_info.json", block_info)
    mark_success(
        meta_path,
        step="collector",
        extra={"has_circle_txt": circle_txt.exists(), "sem_pairs": len(sem_pairs), "mutex_functions": len(mutex_intervals)},
    )
    return block_info
