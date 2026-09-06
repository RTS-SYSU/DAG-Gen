from __future__ import annotations

from pathlib import Path
from typing import Dict

from .base import RuleOutput
from .level2_effective_line_rule import Level2EffectiveLineRule


class Level3PlaceholderRule:
    def rule_id(self) -> str:
        return "placeholder_level3"

    def level(self) -> str:
        return "level3"

    def build(self, *, base_dir: Path, base_name: str, source_file: Path, block_info: Dict) -> RuleOutput:
        # Placeholder: reuse level2 builder as initial implementation.
        base_rule = Level2EffectiveLineRule()
        out = base_rule.build(base_dir=base_dir, base_name=base_name, source_file=source_file, block_info=block_info)
        struct_segments = dict(out.struct_segments)
        struct_segments["level"] = self.level()
        struct_segments["rule_name"] = self.rule_id()
        sched_segments = dict(out.sched_segments)
        sched_segments["level"] = self.level()
        sched_segments["rule_name"] = self.rule_id()
        meta = dict(out.meta)
        meta.update(
            {
                "rule_name": self.rule_id(),
                "level": self.level(),
                "notes": "Level3 placeholder implementation (currently passthrough from level2 rule).",
            }
        )
        return RuleOutput(struct_segments, out.struct_dag, sched_segments, out.sched_dag, meta)

    @staticmethod
    def to_dot(segments_json: Dict, dag_json: Dict) -> str:
        from .level2_effective_line_rule import Level2EffectiveLineRule

        return Level2EffectiveLineRule.to_dot(segments_json, dag_json)

