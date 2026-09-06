from __future__ import annotations

"""Control-flow context extraction compatible with legacy logic.

The legacy implementation uses a multi-state machine to detect if/while/switch
patterns and prefixes calls with ``if/``, ``while/``, and ``switchK/``. This
module mirrors that behavior while returning structured results for later
numbering stages.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ControlEntry:
    prefix: str


ControlMap = Dict[str, List[ControlEntry]]


def build_control_prefix_map(functions_pre: Dict[str, List[Tuple[str, str]]]) -> ControlMap:
    """Convert legacy pre-read results into ordered prefix lists."""

    mapping: ControlMap = {}
    for func_name, entries in functions_pre.items():
        mapping[func_name] = [ControlEntry(prefix=kind) for kind, _ in entries]
    return mapping
