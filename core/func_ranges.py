from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class FuncRange:
    # Original name from pipeline (may include @instanceN suffix).
    name: str
    # Normalized name used for lookup in source file.
    base_name: str
    # Function signature line (where name appears).
    start_line: int
    # Line containing the opening '{' for function body.
    body_start_line: int
    # First statement line within body (best-effort).
    first_stmt_line: Optional[int]
    # Line containing the matching '}' for function body.
    end_line: int
    # Last "return" line within body (best-effort).
    last_return_line: Optional[int]
    # Last statement-ish line within body (best-effort).
    last_stmt_line: Optional[int]


_INSTANCE_SUFFIX_RE = re.compile(r"@instance\d+$")


def normalize_func_name(name: str) -> str:
    """busy_wait_seconds@instance1 -> busy_wait_seconds."""
    return _INSTANCE_SUFFIX_RE.sub("", name)


def is_ignored_compiler_fn(name: str) -> bool:
    """Ignore compiler-inserted symbols like __stack_chk_fail* (including node forms with prefixes)."""
    tail = name.split("/")[-1]
    return tail.startswith("__stack_chk_fail")


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
    offs = [0]
    for m in re.finditer(r"\n", text):
        offs.append(m.end())
    return offs


def _offset_to_line(offs: Sequence[int], offset: int) -> int:
    lo, hi = 0, len(offs) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if offs[mid] <= offset:
            lo = mid + 1
        else:
            hi = mid - 1
    return max(1, hi + 1)


def _find_definition_signature(clean_text: str, func_name: str, start_at: int = 0) -> Optional[Tuple[int, int]]:
    pat = re.compile(rf"\b{re.escape(func_name)}\s*\(")
    m = pat.search(clean_text, pos=start_at)
    if not m:
        return None
    paren = clean_text.find("(", m.start())
    return m.start(), paren


def _scan_to_body_open(clean_text: str, paren_open: int) -> Optional[int]:
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
            return None  # prototype, not definition
        i += 1
    return None


def _match_brace_block(clean_text: str, body_open: int) -> Optional[int]:
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


def _find_first_stmt_line(clean_text: str, offs: Sequence[int], body_open: int, body_close: int) -> Optional[int]:
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


def _last_stmt_and_return_lines(clean_text: str, offs: Sequence[int], body_open: int, body_close: int) -> Tuple[Optional[int], Optional[int]]:
    segment = clean_text[body_open : body_close + 1]
    last_return = None
    last_stmt = None
    for m in re.finditer(r"\breturn\b", segment):
        last_return = _offset_to_line(offs, body_open + m.start())
    # "last_stmt_line" is intended to reflect the last statement-ish line,
    # not the closing brace. Prefer the last ';' inside the body.
    for m in re.finditer(r";", segment):
        last_stmt = _offset_to_line(offs, body_open + m.start())
    if last_stmt is None:
        # Fallback: find the last non-empty, non-brace line before the closing brace.
        body = segment[1:-1] if len(segment) >= 2 else ""
        lines = body.splitlines()
        for i in range(len(lines) - 1, -1, -1):
            t = lines[i].strip()
            if not t or t in ("{", "}"):
                continue
            # body_open is at some line; add i lines (1-based conversion handled by offset_to_line elsewhere),
            # easiest is to compute absolute offset by searching from the end.
            # Use rfind of this line content in the segment to approximate position.
            rel = segment.rfind(lines[i])
            if rel != -1:
                last_stmt = _offset_to_line(offs, body_open + rel)
            break
    return last_stmt, last_return


def extract_func_ranges(source_path: Path, func_names: Iterable[str]) -> List[FuncRange]:
    raw = source_path.read_text(encoding="utf-8", errors="replace")
    clean = _strip_comments_and_strings(raw)
    offs = _line_offsets(clean)

    results: List[FuncRange] = []
    for original_name in func_names:
        if is_ignored_compiler_fn(original_name):
            continue
        base_name = normalize_func_name(original_name)
        pos = 0
        found = None
        while True:
            sig = _find_definition_signature(clean, base_name, start_at=pos)
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
            end_line = _offset_to_line(offs, body_close)
            first_stmt_line = _find_first_stmt_line(clean, offs, body_open, body_close)
            last_stmt_line, last_return_line = _last_stmt_and_return_lines(clean, offs, body_open, body_close)
            found = FuncRange(
                name=str(original_name),
                base_name=str(base_name),
                start_line=int(start_line),
                body_start_line=int(body_start_line),
                first_stmt_line=int(first_stmt_line) if first_stmt_line is not None else None,
                end_line=int(end_line),
                last_return_line=int(last_return_line) if last_return_line is not None else None,
                last_stmt_line=int(last_stmt_line) if last_stmt_line is not None else None,
            )
            break

        if found:
            results.append(found)
    return results
