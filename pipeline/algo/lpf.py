from __future__ import annotations

from typing import Dict, List, Tuple

from .common import load_avg_weights, load_edges, load_segments, make_schedule, rank_scores_desc, topo_sort, validate_priorities


class LPFBlockAlgo:
    def algo_id(self) -> str:
        return "lpf"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        segments = load_segments(segments_json)
        ids = [str(seg["seg_id"]) for seg in segments]
        edges = load_edges(dag_json, ids)
        avg_weights = load_avg_weights(timing_json, ids)

        priorities = self._assign_lpf_priorities(segments=segments, edges=edges, weights=avg_weights, prio_max=99)
        schedule = make_schedule(algo_name=self.algo_id(), base_name=str(segments_json.get("base_name", "")), priorities=priorities)
        self.validate(schedule)
        return schedule

    def validate(self, schedule_json: Dict) -> None:
        validate_priorities(schedule_json)

    @staticmethod
    def _find_sink(segments: List[Dict], topo_order: List[str]) -> str:
        main_segs = [s for s in segments if s.get("function") == "main"]
        if main_segs:
            main_segs.sort(key=lambda x: (int(x.get("end_line", 0)), str(x.get("seg_id"))))
            return str(main_segs[-1]["seg_id"])
        return topo_order[-1]

    def _assign_lpf_priorities(self, *, segments: List[Dict], edges: List[Tuple[str, str]], weights: Dict[str, int], prio_max: int) -> Dict[str, int]:
        ids = [str(s["seg_id"]) for s in segments]
        order = topo_sort(ids, edges)
        sink = self._find_sink(segments, order)

        succ: Dict[str, List[str]] = {n: [] for n in ids}
        for u, v in edges:
            succ.setdefault(u, []).append(v)

        neg_inf = -(1 << 60)
        crit: Dict[str, int] = {n: neg_inf for n in ids}
        crit[sink] = int(weights[sink])
        for n in reversed(order):
            if n == sink:
                continue
            best = neg_inf
            for s in succ.get(n, []):
                if crit.get(s, neg_inf) > best:
                    best = crit[s]
            if best == neg_inf:
                continue
            crit[n] = int(weights[n]) + best

        # Include unreachable nodes with self weight so every block gets a priority.
        for n in ids:
            if crit[n] == neg_inf:
                crit[n] = int(weights[n])

        return rank_scores_desc(crit, prio_max=prio_max)
