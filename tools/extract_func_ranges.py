#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FuncRange:
    name: str
    start_line: int
    body_start_line: int
    first_stmt_line: Optional[int]
    end_line: int
    last_return_line: Optional[int]
    last_stmt_line: Optional[int]


def _strip_comments_and_strings(text: str) -> str:
    # Removes comments and string/char literals, keeping newlines for line indexing.
    out: List[str] = []
    i = 0
    n = len(text)
    state = "code"  # code|line_comment|block_comment|string|char
    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                out.append("  ")
                i += 2
                state = "line_comment"
                continue
            if ch == "/" and nxt == "*":
                out.append("  ")
                i += 2
                state = "block_comment"
                continue
            if ch == '"':
                out.append(" ")
                i += 1
                state = "string"
                continue
            if ch == "'":
                out.append(" ")
                i += 1
                state = "char"
                continue
            out.append(ch)
            i += 1
            continue

        if state == "line_comment":
            if ch == "\n":
                out.append("\n")
                i += 1
                state = "code"
            else:
                out.append(" ")
                i += 1
            continue

        if state == "block_comment":
            if ch == "*" and nxt == "/":
                out.append("  ")
                i += 2
                state = "code"
            else:
                out.append("\n" if ch == "\n" else " ")
                i += 1
            continue

        if state == "string":
            if ch == "\\":
                out.append("  ")
                i += 2
                continue
            if ch == '"':
                out.append(" ")
                i += 1
                state = "code"
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue

        if state == "char":
            if ch == "\\":
                out.append("  ")
                i += 2
                continue
            if ch == "'":
                out.append(" ")
                i += 1
                state = "code"
                continue
            out.append("\n" if ch == "\n" else " ")
            i += 1
            continue

        raise RuntimeError(f"unknown state: {state}")
    return "".join(out)


def _line_offsets(text: str) -> List[int]:
    # line_no(1-based) -> starting offset
    offs = [0]
    for m in re.finditer(r"\n", text):
        offs.append(m.end())
    return offs


def _offset_to_line(offs: Sequence[int], offset: int) -> int:
    # binary search
    lo, hi = 0, len(offs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if offs[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(1, hi + 1)


def _find_definition_signature(clean_text: str, func_name: str, start_at: int = 0) -> Optional[Tuple[int, int]]:
    # Find "func_name(" occurrences in clean text. Return (match_start, paren_open_offset).
    pat = re.compile(rf"\b{re.escape(func_name)}\s*\(")
    m = pat.search(clean_text, pos=start_at)
    if not m:
        return None
    paren = clean_text.find("(", m.start())
    return m.start(), paren


def _scan_to_body_open(clean_text: str, paren_open: int) -> Optional[int]:
    # From '(' scan forward to find the opening '{' that begins the function body,
    # skipping prototypes (ending with ';') and attributes.
    depth = 0
    i = paren_open
    n = len(clean_text)
    while i < n:
        ch = clean_text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "{" and depth == 0:
            return i
        elif ch == ";" and depth == 0:
            return None  # prototype, not a definition
        i += 1
    return None


def _match_brace_block(clean_text: str, body_open: int) -> Optional[int]:
    # Return offset of matching '}' for '{' at body_open.
    depth = 0
    i = body_open
    n = len(clean_text)
    while i < n:
        ch = clean_text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _last_stmt_and_return_lines(clean_text: str, offs: Sequence[int], body_open: int, body_close: int) -> Tuple[Optional[int], Optional[int]]:
    segment = clean_text[body_open : body_close + 1]
    last_return = None
    last_stmt = None

    # last return
    for m in re.finditer(r"\breturn\b", segment):
        last_return = _offset_to_line(offs, body_open + m.start())

    # last statement-ish line: last line that contains a ';' or a '}' before the close brace line.
    # (Helps when functions end without explicit return.)
    for m in re.finditer(r"[;}]", segment):
        last_stmt = _offset_to_line(offs, body_open + m.start())

    return last_stmt, last_return


def _find_first_stmt_line(clean_text: str, offs: Sequence[int], body_open: int, body_close: int) -> Optional[int]:
    # Heuristic: first non-whitespace token after '{' that is not another brace.
    i = body_open + 1
    n = min(len(clean_text), body_close + 1)
    while i < n:
        ch = clean_text[i]
        if ch in (" ", "\t", "\r", "\n"):
            i += 1
            continue
        if ch in ("{", "}"):
            i += 1
            continue
        return _offset_to_line(offs, i)
    return None


_INSTANCE_SUFFIX_RE = re.compile(r"@instance\d+$")


def _normalize_func_name(name: str) -> str:
    # busy_wait_seconds@instance1 -> busy_wait_seconds
    return _INSTANCE_SUFFIX_RE.sub("", name)


def _is_ignored_compiler_fn(name: str) -> bool:
    # e.g. __stack_chk_fail, __stack_chk_fail41, main/__stack_chk_fail41
    tail = name.split("/")[-1]
    return tail.startswith("__stack_chk_fail")


def extract_ranges(source_path: Path, func_names: Iterable[str]) -> List[FuncRange]:
    raw = source_path.read_text(encoding="utf-8", errors="replace")
    clean = _strip_comments_and_strings(raw)
    offs = _line_offsets(clean)

    results: List[FuncRange] = []
    for original_name in func_names:
        if _is_ignored_compiler_fn(original_name):
            continue
        name = _normalize_func_name(original_name)
        pos = 0
        found = None
        while True:
            sig = _find_definition_signature(clean, name, start_at=pos)
            if not sig:
                break
            sig_start, paren_open = sig
            body_open = _scan_to_body_open(clean, paren_open)
            if body_open is None:
                pos = paren_open + 1
                continue
            body_close = _match_brace_block(clean, body_open)
            if body_close is None:
                pos = body_open + 1
                continue

            start_line = _offset_to_line(offs, sig_start)
            body_start_line = _offset_to_line(offs, body_open)
            first_stmt_line = _find_first_stmt_line(clean, offs, body_open, body_close)
            end_line = _offset_to_line(offs, body_close)
            last_stmt_line, last_return_line = _last_stmt_and_return_lines(clean, offs, body_open, body_close)
            found = FuncRange(
                name=original_name,
                start_line=start_line,
                body_start_line=body_start_line,
                first_stmt_line=first_stmt_line,
                end_line=end_line,
                last_return_line=last_return_line,
                last_stmt_line=last_stmt_line,
            )
            break

        if found:
            results.append(found)
    return results


def _load_func_names_from_functions_full(path: Path) -> List[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return sorted([str(k) for k in data.keys()])
    raise ValueError("functions_full.json 顶层必须是对象(dict)")


def main() -> int:
    ap = argparse.ArgumentParser(description="Extract function start/end/return line ranges from a C file.")
    ap.add_argument("--source", required=True, type=Path, help="Path to .c source file")
    ap.add_argument("--functions-full", type=Path, help="Path to functions_full.json (keys are function names)")
    ap.add_argument("--names", nargs="*", help="Explicit function names (overrides --functions-full)")
    ap.add_argument("--out", required=True, type=Path, help="Output JSON path")
    args = ap.parse_args()

    if args.names:
        names = list(args.names)
    elif args.functions_full:
        names = _load_func_names_from_functions_full(args.functions_full)
    else:
        ap.error("must provide --names or --functions-full")
        raise AssertionError

    ranges = extract_ranges(args.source, names)

    payload = {
        "source": str(args.source),
        "functions": [
            {
                "name": r.name,
                "start_line": r.start_line,
                "body_start_line": r.body_start_line,
                "first_stmt_line": r.first_stmt_line,
                "end_line": r.end_line,
                "last_return_line": r.last_return_line,
                "last_stmt_line": r.last_stmt_line,
            }
            for r in ranges
        ],
        "missing": sorted(
            [
                n
                for n in names
                if (n not in {r.name for r in ranges})
                and (not _is_ignored_compiler_fn(n))
            ]
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {args.out} (functions={len(payload['functions'])}, missing={len(payload['missing'])})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
