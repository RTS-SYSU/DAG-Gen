from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Set

from level1.instrument_prio_level1 import instrument_prio_program_timing_and_segment_priorities

from .errors import StageError
from .instrument_levelx import instrument_prio_all_segments_by_start_line
from .io_utils import mark_failed, mark_running, mark_success, read_json, write_json
from .schedule_render import build_const_binding, render_annotated_schedule_dag, render_annotated_schedule_dag_value


def _render_dot(dot_text: str, dot_path: Path, png_path: Path) -> None:
    dot_path.parent.mkdir(parents=True, exist_ok=True)
    dot_path.write_text(dot_text, encoding="utf-8")
    try:
        subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True, capture_output=True)
    except Exception:
        # Keep dot output even when graphviz is unavailable.
        pass


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
    instrument_root = pipeline_root / "instrument" / level / rule_name

    # v3.0: 新目录结构 result/ + timing/
    result_root = instrument_root / "result"
    timing_root = instrument_root / "timing"

    # v3.0: 清理旧结构（旧算法子目录如 cpf/heft/... 直接在 instrument_root 下）
    _KNOWN_ALGOS = {"cpf", "heft", "lpf", "t_level", "wcet_first", "zhao2020"}
    if instrument_root.exists():
        for old_dir in instrument_root.iterdir():
            if old_dir.is_dir() and old_dir.name in _KNOWN_ALGOS:
                shutil.rmtree(old_dir, ignore_errors=True)

    # 状态跟踪用 instrument_root 下的 status 文件
    meta_path = instrument_root / "instrument_status.json"
    mark_running(meta_path, step="instrument", extra={"algo_name": algo_name})

    try:
        block_info = read_json(pipeline_root / "block_info.json")
        source_file = Path(str(block_info["source_file"])).resolve()
        dag_json_path = pipeline_root / "blocks" / level / rule_name / "dag_seg.json"
        segments_json_path = pipeline_root / "blocks" / level / rule_name / "segments.json"
        timing_json_path = pipeline_root / "timing" / level / rule_name / "timing.json"
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

        # 读取源文件内容
        source_text = source_file.read_text(encoding="utf-8", errors="replace")

        # --- 生成算法插桩文件（写入临时变量，后面统一输出到 result/timing） ---
        import tempfile
        tmp_instrumented = Path(tempfile.mktemp(suffix=".c"))
        tmp_instrumented.write_text(source_text, encoding="utf-8")

        mode = (instrument_mode or "auto").strip().lower()
        if mode not in {"auto", "specialized", "generic"}:
            raise StageError(f"invalid instrument_mode: {instrument_mode}")

        use_specialized = (mode == "specialized") or (mode == "auto" and level == "level1")

        if use_specialized:
            warnings = instrument_prio_program_timing_and_segment_priorities(
                tmp_instrumented,
                segments_json=segments_json_path,
                priorities=priorities,
                out_c=tmp_instrumented,
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
                tmp_instrumented,
                segments_json=segments_json_path,
                priorities=priorities,
                out_c=tmp_instrumented,
            )

            if not dag_json_path.exists():
                raise StageError(f"missing dag file: {dag_json_path}")
            if not timing_json_path.exists():
                raise StageError(f"missing timing file: {timing_json_path}")

            dag_json = read_json(dag_json_path)
            timing_json = read_json(timing_json_path)
            const_binding = build_const_binding(
                dag_json=dag_json,
                segments_json=seg_json,
                source_text=source_text,
            )
            annotated_dot = render_annotated_schedule_dag(
                dag_json=dag_json,
                segments_json=seg_json,
                timing_json=timing_json,
                schedule_json=schedule_json,
                const_binding=const_binding,
            )
            validation_root = pipeline_root / "validation" / level / rule_name / algo_name
            _render_dot(
                annotated_dot,
                validation_root / "dag_seg_annotated.dot",
                validation_root / "dag_seg_annotated.png",
            )
            write_json(validation_root / "const_binding.json", const_binding)

            value_dot = render_annotated_schedule_dag_value(
                dag_json=dag_json,
                segments_json=seg_json,
                timing_json=timing_json,
                schedule_json=schedule_json,
                source_text=source_text,
            )
            _render_dot(
                value_dot,
                validation_root / "dag_seg_annotated_value.dot",
                validation_root / "dag_seg_annotated_value.png",
            )

        instrumented_text = tmp_instrumented.read_text(encoding="utf-8", errors="replace")
        try:
            tmp_instrumented.unlink()
        except OSError:
            pass

        # === v3.0: 输出到 result/ 和 timing/ 目录 ===

        # --- result/ 目录：插桩结果（不含测时代码） ---
        # 算法插桩版本
        algo_result_dir = result_root / algo_name
        algo_result_dir.mkdir(parents=True, exist_ok=True)
        (algo_result_dir / f"{algo_name}.c").write_text(instrumented_text, encoding="utf-8")

        # CFS 对照组（纯源文件）
        cfs_result_dir = result_root / "CFS"
        cfs_result_dir.mkdir(parents=True, exist_ok=True)
        (cfs_result_dir / "CFS.c").write_text(source_text, encoding="utf-8")

        # FIFO 对照组（源文件 + FIFO 优先级）
        fifo_result_dir = result_root / "FIFO"
        fifo_result_dir.mkdir(parents=True, exist_ok=True)
        fifo_text = _add_fifo_priority(source_text)
        (fifo_result_dir / "FIFO.c").write_text(fifo_text, encoding="utf-8")

        # --- timing/ 目录：测时版本（在 result 基础上加 main 首尾测时） ---
        # 算法测时版本
        algo_timing_dir = timing_root / algo_name
        algo_timing_dir.mkdir(parents=True, exist_ok=True)
        (algo_timing_dir / f"{algo_name}.c").write_text(
            _inject_main_timing_text(instrumented_text), encoding="utf-8"
        )

        # CFS 测时版本
        cfs_timing_dir = timing_root / "CFS"
        cfs_timing_dir.mkdir(parents=True, exist_ok=True)
        (cfs_timing_dir / "CFS.c").write_text(
            _inject_main_timing_text(source_text), encoding="utf-8"
        )

        # FIFO 测时版本（一次性处理 FIFO + 测时，避免嵌套 { 问题）
        fifo_timing_dir = timing_root / "FIFO"
        fifo_timing_dir.mkdir(parents=True, exist_ok=True)
        (fifo_timing_dir / "FIFO.c").write_text(
            _inject_main_timing_text(fifo_text), encoding="utf-8"
        )

        payload = {
            "status": "success",
            "base_name": base_name,
            "level": level,
            "rule_name": rule_name,
            "view": "single",
            "algo_name": algo_name,
            "instrument_mode": mode,
            "priority_count": len(priorities),
            "warnings": warnings,
            "result_dir": str(result_root),
            "timing_dir": str(timing_root),
        }
        mark_success(meta_path, step="instrument", extra={"priority_count": len(priorities), "warnings_count": len(warnings)})
        return payload
    except Exception as exc:
        mark_failed(meta_path, step="instrument", error=str(exc), extra={"algo_name": algo_name})
        raise


def _add_fifo_priority(source_text: str) -> str:
    """在源文件中添加 FIFO 优先级设置（不含测时代码）"""
    content = source_text
    # 插入 prio_runtime.h
    if '#include "prio_runtime.h"' not in content:
        lines = content.splitlines(keepends=True)
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                insert_at = i + 1
                break
        lines.insert(insert_at, '#include "prio_runtime.h"\n')
        content = "".join(lines)

    # 在 main 函数体开头插入 FIFO 优先级
    if not re.search(r'l1_set_thread_prio_fifo\(99\)', content):
        # 找到 main 函数的 { 后插入
        content = re.sub(
            r'(int\s+main\s*\([^)]*\)\s*\{)',
            r'\1\n    l1_set_thread_prio_fifo(99);',
            content,
            count=1,
        )
    return content


def _inject_main_timing_text(source_text: str) -> str:
    """在源文件文本中注入 MAIN_ELAPSED_S 测时代码，返回新文本。
    
    一次性处理，避免多次插桩导致的嵌套 { 语法问题。
    """
    if "MAIN_ELAPSED_S" in source_text:
        return source_text  # 已经包含测时代码

    lines = source_text.splitlines(keepends=True)

    # 确保头文件存在
    has_time_h = any("<time.h>" in line for line in lines)
    has_stdio_h = any("<stdio.h>" in line for line in lines)
    if not has_time_h or not has_stdio_h:
        insert_at = 0
        for i, line in enumerate(lines):
            if line.strip().startswith('#'):
                insert_at = i + 1
                break
        if not has_time_h:
            lines.insert(insert_at, "#include <time.h>\n")
            insert_at += 1
        if not has_stdio_h:
            lines.insert(insert_at, "#include <stdio.h>\n")

    # 找到 main 函数并在 { 后插入开始计时
    main_found = False
    i = 0
    while i < len(lines) and not main_found:
        if "int main" in lines[i]:
            for j in range(i, min(i + 10, len(lines))):
                if "{" in lines[j]:
                    insert_pos = j + 1
                    lines.insert(insert_pos, "    struct timespec ts_main_begin, ts_main_end;\n")
                    lines.insert(insert_pos + 1, "    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);\n")
                    main_found = True
                    break
            i = j + 1 if main_found else i + 1
        else:
            i += 1

    # 在 return 0; 之前插入结束计时
    for i, line in enumerate(lines):
        if "return 0;" in line:
            lines.insert(i, "    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);\n")
            lines.insert(i + 1, "    {\n")
            lines.insert(i + 2, '        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)\n')
            lines.insert(i + 3, '            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;\n')
            lines.insert(i + 4, '        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\\n", main_s);\n')
            lines.insert(i + 5, "    }\n")
            break

    return "".join(lines)
