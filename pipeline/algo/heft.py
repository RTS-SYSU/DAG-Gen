from __future__ import annotations

from typing import Dict, List, Tuple

from ..constants import SCHEMA_VERSION
from ..errors import ValidationError


class HEFTBlockAlgo:
    """HEFT (zero communication-cost variant) for block DAG scheduling."""

    def algo_id(self) -> str:
        return "heft"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        segments = self._load_segments(segments_json)
        ids = [str(s["seg_id"]) for s in segments]

        edges = self._load_edges(dag_json, valid_nodes=set(ids))
        weights = self._load_weights(timing_json)

        topo = self._topo_sort(ids, edges)
        succ, pred = self._build_adj(ids, edges)
        rank_u = self._compute_rank_u(topo=topo, succ=succ, weights=weights)

        # Use function count as a stable proxy of worker count for EFT selection.
        proc_count = max(1, len({str(s["function"]) for s in segments}))
        assignments, order = self._assign_eft_order(
            ids=ids,
            pred=pred,
            succ=succ,
            rank_u=rank_u,
            weights=weights,
            proc_count=proc_count,
        )

        priorities = self._assign_priorities(rank_u=rank_u, prio_max=99)
        schedule = {
            "schema_version": SCHEMA_VERSION,
            "base_name": str(segments_json.get("base_name", "")),
            "algo_name": self.algo_id(),
            "priorities": priorities,
            "order": order,
            "assignments": assignments,
            "meta": {
                "comm_cost_model": "zero",
                "processor_count": proc_count,
                "rank_u": rank_u,
            },
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
    def _load_segments(segments_json: Dict) -> List[Dict]:
        out: List[Dict] = []
        for s in segments_json.get("segments", []):
            if not isinstance(s, dict):
                continue
            try:
                out.append(
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
        return out

    @staticmethod
    def _load_edges(dag_json: Dict, valid_nodes: set[str]) -> List[Tuple[str, str]]:
        edges: List[Tuple[str, str]] = []
        for e in dag_json.get("edges", []):
            if not isinstance(e, dict):
                continue
            src = e.get("src")
            dst = e.get("dst")
            if isinstance(src, str) and isinstance(dst, str) and src in valid_nodes and dst in valid_nodes:
                edges.append((src, dst))
        return edges

    @staticmethod
    def _load_weights(timing_json: Dict) -> Dict[str, int]:
        weights: Dict[str, int] = {}
        payload = timing_json.get("weights", {})
        if isinstance(payload, dict):
            for seg_id, metric in payload.items():
                if not isinstance(seg_id, str) or not isinstance(metric, dict):
                    continue
                # Prefer avg_ns for stability; fallback to total_ns.
                avg_ns = int(metric.get("avg_ns", 0) or 0)
                total_ns = int(metric.get("total_ns", 0) or 0)
                weights[seg_id] = avg_ns if avg_ns > 0 else total_ns
        return weights

    @staticmethod
    def _build_adj(nodes: List[str], edges: List[Tuple[str, str]]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]]]:
        succ: Dict[str, List[str]] = {n: [] for n in nodes}
        pred: Dict[str, List[str]] = {n: [] for n in nodes}
        for u, v in edges:
            succ.setdefault(u, []).append(v)
            pred.setdefault(v, []).append(u)
        return succ, pred

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
    def _compute_rank_u(*, topo: List[str], succ: Dict[str, List[str]], weights: Dict[str, int]) -> Dict[str, int]:
        rank_u: Dict[str, int] = {}
        for n in reversed(topo):
            w = int(weights.get(n, 0) or 0)
            nxt = succ.get(n, [])
            if not nxt:
                rank_u[n] = w
                continue
            rank_u[n] = w + max(int(rank_u.get(s, 0)) for s in nxt)
        return rank_u

    @staticmethod
    def _assign_eft_order(
        *,
        ids: List[str],
        pred: Dict[str, List[str]],
        succ: Dict[str, List[str]],
        rank_u: Dict[str, int],
        weights: Dict[str, int],
        proc_count: int,
    ) -> Tuple[Dict[str, Dict[str, int]], List[str]]:
        indeg: Dict[str, int] = {n: len(pred.get(n, [])) for n in ids}
        ready: List[str] = sorted([n for n in ids if indeg.get(n, 0) == 0])

        proc_avail = [0 for _ in range(proc_count)]
        starts: Dict[str, int] = {}
        ends: Dict[str, int] = {}
        procs: Dict[str, int] = {}
        order: List[str] = []

        while ready:
            ready.sort(key=lambda n: (-int(rank_u.get(n, 0)), -int(weights.get(n, 0)), n))
            v = ready.pop(0)

            pred_finish = 0
            for p in pred.get(v, []):
                pred_finish = max(pred_finish, int(ends.get(p, 0)))

            wv = int(weights.get(v, 0))
            best_proc = 0
            best_start = max(proc_avail[0], pred_finish)
            best_end = best_start + wv
            for pi in range(1, proc_count):
                start = max(proc_avail[pi], pred_finish)
                end = start + wv
                if end < best_end or (end == best_end and pi < best_proc):
                    best_proc = pi
                    best_start = start
                    best_end = end

            starts[v] = best_start
            ends[v] = best_end
            procs[v] = best_proc
            proc_avail[best_proc] = best_end
            order.append(v)

            for s in succ.get(v, []):
                indeg[s] = int(indeg.get(s, 0)) - 1
                if indeg[s] == 0:
                    ready.append(s)

        if len(order) != len(ids):
            raise ValidationError("HEFT assignment incomplete; check DAG integrity")

        assignments: Dict[str, Dict[str, int]] = {}
        for seg_id in order:
            assignments[seg_id] = {
                "processor": int(procs[seg_id]),
                "start_ns": int(starts[seg_id]),
                "end_ns": int(ends[seg_id]),
            }
        return assignments, order

    @staticmethod
    def _assign_priorities(*, rank_u: Dict[str, int], prio_max: int) -> Dict[str, int]:
        ranked = sorted(rank_u.keys(), key=lambda n: (int(rank_u[n]), n), reverse=True)
        priorities: Dict[str, int] = {}
        for idx, seg_id in enumerate(ranked):
            priorities[seg_id] = max(1, prio_max - idx)
        return priorities
