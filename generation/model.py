from __future__ import annotations

"""数据模型（现代化接口使用）

本文件提供了更清晰、可注解的数据类型，便于在工具/单测中
以较低耦合的方式构建/渲染调用图。legacy 实现仍保留原始的
dict 结构以保证兼容。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass
class Function:
    """函数节点信息（现代化）。

    - files: 该函数来源的 RTL 文件集合
    - calls: 直接调用到的被调函数集合（字典作为 set 使用）
    - refs: 直接引用到的符号集合（字典作为 set 使用）
    - call_sequence: 函数体内按出现顺序记录的调用名（便于推导尾节点）
    - callee_calls/refs: 由 builder 填充的反向索引
    - meta: 预留的额外信息
    """

    name: str
    files: Set[str] = field(default_factory=set)
    calls: Dict[str, bool] = field(default_factory=dict)
    refs: Dict[str, bool] = field(default_factory=dict)
    call_sequence: List[str] = field(default_factory=list)
    callee_calls: Dict[str, bool] = field(default_factory=dict)
    callee_refs: Dict[str, bool] = field(default_factory=dict)
    meta: Dict[str, str] = field(default_factory=dict)


@dataclass
class ThreadInfo:
    """线程信息（现代化）。

    - thread_id: 线程句柄标识（只在现代化实现中使用）
    - task_function: 线程入口函数名
    - create_site: 发生 create 的函数名
    - join_site: 发生 join 的函数名（可选）
    - tail_node: 线程任务内推断的尾节点（可选）
    """

    thread_id: str
    task_function: str
    create_site: str
    join_site: Optional[str] = None
    tail_node: Optional[str] = None


@dataclass
class CallGraph:
    """调用图（现代化）。

    - functions: 函数表
    - thread_infos/thread_edges: 线程补边相关缓存
    - thread_create_queue: 用于轻量队列兜底的辅助结构
    """

    functions: Dict[str, Function] = field(default_factory=dict)
    thread_infos: Dict[str, ThreadInfo] = field(default_factory=dict)
    thread_edges: List[Tuple[str, str]] = field(default_factory=list)
    thread_create_queue: List[str] = field(default_factory=list)

    def ensure_function(self, name: str) -> Function:
        """若不存在则创建一个空函数条目，并返回。"""
        if name not in self.functions:
            self.functions[name] = Function(name=name)
        return self.functions[name]


@dataclass
class RenderOptions:
    """渲染开关集合。与 legacy 语义保持一致。"""

    exclude: Optional[str] = None
    no_externs: bool = False
    max_depth: int = 0
    reverse_path: bool = False
