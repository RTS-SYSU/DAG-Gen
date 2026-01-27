from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


@dataclass(frozen=True)
class Segment:
    seg_id: str
    function: str
    kind: str
    start_line: int
    end_line: int


def _load_segments(segments_json: Path) -> List[Segment]:
    data = json.loads(segments_json.read_text(encoding="utf-8"))
    segs: List[Segment] = []
    for item in data.get("segments", []):
        if not isinstance(item, dict):
            continue
        try:
            segs.append(
                Segment(
                    seg_id=str(item["seg_id"]),
                    function=str(item.get("function", "")),
                    kind=str(item.get("kind", "")),
                    start_line=int(item["start_line"]),
                    end_line=int(item["end_line"]),
                )
            )
        except Exception:
            continue
    return segs


def _active_seg_ids_from_dag_edges(dag_json: Path) -> Set[str]:
    data = json.loads(dag_json.read_text(encoding="utf-8"))
    active: Set[str] = set()
    for e in data.get("edges", []) or []:
        if not isinstance(e, dict):
            continue
        src = e.get("src")
        dst = e.get("dst")
        if isinstance(src, str) and src:
            active.add(src)
        if isinstance(dst, str) and dst:
            active.add(dst)
    return active


def _filter_segments_by_ids(segments: Iterable[Segment], active_ids: Set[str]) -> List[Segment]:
    if not active_ids:
        return list(segments)
    return [s for s in segments if s.seg_id in active_ids]


def _is_control_line(line: str) -> bool:
    s = line.strip()
    return s.startswith(("if", "for", "while", "switch"))


def instrument_source(source_c: Path, segments: List[Segment], out_c: Path) -> Tuple[List[str], List[str]]:
    """Insert SEG_BEGIN/SEG_END around each segment.

    Notes:
    - Stage1 assumes segments are not nested and boundaries are safe statement lines.
    - If a boundary line looks like a control statement line, we skip that segment and record a warning.
    - Multi-line statements are NOT handled yet (documented as TODO).
    """
    warnings: List[str] = []
    skipped: List[str] = []

    lines = source_c.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    n = len(lines)

    before: Dict[int, List[str]] = {}
    after: Dict[int, List[str]] = {}

    for seg in segments:
        if seg.start_line < 1 or seg.end_line < 1 or seg.start_line > n or seg.end_line > n:
            skipped.append(f"[skip] {seg.seg_id}: line out of range {seg.start_line}-{seg.end_line} (file lines={n})")
            continue
        if seg.start_line > seg.end_line:
            skipped.append(f"[skip] {seg.seg_id}: invalid range {seg.start_line}>{seg.end_line}")
            continue
        if _is_control_line(lines[seg.start_line - 1]) or _is_control_line(lines[seg.end_line - 1]):
            warnings.append(f"[warn] {seg.seg_id}: boundary on control statement line, skipped")
            continue

        begin_line = seg.start_line
        end_line = seg.end_line

        before.setdefault(begin_line, []).append(f'SEG_BEGIN("{seg.seg_id}");\n')

        end_text = lines[end_line - 1].strip()
        if end_text == "}" or end_text.startswith("}"):
            # Don't place SEG_END after a closing brace, which would escape function scope.
            before.setdefault(end_line, []).append(f'SEG_END("{seg.seg_id}");\n')
        else:
            after.setdefault(end_line, []).append(f'SEG_END("{seg.seg_id}");\n')

    out_lines: List[str] = []
    inserted_include = False
    # Insert include after feature-test macros like _GNU_SOURCE to avoid breaking CPU_SET, etc.
    insert_at = 0
    feature_def_re = re.compile(r"^\s*#\s*define\s+_(GNU|DEFAULT|POSIX|XOPEN|BSD|SVID)_SOURCE\b")
    for i0, ln in enumerate(lines):
        if feature_def_re.match(ln):
            insert_at = i0 + 1
            continue
        break

    for i in range(1, n + 1):
        if not inserted_include and (i - 1) == insert_at:
            out_lines.append('#include "segtrace.h"\n')
            inserted_include = True
        if i in before:
            # Deterministic order
            for t in sorted(before[i]):
                out_lines.append(t)
        out_lines.append(lines[i - 1])
        if i in after:
            for t in sorted(after[i]):
                out_lines.append(t)

    if not inserted_include:
        warnings.append("[warn] failed to insert segtrace include")

    out_c.write_text("".join(out_lines), encoding="utf-8")
    return warnings, skipped


def _compile(dest_root: Path) -> Path:
    # Compile all project sources plus segtrace runtime, but avoid accidentally
    # picking up other experiment runtimes (e.g. wrap_main/prog_timer) that
    # would break the plain build.
    exclude = {"wrap_main.c", "prog_timer.c"}
    sources = sorted(str(p) for p in dest_root.rglob("*.c") if p.name not in exclude)
    if not sources:
        raise RuntimeError("no .c files found to compile")
    cmd = ["gcc", "-O2", "-std=c11", "-pthread", "-I.", "-Iinclude", "-o", "app", *sources, "-lm", "-ldl"]
    proc = subprocess.run(cmd, cwd=str(dest_root), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"compile failed ({proc.returncode}): {proc.stderr[-400:]}")
    return dest_root / "app"


def _run(app: Path, env: Dict[str, str]) -> None:
    proc = subprocess.run([str(app)], cwd=str(app.parent), capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        raise RuntimeError(f"app failed ({proc.returncode}): {proc.stderr[-400:]}")


def _read_traces(trace_dir: Path) -> List[Tuple[str, int]]:
    """Return list of (seg_id, dur_ns)."""
    out: List[Tuple[str, int]] = []
    for p in sorted(trace_dir.glob("trace.*.csv")):
        for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
            # tid,"seg",t0,t1,dur
            parts = line.split(",", 4)
            if len(parts) != 5:
                continue
            seg_quoted = parts[1].strip()
            if seg_quoted.startswith('"') and seg_quoted.endswith('"'):
                seg_id = seg_quoted[1:-1]
            else:
                seg_id = seg_quoted
            try:
                dur = int(parts[4])
            except Exception:
                continue
            out.append((seg_id, dur))
    return out


def _summarize(durs: List[Tuple[str, int]]) -> Dict[str, Dict]:
    agg: Dict[str, List[int]] = {}
    for seg_id, dur in durs:
        agg.setdefault(seg_id, []).append(dur)
    out: Dict[str, Dict] = {}
    for seg_id, values in agg.items():
        total = sum(values)
        count = len(values)
        out[seg_id] = {
            "total_ns": int(total),
            "count": int(count),
            "avg_ns": int(total // max(1, count)),
            "min_ns": int(min(values)),
            "max_ns": int(max(values)),
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Standalone Level-1 segment time analysis (stage1).")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"), help="Project base dir (contains 中间结果/)")
    ap.add_argument("--base-name", required=True, help="Base name under 中间结果/, e.g. cpu4_thread10_fifo")
    ap.add_argument("--source", required=True, type=Path, help="Path to original .c source file")
    ap.add_argument("--project-name", default=None, help="Output project folder name (default: source stem)")
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name
    source_c = args.source.resolve()
    if source_c.suffix.lower() != ".c":
        raise SystemExit("only .c source supported")

    seg_json = base_dir / "中间结果" / base_name / "level1" / "stage1" / "segments_stage1.json"
    if not seg_json.exists():
        raise SystemExit(f"missing segments json: {seg_json}")

    dag_json = base_dir / "中间结果" / base_name / "level1" / "stage1" / "dag_stage1_seg.json"
    if not dag_json.exists():
        raise SystemExit(f"missing segment DAG json: {dag_json}")

    segments_all = _load_segments(seg_json)
    active_ids = _active_seg_ids_from_dag_edges(dag_json)
    segments = _filter_segments_by_ids(segments_all, active_ids)
    if not segments:
        raise SystemExit("no active segments found (from dag edges src/dst)")

    project_name = args.project_name or source_c.stem
    out_root = base_dir / "中间结果" / base_name / "level1" / "timing" / project_name
    if out_root.exists():
        shutil.rmtree(out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    # Copy the source directory as a "project"
    src_root = source_c.parent
    dest_project = out_root / src_root.name
    shutil.copytree(src_root, dest_project)

    # Inject runtime
    (dest_project / "segtrace.h").write_text((base_dir / "level1" / "segtrace.h").read_text(encoding="utf-8"), encoding="utf-8")
    (dest_project / "segtrace.c").write_text((base_dir / "level1" / "segtrace.c").read_text(encoding="utf-8"), encoding="utf-8")

    # Instrument main source file (by basename mapping)
    target_c = dest_project / source_c.name
    if not target_c.exists():
        raise SystemExit(f"copied project missing source: {target_c}")
    inst_c = target_c  # in-place in copied project
    warnings, skipped = instrument_source(target_c, segments, inst_c)

    # Create trace dir
    trace_dir = out_root / "trace"
    trace_dir.mkdir(parents=True, exist_ok=True)

    # Compile/run
    app = _compile(dest_project)
    env = dict(**{k: v for k, v in (list(__import__("os").environ.items()))})
    env["SEGTRACE_DIR"] = str(trace_dir)
    # segtrace uses segtrace_init only if called; we also allow overriding via env by recompiling? not now.
    # simplest: pass dir via macro init call later (TODO). For now default ./trace under dest_project.
    # We'll symlink/copy trace dir into dest_project/trace:
    proj_trace = dest_project / "trace"
    if proj_trace.exists():
        shutil.rmtree(proj_trace)
    shutil.copytree(trace_dir, proj_trace)
    _run(app, env)

    # Collect traces from dest_project/trace
    durs = _read_traces(proj_trace)
    summary = _summarize(durs)

    time_json = out_root / "time_result_seg.json"
    time_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    log = out_root / "time_analysis_level1.log"
    log.write_text(
        "\n".join(
            [
                f"[segments] {seg_json}",
                f"[dag] {dag_json}",
                f"[active_seg_ids] {len(active_ids)}",
                f"[segments_total] {len(segments_all)}",
                f"[segments_instrumented] {len(segments)}",
                f"[source] {source_c}",
                f"[project] {dest_project}",
                f"[trace_dir] {proj_trace}",
                f"[time_result] {time_json}",
            ]
            + warnings
            + skipped
        ),
        encoding="utf-8",
    )
    print(f"wrote {time_json}")
    print(f"wrote {log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
