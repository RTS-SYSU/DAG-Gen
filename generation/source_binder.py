from __future__ import annotations

"""Source-based binder for pthread_create/pthread_join.

When RTL can't provide a reliable mapping, we parse the C source of the
owner function and try pairing create/join by normalizing the first
argument (thread handle expression).

This is intentionally lightweight (regex + brace counting) to avoid
third-party dependencies. It works for common patterns:
  - pthread_create(&thread, attr, task, arg)
  - pthread_join(thread, retval)
  - handles like &thread, threads[i], ctx->thr, *p
"""

from pathlib import Path
import re
from typing import List, Optional, Tuple


_FUNC_HDR_RE = re.compile(r"^;; Function .*\((?P<func>\S+)\)")
_SRC_LOC_RE = re.compile(r'"(?P<src>[^"\n]+\.c)":(?P<line>\d+):')

_CREATE_RE = re.compile(
    r"pthread_create\s*\(\s*(?P<a1>[^,]+),\s*(?P<a2>[^,]+),\s*(?P<a3>[^,\)]+)(?:,\s*(?P<a4>[^\)]*))?\)"
)
_JOIN_RE = re.compile(r"pthread_join\s*\(\s*(?P<a1>[^,]+),\s*(?P<a2>[^\)]*)\)")


def _read_expand(path: Path) -> List[str]:
    try:
        return path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except Exception:
        return []


def _guess_source_from_expand(expand_lines: List[str], expand_path: Path) -> Optional[Path]:
    for line in expand_lines:
        m = _SRC_LOC_RE.search(line)
        if m:
            src = m.group("src")
            p = Path(src)
            if not p.is_absolute():
                p = (expand_path.parent / p).resolve()
            return p
    return None


def _extract_function_region(src: str, func: str) -> str:
    idx = src.find(func + "(")
    if idx == -1:
        return src
    # move forward to first '{'
    lbrace = src.find("{", idx)
    if lbrace == -1:
        return src[idx:]
    depth = 0
    for i in range(lbrace, len(src)):
        if src[i] == '{':
            depth += 1
        elif src[i] == '}':
            depth -= 1
            if depth == 0:
                return src[idx : i + 1]
    return src[idx:]


def _normalize_handle(expr: str) -> str:
    t = expr.strip()
    # strip outer parentheses
    while t.startswith('(') and t.endswith(')'):
        t = t[1:-1].strip()
    t = t.replace(' ', '')
    # &var
    if t.startswith('&'):
        return f"sym:{t[1:]}"
    # array element var[i]
    if '[' in t and ']' in t:
        return f"sym:{t}"
    # struct member ctx->thr or ctx.thr
    if '->' in t or '.' in t:
        return f"mem:{t}"
    # deref *p
    if t.startswith('*'):
        return f"deref:{t[1:]}"
    # fallback variable name
    return f"sym:{t}"


def _normalize_task(task_expr: str) -> str:
    t = task_expr.strip()
    # strip casts and &
    t = re.sub(r"\([^\)]*\)", "", t)
    t = t.replace('&', '').replace('*', '').strip()
    m = re.search(r"([A-Za-z_][A-Za-z0-9_]*)", t)
    return m.group(1) if m else t


def _scan_calls(func_src: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    creates: List[Tuple[str, str]] = []  # (handleID, task)
    joins: List[str] = []  # handleID
    for m in _CREATE_RE.finditer(func_src):
        a1 = _normalize_handle(m.group('a1'))
        task = _normalize_task(m.group('a3'))
        creates.append((a1, task))
    for m in _JOIN_RE.finditer(func_src):
        a1 = _normalize_handle(m.group('a1'))
        joins.append(a1)
    return creates, joins


def bind_from_source(expand_path: Path, owner_function: str) -> List[str]:
    """Return task_function list matched to join order in source function.

    If join count > create count, the extra joins will use FIFO of creates.
    """
    lines = _read_expand(expand_path)
    if not lines:
        return []
    src_path = _guess_source_from_expand(lines, expand_path)
    if not src_path or not src_path.exists():
        return []
    try:
        src_text = src_path.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return []
    region = _extract_function_region(src_text, owner_function)
    creates, joins = _scan_calls(region)
    if not joins:
        return []

    # build mapping
    result: List[str] = []
    create_queue: List[str] = [task for _, task in creates]
    by_handle = {h: task for h, task in creates}
    for h in joins:
        task = by_handle.get(h)
        if task is None and create_queue:
            task = create_queue.pop(0)
        if task:
            result.append(task)
    return result

