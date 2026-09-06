from __future__ import annotations

import json
import shutil
import subprocess
import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from ..level1.time_analysis_level1 import Segment, instrument_source

from .constants import SCHEMA_VERSION
from .errors import StageError
from .io_utils import mark_failed, mark_running, mark_success, read_json, write_json
from .timing_config import normalize_timing_repeats


def _load_segments(segments_json_path: Path) -> List[Segment]:
    data = read_json(segments_json_path)
    out: List[Segment] = []
    for item in data.get("segments", []):
        if not isinstance(item, dict):
            continue
        try:
            out.append(
                Segment(
                    seg_id=str(item["seg_id"]),
                    function=str(item["function"]),
                    kind=str(item["kind"]),
                    start_line=int(item["start_line"]),
                    end_line=int(item["end_line"]),
                )
            )
        except Exception:
            continue
    return out


def _active_seg_ids(dag_json_path: Path) -> Set[str]:
    data = read_json(dag_json_path)
    ids: Set[str] = set()
    for edge in data.get("edges", []):
        if not isinstance(edge, dict):
            continue
        src = edge.get("src")
        dst = edge.get("dst")
        if isinstance(src, str):
            ids.add(src)
        if isinstance(dst, str):
            ids.add(dst)
    return ids


def _compile_project(project_dir: Path) -> Tuple[int, str, str]:
    sources = sorted(str(p) for p in project_dir.rglob("*.c"))
    if not sources:
        raise StageError(f"no .c files found in {project_dir}")
    cmd = [
        "gcc",
        "-O2",
        "-g",
        "-std=c11",
        "-pthread",
        "-I.",
        "-o",
        "app",
        *sources,
        "-Wl,--wrap=main",
        "-lm",
        "-ldl",
    ]
    proc = subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def _parse_program_total_ns(stderr_text: str) -> int:
    total_ns = 0
    for line in stderr_text.splitlines():
        if line.startswith("PROGRAM_TOTAL_NS="):
            try:
                total_ns = int(line.split("=", 1)[1].strip())
            except Exception:
                continue
    return total_ns


def _read_trace_csv(trace_dir: Path) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    for p in sorted(trace_dir.glob("trace.*.csv")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split(",", 4)
            if len(parts) != 5:
                continue
            seg_quoted = parts[1].strip()
            seg_id = seg_quoted[1:-1] if seg_quoted.startswith('"') and seg_quoted.endswith('"') else seg_quoted
            try:
                dur_ns = int(parts[4])
            except Exception:
                continue
            out.append((seg_id, dur_ns))
    return out


def _summarize(rows: List[Tuple[str, int]]) -> Dict[str, Dict]:
    agg: Dict[str, List[int]] = {}
    for seg_id, dur_ns in rows:
        agg.setdefault(seg_id, []).append(dur_ns)
    out: Dict[str, Dict] = {}
    for seg_id, values in agg.items():
        total = int(sum(values))
        count = int(len(values))
        out[seg_id] = {
            "total_ns": total,
            "count": count,
            "avg_ns": int(total // max(1, count)),
            "min_ns": int(min(values)),
            "max_ns": int(max(values)),
        }
    return out


def run_timing(*, base_dir: Path, base_name: str, level: str, rule_name: str, repeats: Optional[int] = None) -> Dict:
    pipeline_root = base_dir / "intermediate_results" / base_name / "pipeline"
    out_root = pipeline_root / "timing" / level / rule_name
    meta_path = out_root / "timing_meta.json"
    # Ensure a clean output dir, then mark running (avoid deleting the meta we just wrote).
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)
    mark_running(meta_path, step="timing")

    try:
        timing_repeats = normalize_timing_repeats(repeats)
        block_info = read_json(pipeline_root / "block_info.json")
        source_file = Path(str(block_info["source_file"])).resolve()
        segments_json_path = pipeline_root / "blocks" / level / rule_name / "segments.json"
        dag_json_path = pipeline_root / "blocks" / level / rule_name / "dag_seg.json"
        if not segments_json_path.exists():
            raise StageError(f"missing segments file: {segments_json_path}")
        if not dag_json_path.exists():
            raise StageError(f"missing dag file: {dag_json_path}")
        if not source_file.exists():
            raise StageError(f"missing source file: {source_file}")

        logs_dir = out_root / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        source_dir = source_file.parent
        project_dir = out_root / "project"
        shutil.copytree(source_dir, project_dir)

        # Runtime files
        (project_dir / "segtrace.h").write_text((base_dir / "level1" / "segtrace.h").read_text(encoding="utf-8"), encoding="utf-8")
        (project_dir / "segtrace.c").write_text((base_dir / "level1" / "segtrace.c").read_text(encoding="utf-8"), encoding="utf-8")
        (project_dir / "prog_timer.h").write_text((base_dir / "level1" / "prog_timer.h").read_text(encoding="utf-8"), encoding="utf-8")
        (project_dir / "prog_timer.c").write_text((base_dir / "level1" / "prog_timer.c").read_text(encoding="utf-8"), encoding="utf-8")
        (project_dir / "wrap_main.c").write_text((base_dir / "level1" / "wrap_main.c").read_text(encoding="utf-8"), encoding="utf-8")

        segments = _load_segments(segments_json_path)
        active = _active_seg_ids(dag_json_path)
        if active:
            segments = [s for s in segments if s.seg_id in active]
        if not segments:
            raise StageError("no active segments to time")

        target_source = project_dir / source_file.name
        if not target_source.exists():
            raise StageError(f"copied project missing source: {target_source}")
        warnings, skipped = instrument_source(target_source, segments, target_source)
        write_json(logs_dir / "instrument_report.json", {"warnings": warnings, "skipped": skipped, "segments": len(segments)})

        code, compile_stdout, compile_stderr = _compile_project(project_dir)
        (logs_dir / "compile.stdout.log").write_text(compile_stdout, encoding="utf-8")
        (logs_dir / "compile.stderr.log").write_text(compile_stderr, encoding="utf-8")
        if code != 0:
            raise StageError(f"compile failed: see {logs_dir / 'compile.stderr.log'}")

        trace_dir = project_dir / "trace"
        trace_dir.mkdir(parents=True, exist_ok=True)
        env = dict(os.environ)
        # Optional override to keep timing runs bounded for heavy benchmarks.
        # The instrumented program may respect WORK_SCALE; leaving it unset preserves original behavior.
        ws = env.get("MYCALLY_PIPELINE_WORK_SCALE")
        if ws and ws.strip():
            env["WORK_SCALE"] = ws.strip()
        rows: List[Tuple[str, int]] = []
        program_totals_ns: List[int] = []
        for run_idx in range(1, timing_repeats + 1):
            for old_trace in trace_dir.glob("trace.*.csv"):
                old_trace.unlink()
            proc = subprocess.run([str(project_dir / "app")], cwd=str(project_dir), capture_output=True, text=True, env=env)
            run_suffix = f"{run_idx:02d}"
            (logs_dir / f"run.{run_suffix}.stdout.log").write_text(proc.stdout or "", encoding="utf-8")
            (logs_dir / f"run.{run_suffix}.stderr.log").write_text(proc.stderr or "", encoding="utf-8")
            if proc.returncode != 0:
                raise StageError(f"run failed with code {proc.returncode}: see {logs_dir / f'run.{run_suffix}.stderr.log'}")
            rows.extend(_read_trace_csv(trace_dir))
            program_totals_ns.append(_parse_program_total_ns(proc.stderr or ""))

        weights = _summarize(rows)

        # Fill zero weights for pure-blocker segments (sem_wait / pthread_join
        # only) that were skipped by instrument_source and thus have no trace.
        all_seg_ids = {s.seg_id for s in segments}
        for sid in all_seg_ids:
            if sid not in weights:
                weights[sid] = {
                    "total_ns": 0, "count": 0,
                    "avg_ns": 0, "min_ns": 0, "max_ns": 0,
                }
        timing_json = {
            "schema_version": SCHEMA_VERSION,
            "base_name": base_name,
            "level": level,
            "rule_name": rule_name,
            "view": "single",
            "repeats": timing_repeats,
            "weights": weights,
        }
        write_json(out_root / "timing.json", timing_json)
        mark_success(
            meta_path,
            step="timing",
            extra={
                "program_total_ns_avg": int(sum(program_totals_ns) // max(1, len(program_totals_ns))),
                "compile_returncode": code,
                "run_returncode": 0,
                "repeats": timing_repeats,
                "weights_count": len(weights),
                "warnings_count": len(warnings),
                "skipped_count": len(skipped),
                "gcc": "gcc -O2 -g -std=c11 -pthread -Wl,--wrap=main",
            },
        )
        return timing_json
    except Exception as exc:
        mark_failed(meta_path, step="timing", error=str(exc))
        raise
