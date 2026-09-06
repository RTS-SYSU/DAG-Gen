#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple


def _read_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _dot_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _resolve_node_ids(dag_json: Dict, segments_json: Dict) -> List[str]:
    seg_ids = []
    for item in segments_json.get("segments", []):
        if isinstance(item, dict) and isinstance(item.get("seg_id"), str):
            seg_ids.append(item["seg_id"])
    dag_nodes = dag_json.get("nodes")
    if isinstance(dag_nodes, list) and all(isinstance(x, str) for x in dag_nodes):
        return list(dag_nodes)
    return seg_ids


def _resolve_edges(dag_json: Dict) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for e in dag_json.get("edges", []):
        if isinstance(e, dict) and isinstance(e.get("src"), str) and isinstance(e.get("dst"), str):
            out.append((e["src"], e["dst"]))
    return out


def _build_const_binding(segments_json: Dict, node_ids: List[str], source_text: str) -> Dict[str, Dict]:
    seg_map = {}
    for item in segments_json.get("segments", []):
        if isinstance(item, dict) and isinstance(item.get("seg_id"), str):
            seg_map[item["seg_id"]] = item

    lines = source_text.splitlines()
    pattern = re.compile(r"busy_wait_seconds\s*\(\s*(C\d+)\s*\)")
    out: Dict[str, Dict] = {}

    for seg_id in node_ids:
        seg = seg_map.get(seg_id, {})
        try:
            start = int(seg.get("start_line", -1))
            end = int(seg.get("end_line", -1))
        except Exception:
            start, end = -1, -1

        matches: List[Tuple[str, int]] = []
        if start >= 1 and end >= start:
            safe_end = min(end, len(lines))
            for ln in range(start, safe_end + 1):
                for m in pattern.finditer(lines[ln - 1]):
                    matches.append((m.group(1), ln))

        uniq = sorted({name for name, _ in matches})
        if len(uniq) == 0:
            out[seg_id] = {"const_name": "NA", "line": None, "const_names": []}
        elif len(uniq) == 1:
            c = uniq[0]
            line = next(ln for name, ln in matches if name == c)
            out[seg_id] = {"const_name": c, "line": line, "const_names": [c]}
        else:
            out[seg_id] = {
                "const_name": "|".join(uniq),
                "line": min(ln for _, ln in matches),
                "const_names": uniq,
            }
    return out


def _render_dot(node_ids: List[str], edges: List[Tuple[str, str]], avg_ns: Dict[str, int], prio: Dict[str, int], const_map: Dict[str, Dict]) -> str:
    lines = [
        "digraph dag_seg_annotated_const {",
        "  rankdir=LR;",
        '  node [shape=box, style="rounded,filled", fillcolor="#F8FAFC", color="#334155", fontsize=10];',
        '  edge [color="#475569"];',
    ]
    for seg_id in node_ids:
        c = const_map.get(seg_id, {}).get("const_name", "NA")
        label = f"{seg_id}\\nconst={c}\\navg_ns={avg_ns.get(seg_id, -1)}\\nprio={prio.get(seg_id, -1)}"
        lines.append(f'  "{_dot_escape(seg_id)}" [label="{_dot_escape(label)}"];')
    for src, dst in edges:
        lines.append(f'  "{_dot_escape(src)}" -> "{_dot_escape(dst)}";')
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Render additive validation DAG with const names")
    ap.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--base-name", required=True)
    ap.add_argument("--level", default="level2")
    ap.add_argument("--rule", default="effective_line_merge")
    ap.add_argument("--algo", required=True)
    ap.add_argument("--source", type=Path, default=None, help="Optional source path override")
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    pipeline_root = base_dir / "intermediate_results" / args.base_name / "pipeline"

    dag_json = _read_json(pipeline_root / "blocks" / args.level / args.rule / "dag_seg.json")
    segments_json = _read_json(pipeline_root / "blocks" / args.level / args.rule / "segments.json")
    timing_json = _read_json(pipeline_root / "timing" / args.level / args.rule / "timing.json")
    schedule_json = _read_json(pipeline_root / "schedule" / args.level / args.rule / args.algo / "schedule.json")

    if args.source is not None:
        source_file = args.source.resolve()
    else:
        block_info = _read_json(pipeline_root / "block_info.json")
        source_file = Path(str(block_info["source_file"])).resolve()

    source_text = source_file.read_text(encoding="utf-8", errors="replace")
    node_ids = _resolve_node_ids(dag_json, segments_json)
    edges = _resolve_edges(dag_json)
    avg_ns = {k: int(v.get("avg_ns", -1)) for k, v in timing_json.get("weights", {}).items() if isinstance(v, dict)}
    priorities = {str(k): int(v) for k, v in schedule_json.get("priorities", {}).items()}
    const_map = _build_const_binding(segments_json, node_ids, source_text)

    dot_text = _render_dot(node_ids, edges, avg_ns, priorities, const_map)

    out_root = pipeline_root / "validation_const" / args.level / args.rule / args.algo
    out_root.mkdir(parents=True, exist_ok=True)
    dot_path = out_root / "dag_seg_annotated_const.dot"
    png_path = out_root / "dag_seg_annotated_const.png"
    dot_path.write_text(dot_text, encoding="utf-8")
    _write_json(out_root / "const_binding.json", const_map)

    try:
        subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True, capture_output=True)
    except Exception:
        pass

    print(json.dumps({
        "status": "success",
        "base_name": args.base_name,
        "algo": args.algo,
        "dot": str(dot_path),
        "png": str(png_path),
        "const_binding": str(out_root / "const_binding.json"),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
