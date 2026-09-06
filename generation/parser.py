from __future__ import annotations

"""Simplified parser for the modernized interface.

The GUI still runs ``python -m mycallyplus.generation.legacy`` in a subprocess
to generate DOT output with numbering and thread patch edges. This parser keeps
only the minimal call/symbol_ref extraction logic needed by tools and tests.
"""

import fileinput
import re
from typing import Iterable, Optional

from .model import CallGraph


class Parser:
    """minimal RTL parser：extract functions、call、symbol references。"""

    def __init__(self, no_warnings: bool = False, debug_log=None) -> None:
        self._no_warnings = no_warnings
        self._debug_log = debug_log

        # Function-header and call/symbol-reference patterns matching legacy behavior.
        self._function_re = re.compile(r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)(,.*)?\).*$")
        self._call_re = re.compile(r'^.*\(call.*"(?P<target>.*)".*$')
        self._symbol_ref_re = re.compile(r'^.*\(symbol_ref.*"(?P<target>.*)".*$')

    def parse_files(self, files: Iterable[str]) -> CallGraph:
        graph = CallGraph()
        current_function: Optional[str] = None

        for line in fileinput.input(files):
            # Parse the function header.
            header = self._function_re.match(line)
            if header is not None:
                current_function = header.group("function")
                fn = graph.ensure_function(current_function)
                fn.files.add(fileinput.filename())
                continue

            if current_function is None:
                continue

            # match calls
            call_match = self._call_re.match(line)
            if call_match is not None:
                target = call_match.group("target")
                fn = graph.functions[current_function]
                fn.calls.setdefault(target, True)
                fn.call_sequence.append(target)
                continue

            # Match symbol references.
            symbol_match = self._symbol_ref_re.match(line)
            if symbol_match is not None:
                target = symbol_match.group("target")
                graph.functions[current_function].refs.setdefault(target, True)

        return graph
