from __future__ import annotations

from pathlib import Path
from typing import Dict, Set

from mycallyplus_v1.level1.instrument_prio_level1 import instrument_prio_program_timing_and_segment_priorities

from .errors import StageError
from .instrument_levelx import instrument_prio_all_segments_by_start_line
from .io_utils import mark_failed, mark_running, mark_success, read_json, write_json


def run_instrument(
    *,
    base_dir: Path,
    base_name: str,
    level: str,
    rule_name: str,
    algo_name: str,
    instrument_mode: str = "auto",
) -> Dict:
    pipeline_root = base_dir / "中间结果" / base_name / "pipeline"
    out_root = pipeline_root / "instrument" / level / rule_name / algo_name
    meta_path = out_root / "instrument_meta.json"
    mark_running(meta_path, step="instrument", extra={"algo_name": algo_name})

    try:
        block_info = read_json(pipeline_root / "block_info.json")
        source_file = Path(str(block_info["source_file"])).resolve()
        segments_json_path = pipeline_root / "blocks" / level / rule_name / "segments.json"
        schedule_json_path = pipeline_root / "schedule" / level / rule_name / algo_name / "schedule.json"
        if not source_file.exists():
            raise StageError(f"missing source file: {source_file}")
        if not segments_json_path.exists():
            raise StageError(f"missing segments file: {segments_json_path}")
        if not schedule_json_path.exists():
            raise StageError(f"missing schedule file: {schedule_json_path}")

        schedule_json = read_json(schedule_json_path)
        priorities = schedule_json.get("priorities", {})
        if not isinstance(priorities, dict):
            raise StageError("schedule.priorities must be dict")
        priorities = {str(k): int(v) for k, v in priorities.items()}

        out_root.mkdir(parents=True, exist_ok=True)
        source_original = out_root / "source_original.c"
        source_instrumented = out_root / "source_instrumented.c"
        source_original.write_text(source_file.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
        source_instrumented.write_text(source_file.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")

        mode = (instrument_mode or "auto").strip().lower()
        if mode not in {"auto", "specialized", "generic"}:
            raise StageError(f"invalid instrument_mode: {instrument_mode}")

        use_specialized = (mode == "specialized") or (mode == "auto" and level == "level1")

        # Keep Level-1 as dedicated path by default.
        # For level2/3, generic path is default when mode=auto.
        if use_specialized:
            warnings = instrument_prio_program_timing_and_segment_priorities(
                source_instrumented,
                segments_json=segments_json_path,
                priorities=priorities,
                out_c=source_instrumented,
            )
        else:
            seg_json = read_json(segments_json_path)
            seg_ids_segments: Set[str] = set()
            for seg in seg_json.get("segments", []):
                if isinstance(seg, dict):
                    seg_id = seg.get("seg_id")
                    if isinstance(seg_id, str):
                        seg_ids_segments.add(seg_id)

            seg_ids_schedule = set(priorities.keys())
            only_in_schedule = sorted(seg_ids_schedule - seg_ids_segments)
            only_in_segments = sorted(seg_ids_segments - seg_ids_schedule)
            if only_in_schedule or only_in_segments:
                raise StageError(
                    "segments/schedule mismatch: "
                    f"only_in_schedule={len(only_in_schedule)} sample={only_in_schedule[:5]}, "
                    f"only_in_segments={len(only_in_segments)} sample={only_in_segments[:5]}"
                )

            warnings = instrument_prio_all_segments_by_start_line(
                source_instrumented,
                segments_json=segments_json_path,
                priorities=priorities,
                out_c=source_instrumented,
            )

        payload = {
            "status": "success",
            "base_name": base_name,
            "level": level,
            "rule_name": rule_name,
            "view": "single",
            "algo_name": algo_name,
            "instrument_mode": mode,
            "source_original": str(source_original),
            "source_instrumented": str(source_instrumented),
            "priority_count": len(priorities),
            "warnings": warnings,
            "external_dependencies": ["level1/prio_runtime.h"],
            "recommended_compile_cmd": "gcc -O2 -g -std=c11 -pthread source_instrumented.c -o app -lm",
        }
        write_json(meta_path, payload)
        mark_success(meta_path, step="instrument", extra={"priority_count": len(priorities), "warnings_count": len(warnings)})
        return payload
    except Exception as exc:
        mark_failed(meta_path, step="instrument", error=str(exc), extra={"algo_name": algo_name})
        raise
