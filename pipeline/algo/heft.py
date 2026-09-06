from __future__ import annotations

from typing import Dict, List, Tuple

from .common import build_adj, load_avg_weights, load_edges, load_segments, make_schedule, rank_scores_desc, topo_sort, validate_priorities


class HEFTBlockAlgo:
    """HEFT (zero communication-cost variant) for block DAG scheduling."""

    def algo_id(self) -> str:
        return "heft"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        segments = load_segments(segments_json)
        ids = [str(s["seg_id"]) for s in segments]

        edges = load_edges(dag_json, ids)
        weights = load_avg_weights(timing_json, ids)

        topo = topo_sort(ids, edges)
        succ, pred = build_adj(ids, edges)
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

        priorities = rank_scores_desc(rank_u, prio_max=99)
        schedule = make_schedule(
            algo_name=self.algo_id(),
            base_name=str(segments_json.get("base_name", "")),
            priorities=priorities,
            meta={"comm_cost_model": "zero", "processor_count": proc_count, "rank_u": rank_u},
        )
        schedule["order"] = order
        schedule["assignments"] = assignments
        self.validate(schedule)
        return schedule

    def validate(self, schedule_json: Dict) -> None:
        validate_priorities(schedule_json)

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
            raise ValidationError("HEFT assignment inCompleted; check DAG integrity")

        assignments: Dict[str, Dict[str, int]] = {}
        for seg_id in order:
            assignments[seg_id] = {
                "processor": int(procs[seg_id]),
                "start_ns": int(starts[seg_id]),
                "end_ns": int(ends[seg_id]),
            }
        return assignments, order
