from __future__ import annotations

from typing import Dict, List, Set, Tuple

from ..constants import SCHEMA_VERSION
from ..errors import ValidationError


class CPFBlockAlgo:
    def algo_id(self) -> str:
        return "cpf"

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

        priorities, cp_layers = self._assign_cpf_priorities(segments=segments, edges=edges, totals=totals, prio_max=99)
        schedule = {
            "schema_version": SCHEMA_VERSION,
            "base_name": str(segments_json.get("base_name", "")),
            "algo_name": self.algo_id(),
            "priorities": priorities,
            "meta": {"cp_layers": cp_layers},
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
    def _build_adj(nodes: List[str], edges: List[Tuple[str, str]]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        succ: Dict[str, List[str]] = {n: [] for n in nodes}
        pred: Dict[str, List[str]] = {n: [] for n in nodes}
        for u, v in edges:
            succ.setdefault(u, []).append(v)
            pred.setdefault(v, []).append(u)
        return succ, pred

    @staticmethod
    def _extract_longest_path(
        *,
        active_nodes: Set[str],
        edges: List[Tuple[str, str]],
        totals: Dict[str, int],
    ) -> List[str]:
        sub_edges = [(u, v) for (u, v) in edges if u in active_nodes and v in active_nodes]
        topo = CPFBlockAlgo._topo_sort(sorted(active_nodes), sub_edges)
        succ, pred = CPFBlockAlgo._build_adj(topo, sub_edges)

        dist: Dict[str, int] = {}
        best_pred: Dict[str, str | None] = {}
        for n in topo:
            w = int(totals.get(n, 0) or 0)
            preds = pred.get(n, [])
            if not preds:
                dist[n] = w
                best_pred[n] = None
                continue
            chosen = max(preds, key=lambda p: (int(dist.get(p, 0)), p))
            dist[n] = int(dist.get(chosen, 0)) + w
            best_pred[n] = chosen

        sinks = [n for n in topo if not succ.get(n, [])]
        sink = max(sinks, key=lambda n: (int(dist.get(n, 0)), n))

        path_rev: List[str] = []
        cur: str | None = sink
        while cur is not None:
            path_rev.append(cur)
            cur = best_pred.get(cur)
        return list(reversed(path_rev))

    def _assign_cpf_priorities(
        self,
        *,
        segments: List[Dict],
        edges: List[Tuple[str, str]],
        totals: Dict[str, int],
        prio_max: int,
    ) -> Tuple[Dict[str, int], List[List[str]]]:
        active: Set[str] = {str(s["seg_id"]) for s in segments}
        cp_layers: List[List[str]] = []
        ordered: List[str] = []

        while active:
            path = self._extract_longest_path(active_nodes=active, edges=edges, totals=totals)
            if not path:
                break
            cp_layers.append(path)
            ordered.extend(path)
            for node in path:
                if node in active:
                    active.remove(node)

        # Fallback safety: if any node not emitted, append deterministically.
        if active:
            for node in sorted(active):
                ordered.append(node)

        priorities: Dict[str, int] = {}
        for idx, seg_id in enumerate(ordered):
            priorities[seg_id] = max(1, prio_max - idx)
        return priorities, cp_layers
