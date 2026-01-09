from __future__ import annotations

"""构建反向索引（现代化接口）。"""

from typing import Dict, Iterable

from .model import CallGraph, Function


def build_callee_info(graph: CallGraph) -> None:
    """根据正向调用/引用，填充 `callee_calls/callee_refs`。"""
    for caller_name, fn in graph.functions.items():
        _populate_callee_entries(graph, caller_name, fn.calls.keys(), "callee_calls")
        _populate_callee_entries(graph, caller_name, fn.refs.keys(), "callee_refs")


def _populate_callee_entries(
    graph: CallGraph,
    caller_name: str,
    targets: Iterable[str],
    field: str,
) -> None:
    for callee_name in targets:
        if callee_name not in graph.functions:
            continue
        getattr(graph.functions[callee_name], field).setdefault(caller_name, True)


def seed_unit_test_graph() -> Dict[str, Dict[str, Dict[str, bool]]]:
    """兼容 legacy 单测快照的最小数据。"""
    functions: Dict[str, Dict[str, Dict[str, bool]]] = {}
    for name in ["main", "A", "B", "C", "D", "F", "G", "H", "I", "J"]:
        functions[name] = {
            "files": ["unit_test.c"],
            "calls": {},
            "refs": {},
            "callee_calls": {},
            "callee_refs": {},
        }
    functions["main"]["calls"]["A"] = True
    functions["A"]["calls"]["A"] = True
    functions["A"]["calls"]["B"] = True
    functions["B"]["calls"].update({"C": True, "E": True, "F": True, "G": True, "H": True})
    functions["C"]["calls"]["D"] = True
    functions["G"]["calls"]["B"] = True
    functions["H"]["calls"]["I"] = True
    functions["I"]["calls"]["J"] = True
    functions["J"]["calls"]["D"] = True
    return functions
