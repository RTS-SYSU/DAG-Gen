from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

REPO_PARENT = Path(__file__).resolve().parents[3]
if str(REPO_PARENT) not in sys.path:
    sys.path.insert(0, str(REPO_PARENT))

from ScratchDAG.ui.gui import MycallyplusGUIv3


class PipelineFullRunTest(unittest.TestCase):
    def _build_gui_stub(self) -> MycallyplusGUIv3:
        gui = MycallyplusGUIv3.__new__(MycallyplusGUIv3)
        gui.state = SimpleNamespace(source_file=Path("/tmp/demo.c"), get_base_name=lambda: "demo")
        gui.pipeline_level = "-"
        gui.pipeline_rule = "-"
        gui.pipeline_algo = "-"
        gui.base_dir = Path("/tmp/scratchdag-tests")
        gui._pipeline_context = MagicMock(return_value=("demo", Path("/tmp/demo.c")))
        gui._pipeline_notice = MagicMock()
        gui._generate_expand_from_source_impl = MagicMock(return_value=Path("/tmp/demo.c.233r.expand"))
        gui._generate_dag_impl = MagicMock(return_value=Path("/tmp/dag.dot"))
        gui._pipeline_collect_run = MagicMock(return_value={"capabilities": {"has_circle_txt": True}})
        gui._pipeline_blocks_run = MagicMock(return_value=Path("/tmp/blocks"))
        gui._pipeline_timing_run = MagicMock(return_value={"weights": {"A": {"avg_ns": 1}}})
        gui._pipeline_schedule_run = MagicMock(return_value={"priorities": {"A": 99}})
        gui._pipeline_instrument_run = MagicMock(return_value={"source_instrumented": "/tmp/source_instrumented.c"})
        gui._pipeline_validation_outputs = MagicMock(
            return_value={
                "validation_dot": Path("/tmp/validation.dot"),
                "validation_png": Path("/tmp/validation.png"),
                "validation_const": Path("/tmp/const_binding.json"),
            }
        )
        gui._display_image = MagicMock()
        gui.pipeline_entry = MagicMock()
        gui._show_message = MagicMock()
        return gui

    def test_full_run_runs_all_level2_algorithms(self) -> None:
        gui = self._build_gui_stub()
        original_exists = Path.exists

        def fake_exists(path: Path) -> bool:
            if path == Path("/tmp/validation.png"):
                return True
            return original_exists(path)

        try:
            Path.exists = fake_exists  # type: ignore[assignment]
            gui.pipeline_full_run()
        finally:
            Path.exists = original_exists  # type: ignore[assignment]

        gui._generate_expand_from_source_impl.assert_called_once_with(show_message=False)
        gui._generate_dag_impl.assert_called_once_with(force_regenerate=True, show_message=False)
        gui._pipeline_collect_run.assert_called_once_with(base_name="demo", source_file=Path("/tmp/demo.c"))
        gui._pipeline_blocks_run.assert_called_once_with(
            base_name="demo",
            source_file=Path("/tmp/demo.c"),
            level="level2",
            rule_name="effective_line_merge",
        )
        gui._pipeline_timing_run.assert_called_once_with(base_name="demo", level="level2", rule_name="effective_line_merge")
        expected_algos = ["cpf", "heft", "lpf", "t_level", "wcet_first", "zhao2020"]
        self.assertEqual(gui._pipeline_schedule_run.call_count, len(expected_algos))
        self.assertEqual(gui._pipeline_instrument_run.call_count, len(expected_algos))
        self.assertEqual(gui._pipeline_validation_outputs.call_count, len(expected_algos))
        self.assertEqual(
            gui._pipeline_schedule_run.call_args_list,
            [
                unittest.mock.call(
                    base_name="demo",
                    level="level2",
                    rule_name="effective_line_merge",
                    algo_name=algo,
                )
                for algo in expected_algos
            ],
        )
        self.assertEqual(
            gui._pipeline_instrument_run.call_args_list,
            [
                unittest.mock.call(
                    base_name="demo",
                    level="level2",
                    rule_name="effective_line_merge",
                    algo_name=algo,
                    instrument_mode="generic",
                )
                for algo in expected_algos
            ],
        )
        gui._display_image.assert_called_once_with(Path("/tmp/validation.png"))
        gui.pipeline_entry.assert_called_once()
        gui._show_message.assert_not_called()

    def test_full_run_ignores_non_level2_context(self) -> None:
        gui = self._build_gui_stub()
        gui.pipeline_level = "level1"
        gui.pipeline_rule = "stage1_create_join"
        gui.pipeline_algo = "zhao2020"
        gui._pipeline_validation_outputs.return_value["validation_png"] = Path("/tmp/missing_validation.png")
        gui.pipeline_full_run()

        gui._pipeline_blocks_run.assert_called_once_with(
            base_name="demo",
            source_file=Path("/tmp/demo.c"),
            level="level2",
            rule_name="effective_line_merge",
        )
        for call in gui._pipeline_schedule_run.call_args_list:
            self.assertEqual(call.kwargs["level"], "level2")
            self.assertEqual(call.kwargs["rule_name"], "effective_line_merge")
        for call in gui._pipeline_instrument_run.call_args_list:
            self.assertEqual(call.kwargs["level"], "level2")
            self.assertEqual(call.kwargs["rule_name"], "effective_line_merge")
            self.assertEqual(call.kwargs["instrument_mode"], "generic")
        gui._display_image.assert_not_called()


if __name__ == "__main__":
    unittest.main()
