from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class CutPoint:
    function: str
    kind: str  # create|join
    node: str  # original DAG node name (e.g. main/pthread_create20)
    line: int
    entry_fn: Optional[str] = None
    tid_var: Optional[str] = None


@dataclass(frozen=True)
class Segment:
    seg_id: str
    function: str
    kind: str  # compute|create|join
    start_line: int
    end_line: int
    cut_node: Optional[str] = None


_CREATE_NODE_RE = re.compile(r"(^|/)pthread_create(\d+)?$")
_JOIN_NODE_RE = re.compile(r"(^|/)pthread_join(\d+)?$")


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_functions_full(path: Path) -> Dict[str, Dict]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError("functions_full.json must be a dict")
    return data  # type: ignore[return-value]


def _load_functions_ranges(path: Path) -> Dict[str, Dict]:
    data = _load_json(path)
    if not isinstance(data, dict) or "functions" not in data:
        raise ValueError("functions_ranges.json must have top-level {functions:[...]}")
    out: Dict[str, Dict] = {}
    for item in data.get("functions", []):
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if isinstance(name, str) and name:
            out[name] = item
    return out


def _load_internal_meta(path: Path) -> Dict[str, Dict[str, Dict]]:
    data = _load_json(path)
    if not isinstance(data, dict):
        raise ValueError("mycalls_meta_internal.json must be a dict")
    out: Dict[str, Dict[str, Dict]] = {}
    for fn, meta in data.items():
        if isinstance(fn, str) and isinstance(meta, dict):
            out[fn] = meta  # meta: node -> {file,line,col,...}
    return out


def _build_create_node_to_entry_fn(functions_full: Dict[str, Dict]) -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for fn, info in functions_full.items():
        callers = info.get("mycalls", []) or []
        if not isinstance(callers, list):
            continue
        for i, node in enumerate(callers):
            if not isinstance(node, str):
                continue
            if _CREATE_NODE_RE.search(node):
                # legacy inserts entry function node right after create node
                entry = callers[i + 1] if i + 1 < len(callers) else None
                if isinstance(entry, str) and entry in functions_full:
                    mapping[node] = entry
    return mapping


def _build_handle_to_entry_fn(functions_full: Dict[str, Dict]) -> Dict[str, str]:
    """Build global mapping: tid_var(handle) -> entry_fn.

    Important: for chain-created threads (e.g. c0 creates tc1=c1_fn), the mapping
    is stored in the creator thread's myinfo, not necessarily in main.
    """
    out: Dict[str, str] = {}
    for fn, info in functions_full.items():
        myinfo = info.get("myinfo", {}) or {}
        if not isinstance(myinfo, dict):
            continue
        for k, v in myinfo.items():
            if not isinstance(k, str) or not isinstance(v, str):
                continue
            if k in ("tail", "__create_queue__"):
                continue
            # Heuristic: thread handles are typically tc0/tf0/...
            # Even if we can't validate the handle format, mapping only to known entry functions is safe.
            if v in functions_full:
                out[k] = v
    return out


def _iter_stage1_cut_points(
    *,
    functions_full: Dict[str, Dict],
    internal_meta: Dict[str, Dict[str, Dict]],
) -> List[CutPoint]:
    create_to_entry = _build_create_node_to_entry_fn(functions_full)
    handle_to_entry = _build_handle_to_entry_fn(functions_full)

    cuts: List[CutPoint] = []
    for fn, meta_map in internal_meta.items():
        myinfo = (functions_full.get(fn, {}) or {}).get("myinfo", {}) or {}
        for node, meta in meta_map.items():
            if not isinstance(node, str) or not isinstance(meta, dict):
                continue
            line = meta.get("line")
            if not isinstance(line, int):
                continue

            if _CREATE_NODE_RE.search(node):
                cuts.append(
                    CutPoint(
                        function=fn,
                        kind="create",
                        node=node,
                        line=line,
                        entry_fn=create_to_entry.get(node),
                    )
                )
            elif _JOIN_NODE_RE.search(node):
                tid_var = None
                entry_fn = None
                join_var = myinfo.get(node)
                if isinstance(join_var, str):
                    tid_var = join_var
                    # Prefer owner-local myinfo mapping; fallback to global handle->entry map
                    entry = myinfo.get(join_var)
                    if isinstance(entry, str) and entry in functions_full:
                        entry_fn = entry
                    else:
                        entry_fn = handle_to_entry.get(join_var)
                cuts.append(
                    CutPoint(
                        function=fn,
                        kind="join",
                        node=node,
                        line=line,
                        tid_var=tid_var,
                        entry_fn=entry_fn,
                    )
                )
    cuts.sort(key=lambda c: (c.function, c.line, c.node))
    return cuts


def _segment_id(function: str, idx: int, kind: str, start: int, end: int, *, line: Optional[int] = None) -> str:
    """Readable segment id.

    Goal: quickly distinguish thread-execution segments vs create/join segments.
    - exec (compute):   THR:<func>#<idx>@<start>-<end>
    - create:           CRT:<func>#<idx>@L<line>
    - join:             JON:<func>#<idx>@L<line>
    """
    if kind == "compute":
        return f"THR:{function}#{idx:03d}@{start}-{end}"
    if kind == "create":
        assert line is not None
        return f"CRT:{function}#{idx:03d}@L{line}"
    if kind == "join":
        assert line is not None
        return f"JON:{function}#{idx:03d}@L{line}"
    return f"{kind.upper()}:{function}#{idx:03d}@{start}-{end}"


def _build_segments_for_function(
    fn: str,
    *,
    start_line: int,
    end_line: int,
    cut_lines: List[Tuple[int, str, str]],  # (line, kind, node)
) -> List[Segment]:
    # Keep only cut lines that fall within [start_line, end_line]
    cut_lines = [(l, k, n) for (l, k, n) in cut_lines if start_line <= l <= end_line]
    cut_lines.sort(key=lambda x: (x[0], x[1], x[2]))

    segments: List[Segment] = []
    idx = 0
    cur = start_line
    for line, kind, node in cut_lines:
        if cur <= line - 1:
            idx += 1
            segments.append(
                Segment(
                    seg_id=_segment_id(fn, idx, "compute", cur, line - 1),
                    function=fn,
                    kind="compute",
                    start_line=cur,
                    end_line=line - 1,
                )
            )
        idx += 1
        segments.append(
            Segment(
                seg_id=_segment_id(fn, idx, kind, line, line, line=line),
                function=fn,
                kind=kind,
                start_line=line,
                end_line=line,
                cut_node=node,
            )
        )
        cur = line + 1
    if cur <= end_line:
        idx += 1
        segments.append(
            Segment(
                seg_id=_segment_id(fn, idx, "compute", cur, end_line),
                function=fn,
                kind="compute",
                start_line=cur,
                end_line=end_line,
            )
        )
    return segments


def _find_segment_covering_line(segments: List[Segment], line: int) -> Optional[Segment]:
    for s in segments:
        if s.start_line <= line <= s.end_line:
            return s
    return None


def build_stage1_segments_and_dag(
    *,
    base_dir: Path,
    base_name: str,
) -> Tuple[Dict, Dict]:
    gen_root = base_dir / "中间结果" / base_name / "生成dag图"
    functions_full_path = gen_root / "functions_full.json"
    ranges_path = gen_root / "functions_ranges.json"
    internal_meta_path = gen_root / "debug" / "mycalls_meta_internal.json"

    functions_full = _load_functions_full(functions_full_path)
    ranges = _load_functions_ranges(ranges_path)
    internal_meta = _load_internal_meta(internal_meta_path)

    cuts = _iter_stage1_cut_points(functions_full=functions_full, internal_meta=internal_meta)

    cut_by_fn: Dict[str, List[Tuple[int, str, str]]] = {}
    cut_lookup: Dict[str, CutPoint] = {}
    for c in cuts:
        cut_lookup[c.node] = c
        cut_by_fn.setdefault(c.function, []).append((c.line, c.kind, c.node))

    segments_by_fn: Dict[str, List[Segment]] = {}
    segments: List[Dict] = []
    for fn, r in ranges.items():
        level1_start = r.get("level1_start_line")
        level1_end = r.get("level1_end_line")
        if not isinstance(level1_start, int) or not isinstance(level1_end, int):
            continue
        segs = _build_segments_for_function(
            fn,
            start_line=level1_start,
            end_line=level1_end,
            cut_lines=cut_by_fn.get(fn, []),
        )
        segments_by_fn[fn] = segs
        for s in segs:
            segments.append(
                {
                    "seg_id": s.seg_id,
                    "function": s.function,
                    "kind": s.kind,
                    "start_line": s.start_line,
                    "end_line": s.end_line,
                    "cut_node": s.cut_node,
                }
            )

    edges: List[Tuple[str, str, str]] = []  # (src, dst, kind)

    # Intra-function sequential edges
    for fn, segs in segments_by_fn.items():
        for a, b in zip(segs, segs[1:]):
            edges.append((a.seg_id, b.seg_id, "intra"))

    # Create/join semantic edges using existing legacy mappings
    for c in cuts:
        fn_segs = segments_by_fn.get(c.function)
        if not fn_segs:
            continue
        seg = _find_segment_covering_line(fn_segs, c.line)
        if not seg:
            continue

        if c.kind == "create" and c.entry_fn:
            entry_segs = segments_by_fn.get(c.entry_fn)
            if entry_segs:
                edges.append((seg.seg_id, entry_segs[0].seg_id, "create"))
        elif c.kind == "join" and c.entry_fn:
            entry_segs = segments_by_fn.get(c.entry_fn)
            if entry_segs:
                edges.append((entry_segs[-1].seg_id, seg.seg_id, "join"))

    segments_json = {
        "base_name": base_name,
        "source": str(ranges_path),
        "ranges": str(ranges_path),
        "functions_full": str(functions_full_path),
        "mycalls_meta_internal": str(internal_meta_path),
        "stage": 1,
        "cut_points": [
            {
                "function": c.function,
                "kind": c.kind,
                "node": c.node,
                "line": c.line,
                "entry_fn": c.entry_fn,
                "tid_var": c.tid_var,
            }
            for c in cuts
        ],
        "segments": segments,
    }
    dag_json = {
        "base_name": base_name,
        "stage": 1,
        "nodes": [s["seg_id"] for s in segments],
        "edges": [{"src": s, "dst": d, "kind": k} for (s, d, k) in edges],
    }
    return segments_json, dag_json


def _render_seg_dag_dot(dag_json: Dict) -> str:
    lines: List[str] = []
    lines.append("digraph seg_dag {")
    lines.append('  node [shape=box, style="rounded,filled", fontname="Consolas", fontsize=10, fillcolor="#F6F6F6"];')
    for e in dag_json.get("edges", []):
        src = e["src"]
        dst = e["dst"]
        kind = e.get("kind", "")
        if kind == "create":
            lines.append(f'  "{src}" -> "{dst}" [color="#1565C0", penwidth=2.2];')
        elif kind == "join":
            lines.append(f'  "{src}" -> "{dst}" [color="#2E7D32", penwidth=2.2];')
        else:
            lines.append(f'  "{src}" -> "{dst}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Level-1(stage1) segments and segment DAG (create/join only).")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"), help="Project base dir (contains 中间结果/)")
    ap.add_argument("--base-name", required=True, help="Base name under 中间结果/, e.g. cpu4_thread10_fifo")
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name
    out_root = base_dir / "中间结果" / base_name / "level1" / "stage1"
    out_root.mkdir(parents=True, exist_ok=True)

    segments_json, dag_json = build_stage1_segments_and_dag(base_dir=base_dir, base_name=base_name)

    segments_path = out_root / "segments_stage1.json"
    dag_path = out_root / "dag_stage1_seg.json"
    dot_path = out_root / "dag_stage1_seg.dot"

    segments_path.write_text(json.dumps(segments_json, ensure_ascii=False, indent=2), encoding="utf-8")
    dag_path.write_text(json.dumps(dag_json, ensure_ascii=False, indent=2), encoding="utf-8")
    dot_path.write_text(_render_seg_dag_dot(dag_json), encoding="utf-8")

    print(f"wrote {segments_path}")
    print(f"wrote {dag_path}")
    print(f"wrote {dot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
