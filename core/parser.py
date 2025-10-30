from __future__ import annotations

"""简化版解析器（现代化接口）。

说明：GUI 已通过子进程调用 `python -m mycallypro` 使用 legacy 流水线
生成 DOT（包含编号与线程补边）。该解析器用于工具/单测中的最小
构建，保留对 call/symbol_ref 的提取逻辑，便于验证与扩展。
"""

import fileinput
import re
from typing import Iterable, Optional

from .model import CallGraph


class Parser:
    """最小化 RTL 解析：提取函数、调用、符号引用。"""

    def __init__(self, no_warnings: bool = False, debug_log=None) -> None:
        self._no_warnings = no_warnings
        self._debug_log = debug_log

        # 函数头与调用/符号引用模式（与 legacy 等价的正则写法）
        self._function_re = re.compile(r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)(,.*)?\).*$")
        self._call_re = re.compile(r'^.*\(call.*"(?P<target>.*)".*$')
        self._symbol_ref_re = re.compile(r'^.*\(symbol_ref.*"(?P<target>.*)".*$')

    def parse_files(self, files: Iterable[str]) -> CallGraph:
        graph = CallGraph()
        current_function: Optional[str] = None

        for line in fileinput.input(files):
            # 解析函数头
            header = self._function_re.match(line)
            if header is not None:
                current_function = header.group("function")
                fn = graph.ensure_function(current_function)
                fn.files.add(fileinput.filename())
                continue

            if current_function is None:
                continue

            # 匹配调用
            call_match = self._call_re.match(line)
            if call_match is not None:
                target = call_match.group("target")
                fn = graph.functions[current_function]
                fn.calls.setdefault(target, True)
                fn.call_sequence.append(target)
                continue

            # 匹配符号引用
            symbol_match = self._symbol_ref_re.match(line)
            if symbol_match is not None:
                target = symbol_match.group("target")
                graph.functions[current_function].refs.setdefault(target, True)

        return graph
