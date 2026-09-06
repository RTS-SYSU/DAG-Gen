from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List


def _feature_insert_at(lines: List[str]) -> int:
    feature_def_re = re.compile(r"^\s*#\s*define\s+_(GNU|DEFAULT|POSIX|XOPEN|BSD|SVID)_SOURCE\b")
    insert_at = 0
    for i, ln in enumerate(lines):
        if feature_def_re.match(ln):
            insert_at = i + 1
            continue
        break
    return insert_at


def instrument_prio_all_segments_by_start_line(
    source_c: Path,
    *,
    segments_json: Path,
    priorities: Dict[str, int],
    out_c: Path,
) -> List[str]:
    warnings: List[str] = []
    lines0 = source_c.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    insert_at = _feature_insert_at(lines0)
    lines = lines0[:insert_at] + ['#include "prio_runtime.h"\n'] + lines0[insert_at:]

    seg_data = json.loads(segments_json.read_text(encoding="utf-8"))
    segments = seg_data.get("segments", [])

    include_shift = 1
    inserts_prio: Dict[int, List[int]] = {}

    for seg in segments:
        if not isinstance(seg, dict):
            continue
        seg_id = seg.get("seg_id")
        start_line = seg.get("start_line")
        if not isinstance(seg_id, str) or not isinstance(start_line, int):
            continue
        prio = priorities.get(seg_id)
        if prio is None:
            continue
        ins_line = start_line + include_shift
        inserts_prio.setdefault(ins_line, []).append(int(prio))

    out: List[str] = []
    for i in range(1, len(lines) + 1):
        prios = inserts_prio.get(i, [])
        if prios:
            indent = re.match(r"[ \t]*", lines[i - 1]).group(0)  # type: ignore[union-attr]
            for prio in prios:
                out.append(f"{indent}l1_set_thread_prio_fifo({prio});\n")
        out.append(lines[i - 1])
    out_c.write_text("".join(out), encoding="utf-8")
    return warnings
