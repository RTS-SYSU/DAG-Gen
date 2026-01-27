from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Set, Tuple


@dataclass(frozen=True)
class SegNode:
    seg_id: str
    function: str
    kind: str
    start_line: int
    end_line: int


def _topo_sort(nodes: Sequence[str], edges: Sequence[Tuple[str, str]]) -> List[str]:
    out_adj: Dict[str, List[str]] = {n: [] for n in nodes}
    indeg: Dict[str, int] = {n: 0 for n in nodes}
    for u, v in edges:
        if u not in indeg:
            indeg[u] = 0
            out_adj[u] = []
        if v not in indeg:
            indeg[v] = 0
            out_adj[v] = []
        out_adj[u].append(v)
        indeg[v] += 1
    q = [n for n, d in indeg.items() if d == 0]
    order: List[str] = []
    i = 0
    while i < len(q):
        u = q[i]
        i += 1
        order.append(u)
        for v in out_adj.get(u, []):
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if len(order) != len(indeg):
        raise RuntimeError("segment DAG has a cycle; longest path requires DAG")
    return order


def _reachable_to_sink(edges: Sequence[Tuple[str, str]], sink: str) -> Set[str]:
    rev: Dict[str, List[str]] = {}
    for u, v in edges:
        rev.setdefault(v, []).append(u)
    seen: Set[str] = set()
    stack = [sink]
    while stack:
        x = stack.pop()
        if x in seen:
            continue
        seen.add(x)
        stack.extend(rev.get(x, []))
    return seen


def compute_crit_to_sink(
    *,
    nodes: List[SegNode],
    edges: List[Tuple[str, str]],
    weights: Dict[str, int],
    sink: str,
) -> Tuple[Dict[str, int], Dict[str, str]]:
    ids = [n.seg_id for n in nodes]
    order = _topo_sort(ids, edges)
    reach = _reachable_to_sink(edges, sink)
    succ: Dict[str, List[str]] = {n: [] for n in ids}
    for u, v in edges:
        succ.setdefault(u, []).append(v)
    neg_inf = -(1 << 60)
    crit: Dict[str, int] = {n: neg_inf for n in ids}
    choice: Dict[str, str] = {}
    for n in reversed(order):
        if n not in reach:
            continue
        w = int(weights.get(n, 0) or 0)
        if n == sink:
            crit[n] = w
            continue
        best = neg_inf
        best_succ = None
        for s in succ.get(n, []):
            if s in reach:
                val = crit.get(s, neg_inf)
                if val > best or (val == best and s < (best_succ or s)):
                    best = val
                    best_succ = s
        if best == neg_inf:
            continue
        crit[n] = w + best
        if best_succ is not None:
            choice[n] = best_succ
    return {k: v for k, v in crit.items() if v != neg_inf}, choice


def assign_segment_priorities(
    *,
    segments: List[SegNode],
    edges: List[Tuple[str, str]],
    seg_total_ns: Dict[str, int],
    prio_max: int,
    only_entry_functions: bool,
) -> Dict[str, int]:
    segs_by_fn: Dict[str, List[SegNode]] = {}
    for s in segments:
        segs_by_fn.setdefault(s.function, []).append(s)
    for fn in segs_by_fn:
        segs_by_fn[fn].sort(key=lambda x: (x.start_line, x.end_line, x.seg_id))
    main_segs = segs_by_fn.get("main")
    if not main_segs:
        raise RuntimeError("cannot find main segments")
    sink = main_segs[-1].seg_id

    # Weight policy: create/join weight = 0; compute from total_ns.
    weights: Dict[str, int] = {}
    for s in segments:
        if s.kind in ("create", "join"):
            weights[s.seg_id] = 0
        else:
            weights[s.seg_id] = int(seg_total_ns.get(s.seg_id, 0) or 0)

    crit, choice = compute_crit_to_sink(nodes=segments, edges=edges, weights=weights, sink=sink)

    entry_fns: Set[str] = set()
    if only_entry_functions:
        seg_by_id = {s.seg_id: s for s in segments}
        for u, v in edges:
            src = seg_by_id.get(u)
            dst = seg_by_id.get(v)
            if not src or not dst:
                continue
            if src.kind == "create":
                entry_fns.add(dst.function)
        entry_fns.discard("main")

    # Greedy by path discovery order:
    # 1) pick the unassigned compute node with max crit (longest-to-sink)
    # 2) reconstruct one longest path to sink using choice[] and assign priorities
    # 3) next path starts from current prio after subtracting assigned count
    seg_by_id = {s.seg_id: s for s in segments}
    assigned: Dict[str, int] = {}
    available = {s.seg_id for s in segments if s.kind == "compute" and (not only_entry_functions or s.function in entry_fns)}

    current_prio = prio_max
    while current_prio > 0 and available:
        # pick start with max crit
        start = None
        best_val = -(1 << 60)
        for seg_id in available:
            val = crit.get(seg_id, -(1 << 60))
            if val > best_val or (val == best_val and seg_id < (start or seg_id)):
                best_val = val
                start = seg_id
        if start is None or best_val == -(1 << 60):
            break

        # reconstruct path start -> ... -> sink using choice; stop if successor missing
        path: List[str] = []
        cur = start
        while cur and cur in available:
            path.append(cur)
            nxt = choice.get(cur)
            if nxt is None or nxt == cur:
                break
            cur = nxt
        # assign along path
        for seg_id in path:
            if current_prio < 1:
                break
            assigned[seg_id] = current_prio
            current_prio -= 1
            available.discard(seg_id)
        # after finishing this path, continue to next path with remaining prio

    return assigned


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute LPF segment priorities from Level-1 segment DAG and timings.")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"))
    ap.add_argument("--base-name", required=True)
    ap.add_argument("--project", required=True, help="Project name under level1/timing/<project>/")
    ap.add_argument("--prio-max", type=int, default=80)
    ap.add_argument("--only-entry-functions", action="store_true", help="Only assign priorities to thread entry functions (exclude helper functions like busy_wait_seconds).")
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name
    stage_dir = base_dir / "中间结果" / base_name / "level1" / "stage1"
    timing_dir = base_dir / "中间结果" / base_name / "level1" / "timing" / args.project

    segments_json = json.loads((stage_dir / "segments_stage1.json").read_text(encoding="utf-8"))
    dag_json = json.loads((stage_dir / "dag_stage1_seg.json").read_text(encoding="utf-8"))
    time_json = json.loads((timing_dir / "time_result_seg.json").read_text(encoding="utf-8"))

    segments: List[SegNode] = []
    for s in segments_json.get("segments", []):
        if not isinstance(s, dict):
            continue
        segments.append(
            SegNode(
                seg_id=str(s["seg_id"]),
                function=str(s["function"]),
                kind=str(s["kind"]),
                start_line=int(s["start_line"]),
                end_line=int(s["end_line"]),
            )
        )
    edges = [(e["src"], e["dst"]) for e in dag_json.get("edges", []) if isinstance(e, dict)]
    totals = {k: int(v.get("total_ns", 0) or 0) for k, v in time_json.items() if isinstance(v, dict)}
    priorities = assign_segment_priorities(
        segments=segments,
        edges=edges,
        seg_total_ns=totals,
        prio_max=args.prio_max,
        only_entry_functions=bool(args.only_entry_functions),
    )

    out_dir = base_dir / "中间结果" / base_name / "level1" / "schedule" / ("lpf_segment_entry" if args.only_entry_functions else "lpf_segment")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "schedule_seg.json"
    payload = {
        "base_name": base_name,
        "project": args.project,
        "prio_max": args.prio_max,
        "priorities": priorities,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
