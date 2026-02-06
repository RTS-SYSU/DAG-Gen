from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


EDGE_RE = re.compile(r'"([^"]+)"\s*->\s*"([^"]+)"')
NODE_RE = re.compile(r'"([^"]+)"')


def _read_dot(dot_path: Path) -> Tuple[Set[str], List[Tuple[str, str]]]:
    text = dot_path.read_text(encoding="utf-8", errors="ignore")
    edges = EDGE_RE.findall(text)
    nodes = set(NODE_RE.findall(text))
    return nodes, [(a, b) for a, b in edges]


def _parse_sem_pairs(circle_path: Path) -> List[Tuple[str, str]]:
    """Return list of (post_node, wait_node)."""
    pairs: Dict[str, Dict[str, str]] = {}
    block = None
    for line in circle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        s = line.strip()
        if not s:
            continue
        if s == "互斥量":
            block = "mutex"
            continue
        if s == "信号量":
            block = "sem"
            continue
        if block != "sem":
            continue
        parts = s.split()
        if len(parts) < 3:
            continue
        func, var, idx = parts[0], parts[1], parts[2]
        rec = pairs.setdefault(idx, {"post": None, "wait": None})
        if "sem_post" in func:
            rec["post"] = func
        elif "sem_wait" in func:
            rec["wait"] = func
    out: List[Tuple[str, str]] = []
    for rec in pairs.values():
        if rec.get("post") and rec.get("wait"):
            out.append((rec["post"], rec["wait"]))  # type: ignore[arg-type]
    return out


def _to_dot(nodes: Set[str], edges: List[Tuple[str, str]]) -> str:
    lines = ["digraph merged {", '  rankdir=LR;', '  node [shape=box, fontname="Consolas", fontsize=10];']
    for n in sorted(nodes):
        lines.append(f'  "{n}";')
    for u, v in edges:
        lines.append(f'  "{u}" -> "{v}";')
    lines.append("}")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge post->wait edges into existing DAG (Level-2 pre-step).")
    ap.add_argument("--base-dir", type=Path, default=Path("mycallyplus_v1"))
    ap.add_argument("--base-name", required=True)
    args = ap.parse_args()

    base_dir = args.base_dir.resolve()
    base_name = args.base_name

    dag_path = base_dir / "中间结果" / base_name / "生成dag图" / "dag.dot"
    circle_path = base_dir / "中间结果" / base_name / "配置文件" / "circle.txt"
    if not dag_path.exists():
        raise SystemExit(f"missing dag.dot: {dag_path}")
    if not circle_path.exists():
        raise SystemExit(f"missing circle.txt: {circle_path}")

    nodes, edges = _read_dot(dag_path)
    sem_pairs = _parse_sem_pairs(circle_path)

    # add post->wait edges
    for post, wait in sem_pairs:
        if post not in nodes:
            nodes.add(post)
        if wait not in nodes:
            nodes.add(wait)
        edges.append((post, wait))

    out_dir = base_dir / "中间结果" / base_name / "level2" / "merge_post_wait"
    out_dir.mkdir(parents=True, exist_ok=True)
    dag_json = {"nodes": sorted(nodes), "edges": [{"src": u, "dst": v, "kind": "sem_dep"} for u, v in edges]}
    (out_dir / "dag_level2_sem.json").write_text(json.dumps(dag_json, ensure_ascii=False, indent=2), encoding="utf-8")
    dot_str = _to_dot(nodes, edges)
    dot_path = out_dir / "dag_level2_sem.dot"
    dot_path.write_text(dot_str, encoding="utf-8")
    png_path = out_dir / "dag_level2_sem.png"
    try:
        import subprocess

        subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True, capture_output=True)
    except Exception:
        pass
    print(f"wrote {dot_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

