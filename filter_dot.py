#!/usr/bin/env python3
"""
Mycallyplus 内置 DOT 过滤器：简化节点名，去掉作用域前缀/参数列表/编译器后缀。

用法：
    python -m mycallyplus.filter_dot path/to/dag.dot

输出：
    在同目录生成 dag_filt.dot（源文件名后追加 _filt）。
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Iterable


THUNK_PREFIX_RE = re.compile(
    r"^(?:non-virtual thunk to |virtual thunk to |covariant return thunk to )"
)

SUFFIX_RE = re.compile(
    r"(?:\.(?:part|constprop|isra)\.\d+|\.(?:cold|llvm\.[A-Za-z0-9_]+)|\[(?:clone [^\]]+)\])$"
)


def drop_outer_template(name: str) -> str:
    """去掉末尾的 <...> 模板实参（仅处理尾部一段，支持嵌套 <>）."""
    if not name.endswith(">"):
        return name
    depth = 0
    for i in range(len(name) - 1, -1, -1):
        ch = name[i]
        if ch == ">":
            depth += 1
        elif ch == "<":
            depth -= 1
            if depth == 0:
                return name[:i].rstrip()
    return name


def strip_params_and_trailing(name: str) -> str:
    """去掉参数列表及其后的限定/属性."""
    if "(" in name:
        name = name.split("(", 1)[0]
    name = re.sub(
        r"(?:\s+const|\s+volatile|\s+const volatile|\s+[&]{1,2}|\s+noexcept.*|\s+throw\(.*\))$",
        "",
        name,
    )
    return name.strip()


def clean_symbol(raw: str) -> str:
    """将原始节点名简化为核心函数名（保留 operator/构造/析构标识）."""
    name = THUNK_PREFIX_RE.sub("", raw.strip())
    name = SUFFIX_RE.sub("", name)
    name = strip_params_and_trailing(name)
    core = name.split("::")[-1].strip()
    core = drop_outer_template(core)
    return core or name


def simplify_node(node: str) -> str:
    """处理形如 A/B/C 的复合节点，对每一段简化后再拼回."""
    parts = [clean_symbol(p) for p in node.split("/")]
    return "/".join(parts)


def process_lines(lines: Iterable[str]) -> Iterable[str]:
    """对 dot 内容逐行替换节点名."""
    node_re = re.compile(r'"([^"]+)"')
    for line in lines:
        def repl(match: re.Match[str]) -> str:
            original = match.group(1)
            simplified = simplify_node(original)
            return f'"{simplified}"'

        yield node_re.sub(repl, line)


def filter_file(src: Path, dst: Path) -> None:
    with src.open("r", encoding="utf-8") as f:
        lines = list(process_lines(f))
    with dst.open("w", encoding="utf-8") as f:
        f.writelines(lines)


def main() -> None:
    if len(sys.argv) != 2:
        print("用法: python -m mycallyplus.filter_dot path/to/dag.dot", file=sys.stderr)
        sys.exit(1)

    src = Path(sys.argv[1]).expanduser()
    if not src.is_file():
        print(f"文件不存在: {src}", file=sys.stderr)
        sys.exit(1)

    dst = src.with_name(src.stem + "_filt" + src.suffix)
    filter_file(src, dst)
    print(f"已生成: {dst}")


if __name__ == "__main__":
    main()
