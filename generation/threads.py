from __future__ import annotations

"""线程补边（现代化接口）。

仅用于 UT 或工具链。GUI/CLI 的线程补边来自 legacy 流程。"""

from typing import List, Tuple

from .model import CallGraph, ThreadInfo


def infer_thread_edges(graph: CallGraph) -> List[Tuple[str, str]]:
    """根据现代化缓存，推导 `tail -> pthread_join` 边。"""
    if graph.thread_edges:
        return graph.thread_edges

    edges: List[Tuple[str, str]] = []
    for _, info in graph.thread_infos.items():
        task = info.task_function
        if not task:
            continue
        tail = _find_tail(graph, task)
        edges.append((tail, "pthread_join"))
    return edges


def _find_tail(graph: CallGraph, task: str) -> str:
    fn = graph.functions.get(task)
    if not fn or not fn.call_sequence:
        return task
    last_call = fn.call_sequence[-1]
    return last_call if last_call else task
