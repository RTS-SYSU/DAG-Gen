from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple


@dataclass(frozen=True)
class LongestPathResult:
    path: List[str]
    total_weight_ns: int
    missing_weight_nodes: List[str]
    node_weight_ns: Dict[str, int]


_EDGE_RE = re.compile(r'"([^"]+)"\s*->\s*"([^"]+)"')
_NODE_QUOTED_RE = re.compile(r'"([^"]+)"')
_NODE_STMT_RE = re.compile(r'^(?P<indent>\s*)"(?P<name>[^"]+)"\s*(?P<attrs>\[[^\]]*\])?\s*;?\s*$')
_EDGE_STMT_RE = re.compile(
    r'^(?P<indent>\s*)"(?P<src>[^"]+)"\s*->\s*"(?P<dst>[^"]+)"\s*(?P<attrs>\[[^\]]*\])?\s*;?\s*$'
)


def parse_dot_edges(dot_path: Path) -> Tuple[Set[str], List[Tuple[str, str]]]:
    """极简解析 legacy 输出的 DOT，抽取节点集合与有向边列表。"""
    text = dot_path.read_text(encoding="utf-8", errors="replace")
    edges = _EDGE_RE.findall(text)
    nodes: Set[str] = set()
    for a, b in edges:
        nodes.add(a)
        nodes.add(b)
    # nodes that appear only as standalone "node" lines
    for name in _NODE_QUOTED_RE.findall(text):
        nodes.add(name)
    # strip graphviz keywords if accidentally captured
    nodes.discard("callgraph")
    return nodes, [(a, b) for a, b in edges]


def load_time_result_weights(time_result_json: Path) -> Dict[str, int]:
    """读取 time_result.json，返回 {node_key: total_ns}。"""
    data = json.loads(time_result_json.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("time_result.json 顶层必须是对象(dict)")
    out: Dict[str, int] = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        try:
            out[str(k)] = int(v.get("total_ns", 0) or 0)
        except Exception:
            out[str(k)] = 0
    return out


def topo_sort_or_cycle(nodes: Iterable[str], edges: Sequence[Tuple[str, str]]) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    """Kahn 拓扑排序；若有环，返回一个用于定位的环路径（尽力）。"""
    nodes = list(nodes)
    out_adj: Dict[str, List[str]] = {n: [] for n in nodes}
    indeg: Dict[str, int] = {n: 0 for n in nodes}
    for u, v in edges:
        out_adj.setdefault(u, []).append(v)
        indeg.setdefault(v, 0)
        indeg.setdefault(u, 0)
        indeg[v] += 1

    q = [n for n in indeg.keys() if indeg[n] == 0]
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

    if len(order) == len(indeg):
        return order, None

    # cycle exists: try to find one cycle path by DFS on remaining nodes
    remaining = {n for n, d in indeg.items() if d > 0}
    cycle = _find_cycle(out_adj, remaining)
    return None, cycle


def _find_cycle(adj: Mapping[str, List[str]], candidates: Set[str]) -> Optional[List[str]]:
    visiting: Set[str] = set()
    visited: Set[str] = set()
    parent: Dict[str, str] = {}

    def dfs(u: str) -> Optional[List[str]]:
        visiting.add(u)
        for v in adj.get(u, []):
            if v not in candidates:
                continue
            if v not in visited:
                if v in visiting:
                    # reconstruct cycle u -> ... -> v
                    cycle = [v, u]
                    cur = u
                    while cur in parent and parent[cur] != v:
                        cur = parent[cur]
                        cycle.append(cur)
                    cycle.append(v)
                    cycle.reverse()
                    return cycle
                parent[v] = u
                found = dfs(v)
                if found:
                    return found
        visiting.remove(u)
        visited.add(u)
        return None

    for n in list(candidates):
        if n in visited:
            continue
        found = dfs(n)
        if found:
            return found
    return None


def find_single_source(nodes: Iterable[str], edges: Sequence[Tuple[str, str]]) -> Optional[str]:
    indeg: Dict[str, int] = {n: 0 for n in nodes}
    for u, v in edges:
        indeg.setdefault(u, 0)
        indeg.setdefault(v, 0)
        indeg[v] += 1
    sources = [n for n, d in indeg.items() if d == 0]
    if len(sources) == 1:
        return sources[0]
    return None


def longest_path_dag(
    nodes: Iterable[str],
    edges: Sequence[Tuple[str, str]],
    node_weight_ns: Mapping[str, int],
    *,
    source: Optional[str] = None,
) -> LongestPathResult:
    nodes_set = set(nodes)
    weights: Dict[str, int] = {n: int(node_weight_ns.get(n, 0) or 0) for n in nodes_set}
    missing = sorted([n for n in nodes_set if n not in node_weight_ns])

    order, cycle = topo_sort_or_cycle(nodes_set, edges)
    if cycle:
        detail = " -> ".join(cycle[:12] + (["..."] if len(cycle) > 12 else []))
        raise RuntimeError(
            "图中存在有向环，无法在含环图上计算最长路径（Longest Path 仅对 DAG 有定义）。"
            f"\n环示例: {detail}"
        )
    assert order is not None

    # build predecessors for DP
    pred: Dict[str, List[str]] = {n: [] for n in nodes_set}
    for u, v in edges:
        if u in nodes_set and v in nodes_set:
            pred[v].append(u)

    neg_inf = -(1 << 60)
    dist: Dict[str, int] = {n: neg_inf for n in nodes_set}
    prev: Dict[str, Optional[str]] = {n: None for n in nodes_set}

    if source:
        dist[source] = weights.get(source, 0)
    else:
        # global: allow starting anywhere
        for n in nodes_set:
            dist[n] = weights.get(n, 0)

    for v in order:
        base = weights.get(v, 0)
        # choose best predecessor
        best_u = None
        best_val = dist[v]
        for u in pred.get(v, []):
            cand = dist.get(u, neg_inf) + base
            if cand > best_val:
                best_val = cand
                best_u = u
        dist[v] = best_val
        if best_u is not None:
            prev[v] = best_u

    end = max(order, key=lambda n: dist.get(n, neg_inf))
    total = dist.get(end, 0)
    path: List[str] = []
    cur: Optional[str] = end
    seen: Set[str] = set()
    while cur is not None and cur not in seen:
        seen.add(cur)
        path.append(cur)
        cur = prev.get(cur)
    path.reverse()

    return LongestPathResult(
        path=path,
        total_weight_ns=int(total if total != neg_inf else 0),
        missing_weight_nodes=missing,
        node_weight_ns={k: int(v) for k, v in weights.items()},
    )


def build_weighted_highlighted_dot(
    nodes: Iterable[str],
    edges: Sequence[Tuple[str, str]],
    weights_ns: Mapping[str, int],
    longest_path: Sequence[str],
    *,
    title: str = "Weighted DAG (total_ns)",
) -> str:
    nodes_set = set(nodes)
    path_set = set(longest_path)
    path_edges = set(zip(longest_path, longest_path[1:]))

    lines: List[str] = []
    lines.append("digraph WeightedCallgraph {")
    lines.append('  graph [rankdir=LR, labelloc="t", fontsize=18, label="%s"];' % _escape(title))
    lines.append('  node [shape=box, style="rounded,filled", fontname="Consolas", fontsize=10, fillcolor="#F6F6F6"];')
    lines.append('  edge [color="#666666", penwidth=1.2];')

    for n in sorted(nodes_set):
        w = int(weights_ns.get(n, 0) or 0)
        label = f"{n}\\n{w:,} ns"
        attrs = []
        attrs.append(f'label="{_escape(label)}"')
        if n in path_set:
            attrs.append('fillcolor="#FFE082"')
            attrs.append('color="#D84315"')
            attrs.append('penwidth=2.2')
        lines.append(f'  "{_escape(n)}" [{", ".join(attrs)}];')

    for u, v in edges:
        if u not in nodes_set or v not in nodes_set:
            continue
        attrs = []
        if (u, v) in path_edges:
            attrs.append('color="#D32F2F"')
            attrs.append("penwidth=3.2")
        lines.append(f'  "{_escape(u)}" -> "{_escape(v)}"{(" [" + ", ".join(attrs) + "]") if attrs else ""};')

    lines.append("}")
    return "\n".join(lines)


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def write_longest_path_json(
    output_path: Path,
    *,
    dot_path: Path,
    time_json_path: Path,
    result: LongestPathResult,
) -> None:
    payload = {
        "dot": str(dot_path),
        "time_result": str(time_json_path),
        "total_weight_ns": result.total_weight_ns,
        "path": result.path,
        "missing_weight_nodes_count": len(result.missing_weight_nodes),
        "missing_weight_nodes_sample": result.missing_weight_nodes[:50],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


# ===================== CPC 调度（节点级优先级分配） =====================

@dataclass(frozen=True)
class CpcResult:
    priorities: Dict[str, int]
    providers: List[List[str]]
    longest_path: List[str]
    node_weight_ns: Dict[str, int]
    m: int


def compute_cpc_priorities(
    nodes: Iterable[str],
    edges: Sequence[Tuple[str, str]],
    node_weight_ns: Mapping[str, int],
    longest_path: Sequence[str],
    *,
    m: int = 2,
) -> CpcResult:
    """按 CPC 框架分配节点优先级（简化：关键路径合并为 provider 段）。

    - 输入：节点集合、边、节点权重（缺省置 0）、最长路径节点序列。
    - 处理：
        1) 将最长路径切段：若相邻关键节点的唯一前驱就是前一节点，则归入同一 provider；
           否则开启新段。
        2) 先按 provider 段顺序分配最高优先级（段内从前到后递减）。
        3) 剩余节点：在未分配子图中反复提取“局部最长链”并分配递减优先级
           （若存在环则抛出异常）。
    - 返回：每个节点的优先级、provider 划分、权重、m。
    """
    nodes_set = set(nodes)
    weights: Dict[str, int] = {n: int(node_weight_ns.get(n, 0) or 0) for n in nodes_set}

    order, cycle = topo_sort_or_cycle(nodes_set, edges)
    if cycle:
        detail = " -> ".join(cycle[:12] + (["..."] if len(cycle) > 12 else []))
        raise RuntimeError(f"CPC 失败：图中存在环，无法在含环图上分配优先级。\n环示例: {detail}")
    assert order is not None

    pred: Dict[str, List[str]] = {n: [] for n in nodes_set}
    succ: Dict[str, List[str]] = {n: [] for n in nodes_set}
    for u, v in edges:
        if u in nodes_set and v in nodes_set:
            succ[u].append(v)
            pred[v].append(u)

    # 1) provider 划分
    providers: List[List[str]] = []
    current: List[str] = []
    for idx, n in enumerate(longest_path):
        if n not in nodes_set:
            continue
        if not current:
            current = [n]
            continue
        prev = longest_path[idx - 1]
        if prev in nodes_set and pred.get(n, []) == [prev]:
            current.append(n)
        else:
            providers.append(current)
            current = [n]
    if current:
        providers.append(current)

    priorities: Dict[str, int] = {}
    next_prio = len(nodes_set) * 2  # 留足空间

    # 2) provider 段优先级：沿路径递减
    for segment in providers:
        for n in segment:
            if n not in nodes_set:
                continue
            priorities[n] = next_prio
            next_prio -= 1

    # 3) 余下节点：在未分配子图上反复取局部最长链
    unassigned: Set[str] = {n for n in nodes_set if n not in priorities}

    def longest_chain_in_subgraph(candidates: Set[str]) -> List[str]:
        """在 candidates 子图中找到一条“终点最长”的链（基于权重累加）。"""
        if not candidates:
            return []
        # 子图拓扑顺序
        sub_edges = [(u, v) for u, v in edges if u in candidates and v in candidates]
        sub_order, sub_cycle = topo_sort_or_cycle(candidates, sub_edges)
        if sub_cycle:
            detail = " -> ".join(sub_cycle[:12] + (["..."] if len(sub_cycle) > 12 else []))
            raise RuntimeError(f"CPC 子图含环，无法继续分配优先级。\n环示例: {detail}")
        assert sub_order is not None

        sub_pred: Dict[str, List[str]] = {n: [] for n in candidates}
        for u, v in sub_edges:
            sub_pred[v].append(u)

        neg_inf = -(1 << 60)
        dist: Dict[str, int] = {n: neg_inf for n in candidates}
        prev: Dict[str, Optional[str]] = {n: None for n in candidates}
        sinks = {n for n in candidates if all(s not in candidates for s in succ.get(n, []))}

        for n in sub_order:
            base = weights.get(n, 0)
            best = base
            best_u = None
            for u in sub_pred.get(n, []):
                cand = dist.get(u, neg_inf) + base
                if cand > best:
                    best = cand
                    best_u = u
            dist[n] = best
            if best_u is not None:
                prev[n] = best_u

        # 选择 dist 最大且是“子图内终点”的节点
        end = max(sinks if sinks else candidates, key=lambda n: dist.get(n, neg_inf))
        chain: List[str] = []
        seen: Set[str] = set()
        cur: Optional[str] = end
        while cur is not None and cur not in seen:
            seen.add(cur)
            chain.append(cur)
            cur = prev.get(cur)
        chain.reverse()
        return chain

    while unassigned:
        chain = longest_chain_in_subgraph(unassigned)
        if not chain:
            break
        for n in chain:
            priorities[n] = next_prio
            next_prio -= 1
        unassigned.difference_update(chain)

    # 对极端情况（空链未覆盖）兜底
    for n in list(unassigned):
        priorities[n] = next_prio
        next_prio -= 1

    return CpcResult(
        priorities=priorities,
        providers=providers,
        longest_path=[n for n in longest_path if n in nodes_set],
        node_weight_ns=weights,
        m=m,
    )


def apply_priorities_to_dot(
    dot_text: str,
    *,
    priorities: Mapping[str, int],
    node_weight_ns: Mapping[str, int],
    longest_path: Sequence[str],
) -> str:
    """在原 DOT 上追加优先级/权重提示，高亮最长路径。

    - 对所有节点追加 xlabel=prio，tooltip=total_ns。
    - λ* 节点填充高亮，λ* 边高亮。
    """
    path_nodes = set(longest_path)
    path_edges = set(zip(longest_path, longest_path[1:]))
    lines = dot_text.splitlines(keepends=False)
    out: List[str] = []
    seen_node_stmt: Set[str] = set()

    for line in lines:
        edge_m = _EDGE_STMT_RE.match(line)
        if edge_m:
            src = edge_m.group("src")
            dst = edge_m.group("dst")
            attrs = edge_m.group("attrs")
            if (src, dst) in path_edges:
                merged = _merge_attrs(
                    attrs,
                    {
                        "color": "#D32F2F",
                        "penwidth": "3.0",
                    },
                )
                out.append(f'{edge_m.group("indent")}"{src}" -> "{dst}" {merged};'.rstrip())
            else:
                out.append(line)
            continue

        node_m = _NODE_STMT_RE.match(line)
        if node_m:
            name = node_m.group("name")
            attrs = node_m.group("attrs")
            seen_node_stmt.add(name)
            base_attrs = _parse_attrs(attrs)
            base_attrs["label"] = _append_prio_to_label(name, base_attrs.get("label"), priorities.get(name, 0))
            base_attrs["tooltip"] = f"{int(node_weight_ns.get(name, 0) or 0)} ns"
            if name in path_nodes:
                base_attrs.update(
                    {
                        "style": "filled",
                        "fillcolor": "#FFE082",
                        "color": "#D84315",
                        "penwidth": "2.2",
                    }
                )
            merged = "[" + ", ".join(_format_attr(k, v) for k, v in base_attrs.items()) + "]"
            out.append(f'{node_m.group("indent")}"{name}" {merged};')
            continue

        out.append(line)

    # 补充未显式声明的节点
    missing = [n for n in priorities.keys() if n not in seen_node_stmt]
    if missing:
        patch: List[str] = ["", "  // === CPC priority patch (auto-generated) ==="]
        for n in missing:
            attrs = {
                "label": _append_prio_to_label(n, None, priorities.get(n, 0)),
                "tooltip": f"{int(node_weight_ns.get(n, 0) or 0)} ns",
            }
            if n in path_nodes:
                attrs.update(
                    {
                        "style": "filled",
                        "fillcolor": "#FFE082",
                        "color": "#D84315",
                        "penwidth": "2.2",
                    }
                )
            merged = _merge_attrs(None, attrs)
            patch.append(f'  "{n}" {merged};')

        inserted = False
        for i in range(len(out) - 1, -1, -1):
            if out[i].strip() == "}":
                out[i:i] = patch
                inserted = True
                break
        if not inserted:
            out.extend(patch)

    return "\n".join(out) + ("\n" if dot_text.endswith("\n") else "")


def write_cpc_schedule_json(
    output_path: Path,
    *,
    dot_path: Path,
    time_json_path: Path,
    longest_json_path: Path,
    result: CpcResult,
) -> None:
    payload = {
        "dot": str(dot_path),
        "time_result": str(time_json_path),
        "longest_path_json": str(longest_json_path),
        "m": result.m,
        "providers": result.providers,
        "priorities": result.priorities,
        "longest_path": result.longest_path,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def highlight_dot_inplace(
    dot_text: str,
    *,
    path_nodes: Sequence[str],
    path_edges: Sequence[Tuple[str, str]],
    node_weight_ns: Mapping[str, int],
) -> str:
    """在原 DOT 文本上增量高亮最长路径（保留原 DOT 的结构与样式）。

    - 对最长路径上的边追加/合并高亮属性（红色加粗）。
    - 对最长路径上的节点追加/合并高亮属性（填充色/边框色/线宽），并添加 tooltip=total_ns。
    - 若某些节点在原 DOT 中没有显式 node 语句，则在结尾 '}' 前补一段 node 定义补丁。
    """
    path_node_set = set(path_nodes)
    path_edge_set = set(path_edges)

    lines = dot_text.splitlines(keepends=False)
    out: List[str] = []

    # Track which nodes are explicitly mentioned as node statements
    seen_node_stmt: Set[str] = set()

    for line in lines:
        edge_m = _EDGE_STMT_RE.match(line)
        if edge_m:
            src = edge_m.group("src")
            dst = edge_m.group("dst")
            attrs = edge_m.group("attrs")
            if (src, dst) in path_edge_set:
                merged = _merge_attrs(
                    attrs,
                    {
                        "color": "#D32F2F",
                        "penwidth": "3.2",
                    },
                )
                out.append(f'{edge_m.group("indent")}"{src}" -> "{dst}" {merged};'.rstrip())
            else:
                out.append(line)
            continue

        node_m = _NODE_STMT_RE.match(line)
        if node_m:
            name = node_m.group("name")
            attrs = node_m.group("attrs")
            if name in path_node_set:
                seen_node_stmt.add(name)
                w = int(node_weight_ns.get(name, 0) or 0)
                merged = _merge_attrs(
                    attrs,
                    {
                        "style": "filled",
                        "fillcolor": "#FFE082",
                        "color": "#D84315",
                        "penwidth": "2.2",
                        "tooltip": f"{w} ns",
                    },
                )
                out.append(f'{node_m.group("indent")}"{name}" {merged};'.rstrip())
            else:
                # still count as explicitly declared node (avoid duplicate patch)
                seen_node_stmt.add(name)
                out.append(line)
            continue

        out.append(line)

    # Append missing highlighted node statements before closing brace if possible
    missing = [n for n in path_nodes if n not in seen_node_stmt]
    if missing:
        patch_lines: List[str] = []
        patch_lines.append("")
        patch_lines.append("  // === Longest path highlight patch (auto-generated) ===")
        for n in missing:
            w = int(node_weight_ns.get(n, 0) or 0)
            merged = _merge_attrs(
                None,
                {
                    "style": "filled",
                    "fillcolor": "#FFE082",
                    "color": "#D84315",
                    "penwidth": "2.2",
                    "tooltip": f"{w} ns",
                },
            )
            patch_lines.append(f'  "{n}" {merged};')

        # insert before last '}' line
        inserted = False
        for i in range(len(out) - 1, -1, -1):
            if out[i].strip() == "}":
                out[i:i] = patch_lines
                inserted = True
                break
        if not inserted:
            out.extend(patch_lines)

    return "\n".join(out) + ("\n" if dot_text.endswith("\n") else "")


def _merge_attrs(existing: Optional[str], updates: Mapping[str, str]) -> str:
    """合并 Graphviz 属性块，返回形如 [a=b, c="d"] 的字符串。"""
    attrs = _parse_attrs(existing)
    attrs.update(updates)
    return "[" + ", ".join(_format_attr(k, v) for k, v in attrs.items()) + "]"


def _parse_attrs(attr_block: Optional[str]) -> Dict[str, str]:
    if not attr_block:
        return {}
    s = attr_block.strip()
    if s.startswith("[") and s.endswith("]"):
        s = s[1:-1]
    s = s.strip()
    if not s:
        return {}

    parts = _split_commas(s)
    out: Dict[str, str] = {}
    for p in parts:
        if not p.strip():
            continue
        if "=" not in p:
            # bareword attr (rare) -> keep as-is using empty key skip
            continue
        k, v = p.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"')
        if k:
            out[k] = v
    return out


def _split_commas(s: str) -> List[str]:
    parts: List[str] = []
    buf: List[str] = []
    in_quote = False
    esc = False
    for ch in s:
        if esc:
            buf.append(ch)
            esc = False
            continue
        if ch == "\\":
            buf.append(ch)
            esc = True
            continue
        if ch == '"':
            buf.append(ch)
            in_quote = not in_quote
            continue
        if ch == "," and not in_quote:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(ch)
    if buf:
        parts.append("".join(buf).strip())
    return parts


def _format_attr(key: str, val: str) -> str:
    # numbers and simple identifiers can be unquoted, but quoting is safe
    if key in ("penwidth",):
        return f"{key}={val}"
    if re.fullmatch(r"[A-Za-z0-9_./:+-]+", val) and not val.startswith("#"):
        return f'{key}="{val}"'
    # keep colors like #RRGGBB quoted
    return f'{key}="{val}"'


def _append_prio_to_label(name: str, existing_label: Optional[str], prio: int) -> str:
    """在已有 label 后追加 prio 行，若无 label 则用 name 起始。"""
    if not existing_label:
        base = name
    else:
        base = existing_label.strip('"')
    return f"{base}\\nprio={prio}"
