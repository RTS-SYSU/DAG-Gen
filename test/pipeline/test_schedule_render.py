from __future__ import annotations

import unittest

from pipeline.errors import ValidationError
from pipeline.schedule_render import render_annotated_schedule_dag


def _sample_segments_json():
    return {
        "segments": [
            {"seg_id": "A", "function": "main", "kind": "compute", "start_line": 1, "end_line": 1},
            {"seg_id": "B", "function": "main", "kind": "compute", "start_line": 2, "end_line": 2},
        ]
    }


def _sample_dag_json():
    return {
        "nodes": ["A", "B"],
        "edges": [
            {"src": "A", "dst": "B", "kind": "intra"},
        ],
    }


def _sample_timing_json():
    return {
        "weights": {
            "A": {"avg_ns": 100},
            "B": {"avg_ns": 200},
        }
    }


def _sample_schedule_json():
    return {"priorities": {"A": 99, "B": 98}}


class ScheduleRenderTest(unittest.TestCase):
    def test_render_contains_weight_and_priority(self) -> None:
        dot = render_annotated_schedule_dag(
            dag_json=_sample_dag_json(),
            segments_json=_sample_segments_json(),
            timing_json=_sample_timing_json(),
            schedule_json=_sample_schedule_json(),
        )
        self.assertIn('digraph dag_seg_annotated {', dot)
        self.assertIn('"A" [label="A\\navg_ns=100\\nprio=99"];', dot)
        self.assertIn('"B" [label="B\\navg_ns=200\\nprio=98"];', dot)
        self.assertIn('"A" -> "B";', dot)

    def test_missing_avg_ns_raises(self) -> None:
        bad_timing = {"weights": {"A": {"avg_ns": 100}, "B": {}}}
        with self.assertRaises(ValidationError):
            render_annotated_schedule_dag(
                dag_json=_sample_dag_json(),
                segments_json=_sample_segments_json(),
                timing_json=bad_timing,
                schedule_json=_sample_schedule_json(),
            )

    def test_missing_priority_raises(self) -> None:
        bad_schedule = {"priorities": {"A": 99}}
        with self.assertRaises(ValidationError):
            render_annotated_schedule_dag(
                dag_json=_sample_dag_json(),
                segments_json=_sample_segments_json(),
                timing_json=_sample_timing_json(),
                schedule_json=bad_schedule,
            )


if __name__ == "__main__":
    unittest.main()
