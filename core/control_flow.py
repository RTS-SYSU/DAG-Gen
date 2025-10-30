from __future__ import annotations

"""控制流上下文提取（兼容 legacy 逻辑）。

legacy 实现通过多状态机识别 if/while/switch，并在 mycalls
中添加 `if/`, `while/`, `switchK/` 等前缀。为了保持兼容，我们
在本模块中复刻该逻辑，但输出结构化结果供编号阶段使用。
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class ControlEntry:
    prefix: str


ControlMap = Dict[str, List[ControlEntry]]


def build_control_prefix_map(functions_pre: Dict[str, List[Tuple[str, str]]]) -> ControlMap:
    """将 legacy 预读结果转换为有序前缀列表。"""

    mapping: ControlMap = {}
    for func_name, entries in functions_pre.items():
        mapping[func_name] = [ControlEntry(prefix=kind) for kind, _ in entries]
    return mapping
