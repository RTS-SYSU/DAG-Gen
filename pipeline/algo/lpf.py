from __future__ import annotations

from typing import Dict, List, Tuple

from ..constants import SCHEMA_VERSION
from ..errors import ValidationError


class LPFBlockAlgo:
    def algo_id(self) -> str:
        return "lpf"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        segments: List[Dict] = []
        for s in segments_json.get("segments", []):
            if not isinstance(s, dict):
                continue
            try:
                segments.append(
                    {
                        "seg_id": str(s["seg_id"]),
                        "function": str(s["function"]),
                        "kind": str(s["kind"]),
                        "start_line": int(s["start_line"]),
                        "end_line": int(s["end_line"]),
                    }
                )
            except Exception:
                continue

        edges: List[Tuple[str, str]] = []
        for e in dag_json.get("edges", []):
            if not isinstance(e, dict):
                continue
            src = e.get("src")
            dst = e.get("dst")
            if isinstance(src, str) and isinstance(dst, str):
                edges.append((src, dst))

        totals: Dict[str, int] = {}
        weights = timing_json.get("weights", {})
        if isinstance(weights, dict):
            for seg_id, metric in weights.items():
                if isinstance(seg_id, str) and isinstance(metric, dict):
                    totals[seg_id] = int(metric.get("total_ns", 0) or 0)

        priorities = self._assign_lpf_priorities(segments=segments, edges=edges, totals=totals, prio_max=99)
        schedule = {
            "schema_version": SCHEMA_VERSION,
            "base_name": str(segments_json.get("base_name", "")),
            "algo_name": self.algo_id(),
            "priorities": priorities,
        }
        self.validate(schedule)
        return schedule

    def validate(self, schedule_json: Dict) -> None:
        prios = schedule_json.get("priorities")
        if not isinstance(prios, dict):
            raise ValidationError("schedule.priorities must be dict")
        for seg_id, val in prios.items():
            if not isinstance(seg_id, str):
                raise ValidationError("schedule priority key must be string seg_id")
            iv = int(val)
            if iv < 1 or iv > 99:
                raise ValidationError(f"priority for {seg_id} out of range 1..99: {iv}")

    @staticmethod
    def _topo_sort(nodes: List[str], edges: List[Tuple[str, str]]) -> List[str]:
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
        q = sorted([n for n, d in indeg.items() if d == 0])
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
            raise ValidationError("segment DAG has a cycle")
        return order

    @staticmethod
    def _find_sink(segments: List[Dict], topo_order: List[str]) -> str:
        main_segs = [s for s in segments if s.get("function") == "main"]
        if main_segs:
            main_segs.sort(key=lambda x: (int(x.get("end_line", 0)), str(x.get("seg_id"))))
            return str(main_segs[-1]["seg_id"])
        return topo_order[-1]

    def _assign_lpf_priorities(self, *, segments: List[Dict], edges: List[Tuple[str, str]], totals: Dict[str, int], prio_max: int) -> Dict[str, int]:
        ids = [str(s["seg_id"]) for s in segments]
        order = self._topo_sort(ids, edges)
        sink = self._find_sink(segments, order)

        succ: Dict[str, List[str]] = {n: [] for n in ids}
        for u, v in edges:
            succ.setdefault(u, []).append(v)

        neg_inf = -(1 << 60)
        crit: Dict[str, int] = {n: neg_inf for n in ids}
        crit[sink] = int(totals.get(sink, 0) or 0)
        for n in reversed(order):
            if n == sink:
                continue
            best = neg_inf
            for s in succ.get(n, []):
                if crit.get(s, neg_inf) > best:
                    best = crit[s]
            if best == neg_inf:
                continue
            crit[n] = int(totals.get(n, 0) or 0) + best

        # Include unreachable nodes with self weight so every block gets a priority.
        for n in ids:
            if crit[n] == neg_inf:
                crit[n] = int(totals.get(n, 0) or 0)

        ranked = sorted(ids, key=lambda n: (crit[n], n), reverse=True)
        priorities: Dict[str, int] = {}
        for idx, seg_id in enumerate(ranked):
            priorities[seg_id] = max(1, prio_max - idx)
        return priorities
