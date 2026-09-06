from __future__ import annotations

import json
from pathlib import Path
from typing import Dict

from ...level2 import merge_post_wait_dag
from ...level2 import segment_dag_level2

from .base import RuleOutput
from .utils import normalize_dag, normalize_segments


def _build_merge_post_wait(base_dir: Path, base_name: str) -> None:
    dag_path = base_dir / "intermediate_results" / base_name / "dag_generation" / "dag.dot"
    circle_path = base_dir / "intermediate_results" / base_name / "config_files" / "circle.txt"
    if not dag_path.exists() or not circle_path.exists():
        return
    nodes, edges = merge_post_wait_dag._read_dot(dag_path)  # type: ignore[attr-defined]
    sem_pairs = merge_post_wait_dag._parse_sem_pairs(circle_path)  # type: ignore[attr-defined]
    for post, wait in sem_pairs:
        if post not in nodes:
            nodes.add(post)
        if wait not in nodes:
            nodes.add(wait)
        edges.append((post, wait))
    out_dir = base_dir / "intermediate_results" / base_name / "level2" / "merge_post_wait"
    out_dir.mkdir(parents=True, exist_ok=True)
    dag_json = {"nodes": sorted(nodes), "edges": [{"src": u, "dst": v, "kind": "sem_dep"} for u, v in edges]}
    (out_dir / "dag_level2_sem.json").write_text(json.dumps(dag_json, ensure_ascii=False, indent=2), encoding="utf-8")
    dot_str = merge_post_wait_dag._to_dot(nodes, edges)  # type: ignore[attr-defined]
    (out_dir / "dag_level2_sem.dot").write_text(dot_str, encoding="utf-8")
    if circle_path.exists():
        import shutil

        shutil.copy2(circle_path, out_dir / "circle.txt")


class Level2EffectiveLineRule:
    def rule_id(self) -> str:
        return "effective_line_merge"

    def level(self) -> str:
        return "level2"

    def build(self, *, base_dir: Path, base_name: str, source_file: Path, block_info: Dict) -> RuleOutput:
        _ = block_info
        _build_merge_post_wait(base_dir, base_name)
        seg_raw, dag_raw = segment_dag_level2.build_level2_segments_and_dag(
            base_dir=base_dir, base_name=base_name, source_file=source_file
        )
        seg_struct, ext_struct = normalize_segments(
            base_name=base_name,
            level=self.level(),
            rule_name=self.rule_id(),
            view="struct",
            segments_in=seg_raw.get("segments", []),
        )
        dag_struct = normalize_dag(
            base_name=base_name,
            nodes_in=dag_raw.get("nodes", []),
            edges_in=dag_raw.get("edges", []),
        )

        seg_sched = dict(seg_struct)
        seg_sched["view"] = "sched"
        dag_sched = dict(dag_struct)

        meta = {
            "rule_name": self.rule_id(),
            "level": self.level(),
            "kind_extensions": sorted(set(ext_struct)),
            "notes": "Level2 effective-line merge rule reused as both struct and sched views.",
        }
        return RuleOutput(seg_struct, dag_struct, seg_sched, dag_sched, meta)

    @staticmethod
    def to_dot(segments_json: Dict, dag_json: Dict) -> str:
        return segment_dag_level2._to_dot(segments_json, dag_json)  # type: ignore[attr-defined]
