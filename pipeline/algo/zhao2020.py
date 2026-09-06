from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from .common import build_adj, load_avg_weights, load_edges, load_node_ids, make_schedule, topo_sort, validate_priorities


NodeId = str
Edge = Tuple[NodeId, NodeId]


@dataclass
class Provider:
    idx: int
    nodes: List[NodeId]
    F: Set[NodeId]
    G: Set[NodeId]


@dataclass
class CPCModel:
    critical_path: List[NodeId]
    critical_set: Set[NodeId]
    consumers_all: Set[NodeId]
    providers: List[Provider]


class Zhao2020BlockAlgo:
    """
    RTSS 2020 (Zhao et al.): CPC model + EA rule-based priority assignment.

    Outputs fixed priorities for nodes (segments) and keeps priorities in 1..99.
    """

    def algo_id(self) -> str:
        return "zhao2020"

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        nodes = load_node_ids(segments_json)
        edges = load_edges(dag_json, nodes)

        if not nodes:
            schedule = make_schedule(
                algo_name=self.algo_id(),
                base_name=str(segments_json.get("base_name", "")),
                priorities={},
                meta={"critical_path": [], "providers": []},
            )
            self.validate(schedule)
            return schedule
        wcet = load_avg_weights(timing_json, nodes)

        critical_path = self._critical_path_longest_Completed(nodes=nodes, edges=edges, wcet=wcet)
        cpc = self._build_cpc_model(nodes=nodes, edges=edges, critical_path=critical_path)
        priorities = self._ea_priority_assignment(nodes=nodes, edges=edges, wcet=wcet, cpc=cpc, prio_max=99)

        schedule = make_schedule(
            algo_name=self.algo_id(),
            base_name=str(segments_json.get("base_name", "")),
            priorities=priorities,
            meta=self._build_meta(cpc),
        )
        self.validate(schedule)
        return schedule

    def validate(self, schedule_json: Dict) -> None:
        validate_priorities(schedule_json)

    @staticmethod
    def _build_adj(nodes: List[NodeId], edges: List[Edge]) -> Tuple[Dict[NodeId, List[NodeId]], Dict[NodeId, List[NodeId]]]:
        return build_adj(nodes, edges)

    @staticmethod
    def _topo_sort(nodes: List[NodeId], edges: List[Edge]) -> List[NodeId]:
        return topo_sort(nodes, edges)

    @staticmethod
    def _critical_path_longest_Completed(*, nodes: List[NodeId], edges: List[Edge], wcet: Dict[NodeId, int]) -> List[NodeId]:
        succ, pred = Zhao2020BlockAlgo._build_adj(nodes, edges)
        sources = [n for n in nodes if not pred.get(n)]
        sinks = [n for n in nodes if not succ.get(n)]
        if not sources or not sinks:
            # Degenerate graphs still get a deterministic critical path.
            return [min(nodes)]

        vsrc = "__vsrc__"
        vsink = "__vsink__"
        while vsrc in succ or vsrc in pred:
            vsrc += "_"
        while vsink in succ or vsink in pred or vsink == vsrc:
            vsink += "_"

        aug_nodes = list(nodes) + [vsrc, vsink]
        aug_edges: List[Edge] = list(edges)
        for s in sources:
            aug_edges.append((vsrc, s))
        for t in sinks:
            aug_edges.append((t, vsink))

        topo = Zhao2020BlockAlgo._topo_sort(aug_nodes, aug_edges)
        aug_succ, _ = Zhao2020BlockAlgo._build_adj(aug_nodes, aug_edges)

        dp: Dict[NodeId, int] = {}
        nxt: Dict[NodeId, Optional[NodeId]] = {}
        for u in reversed(topo):
            best_v: Optional[NodeId] = None
            best = -(1 << 60)
            for v in aug_succ.get(u, []):
                val = int(dp.get(v, 0))
                if val > best or (val == best and (best_v is None or v < best_v)):
                    best = val
                    best_v = v
            w = int(wcet.get(u, 0) or 0)
            dp[u] = w + (best if best_v is not None else 0)
            nxt[u] = best_v

        path: List[NodeId] = []
        cur: Optional[NodeId] = vsrc
        while cur is not None:
            path.append(cur)
            if cur == vsink:
                break
            cur = nxt.get(cur)

        # Remove virtual endpoints.
        out = [n for n in path if n not in {vsrc, vsink}]
        if not out:
            out = [min(nodes)]
        return out

    @staticmethod
    def _build_cpc_model(*, nodes: List[NodeId], edges: List[Edge], critical_path: List[NodeId]) -> CPCModel:
        succ, pred = Zhao2020BlockAlgo._build_adj(nodes, edges)
        critical_set = set(critical_path)
        consumers_all = set(nodes) - critical_set

        # Step 1: split critical path into providers.
        providers_nodes: List[List[NodeId]] = []
        i = 0
        while i < len(critical_path):
            cur = [critical_path[i]]
            j = i
            while j + 1 < len(critical_path):
                vj = critical_path[j]
                vnext = critical_path[j + 1]
                if set(pred.get(vnext, [])) == {vj}:
                    cur.append(vnext)
                    j += 1
                else:
                    break
            providers_nodes.append(cur)
            i = j + 1

        # Ancestors/descendants caches (on-demand).
        anc_cache: Dict[NodeId, Set[NodeId]] = {}
        des_cache: Dict[NodeId, Set[NodeId]] = {}

        def ancestors(v: NodeId) -> Set[NodeId]:
            if v in anc_cache:
                return anc_cache[v]
            seen: Set[NodeId] = set()
            stack = list(pred.get(v, []))
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                stack.extend(pred.get(u, []))
            anc_cache[v] = seen
            return seen

        def descendants(v: NodeId) -> Set[NodeId]:
            if v in des_cache:
                return des_cache[v]
            seen: Set[NodeId] = set()
            stack = list(succ.get(v, []))
            while stack:
                u = stack.pop()
                if u in seen:
                    continue
                seen.add(u)
                stack.extend(succ.get(u, []))
            des_cache[v] = seen
            return seen

        # Step 2: compute F/G per provider using V_not (V¬) updates.
        V_not = set(consumers_all)
        providers: List[Provider] = []
        for idx, pnodes in enumerate(providers_nodes):
            if idx + 1 >= len(providers_nodes):
                providers.append(Provider(idx=idx + 1, nodes=pnodes, F=set(), G=set()))
                continue

            head_next = providers_nodes[idx + 1][0]
            F = ancestors(head_next) & V_not

            G: Set[NodeId] = set()
            for vj in F:
                C_vj = V_not - ancestors(vj) - descendants(vj) - {vj}
                G |= C_vj

            V_not -= F
            providers.append(Provider(idx=idx + 1, nodes=pnodes, F=F, G=G))

        return CPCModel(
            critical_path=list(critical_path),
            critical_set=critical_set,
            consumers_all=consumers_all,
            providers=providers,
        )

    @staticmethod
    def _ea_priority_assignment(*, nodes: List[NodeId], edges: List[Edge], wcet: Dict[NodeId, int], cpc: CPCModel, prio_max: int) -> Dict[NodeId, int]:
        priorities: Dict[NodeId, int] = {}
        p = int(prio_max)

        def dec(val: int) -> int:
            return max(1, val - 1)

        # Rule 1: assign critical path with highest priorities.
        for v in cpc.critical_path:
            if v in priorities:
                continue
            priorities[v] = p
            p = dec(p)

        # Rule 2 + Rule 3*: process each consumer group in provider order.
        for provider in cpc.providers:
            if not provider.F:
                continue
            p = Zhao2020BlockAlgo._assign_consumer_group(
                group_nodes=set(provider.F),
                all_edges=edges,
                wcet=wcet,
                p=p,
                priorities=priorities,
            )

        # Fallback: assign any remaining nodes deterministically.
        for v in sorted(nodes):
            if v in priorities:
                continue
            priorities[v] = p
            p = dec(p)

        return priorities

    @staticmethod
    def _assign_consumer_group(
        *,
        group_nodes: Set[NodeId],
        all_edges: List[Edge],
        wcet: Dict[NodeId, int],
        p: int,
        priorities: Dict[NodeId, int],
    ) -> int:
        def dec(val: int) -> int:
            return max(1, val - 1)

        def induced_edges(ns: Set[NodeId]) -> List[Edge]:
            return [(u, v) for (u, v) in all_edges if u in ns and v in ns]

        # Loop until group is fully assigned, unless nested CPC recursion takes over.
        remaining = set(group_nodes)
        while remaining:
            sub_nodes = sorted(remaining)
            sub_edges = induced_edges(remaining)

            topo = Zhao2020BlockAlgo._topo_sort(sub_nodes, sub_edges)
            succ, pred = Zhao2020BlockAlgo._build_adj(sub_nodes, sub_edges)

            # DP: longest path ending at each node (within induced subgraph).
            best_end: Dict[NodeId, int] = {}
            best_pred: Dict[NodeId, Optional[NodeId]] = {}
            for v in topo:
                w = int(wcet.get(v, 0) or 0)
                preds = pred.get(v, [])
                if not preds:
                    best_end[v] = w
                    best_pred[v] = None
                    continue
                chosen: Optional[NodeId] = None
                chosen_val = -(1 << 60)
                for pv in preds:
                    val = int(best_end.get(pv, 0))
                    if val > chosen_val or (val == chosen_val and (chosen is None or pv < chosen)):
                        chosen_val = val
                        chosen = pv
                best_end[v] = w + int(chosen_val)
                best_pred[v] = chosen

            sinks = [v for v in sub_nodes if not succ.get(v)]
            ve = max(sinks, key=lambda x: (int(best_end.get(x, 0)), x))

            path_rev: List[NodeId] = []
            cur: Optional[NodeId] = ve
            while cur is not None:
                path_rev.append(cur)
                cur = best_pred.get(cur)
            path = list(reversed(path_rev))

            # Nested CPC trigger: any node on the path has in-degree > 1 in the induced subgraph.
            if any(len(pred.get(x, [])) > 1 for x in path):
                cpc_inner = Zhao2020BlockAlgo._build_cpc_model(nodes=sub_nodes, edges=sub_edges, critical_path=path)

                # Run EA on this subgraph and return (fully handled by recursion).
                inner_priorities = Zhao2020BlockAlgo._ea_priority_assignment(
                    nodes=sub_nodes,
                    edges=sub_edges,
                    wcet=wcet,
                    cpc=cpc_inner,
                    prio_max=p,
                )
                # Merge assigned priorities and update p to the next after the smallest assigned.
                for k, v in inner_priorities.items():
                    if k in priorities:
                        continue
                    priorities[k] = int(v)
                p = min(priorities.get(k, p) for k in sub_nodes)
                p = dec(p)
                return p

            # Independent path: assign priorities along the path.
            for v in path:
                if v in priorities:
                    continue
                priorities[v] = p
                p = dec(p)
            remaining -= set(path)

        return p

    @staticmethod
    def _build_meta(cpc: CPCModel) -> Dict:
        providers_meta: List[Dict] = []
        for pr in cpc.providers:
            providers_meta.append(
                {
                    "idx": pr.idx,
                    "nodes": list(pr.nodes),
                    "F_size": len(pr.F),
                    "G_size": len(pr.G),
                    "F": sorted(pr.F),
                    "G": sorted(pr.G),
                }
            )
        return {
            "critical_path": list(cpc.critical_path),
            "providers": providers_meta,
        }
