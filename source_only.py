#!/usr/bin/env python3
"""
从 .expand 生成“源码调用图”：仅保留调用点来源文件名与指定源文件名一致的边。

用法:
    python -m mycallyplus.source_only --expand path/to/file.233r.expand --source <basename> --output out.dot
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, Set


def parse_expand(expand_path: Path, source_basename: str) -> Dict[str, Set[str]]:
    """解析 expand，返回仅来自指定源文件的调用边集合，带 legacy 式编号。

    同时返回两套边：
    - all_edges: 不过滤源文件
    - filtered_edges: 仅保留源文件匹配 source_basename 的调用
    """
    func_re = re.compile(r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)")
    call_target_re = re.compile(r'\(call.*?"(?P<target>[^"]+)"')
    src_re = re.compile(r'"(?P<file>[^"]+)":(?P<line>\d+):(?P<col>\d+)')

    # 先收集所有定义的函数名
    defined: Set[str] = set()
    for line in expand_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        m_func = func_re.match(line)
        if m_func:
            defined.add(m_func.group("function"))

    edges: Dict[str, Set[str]] = {}
    current_fn: str | None = None
    pending_target: str | None = None
    call_counter: Dict[str, int] = {}  # 每个 caller 的编号计数

    with expand_path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m_func = func_re.match(line)
            if m_func:
                current_fn = m_func.group("function")
                edges.setdefault(current_fn, set())
                pending_target = None
                continue

            if current_fn is None:
                continue

            # 捕获 call 目标
            m_target = call_target_re.search(line)
            if m_target:
                # 新的调用出现，若上一个挂起未匹配到源位则覆盖
                raw_target = m_target.group("target")
                # 应用编号规则：未定义的目标加 caller 前缀与序号
                if raw_target in defined:
                    pending_target = raw_target
                else:
                    call_counter[current_fn] = call_counter.get(current_fn, 0) + 1
                    pending_target = f"{current_fn}/{raw_target}{call_counter[current_fn]}"

                # 同行若带源位直接匹配
                m_src_inline = src_re.search(line)
                if m_src_inline and Path(m_src_inline.group("file")).name == source_basename:
                    edges.setdefault(current_fn, set()).add(pending_target)
                    pending_target = None
                continue

            # 挂起状态下，尝试在后续行匹配源位
            if pending_target:
                m_src = src_re.search(line)
                if m_src and Path(m_src.group("file")).name == source_basename:
                    edges.setdefault(current_fn, set()).add(pending_target)
                    pending_target = None
                # 若不是目标源文件，则保持挂起，等待后续可能的源行

    return edges


def write_dot(edges: Dict[str, Set[str]], output: Path) -> None:
    lines = ["strict digraph callgraph {\n"]
    for caller, callees in edges.items():
        for callee in sorted(callees):
            lines.append(f"\"{caller}\" -> \"{callee}\";\n")
    lines.append("}\n")
    output.write_text("".join(lines), encoding="utf-8")


def _derive_default_paths(expand: Path) -> tuple[Path, Path, Path]:
    """根据 expand 路径推导输出目录与文件名."""
    base_dir = expand.parents[2] if len(expand.parents) >= 3 else expand.parent
    base_name = expand.stem
    if base_name.endswith(".233r"):
        base_name = base_name[:-5]
    if "." in base_name:
        base_name = base_name.split(".")[0]
    out_dir = base_dir / "中间结果" / base_name / "生成dag图"
    out_dir.mkdir(parents=True, exist_ok=True)
    dot_path = out_dir / "dag_source_only.dot"
    filt_dot_path = out_dir / "dag_source_only_filt.dot"
    png_path = out_dir / "dag_source_only_filt.png"
    return dot_path, filt_dot_path, png_path


def main() -> int:
    ap = argparse.ArgumentParser(description="生成仅包含指定源文件调用的 DOT")
    ap.add_argument("--expand", required=True, type=Path, help=".233r.expand 文件路径")
    ap.add_argument("--source", required=True, help="源文件 basename，例如 FixedwingRateControl.cpp")
    ap.add_argument("--output", type=Path, help="输出 dot 路径（可选，默认放在中间结果/<基名>/生成dag图）")
    args = ap.parse_args()

    # 推导输出路径
    if args.output:
        dot_path = args.output
        out_dir = dot_path.parent
        filt_dot_path = out_dir / "dag_source_only_filt.dot"
        png_path = out_dir / "dag_source_only_filt.png"
        out_dir.mkdir(parents=True, exist_ok=True)
    else:
        dot_path, filt_dot_path, png_path = _derive_default_paths(args.expand)

    edges = parse_expand(args.expand, args.source)
    write_dot(edges, dot_path)
    print(f"已生成源码调用图: {dot_path}")

    # 保留过滤前后：过滤版目前为直接复制，保留编号
    import shutil, subprocess
    shutil.copy2(dot_path, filt_dot_path)

    # 渲染 PNG
    try:
        subprocess.run(
            ["dot", "-Tpng", str(filt_dot_path), "-o", str(png_path)],
            check=True,
            capture_output=True,
        )
        print(f"已渲染: {png_path}")
    except Exception as e:
        print(f"渲染 PNG 失败: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
