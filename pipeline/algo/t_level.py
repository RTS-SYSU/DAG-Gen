from __future__ import annotations

from typing import Dict

from .common import build_adj, load_avg_weights, load_edges, load_node_ids, make_schedule, rank_scores_desc, topo_sort, validate_priorities


class TLevelBlockAlgo:
    def algo_id(self) -> str:
        return "t_level"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        node_ids = load_node_ids(segments_json)
        edges = load_edges(dag_json, node_ids)
        order = topo_sort(node_ids, edges)
        weights = load_avg_weights(timing_json, node_ids)
        _, pred = build_adj(node_ids, edges)

        scores: Dict[str, int] = {}
        for seg_id in order:
            parents = pred.get(seg_id, [])
            if not parents:
                scores[seg_id] = 0
                continue
            scores[seg_id] = max(int(scores[parent]) + int(weights[parent]) for parent in parents)

        priorities = rank_scores_desc(scores, prio_max=99)
        schedule = make_schedule(
            algo_name=self.algo_id(),
            base_name=str(segments_json.get("base_name", "")),
            priorities=priorities,
            meta={"scores": scores},
        )
        self.validate(schedule)
        return schedule

    def validate(self, schedule_json: Dict) -> None:
        validate_priorities(schedule_json)
