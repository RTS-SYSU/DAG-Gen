from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from mycallyplus_v1.level1.segment_dag import _iter_stage1_cut_points  # type: ignore
from mycallyplus_v1.level1.segment_dag import _load_functions_full, _load_functions_ranges, _load_internal_meta  # type: ignore


@dataclass(frozen=True)
class Segment:
    seg_id: str
    function: str
    kind: str  # compute|mutex_cs
    start_line: int
    end_line: int


_CREATE_NODE_RE = re.compile(r"(^|/)pthread_create(\d+)?$")
_JOIN_NODE_RE = re.compile(r"(^|/)pthread_join(\d+)?$")
_SEM_POST_NODE_RE = re.compile(r"(^|/)sem_post(\d+)?$")
_SEM_WAIT_NODE_RE = re.compile(r"(^|/)sem_wait(\d+)?$")
_MU_LOCK_NODE_RE = re.compile(r"(^|/)pthread_mutex_lock(\d+)?$")
_MU_UNLOCK_NODE_RE = re.compile(r"(^|/)pthread_mutex_unlock(\d+)?$")

def _segment_id(fn: str, idx: int, kind: str, start: int, end: int) -> str:
    if kind == "mutex_cs":
        return f"MU:{fn}#{idx:03d}@{start}-{end}"
    return f"SEG:{fn}#{idx:03d}@{start}-{end}"


def _build_node_owner_and_order(
    internal_meta: Dict[str, Dict[str, Dict]],
) -> Tuple[Dict[str, Tuple[str, int]], Dict[str, List[str]]]:
    node_owner_line: Dict[str, Tuple[str, int]] = {}
    ordered_nodes_by_fn: Dict[str, List[str]] = {}
    for fn, meta_map in internal_meta.items():
        if not isinstance(meta_map, dict) or not meta_map:
            continue
        ordered_nodes_by_fn[fn] = list(meta_map.keys())
        for node, meta in meta_map.items():
            if not isinstance(node, str) or not isinstance(meta, dict):
                continue
            line = meta.get("line")
            if not isinstance(line, int):
                continue
            # Assumption (confirmed by user): internal_meta keys preserve call order and are globally unique.
            node_owner_line[node] = (fn, line)
    return node_owner_line, ordered_nodes_by_fn


def _pair_mutex_intervals(
    *,
    internal_meta: Dict[str, Dict[str, Dict]],
) -> Dict[str, List[Tuple[int, int]]]:
    """Pair lock/unlock per function using internal-meta order (stack-based)."""
    intervals: Dict[str, List[Tuple[int, int]]] = {}
    for fn, meta_map in internal_meta.items():
        if not isinstance(meta_map, dict) or not meta_map:
            continue
        stack: List[int] = []
        for node, meta in meta_map.items():
            if not isinstance(node, str) or not isinstance(meta, dict):
                continue
            line = meta.get("line")
            if not isinstance(line, int):
                continue
            if _MU_LOCK_NODE_RE.search(node):
                stack.append(line)
            elif _MU_UNLOCK_NODE_RE.search(node):
                if not stack:
                    continue
                lock_line = stack.pop()
                if lock_line <= line:
                    intervals.setdefault(fn, []).append((lock_line, line))
    for fn in list(intervals.keys()):
        intervals[fn].sort()
    return intervals


def _parse_circle_sem_pairs(circle_path: Path) -> List[Tuple[str, str]]:
    """Return list of (post_node, wait_node) parsed from circle.txt."""
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
        # Example: c1_fn/sem_post9 sem sem51 142 zhang1.c
        if len(parts) < 3:
            continue
        node, _tag, idx = parts[0], parts[1], parts[2]
        rec = pairs.setdefault(idx, {"post": None, "wait": None})
        if "sem_post" in node:
            rec["post"] = node
        elif "sem_wait" in node:
            rec["wait"] = node
    out: List[Tuple[str, str]] = []
    for rec in pairs.values():
        if rec.get("post") and rec.get("wait"):
            out.append((rec["post"], rec["wait"]))  # type: ignore[arg-type]
    return out


def _line_has_effective_code(raw_line: str, *, in_block_comment: bool) -> Tuple[bool, bool]:
    """Return (has_effective_code, next_in_block_comment)."""
    line = raw_line
    i = 0
    n = len(line)
    has_code = False
    while i < n:
        if in_block_comment:
            end = line.find("*/", i)
            if end < 0:
                return has_code, True
            i = end + 2
            in_block_comment = False
            continue

        if i + 1 < n and line[i] == "/" and line[i + 1] == "/":
            break
        if i + 1 < n and line[i] == "/" and line[i + 1] == "*":
            in_block_comment = True
            i += 2
            continue
        if not line[i].isspace():
            has_code = True
        i += 1
    return has_code, in_block_comment


def _build_effective_line_neighbors(
    *,
    source_lines: Sequence[str],
    fn_range: Dict[str, Tuple[int, int]],
) -> Tuple[Dict[str, Dict[int, Optional[int]]], Dict[str, Dict[int, Optional[int]]]]:
    """Build prev/next effective code line mapping for each function range."""
    line_is_effective: Dict[int, bool] = {}
    in_block_comment = False
    for lineno, raw in enumerate(source_lines, start=1):
        has_code, in_block_comment = _line_has_effective_code(raw, in_block_comment=in_block_comment)
        line_is_effective[lineno] = has_code

    prev_map_by_fn: Dict[str, Dict[int, Optional[int]]] = {}
    next_map_by_fn: Dict[str, Dict[int, Optional[int]]] = {}
    for fn, (start, end) in fn_range.items():
        effective_lines = [ln for ln in range(start, end + 1) if line_is_effective.get(ln, False)]
        prev_map: Dict[int, Optional[int]] = {}
        next_map: Dict[int, Optional[int]] = {}
        for ln in range(start, end + 1):
            prev_ln = None
            next_ln = None
            for candidate in reversed(effective_lines):
                if candidate < ln:
                    prev_ln = candidate
                    break
            for candidate in effective_lines:
                if candidate > ln:
                    next_ln = candidate
                    break
            prev_map[ln] = prev_ln
            next_map[ln] = next_ln
        prev_map_by_fn[fn] = prev_map
        next_map_by_fn[fn] = next_map
    return prev_map_by_fn, next_map_by_fn


def _build_segments_for_function(
    fn: str,
    *,
    start_line: int,
    end_line: int,
    cut_after: Set[int],
    mutex_intervals: Sequence[Tuple[int, int]],
) -> List[Segment]:
    if start_line <= 0 or end_line < start_line:
        return []

    lock_lines = sorted({a for (a, _b) in mutex_intervals})
    boundaries = sorted({k for k in cut_after if start_line <= k <= end_line})

    spans: List[Tuple[int, int]] = []
    cur = start_line
    for k in boundaries:
        if cur <= k:
            spans.append((cur, k))
            cur = k + 1
    if cur <= end_line:
        spans.append((cur, end_line))

    out: List[Segment] = []
    idx = 0
    for a, b in spans:
        kind = "compute"
        if any(a <= l <= b for l in lock_lines):
            kind = "mutex_cs"
        idx += 1
        out.append(Segment(_segment_id(fn, idx, kind, a, b), fn, kind, a, b))
    return out


def _find_segment_index_covering_line(segs: Sequence[Segment], line: int) -> Optional[int]:
    for i, s in enumerate(segs):
        if s.start_line <= line <= s.end_line:
            return i
    return None


def build_level2_segments_and_dag(
    *,
    base_dir: Path,
    base_name: str,
    source_file: Path,
) -> Tuple[Dict, Dict]:
    """Build Level-2 segments + segment DAG.

    Inputs:
    - merged Level-2 DAG dot: 中间结果/<base>/level2/merge_post_wait/dag_level2_sem.dot (preferred)
    - internal meta:          中间结果/<base>/生成dag图/debug/mycalls_meta_internal.json
    - functions ranges:       中间结果/<base>/生成dag图/functions_ranges.json
    - functions full:         中间结果/<base>/生成dag图/functions_full.json

    Segmentation rules (Level-2, per user doc):
    - create/sem_post: cut AFTER line (belongs to previous segment)
    - join/sem_wait:   cut BEFORE line (belongs to next segment)
    - mutex: cut BEFORE lock, cut AFTER unlock; cuts inside critical section are ignored
    - merge rules:
        * create: if previous block is mutex_cs, remove mutex_cs's unlock cut to merge
        * join:   if next block is mutex_cs, remove mutex_cs's lock cut to merge
    - thread boundary rules (only for main + thread entry functions):
        * start: if first call is not lock/wait, draw start line (no-op for ranges; kept for consistency)
        * end:   if last call is not unlock/post/create, cut at function end
      First/last call is derived from internal_meta order.
    """
    gen_root = base_dir / "中间结果" / base_name / "生成dag图"
    level2_merge_root = base_dir / "中间结果" / base_name / "level2" / "merge_post_wait"

    functions_full_path = gen_root / "functions_full.json"
    ranges_path = gen_root / "functions_ranges.json"
    internal_meta_path = gen_root / "debug" / "mycalls_meta_internal.json"

    merged_dot_path = level2_merge_root / "dag_level2_sem.dot"
    if not merged_dot_path.exists():
        merged_dot_path = gen_root / "dag.dot"

    functions_full = _load_functions_full(functions_full_path)
    ranges = _load_functions_ranges(ranges_path)
    internal_meta = _load_internal_meta(internal_meta_path)

    node_owner_line, ordered_nodes_by_fn = _build_node_owner_and_order(internal_meta)
    mutex_intervals_by_fn = _pair_mutex_intervals(internal_meta=internal_meta)

    cuts = _iter_stage1_cut_points(functions_full=functions_full, internal_meta=internal_meta)

    thread_entry_fns: Set[str] = {"main"}
    for c in cuts:
        if c.kind == "create" and c.entry_fn:
            thread_entry_fns.add(c.entry_fn)

    # Build function ranges:
    # - exclude trailing return/brace from segmentation
    # - prefer semantic statement boundaries over function closing brace
    fn_range: Dict[str, Tuple[int, int]] = {}
    for fn, info in ranges.items():
        s = info.get("level1_start_line") or info.get("first_stmt_line") or info.get("start_line")
        last_return = info.get("last_return_line")
        last_stmt = info.get("last_stmt_line")
        level1_end = info.get("level1_end_line")
        end_line = info.get("end_line")

        e: Optional[int] = None
        if isinstance(last_return, int) and last_return > 0:
            # If return exists, do not include return in segment range.
            e = last_return - 1
        elif isinstance(last_stmt, int) and last_stmt > 0:
            # Prefer last statement line (normally before "}").
            e = last_stmt
        elif isinstance(level1_end, int) and level1_end > 0:
            e = level1_end
        elif isinstance(end_line, int) and end_line > 0:
            # Final fallback: avoid including closing brace when only end_line is available.
            e = end_line - 1

        if isinstance(s, int) and isinstance(e, int) and s > 0 and e >= s:
            fn_range[fn] = (s, e)

    # Collect per-function cut-after positions
    cut_after_by_fn: Dict[str, Set[int]] = {}
    create_lines_by_fn: Dict[str, List[int]] = {}
    sem_post_lines_by_fn: Dict[str, List[int]] = {}
    join_lines_by_fn: Dict[str, List[int]] = {}
    sem_wait_lines_by_fn: Dict[str, List[int]] = {}
    lock_lines_by_fn: Dict[str, Set[int]] = {}
    unlock_lines_by_fn: Dict[str, Set[int]] = {}

    source_lines = source_file.read_text(encoding="utf-8", errors="replace").splitlines()
    prev_effective_by_fn, next_effective_by_fn = _build_effective_line_neighbors(
        source_lines=source_lines,
        fn_range=fn_range,
    )

    for node, (owner_fn, line) in node_owner_line.items():
        if owner_fn not in fn_range:
            continue
        start_line, _end_line = fn_range[owner_fn]

        if _CREATE_NODE_RE.search(node):
            cut_after_by_fn.setdefault(owner_fn, set()).add(line)
            create_lines_by_fn.setdefault(owner_fn, []).append(line)
        elif _SEM_POST_NODE_RE.search(node):
            cut_after_by_fn.setdefault(owner_fn, set()).add(line)
            sem_post_lines_by_fn.setdefault(owner_fn, []).append(line)
        elif _MU_UNLOCK_NODE_RE.search(node):
            cut_after_by_fn.setdefault(owner_fn, set()).add(line)
            unlock_lines_by_fn.setdefault(owner_fn, set()).add(line)

        if _JOIN_NODE_RE.search(node):
            if line - 1 >= start_line:
                cut_after_by_fn.setdefault(owner_fn, set()).add(line - 1)
            join_lines_by_fn.setdefault(owner_fn, []).append(line)
        elif _SEM_WAIT_NODE_RE.search(node):
            if line - 1 >= start_line:
                cut_after_by_fn.setdefault(owner_fn, set()).add(line - 1)
            sem_wait_lines_by_fn.setdefault(owner_fn, []).append(line)
        elif _MU_LOCK_NODE_RE.search(node):
            if line - 1 >= start_line:
                cut_after_by_fn.setdefault(owner_fn, set()).add(line - 1)
            lock_lines_by_fn.setdefault(owner_fn, set()).add(line)

    # Thread boundary rules
    entry_cut_applied: Dict[str, bool] = {}
    exit_cut_applied: Dict[str, bool] = {}
    for fn in sorted(thread_entry_fns):
        if fn not in fn_range:
            continue
        nodes = ordered_nodes_by_fn.get(fn, [])
        if not nodes:
            continue
        start, end = fn_range[fn]
        first = nodes[0]
        last = nodes[-1]
        if not (_MU_LOCK_NODE_RE.search(first) or _SEM_WAIT_NODE_RE.search(first)):
            cut_after_by_fn.setdefault(fn, set()).add(start - 1)
            entry_cut_applied[fn] = True
        else:
            entry_cut_applied[fn] = False
        if not (_MU_UNLOCK_NODE_RE.search(last) or _SEM_POST_NODE_RE.search(last) or _CREATE_NODE_RE.search(last)):
            cut_after_by_fn.setdefault(fn, set()).add(end)
            exit_cut_applied[fn] = True
        else:
            exit_cut_applied[fn] = False

    # Remove cuts that would split inside mutex critical sections
    for fn, intervals in mutex_intervals_by_fn.items():
        if fn not in fn_range:
            continue
        cuts_set = cut_after_by_fn.get(fn)
        if not cuts_set:
            continue
        filtered = set(cuts_set)
        for lock_line, unlock_line in intervals:
            for k in list(filtered):
                if lock_line <= k < unlock_line:
                    filtered.discard(k)
        cut_after_by_fn[fn] = filtered

    # Apply merge rules based on nearest effective code lines (skip blanks/comments)
    for fn in fn_range.keys():
        fn_cuts = cut_after_by_fn.setdefault(fn, set())
        prev_effective = prev_effective_by_fn.get(fn, {})
        next_effective = next_effective_by_fn.get(fn, {})
        fn_unlock_lines = unlock_lines_by_fn.get(fn, set())
        fn_lock_lines = lock_lines_by_fn.get(fn, set())

        for line in create_lines_by_fn.get(fn, []) + sem_post_lines_by_fn.get(fn, []):
            prev_line = prev_effective.get(line)
            if isinstance(prev_line, int) and prev_line in fn_unlock_lines:
                fn_cuts.discard(prev_line)

        for line in join_lines_by_fn.get(fn, []) + sem_wait_lines_by_fn.get(fn, []):
            next_line = next_effective.get(line)
            if isinstance(next_line, int) and next_line in fn_lock_lines:
                fn_cuts.discard(next_line - 1)

    # Build initial segments
    segs_by_fn: Dict[str, List[Segment]] = {}
    for fn, (s, e) in fn_range.items():
        if fn not in ordered_nodes_by_fn:
            continue
        segs_by_fn[fn] = _build_segments_for_function(
            fn,
            start_line=s,
            end_line=e,
            cut_after=cut_after_by_fn.get(fn, set()),
            mutex_intervals=mutex_intervals_by_fn.get(fn, []),
        )

    # Flatten segments (stable order)
    all_segments: List[Segment] = []
    for fn in sorted(segs_by_fn.keys()):
        all_segments.extend(segs_by_fn[fn])

    # Map node->segment
    node_to_seg: Dict[str, str] = {}
    for node, (owner_fn, line) in node_owner_line.items():
        segs = segs_by_fn.get(owner_fn)
        if not segs:
            continue
        idx = _find_segment_index_covering_line(segs, line)
        if idx is None:
            continue
        node_to_seg[node] = segs[idx].seg_id
    for fn, segs in segs_by_fn.items():
        if segs:
            node_to_seg.setdefault(fn, segs[0].seg_id)

    edges: Set[Tuple[str, str, str]] = set()

    # Intra-function sequential edges
    for fn, segs in segs_by_fn.items():
        for a, b in zip(segs, segs[1:]):
            edges.add((a.seg_id, b.seg_id, "intra"))

    def _find_seg_id(fn: str, line: int) -> Optional[str]:
        segs = segs_by_fn.get(fn)
        if not segs:
            return None
        idx = _find_segment_index_covering_line(segs, line)
        if idx is None:
            return None
        return segs[idx].seg_id

    # Create/join semantic edges (reuse legacy mapping logic from level1 cut points)
    for c in cuts:
        if c.kind == "create" and c.entry_fn:
            src = _find_seg_id(c.function, c.line)
            dst_list = segs_by_fn.get(c.entry_fn)
            if src and dst_list:
                edges.add((src, dst_list[0].seg_id, "create"))
        elif c.kind == "join" and c.entry_fn:
            dst = _find_seg_id(c.function, c.line)
            src_list = segs_by_fn.get(c.entry_fn)
            if dst and src_list:
                edges.add((src_list[-1].seg_id, dst, "join"))

    # Semaphore dep edges: post->wait pairs from circle.txt (same source as merge_post_wait stage)
    circle_path = level2_merge_root / "circle.txt"
    if not circle_path.exists():
        circle_path = base_dir / "中间结果" / base_name / "配置文件" / "circle.txt"
    if circle_path.exists():
        for post_node, wait_node in _parse_circle_sem_pairs(circle_path):
            post = node_owner_line.get(post_node)
            wait = node_owner_line.get(wait_node)
            if not post or not wait:
                continue
            post_fn, post_line = post
            wait_fn, wait_line = wait
            sp = _find_seg_id(post_fn, post_line)
            sw = _find_seg_id(wait_fn, wait_line)
            if sp and sw and sp != sw:
                edges.add((sp, sw, "sem_dep"))

    dag_edges = [{"src": s, "dst": d, "kind": k} for (s, d, k) in sorted(edges)]

    seg_json = {
        "base_name": base_name,
        "source_file": str(source_file),
        "inputs": {
            "functions_full": str(functions_full_path),
            "functions_ranges": str(ranges_path),
            "mycalls_meta_internal": str(internal_meta_path),
            "merged_dag_dot": str(merged_dot_path),
        },
        "thread_entry_functions": sorted(thread_entry_fns),
        "entry_cut_applied": entry_cut_applied,
        "exit_cut_applied": exit_cut_applied,
        "segments": [
            {
                "seg_id": s.seg_id,
                "function": s.function,
                "kind": s.kind,
                "start_line": s.start_line,
                "end_line": s.end_line,
            }
            for s in all_segments
        ],
    }
    dag_json = {
        "base_name": base_name,
        "nodes": [s.seg_id for s in all_segments],
        "edges": dag_edges,
    }
    return seg_json, dag_json


def _to_dot(seg_json: Dict, dag_json: Dict) -> str:
    segs = {s["seg_id"]: s for s in seg_json.get("segments", []) if isinstance(s, dict)}
    lines: List[str] = []
    lines.append("digraph Level2SegDAG {")
    lines.append("  rankdir=LR;")
    lines.append('  node [shape=box, fontname="Consolas", fontsize=10];')
    thread_palette = [
        "#E3F2FD",
        "#E8F5E9",
        "#FFF3E0",
        "#F3E5F5",
        "#E0F7FA",
        "#FCE4EC",
        "#F1F8E9",
        "#EDE7F6",
    ]
    fn_order = sorted({str(s.get("function", "")) for s in segs.values()})
    fn_color = {fn: thread_palette[i % len(thread_palette)] for i, fn in enumerate(fn_order)}
    for seg_id, s in sorted(segs.items()):
        fn = s.get("function", "")
        kind = s.get("kind", "")
        start = s.get("start_line", "")
        end = s.get("end_line", "")
        fill = fn_color.get(str(fn), "#F6F6F6")
        label = f"{seg_id}\\n{fn} {kind} @{start}-{end}"
        lines.append(f'  "{seg_id}" [style="rounded,filled", fillcolor="{fill}", label="{label}"];')
    edge_color = {
        "intra": "#666666",
        "create": "#1565C0",
        "join": "#2E7D32",
        "sem_dep": "#D32F2F",
    }
    for e in dag_json.get("edges", []):
        if not isinstance(e, dict):
            continue
        src = e.get("src")
        dst = e.get("dst")
        kind = e.get("kind", "intra")
        if src not in segs or dst not in segs:
            continue
        color = edge_color.get(kind, "#666666")
        style = "dashed" if kind == "sem_dep" else "solid"
        penwidth = "2.2" if kind in ("create", "join", "sem_dep") else "1.0"
        lines.append(f'  "{src}" -> "{dst}" [color="{color}", style="{style}", penwidth={penwidth}];')
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Level-2 segment DAG (create/join/post/wait/mutex rules).")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"))
    ap.add_argument("--base-name", required=True)
    ap.add_argument("--source-file", type=Path, required=True)
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name
    source_file = args.source_file.resolve()

    seg_json, dag_json = build_level2_segments_and_dag(base_dir=base_dir, base_name=base_name, source_file=source_file)

    out_dir = base_dir / "中间结果" / base_name / "level2" / "stage2"
    out_dir.mkdir(parents=True, exist_ok=True)
    seg_path = out_dir / "segments_level2.json"
    dag_path = out_dir / "dag_level2_seg.json"
    dot_path = out_dir / "dag_level2_seg.dot"

    seg_path.write_text(json.dumps(seg_json, ensure_ascii=False, indent=2), encoding="utf-8")
    dag_path.write_text(json.dumps(dag_json, ensure_ascii=False, indent=2), encoding="utf-8")
    dot_path.write_text(_to_dot(seg_json, dag_json), encoding="utf-8")
    print(f"wrote {seg_path}")
    print(f"wrote {dag_path}")
    print(f"wrote {dot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
