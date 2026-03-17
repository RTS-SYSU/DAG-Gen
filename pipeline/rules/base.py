from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Protocol


@dataclass(frozen=True)
class RuleOutput:
    struct_segments: Dict
    struct_dag: Dict
    sched_segments: Dict
    sched_dag: Dict
    meta: Dict


class RulePlugin(Protocol):
    def rule_id(self) -> str:
        ...

    def level(self) -> str:
        ...

    def build(self, *, base_dir: Path, base_name: str, source_file: Path, block_info: Dict) -> RuleOutput:
        ...

