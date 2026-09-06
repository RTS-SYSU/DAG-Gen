from __future__ import annotations

from typing import Dict

from .common import load_avg_weights, load_edges, load_node_ids, make_schedule, rank_scores_desc, topo_sort, validate_priorities


class WCETFirstBlockAlgo:
    def algo_id(self) -> str:
        return "FIFO"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        node_ids = load_node_ids(segments_json)
        topo_sort(node_ids, load_edges(dag_json, node_ids))
        scores = load_avg_weights(timing_json, node_ids)
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
