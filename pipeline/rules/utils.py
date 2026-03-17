from __future__ import annotations

from typing import Dict, List, Set, Tuple

from ..constants import SCHEMA_VERSION, STANDARD_KINDS


def normalize_segments(*, base_name: str, level: str, rule_name: str, view: str, segments_in: List[Dict]) -> Tuple[Dict, List[str]]:
    segments: List[Dict] = []
    extensions: Set[str] = set()
    for item in segments_in:
        if not isinstance(item, dict):
            continue
        seg_id = item.get("seg_id")
        function = item.get("function")
        kind = item.get("kind")
        start_line = item.get("start_line")
        end_line = item.get("end_line")
        if not isinstance(seg_id, str) or not isinstance(function, str):
            continue
        if not isinstance(kind, str):
            continue
        if not isinstance(start_line, int) or not isinstance(end_line, int):
            continue
        if kind not in STANDARD_KINDS:
            extensions.add(kind)
        segments.append(
            {
                "seg_id": seg_id,
                "function": function,
                "kind": kind,
                "start_line": start_line,
                "end_line": end_line,
            }
        )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "base_name": base_name,
        "level": level,
        "rule_name": rule_name,
        "view": view,
        "segments": segments,
    }
    return payload, sorted(extensions)


def normalize_dag(*, base_name: str, nodes_in: List[str], edges_in: List[Dict]) -> Dict:
    nodes = [n for n in nodes_in if isinstance(n, str)]
    node_set = set(nodes)
    edges: List[Dict] = []
    for e in edges_in:
        if not isinstance(e, dict):
            continue
        src = e.get("src")
        dst = e.get("dst")
        kind = e.get("kind", "intra")
        if not isinstance(src, str) or not isinstance(dst, str) or not isinstance(kind, str):
            continue
        if src in node_set and dst in node_set:
            edges.append({"src": src, "dst": dst, "kind": kind})
    return {"schema_version": SCHEMA_VERSION, "base_name": base_name, "nodes": nodes, "edges": edges}

