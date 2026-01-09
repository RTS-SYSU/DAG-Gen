from __future__ import annotations

"""核心功能模块：解析、数据模型、控制流分析、线程分析"""

from .parser import Parser
from .model import CallGraph, Function, ThreadInfo, RenderOptions
from .control_flow import build_control_prefix_map, ControlEntry, ControlMap
from .threads import infer_thread_edges
from .thread_map import resolve_join_edges, collect_thread_edges

__all__ = [
    "Parser",
    "CallGraph",
    "Function",
    "ThreadInfo",
    "RenderOptions",
    "build_control_prefix_map",
    "ControlEntry",
    "ControlMap",
    "infer_thread_edges",
    "resolve_join_edges",
    "collect_thread_edges",
]
