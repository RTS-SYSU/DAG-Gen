from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .common import build_adj, load_avg_weights, load_edges, load_segments, make_schedule, topo_sort, validate_priorities


class CPFBlockAlgo:
    def algo_id(self) -> str:
        return "LPF"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        segments = load_segments(segments_json)
        ids = [str(seg["seg_id"]) for seg in segments]
        edges = load_edges(dag_json, ids)
        avg_weights = load_avg_weights(timing_json, ids)

        priorities, cp_layers = self._assign_cpf_priorities(segments=segments, edges=edges, weights=avg_weights, prio_max=99)
        schedule = make_schedule(
            algo_name=self.algo_id(),
            base_name=str(segments_json.get("base_name", "")),
            priorities=priorities,
            meta={"cp_layers": cp_layers},
        )
        self.validate(schedule)
        return schedule

    def validate(self, schedule_json: Dict) -> None:
        validate_priorities(schedule_json)

    @staticmethod
    def _extract_longest_path(
        *,
        active_nodes: Set[str],
        edges: List[Tuple[str, str]],
        weights: Dict[str, int],
    ) -> List[str]:
        sub_edges = [(u, v) for (u, v) in edges if u in active_nodes and v in active_nodes]
        topo = topo_sort(sorted(active_nodes), sub_edges)
        succ, pred = build_adj(topo, sub_edges)

        dist: Dict[str, int] = {}
        best_pred: Dict[str, Optional[str]] = {}
        for n in topo:
            w = int(weights[n])
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
        cur: Optional[str] = sink
        while cur is not None:
            path_rev.append(cur)
            cur = best_pred.get(cur)
        return list(reversed(path_rev))

    def _assign_cpf_priorities(
        self,
        *,
        segments: List[Dict],
        edges: List[Tuple[str, str]],
        weights: Dict[str, int],
        prio_max: int,
    ) -> Tuple[Dict[str, int], List[List[str]]]:
        active: Set[str] = {str(s["seg_id"]) for s in segments}
        cp_layers: List[List[str]] = []
        ordered: List[str] = []

        while active:
            path = self._extract_longest_path(active_nodes=active, edges=edges, weights=weights)
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
