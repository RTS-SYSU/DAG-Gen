from __future__ import annotations

from pathlib import Path
from typing import Dict

from ...level1.segment_dag import _render_seg_dag_dot, build_stage1_segments_and_dag

from .base import RuleOutput
from .utils import normalize_dag, normalize_segments


class Level1Stage1Rule:
    def rule_id(self) -> str:
        return "stage1_create_join"

    def level(self) -> str:
        return "level1"

    def build(self, *, base_dir: Path, base_name: str, source_file: Path, block_info: Dict) -> RuleOutput:
        _ = source_file
        _ = block_info
        seg_json_raw, dag_json_raw = build_stage1_segments_and_dag(base_dir=base_dir, base_name=base_name)

        seg_struct, ext_struct = normalize_segments(
            base_name=base_name,
            level=self.level(),
            rule_name=self.rule_id(),
            view="struct",
            segments_in=seg_json_raw.get("segments", []),
        )
        dag_struct = normalize_dag(
            base_name=base_name,
            nodes_in=dag_json_raw.get("nodes", []),
            edges_in=dag_json_raw.get("edges", []),
        )

        # Stage1 has no struct/sched distinction yet, keep identical outputs.
        seg_sched = dict(seg_struct)
        seg_sched["view"] = "sched"
        dag_sched = dict(dag_struct)

        meta = {
            "rule_name": self.rule_id(),
            "level": self.level(),
            "kind_extensions": sorted(set(ext_struct)),
            "notes": "Stage1 create/join segmentation reused as both struct and sched views.",
        }
        return RuleOutput(seg_struct, dag_struct, seg_sched, dag_sched, meta)

    @staticmethod
    def to_dot(segments_json: Dict, dag_json: Dict) -> str:
        _ = segments_json
        return _render_seg_dag_dot(dag_json)
