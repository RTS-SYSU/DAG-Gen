from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class SegNode:
    seg_id: str
    function: str
    kind: str
    start_line: int
    end_line: int


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


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


def _reachable_to_sink(nodes: Iterable[str], edges: Sequence[Tuple[str, str]], sink: str) -> Set[str]:
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


def compute_segment_criticality_to_main_end(
    *,
    nodes: Dict[str, SegNode],
    edges: Sequence[Tuple[str, str]],
    weights_ns: Dict[str, int],
    main_end_seg_id: str,
) -> Dict[str, int]:
    all_nodes = list(nodes.keys())
    order = _topo_sort(all_nodes, edges)
    reach = _reachable_to_sink(all_nodes, edges, main_end_seg_id)

    # successors
    succ: Dict[str, List[str]] = {n: [] for n in all_nodes}
    for u, v in edges:
        if u in succ:
            succ[u].append(v)

    neg_inf = -(1 << 60)
    crit: Dict[str, int] = {n: neg_inf for n in all_nodes}

    # DP in reverse topo
    for n in reversed(order):
        if n not in reach:
            continue
        w = int(weights_ns.get(n, 0) or 0)
        if n == main_end_seg_id:
            crit[n] = w
            continue
        best = neg_inf
        for s in succ.get(n, []):
            if s in reach:
                best = max(best, crit.get(s, neg_inf))
        if best == neg_inf:
            # no path to sink
            continue
        crit[n] = w + best
    return {k: v for k, v in crit.items() if v != neg_inf}


def assign_thread_priorities(
    *,
    segments: List[SegNode],
    dag_edges: List[Tuple[str, str]],
    seg_weights_ns: Dict[str, int],
    prio_min: int,
    prio_max: int,
) -> Dict[str, int]:
    seg_by_id = {s.seg_id: s for s in segments}
    segs_by_fn: Dict[str, List[SegNode]] = {}
    for s in segments:
        segs_by_fn.setdefault(s.function, []).append(s)
    for fn in segs_by_fn:
        segs_by_fn[fn].sort(key=lambda x: (x.start_line, x.end_line, x.seg_id))

    main_segs = segs_by_fn.get("main")
    if not main_segs:
        raise RuntimeError("cannot find main segments")
    main_end = main_segs[-1].seg_id

    # Weight policy (stage1): create/join weight = 0, compute weight from measured totals
    weights: Dict[str, int] = {}
    for seg_id, s in seg_by_id.items():
        if s.kind in ("create", "join"):
            weights[seg_id] = 0
        else:
            weights[seg_id] = int(seg_weights_ns.get(seg_id, 0) or 0)

    crit = compute_segment_criticality_to_main_end(
        nodes=seg_by_id, edges=dag_edges, weights_ns=weights, main_end_seg_id=main_end
    )

    # Decide which functions are thread entry functions: those reachable from any create edge destination
    entry_fns: Set[str] = set()
    for u, v in dag_edges:
        if seg_by_id.get(u) and seg_by_id[u].kind == "create":
            entry_fns.add(seg_by_id.get(v).function if v in seg_by_id else "")
    entry_fns.discard("")
    entry_fns.discard("main")

    scores: List[Tuple[str, int]] = []
    for fn in sorted(entry_fns):
        fn_segs = segs_by_fn.get(fn, [])
        if not fn_segs:
            continue
        score = int(crit.get(fn_segs[0].seg_id, 0) or 0)
        scores.append((fn, score))

    scores.sort(key=lambda x: (-x[1], x[0]))
    n = len(scores)
    if n == 0:
        return {}
    if n == 1:
        return {scores[0][0]: prio_max}
    span = max(0, prio_max - prio_min)
    out: Dict[str, int] = {}
    for i, (fn, _) in enumerate(scores):
        prio = int(round(prio_max - (span * i) / (n - 1)))
        prio = max(prio_min, min(prio_max, prio))
        out[fn] = prio
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Compute LPF thread priorities from Level-1 segment DAG and timings.")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"))
    ap.add_argument("--base-name", required=True)
    ap.add_argument("--project", required=True, help="Project name under 时间分析_level1/<project>/")
    ap.add_argument("--prio-min", type=int, default=10)
    ap.add_argument("--prio-max", type=int, default=80)
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name
    stage_dir = base_dir / "中间结果" / base_name / "level1" / "stage1"
    ta_dir = base_dir / "中间结果" / base_name / "level1" / "timing" / args.project

    segments_json = json.loads((stage_dir / "segments_stage1.json").read_text(encoding="utf-8"))
    dag_json = json.loads((stage_dir / "dag_stage1_seg.json").read_text(encoding="utf-8"))
    time_json = json.loads((ta_dir / "time_result_seg.json").read_text(encoding="utf-8"))

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
    weights = {k: int(v.get("total_ns", 0) or 0) for k, v in time_json.items() if isinstance(v, dict)}

    priorities = assign_thread_priorities(
        segments=segments,
        dag_edges=edges,
        seg_weights_ns=weights,
        prio_min=args.prio_min,
        prio_max=args.prio_max,
    )

    out_dir = base_dir / "中间结果" / base_name / "level1" / "schedule" / "lpf_thread"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "schedule_thread.json"
    payload = {
        "base_name": base_name,
        "project": args.project,
        "prio_range": {"min": args.prio_min, "max": args.prio_max},
        "priorities": priorities,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
