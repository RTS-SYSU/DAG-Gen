from __future__ import annotations

"""
线程补边解析（兼容 legacy 结构）。

legacy 实现会在解析过程中将线程相关信息记录在
`functions[func]["myinfo"]` 字典中：

myinfo 结构（原始 mycally 约定）：
    {
        "tail": <当前函数编号后的尾节点名>,
        <thread_id>: <task_function>,
        <join_node>: <thread_id>
    }

使用方式：
    1. 解析阶段当遇到 pthread_create 时，会将 thread_id → task_function
       的映射写入 myinfo，并把任务尾节点保存到 task_function 的
       myinfo["tail"]。
    2. 遇到 pthread_join 时，会将 join_node → thread_id 写入 myinfo。

本模块提供两个辅助函数：
    - resolve_join_edges()：单次求解某个 join 节点应补上的 “tail -> join”
      边，供 legacy.full_call_graph 在遍历 mycalls 时调用。
    - collect_thread_edges()：一次性收集所有补边，可用于后续替换 inline
      逻辑（当前未使用，仅提供给未来迭代）。
"""

from typing import Dict, Iterable, List, Tuple
import re
from pathlib import Path
from .source_binder import bind_from_source


def resolve_join_edges(functions: Dict[str, Dict], owner_function: str, join_node: str) -> List[Tuple[str, str]]:
    """
    根据 legacy myinfo 结构推导线程补边。

    参数:
        functions: legacy 函数表（dict）
        owner_function: 当前 join 节点所属的函数名
        join_node: 当前编号后的 join 节点名

    返回:
        形如 [(tail_node, join_node)] 的列表；若无法解析则返回空列表。
    """

    # 仅当节点名的最后一段为 pthread_join 或 pthread_join<数字> 时才进入配对
    # 例：main/pthread_join7、main/while/pthread_join6
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
            # 使用 LIFO（最近创建的线程更可能先被 join）
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
    # 若该任务仍在队列中，移除其最后一个出现位置，避免重复配对
    for i in range(len(queue) - 1, -1, -1):
        if queue[i] == task_function:
            del queue[i]
            break

    return [(tail_node, join_node)]


def collect_thread_edges(functions: Dict[str, Dict]) -> List[Tuple[str, str]]:
    """
    扫描所有函数，收集 legacy myinfo 中记录的线程补边。

    目前仅提供给未来的渲染重构使用；legacy.full_call_graph
    仍采用 inline 输出方式。
    """

    edges: List[Tuple[str, str]] = []
    for func_name, info in functions.items():
        myinfo = info.get("myinfo", {})
        if not myinfo:
            continue
        for join_node, thread_id in myinfo.items():
            if join_node == "tail":
                continue
            # 只处理 join 节点（指向 thread_id），其他（thread_id->task）的映射跳过
            if isinstance(thread_id, str) and thread_id in myinfo:
                edges.extend(resolve_join_edges(functions, func_name, join_node))
    return edges
