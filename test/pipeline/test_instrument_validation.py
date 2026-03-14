from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_PARENT = Path(__file__).resolve().parents[3]
if str(REPO_PARENT) not in sys.path:
    sys.path.insert(0, str(REPO_PARENT))

from ScratchDAG.pipeline.instrument import run_instrument


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_min_case(base_dir: Path, *, level: str, rule_name: str, algo_name: str) -> None:
    source_file = base_dir / "src.c"
    source_file.write_text("int main(void) { return 0; }\n", encoding="utf-8")

    pipeline_root = base_dir / "中间结果" / "demo" / "pipeline"
    _write_json(pipeline_root / "block_info.json", {"source_file": str(source_file)})
    _write_json(
        pipeline_root / "blocks" / level / rule_name / "segments.json",
        {
            "segments": [
                {"seg_id": "A", "function": "main", "kind": "compute", "start_line": 1, "end_line": 1},
            ]
        },
    )
    _write_json(
        pipeline_root / "blocks" / level / rule_name / "dag_seg.json",
        {
            "nodes": ["A"],
            "edges": [],
        },
    )
    _write_json(
        pipeline_root / "timing" / level / rule_name / "timing.json",
        {"weights": {"A": {"avg_ns": 123}}},
    )
    _write_json(
        pipeline_root / "schedule" / level / rule_name / algo_name / "schedule.json",
        {"priorities": {"A": 99}},
    )


class InstrumentValidationTest(unittest.TestCase):
    def test_generic_mode_generates_validation_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            _prepare_min_case(base_dir, level="level2", rule_name="effective_line_merge", algo_name="t_level")
            with patch("ScratchDAG.pipeline.instrument.instrument_prio_all_segments_by_start_line", return_value=[]):
                run_instrument(
                    base_dir=base_dir,
                    base_name="demo",
                    level="level2",
                    rule_name="effective_line_merge",
                    algo_name="t_level",
                    instrument_mode="generic",
                )

            validation_root = (
                base_dir / "中间结果" / "demo" / "pipeline" / "validation" / "level2" / "effective_line_merge" / "t_level"
            )
            self.assertTrue((validation_root / "dag_seg_annotated.dot").exists())

    def test_specialized_mode_does_not_generate_validation_graph(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp)
            _prepare_min_case(base_dir, level="level1", rule_name="stage1_create_join", algo_name="cpf")
            with patch("ScratchDAG.pipeline.instrument.instrument_prio_program_timing_and_segment_priorities", return_value=[]):
                run_instrument(
                    base_dir=base_dir,
                    base_name="demo",
                    level="level1",
                    rule_name="stage1_create_join",
                    algo_name="cpf",
                    instrument_mode="specialized",
                )

            validation_root = base_dir / "中间结果" / "demo" / "pipeline" / "validation" / "level1" / "stage1_create_join" / "cpf"
            self.assertFalse((validation_root / "dag_seg_annotated.dot").exists())
            self.assertFalse((validation_root / "dag_seg_annotated.png").exists())


if __name__ == "__main__":
    unittest.main()
