from __future__ import annotations

from typing import Dict, Protocol


class AlgoPlugin(Protocol):
    def algo_id(self) -> str:
        ...

    def compute(self, *, dag_json: Dict, segments_json: Dict, timing_json: Dict) -> Dict:
        ...

    def validate(self, schedule_json: Dict) -> None:
        ...

