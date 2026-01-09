#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调用 legacy.py 处理 .expand（含 --source-file），随后仅保留 extern==1 的调用生成 .dot/.png。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_functions(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def build_filtered_dot(functions: dict) -> str:
    lines = ["strict digraph callgraph {"]
    for func, finfo in sorted(functions.items()):
        meta_map = finfo.get("mycalls_meta", {})
        if not isinstance(meta_map, dict):
            continue
        pre = None
        for caller, meta in meta_map.items():
            if not isinstance(meta, dict):
                continue
            if meta.get("extern") != 1:
                continue
            # 只输出 extern==1 的节点/边
            if pre is None:
                lines.append(f'"{func}" -> "{caller}";')
            else:
                lines.append(f'"{pre}" -> "{caller}";')
            lines.append(f'"{caller}" [style=dashed]')
            pre = caller
        if pre is None:
            lines.append(f'"{func}"')
    lines.append("}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="运行 legacy 生成数据，并过滤 extern==1 生成 dot/png")
    parser.add_argument("--source-file", required=True, help="选中的源文件")
    parser.add_argument("expand", nargs="+", help=".expand 文件路径")
    parser.add_argument("--output-base", help="输出目录，默认与 legacy 输出相同")
    args = parser.parse_args()

    root_dir = Path(__file__).resolve().parents[2]
    legacy_script = root_dir / "mycallyplus" / "generation" / "legacy.py"
    if not legacy_script.exists():
        print(f"legacy.py 不存在: {legacy_script}", file=sys.stderr)
        sys.exit(1)

    # 调用 legacy.py
    cmd = [sys.executable, str(legacy_script), "--source-file", args.source_file] + args.expand
    proc = subprocess.run(cmd, cwd=root_dir, capture_output=True, text=True)
    sys.stdout.write(proc.stdout)
    sys.stderr.write(proc.stderr)
    if proc.returncode != 0:
        sys.exit(proc.returncode)

    # 推导 functions_full.json 路径（沿用 legacy 规则）
    first_rtl = Path(args.expand[0])
    base_name = first_rtl.stem
    if base_name.endswith(".233r"):
        base_name = base_name[:-5]
    if "." in base_name:
        base_name = base_name.split(".")[0]
    out_base = Path(args.output_base).expanduser().resolve() if args.output_base else root_dir / "中间结果" / base_name / "生成dag图"
    json_path = out_base / "functions_full.json"
    if not json_path.exists():
        print(f"未找到 functions_full.json: {json_path}", file=sys.stderr)
        sys.exit(1)

    functions = load_functions(json_path)
    dot_str = build_filtered_dot(functions)

    dot_path = out_base / "filtered.dot"
    png_path = out_base / "filtered.png"
    dot_path.write_text(dot_str, encoding="utf-8")
    try:
        subprocess.run(
            ["dot", "-Tpng", str(dot_path), "-o", str(png_path)],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as exc:  # pragma: no cover
        print(f"渲染 PNG 失败: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"生成 {dot_path}")
    print(f"生成 {png_path}")


if __name__ == "__main__":
    main()
