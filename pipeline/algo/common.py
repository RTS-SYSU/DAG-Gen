from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

from ..constants import SCHEMA_VERSION
from ..errors import ValidationError

SegmentRow = Dict[str, Union[int, str]]
Edge = Tuple[str, str]


def load_segments(segments_json: Dict) -> List[SegmentRow]:
    out: List[SegmentRow] = []
    for item in segments_json.get("segments", []):
        if not isinstance(item, dict):
            continue
        try:
            out.append(
                {
                    "seg_id": str(item["seg_id"]),
                    "function": str(item["function"]),
                    "kind": str(item["kind"]),
                    "start_line": int(item["start_line"]),
                    "end_line": int(item["end_line"]),
                }
            )
        except Exception:
            continue
    return out


def load_node_ids(segments_json: Dict) -> List[str]:
    return [str(seg["seg_id"]) for seg in load_segments(segments_json)]


def load_edges(dag_json: Dict, valid_nodes: Iterable[str]) -> List[Edge]:
    valid = set(valid_nodes)
    edges: List[Edge] = []
    for item in dag_json.get("edges", []):
        if not isinstance(item, dict):
            continue
        src = item.get("src")
        dst = item.get("dst")
        if isinstance(src, str) and isinstance(dst, str) and src in valid and dst in valid:
            edges.append((src, dst))
    return edges


def load_avg_weights(timing_json: Dict, valid_nodes: Iterable[str]) -> Dict[str, int]:
    valid = set(valid_nodes)
    payload = timing_json.get("weights", {})
    if not isinstance(payload, dict):
        raise ValidationError("timing.weights must be dict")

    weights: Dict[str, int] = {}
    for seg_id in sorted(valid):
        if seg_id not in payload:
            raise ValidationError(f"timing weight missing for segment: {seg_id}")
        metric = payload[seg_id]
        if not isinstance(metric, dict):
            raise ValidationError(f"timing weight for {seg_id} must be dict")
        if "avg_ns" not in metric:
            raise ValidationError(f"timing weight for {seg_id} missing avg_ns")
        try:
            weights[seg_id] = int(metric["avg_ns"])
        except Exception as exc:
            raise ValidationError(f"timing weight for {seg_id} has invalid avg_ns") from exc
    return weights


def build_adj(nodes: Sequence[str], edges: Sequence[Edge]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
    succ: Dict[str, List[str]] = {n: [] for n in nodes}
    pred: Dict[str, List[str]] = {n: [] for n in nodes}
    for u, v in edges:
        succ.setdefault(u, []).append(v)
        pred.setdefault(v, []).append(u)
    return succ, pred


def topo_sort(nodes: Sequence[str], edges: Sequence[Edge]) -> List[str]:
    succ, pred = build_adj(nodes, edges)
    indeg: Dict[str, int] = {n: len(pred.get(n, [])) for n in nodes}
    ready = sorted([n for n, deg in indeg.items() if deg == 0])
    order: List[str] = []
    i = 0
    while i < len(ready):
        cur = ready[i]
        i += 1
        order.append(cur)
        for nxt in succ.get(cur, []):
            indeg[nxt] -= 1
            if indeg[nxt] == 0:
                ready.append(nxt)
    if len(order) != len(indeg):
        raise ValidationError("segment DAG has a cycle")
    return order


def rank_scores_desc(scores: Dict[str, int], *, prio_max: int) -> Dict[str, int]:
    ranked = sorted(scores.keys(), key=lambda seg_id: (-int(scores[seg_id]), seg_id))
    priorities: Dict[str, int] = {}
    for idx, seg_id in enumerate(ranked):
        priorities[seg_id] = max(1, prio_max - idx)
    return priorities


def validate_priorities(schedule_json: Dict) -> None:
    prios = schedule_json.get("priorities")
    if not isinstance(prios, dict):
        raise ValidationError("schedule.priorities must be dict")
    for seg_id, val in prios.items():
        if not isinstance(seg_id, str):
            raise ValidationError("schedule priority key must be string seg_id")
        iv = int(val)
        if iv < 1 or iv > 99:
            raise ValidationError(f"priority for {seg_id} out of range 1..99: {iv}")


def make_schedule(*, algo_name: str, base_name: str, priorities: Dict[str, int], meta: Optional[Dict] = None) -> Dict:
    schedule = {
        "schema_version": SCHEMA_VERSION,
        "base_name": base_name,
        "algo_name": algo_name,
        "priorities": priorities,
    }
    if meta:
        schedule["meta"] = meta
    return schedule
