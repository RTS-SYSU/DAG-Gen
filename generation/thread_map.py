from __future__ import annotations

"""
Thread patch-edge parsing (compatible with the legacy structure).

The legacy implementation records thread-related information during parsing in
`functions[func]["myinfo"]` the dictionary:

myinfo structure (original mycally convention):
    {
        "tail": <tail node name after numbering in the current function>,
        <thread_id>: <task_function>,
        <join_node>: <thread_id>
    }

usemethod：
    1. During parsing, when `pthread_create` is encountered, it stores the mapping `thread_id -> task_function`
       into `myinfo`, and saves the task tail node into the target `task_function`
       myinfo["tail"]。
    2. When `pthread_join` is encountered, it writes `join_node -> thread_id` into `myinfo`.

This module provides two helper functions:
    - resolve_join_edges()：Resolve the `tail -> join` edge that should be added for a single join node
      edge for `legacy.full_call_graph` to call while traversing `mycalls`.
    - collect_thread_edges()：Collect all patch edges at once for future replacement of inline logic
      (currently unused, provided only for future iterations).
"""

from typing import Dict, Iterable, List, Tuple
import re
from pathlib import Path
from .source_binder import bind_from_source


def resolve_join_edges(functions: Dict[str, Dict], owner_function: str, join_node: str) -> List[Tuple[str, str]]:
    """
    Infer thread patch edges from the legacy myinfo structure.

    Parameters:
        functions: legacy function table (`dict`)
        owner_function: function name owning the current join node
        join_node: numbered join-node name for the current context

    Returns:
        A list like `[(tail_node, join_node)]`; return an empty list if parsing fails.
    """

    # Only enter pairing when the last segment of the node name is `pthread_join` or `pthread_join<digits>`
    # Example: main/pthread_join7、main/while/pthread_join6
    if not re.search(r"(^|/)pthread_join(\d+)?$", join_node):
        return []

    owner_info = functions.get(owner_function, {})
    myinfo = owner_info.get("myinfo", {})
    if not myinfo:
        return []

    thread_id = myinfo.get(join_node)
    task_function = None

    if thread_id and thread_id in myinfo:
        task_function = myinfo.get(thread_id)
    else:
        queue = myinfo.get("__create_queue__", [])
        if queue:
            # Use LIFO (a recently created thread is more likely to be joined first)
            task_function = queue.pop()
            myinfo[join_node] = thread_id or f"__queue__{task_function}"
            if thread_id is None:
                myinfo.setdefault(task_function, task_function)

    if not task_function:
        # Source binder fallback
        files = owner_info.get("files", [])
        if files:
            expand_path = Path(files[0])
            pending = myinfo.get("__source_bind_queue__")
            if pending is None:
                pending = bind_from_source(expand_path, owner_function)
                myinfo["__source_bind_queue__"] = pending
            if pending:
                task_function = pending.pop(0)
                # inject mapping for future lookups
                myinfo[join_node] = f"__src__{task_function}"
                myinfo.setdefault(f"__src__{task_function}", task_function)
            else:
                return []

    task_info = functions.get(task_function, {}).get("myinfo", {})
    tail_node = task_info.get("tail")
    if not tail_node:
        return []

    queue = myinfo.get("__create_queue__", [])
    # If the task is still in the queue, remove its last occurrence to avoid duplicate pairing
    for i in range(len(queue) - 1, -1, -1):
        if queue[i] == task_function:
            del queue[i]
            break

    return [(tail_node, join_node)]


def collect_thread_edges(functions: Dict[str, Dict]) -> List[Tuple[str, str]]:
    """
    Scan all functions and collect thread patch edges recorded in legacy myinfo.

    Currently provided only for future rendering refactors; `legacy.full_call_graph`
    still uses the inline output method.
    """

    edges: List[Tuple[str, str]] = []
    for func_name, info in functions.items():
        myinfo = info.get("myinfo", {})
        if not myinfo:
            continue
        for join_node, thread_id in myinfo.items():
            if join_node == "tail":
                continue
            # Only handle join nodes (pointing to `thread_id`); skip other mappings such as `thread_id -> task`
            if isinstance(thread_id, str) and thread_id in myinfo:
                edges.extend(resolve_join_edges(functions, func_name, join_node))
    return edges
