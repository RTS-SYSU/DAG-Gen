from __future__ import annotations

"""现代化 DOT/路径渲染（供工具与单测使用）。

说明：GUI 与 CLI 使用 legacy 生成 DOT；该渲染器用于最小快照
或其它工具链调用，与 legacy 语义对齐（exclude/no_externs 等）。
"""

import re
from typing import Dict, Iterable, List, Optional, Tuple

from .model import CallGraph, Function, RenderOptions


class DotRenderer:
    """将 `CallGraph` 渲染为 Graphviz DOT。"""

    def __init__(
        self,
        graph: CallGraph,
        options: RenderOptions,
        extra_edges: Iterable[Tuple[str, str]] = (),
    ) -> None:
        self.graph = graph
        self.options = options
        self.extra_edges = list(extra_edges)
        self._exclude_regex = re.compile(options.exclude) if options.exclude else None

    def render_full(self) -> str:
        lines: List[str] = ["strict digraph callgraph {"]
        for func in sorted(self.graph.functions):
            if self._is_excluded(func):
                continue
            current = self.graph.functions[func]
            emitted = False
            for callee in current.calls.keys():
                if self.options.no_externs and callee not in self.graph.functions:
                    continue
                if self._is_excluded(callee):
                    continue
                lines.append(f'"{func}" -> "{callee}";')
                if callee not in self.graph.functions:
                    lines.append(f'"{callee}" [style=dashed]')
                emitted = True
            if not emitted:
                lines.append(f'"{func}"')

        for src, dst in self.extra_edges:
            if self._is_excluded(src) or self._is_excluded(dst):
                continue
            if self.options.no_externs and dst not in self.graph.functions:
                continue
            lines.append(f'"{src}" -> "{dst}";')

        lines.append("}")
        return "\n".join(lines)

    def _is_excluded(self, name: str) -> bool:
        return bool(self._exclude_regex and self._exclude_regex.match(name))


def dump_path(
    path: List[str],
    functions: Dict[str, Function],
    function_name: str,
    *,
    options: RenderOptions,
    call_index: str = "calls",
    stdio_buffer: Optional[List[str]] = None,
    reverse_path: bool = False,
    __seen_in_path: Optional[Dict[str, bool]] = None,
) -> None:
    """以 ASCII 形式（兼容 legacy）输出路径快照。"""

    max_depth = options.max_depth
    exclude_regex = re.compile(options.exclude) if options.exclude else None
    no_externs = options.no_externs

    if __seen_in_path is None:
        __seen_in_path = {}

    my_seen = __seen_in_path

    if exclude_regex and exclude_regex.match(function_name):
        _dump_path_ascii(path, reverse_path, stdio_buffer, truncated=True)
        return

    if max_depth > 0 and len(path) >= max_depth:
        _dump_path_ascii(path, reverse_path, stdio_buffer, truncated=True)
        return

    if function_name in my_seen:
        if max_depth <= 0 or (len(path) + 1) <= max_depth:
            _dump_path_ascii(path + [function_name], reverse_path, stdio_buffer)
        return

    my_seen[function_name] = True

    children = 0
    for callee in getattr(functions[function_name], call_index, {}).keys():
        if callee in functions:
            children += 1
            if function_name != callee:
                dump_path(
                    path + [function_name],
                    functions,
                    callee,
                    options=options,
                    call_index=call_index,
                    stdio_buffer=stdio_buffer,
                    reverse_path=reverse_path,
                    __seen_in_path=my_seen,
                )
            else:
                _dump_path_ascii(path + [function_name, callee], reverse_path, stdio_buffer)
        elif (not exclude_regex or not exclude_regex.match(callee)) and (
            max_depth <= 0 or (len(path) + 2) <= max_depth
        ) and not no_externs:
            children += 1
            _dump_path_ascii(path + [function_name, callee], reverse_path, stdio_buffer, externs=True)
        else:
            _print_buf(stdio_buffer, f'"{function_name}" [color=red];')

    if children == 0:
        _dump_path_ascii(path + [function_name], reverse_path, stdio_buffer)


def _dump_path_ascii(
    path: List[str],
    reverse: bool,
    stdio_buffer: Optional[List[str]],
    truncated: bool = False,
    externs: bool = False,
) -> None:
    if not path:
        return
    ordered = list(reversed(path)) if reverse else path
    ascii_path = " -> ".join(f'"{item}"' for item in ordered)
    if truncated or externs:
        tail = path[-1] if not reverse else path[-1]
        ascii_path += f';\n"{tail}"'
        if externs:
            ascii_path += " [style=dashed]"
        if truncated:
            ascii_path += " [color=red]"
        ascii_path += ";"
    else:
        ascii_path += ";"
    _print_buf(stdio_buffer, ascii_path)


def _print_buf(buffer: Optional[List[str]], text: str) -> None:
    if buffer is not None:
        buffer.append(text)
    print(text)
