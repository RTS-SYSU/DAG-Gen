from __future__ import annotations

import unittest

from pipeline.algo import CPFBlockAlgo
from pipeline.algo import HEFTBlockAlgo
from pipeline.algo import LPFBlockAlgo
from pipeline.algo import TLevelBlockAlgo
from pipeline.algo import WCETFirstBlockAlgo
from pipeline.algo import Zhao2020BlockAlgo
from pipeline.algo_registry import list_algos
from pipeline.errors import ValidationError
from pipeline.timing_config import DEFAULT_TIMING_REPEATS, normalize_timing_repeats


def _segments_json():
    return {
        "base_name": "demo",
        "segments": [
            {"seg_id": "A", "function": "main", "kind": "compute", "start_line": 1, "end_line": 1},
            {"seg_id": "B", "function": "main", "kind": "compute", "start_line": 2, "end_line": 2},
            {"seg_id": "C", "function": "main", "kind": "compute", "start_line": 3, "end_line": 3},
            {"seg_id": "D", "function": "main", "kind": "compute", "start_line": 4, "end_line": 4},
        ],
    }


def _dag_json():
    return {
        "edges": [
            {"src": "A", "dst": "B"},
            {"src": "A", "dst": "C"},
            {"src": "B", "dst": "D"},
            {"src": "C", "dst": "D"},
        ]
    }


def _timing_json():
    return {
        "weights": {
            "A": {"avg_ns": 2, "total_ns": 20, "count": 10},
            "B": {"avg_ns": 5, "total_ns": 50, "count": 10},
            "C": {"avg_ns": 3, "total_ns": 30, "count": 10},
            "D": {"avg_ns": 4, "total_ns": 40, "count": 10},
        }
    }


class BlockAlgoTest(unittest.TestCase):
    def test_registry_contains_new_algos(self) -> None:
        algos = list_algos()
        self.assertIn("wcet_first", algos)
        self.assertIn("t_level", algos)

    def test_wcet_first_matches_doc_example(self) -> None:
        schedule = WCETFirstBlockAlgo().compute(
            dag_json=_dag_json(),
            segments_json=_segments_json(),
            timing_json=_timing_json(),
        )
        self.assertEqual(schedule["meta"]["scores"], {"A": 2, "B": 5, "C": 3, "D": 4})
        self.assertEqual(schedule["priorities"]["B"], 99)
        self.assertEqual(schedule["priorities"]["D"], 98)
        self.assertEqual(schedule["priorities"]["C"], 97)
        self.assertEqual(schedule["priorities"]["A"], 96)

    def test_t_level_matches_doc_example(self) -> None:
        schedule = TLevelBlockAlgo().compute(
            dag_json=_dag_json(),
            segments_json=_segments_json(),
            timing_json=_timing_json(),
        )
        self.assertEqual(schedule["meta"]["scores"], {"A": 0, "B": 2, "C": 2, "D": 7})
        self.assertEqual(schedule["priorities"]["D"], 99)
        self.assertEqual(schedule["priorities"]["B"], 98)
        self.assertEqual(schedule["priorities"]["C"], 97)
        self.assertEqual(schedule["priorities"]["A"], 96)

    def test_tie_break_uses_seg_id(self) -> None:
        timing_json = {"weights": {"A": {"avg_ns": 5}, "B": {"avg_ns": 5}}}
        segments_json = {
            "base_name": "tie",
            "segments": [
                {"seg_id": "A", "function": "main", "kind": "compute", "start_line": 1, "end_line": 1},
                {"seg_id": "B", "function": "main", "kind": "compute", "start_line": 2, "end_line": 2},
            ],
        }
        dag_json = {"edges": []}
        schedule = WCETFirstBlockAlgo().compute(dag_json=dag_json, segments_json=segments_json, timing_json=timing_json)
        self.assertGreater(schedule["priorities"]["A"], schedule["priorities"]["B"])

    def test_cycle_raises(self) -> None:
        dag_json = {"edges": [{"src": "A", "dst": "B"}, {"src": "B", "dst": "A"}]}
        with self.assertRaises(ValidationError):
            TLevelBlockAlgo().compute(dag_json=dag_json, segments_json=_segments_json(), timing_json=_timing_json())

    def test_missing_avg_raises(self) -> None:
        bad_timing = {"weights": {"A": {"avg_ns": 2}, "B": {"avg_ns": 5}, "C": {"avg_ns": 3}}}
        with self.assertRaises(ValidationError):
            WCETFirstBlockAlgo().compute(dag_json=_dag_json(), segments_json=_segments_json(), timing_json=bad_timing)

    def test_existing_algos_accept_avg_weights(self) -> None:
        for algo in (LPFBlockAlgo(), CPFBlockAlgo(), HEFTBlockAlgo(), Zhao2020BlockAlgo()):
            schedule = algo.compute(dag_json=_dag_json(), segments_json=_segments_json(), timing_json=_timing_json())
            self.assertEqual(set(schedule["priorities"].keys()), {"A", "B", "C", "D"})

    def test_timing_repeats_default_and_validation(self) -> None:
        self.assertEqual(DEFAULT_TIMING_REPEATS, 10)
        self.assertEqual(normalize_timing_repeats(None), 10)
        self.assertEqual(normalize_timing_repeats(3), 3)
        with self.assertRaises(Exception):
            normalize_timing_repeats(0)


if __name__ == "__main__":
    unittest.main()
