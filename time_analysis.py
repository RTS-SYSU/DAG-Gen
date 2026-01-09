"""
时间分析（按调用点插桩）工具。

实现要点基于《时间分析_CallSite_V1_实现规范.md》：
- 读取 mycalls_meta_internal.json，定位 (file,line) 调用点
- 在调用语句前后插入计时代码（TA_BEGIN / TA_END 标记）
- 自动拷贝运行时库 time_stat.c/h，编译、运行并产出 time_result.json
- 仅支持 C 语言；复杂表达式、无法定界的语句会被跳过并记录 warning
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple, Mapping

# 轻量级 DOT 解析正则（兼容 legacy 输出）
_EDGE_RE = re.compile(r'"([^"]+)"\s*->\s*"([^"]+)"')
_NODE_QUOTED_RE = re.compile(r'"([^"]+)"')


@dataclass
class CallSite:
    file: Path
    line: int
    col: Optional[int]
    func: str
    raw_key: str


@dataclass
class InstrumentResult:
    instrumented_dir: Path
    app_path: Path
    result_json: Path
    prio_result_json: Optional[Path]
    prio_weighted_dot: Optional[Path]
    metrics_json: Optional[Path]
    log_path: Path
    instrumented_files: List[Path]
    warnings: List[str]
    skipped: List[str]


def _infer_base_name_from_meta(meta_json: Path, base_dir: Path) -> Optional[str]:
    """若 meta_json 位于 <base_dir>/中间结果/<basename>/... 下，返回 <basename>。"""
    try:
        meta_json = meta_json.resolve()
        base_dir = base_dir.resolve()
        rel = meta_json.relative_to(base_dir)
    except Exception:
        return None
    parts = rel.parts
    if len(parts) >= 2 and parts[0] == "中间结果":
        return parts[1]
    return None


def _flatten_meta(obj: Dict) -> List[Tuple[str, Dict]]:
    """展开 mycalls_meta_internal 的层级结构，返回 (key, meta) 列表。"""
    out: List[Tuple[str, Dict]] = []
    for k, v in obj.items():
        if isinstance(v, dict) and {"file", "line"} <= set(v.keys()):
            out.append((k, v))
        elif isinstance(v, dict):
            out.extend(_flatten_meta(v))
    return out


def _infer_func_from_key(raw_key: str, meta: Dict) -> str:
    """从键名或 meta 中推断 func 名，去掉尾部数字。"""
    if isinstance(meta, dict):
        fn = meta.get("func")
        if isinstance(fn, str) and fn.strip():
            return fn.strip()
    tail = raw_key.split("/")[-1]
    m = re.match(r"([A-Za-z_][A-Za-z0-9_]*?)(\d*)$", tail)
    return m.group(1) if m else tail


def load_call_sites(json_path: Path) -> List[CallSite]:
    """解析 mycalls_meta_internal.json，生成 CallSite 列表。"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    sites: List[CallSite] = []
    for raw_key, meta in _flatten_meta(data):
        if not isinstance(meta, dict):
            continue
        file_field = meta.get("file")
        line = meta.get("line")
        if not file_field or not line:
            continue
        col = meta.get("col")
        func = _infer_func_from_key(raw_key, meta)
        sites.append(
            CallSite(
                file=Path(str(file_field)),
                line=int(line),
                col=int(col) if col is not None else None,
                func=func,
                raw_key=raw_key,
            )
        )
    return sites


def _strip_strings(text: str) -> str:
    """去掉字符串/字符字面量的内容，避免误判赋值/三目。"""
    res = []
    it = iter(range(len(text)))
    i = 0
    in_str = None
    while i < len(text):
        ch = text[i]
        if in_str:
            if ch == "\\":
                i += 2
                continue
            if ch == in_str:
                in_str = None
            i += 1
            continue
        if ch in ("\"", "'"):
            in_str = ch
            i += 1
            continue
        res.append(ch)
        i += 1
    return "".join(res)


def _has_assignment(expr: str) -> bool:
    """粗略判断是否存在赋值 = ，忽略 ==, <=, >=, !=."""
    expr = _strip_strings(expr)
    return re.search(r"(?<![=!<>])=(?![=])", expr) is not None


def _has_question(expr: str) -> bool:
    expr = _strip_strings(expr)
    return "?" in expr


def _is_control_statement(expr: str) -> bool:
    s = expr.lstrip()
    return s.startswith(("if", "while", "for", "switch", "return"))


def _find_stmt_end(lines: List[str], start_idx: int) -> Optional[int]:
    """从 start_idx 起向下扫描，找到分号结束的行号（括号深度归零）。"""
    depth = 0
    for idx in range(start_idx, len(lines)):
        line = lines[idx]
        for ch in line:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth = max(0, depth - 1)
        if ";" in line and depth == 0:
            return idx
    return None


def _ensure_include(lines: List[str]) -> Tuple[List[str], bool, int]:
    """确保 time_stat.h 已包含；返回新行列表、是否新增、插入位置前的增加行数。"""
    include_marker = 'time_stat.h"  // TA_INCLUDE'
    if any(include_marker in ln for ln in lines):
        return lines, False, 0
    # 找到首个非空且非纯注释的行前插入
    insert_at = 0
    feature_def_re = re.compile(r"^\s*#\s*define\s+_(GNU|DEFAULT|POSIX|XOPEN|BSD|SVID)_SOURCE\b")
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "#!")):
            continue
        # 头部的特性宏应保留在所有 include 之前
        if feature_def_re.match(ln):
            continue
        insert_at = i
        break
    new_lines = (
        lines[:insert_at]
        + ['#include "time_stat.h"  // TA_INCLUDE\n']
        + lines[insert_at:]
    )
    return new_lines, True, 1


def _sanitize_var_name(basename: str, line: int, seq: int) -> str:
    safe_base = re.sub(r"[^A-Za-z0-9_]", "_", basename)
    return f"__ta_t0_{safe_base}_{line}_{seq}"


def _find_call_span(text: str, func: str) -> Optional[Tuple[int, int]]:
    """在文本中找到 func(...) 的起止位置，返回 (start, end)。"""
    pattern = re.compile(rf"\b{re.escape(func)}\s*\(")
    m = pattern.search(text)
    if not m:
        return None
    start = m.start()
    depth = 0
    for idx in range(m.end(), len(text)):
        ch = text[idx]
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                return start, idx + 1
            depth -= 1
    return None


def _already_instrumented(lines: List[str], start_idx: int, file_name: str, line_no: int, func: str) -> bool:
    """判断该行是否已针对同一调用点插桩过（包含函数名）。"""
    token = f"TA_BEGIN: {file_name}:{line_no} {func}"
    for i in range(max(0, start_idx - 3), min(len(lines), start_idx + 4)):
        if token in lines[i]:
            return True
    return False


def instrument_file(
    file_path: Path,
    sites: List[CallSite],
    log: List[str],
    *,
    priorities: Optional[Mapping[str, int]] = None,
    cpc_mode: bool = False,
) -> Tuple[List[str], List[str], List[str]]:
    """对单个文件插桩，返回修改后的行、警告列表、成功插桩的key列表。"""
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines, added_include, include_added = _ensure_include(lines)
    if added_include:
        log.append(f"[include] {file_path} 插入 time_stat.h")
    warnings: List[str] = []
    instrumented_keys: List[str] = []

    # 按行号降序，避免前面插入影响后续定位
    seq = 1
    seen_prefix_prio: Dict[str, int] = {}
    base_offset = include_added  # include 插入行数，统一偏移
    for site in sorted(sites, key=lambda s: (s.line, s.col or 0), reverse=True):
        # 跳过编译器插入/不应插桩的内部符号，避免跨函数边界破坏源码
        if (
            site.func.startswith("__stack_chk")
            or "__stack_chk" in site.raw_key
            or site.func.startswith("__builtin_")
        ):
            warnings.append(f"[skipgen] {file_path}:{site.line} 跳过编译器内部调用 {site.raw_key}")
            continue
        start_idx = site.line - 1 + base_offset
        if start_idx < 0 or start_idx >= len(lines):
            warnings.append(f"[miss] {file_path}:{site.line} 越界，跳过 {site.func}")
            continue
        key_str = site.raw_key
        if _already_instrumented(lines, start_idx, file_path.name, site.line, site.func):
            log.append(f"[skip] {file_path}:{site.line} 已有 TA 标记，跳过")
            continue

        stmt_end = _find_stmt_end(lines, start_idx)
        if stmt_end is None:
            warnings.append(f"[warn] {file_path}:{site.line} 未找到语句结束，跳过 {site.func}")
            continue

        var_name = _sanitize_var_name(site.raw_key, site.line, seq)
        seq += 1
        snippet = "".join(lines[start_idx : stmt_end + 1])
        stripped = snippet.lstrip()
        if stripped.startswith(("if", "while", "for")):
            span = _find_call_span(snippet, site.func)
            if not span:
                warnings.append(f"[warn] {file_path}:{site.line} 控制语句中未找到调用 {site.func}")
                continue

            # 解析控制语句条件括号范围，仅当调用位于条件内才按表达式包裹
            kw_m = re.match(r"\s*(if|while|for)\b", snippet)
            cond_span: Optional[Tuple[int, int]] = None
            if kw_m:
                kw_end = kw_m.end()
                open_idx = snippet.find("(", kw_end)
                if open_idx != -1:
                    depth = 0
                    for j in range(open_idx + 1, len(snippet)):
                        ch = snippet[j]
                        if ch == "(":
                            depth += 1
                        elif ch == ")":
                            if depth == 0:
                                cond_span = (open_idx, j + 1)
                                break
                            depth -= 1

            call_text = snippet[span[0] : span[1]]
            in_cond = cond_span is not None and span[0] >= cond_span[0] and span[1] <= cond_span[1]

            if in_cond:
                wrapped = (
                    f"(__extension__({{ uint64_t {var_name} = now_ns(); "
                    f"__auto_type __ta_ret = {call_text}; "
                    f"uint64_t {var_name}_dur = now_ns() - {var_name}; "
                    f'time_account("{key_str}", {var_name}_dur); '
                    f'time_trace("{key_str}", {var_name}, {var_name}_dur); '
                    f"__ta_ret; }}))"
                )
                new_snippet = snippet[: span[0]] + wrapped + snippet[span[1] :]
                new_lines = new_snippet.splitlines(keepends=True)
                lines[start_idx : stmt_end + 1] = new_lines
                log.append(f"[ok] {file_path}:{site.line} {site.func} (cond-expr)")
                instrumented_keys.append(key_str)
                base_offset += len(new_lines) - (stmt_end + 1 - start_idx)
                continue

            # 条件外的调用：当前版本不做该类“同一行控制语句内”的特殊识别与改写
            warnings.append(
                f"[skip] {file_path}:{site.line} 控制语句非条件内调用暂不插桩: {site.raw_key}"
            )
            continue

        prio = 0
        thread_prefix = key_str.split("/", 1)[0]
        if priorities:
            prio = int(priorities.get(key_str, 0) or 0)
            if prio <= 0:
                prio = int(priorities.get(thread_prefix, 0) or 0)

        # 仅在每个线程前缀首次插桩时设置优先级，避免每次调用都做系统调用
        maybe_prio_line = ""
        if cpc_mode and prio > 0 and thread_prefix not in seen_prefix_prio:
            maybe_prio_line = f"ta_set_priority({prio});\n"
            seen_prefix_prio[thread_prefix] = prio

        begin_lines = [
            f"// TA_BEGIN: {file_path.name}:{site.line} {site.func}\n",
            "; /* TA_PAD */\n",
            maybe_prio_line,
            f"uint64_t {var_name} = now_ns();\n",
        ]
        end_lines = [
            f"// TA_END: {file_path.name}:{site.line} {site.func}\n",
            f"uint64_t {var_name}_dur = now_ns() - {var_name};\n",
            f'time_account("{key_str}", {var_name}_dur);\n',
            f'time_trace("{key_str}", {var_name}, {var_name}_dur);\n',
        ]

        # 插入：先 BEGIN，再 END（END 位置需 +2 偏移）
        lines[start_idx:start_idx] = begin_lines
        stmt_end += len(begin_lines)
        end_insert_at = stmt_end + 1
        lines[end_insert_at:end_insert_at] = end_lines
        log.append(f"[ok] {file_path}:{site.line} {site.func}")
        instrumented_keys.append(key_str)

    return lines, warnings, instrumented_keys


def _write_time_stat(dest_dir: Path) -> None:
    """写入 time_stat.c/h。"""
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "time_stat.h").write_text(
        "\n".join(
            [
                "#ifndef TIME_STAT_H",
                "#define TIME_STAT_H",
                "",
                "#include <stdint.h>",
                "",
                "#ifdef __cplusplus",
                'extern "C" {',
                "#endif",
                "",
                "uint64_t now_ns(void);",
                'void time_account(const char* key, uint64_t dur_ns);',
                'void time_trace(const char* key, uint64_t start_ns, uint64_t dur_ns);',
                "void ta_set_priority(int prio);",
                "",
                "#ifdef __cplusplus",
                "}",
                "#endif",
                "",
                "#endif",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (dest_dir / "time_stat.c").write_text(
        "\n".join(
            [
                "#define _GNU_SOURCE",
                '#include "time_stat.h"',
                "#include <time.h>",
                "#include <pthread.h>",
                "#include <sched.h>",
                "#include <errno.h>",
                "#include <stdio.h>",
                "#include <string.h>",
                "#include <stdlib.h>",
                "",
                "typedef struct {",
                "    char key[160];",
                "    unsigned long long total_ns;",
                "    unsigned long long count;",
                "    unsigned long long max_ns;",
                "    unsigned long long min_ns;",
                "} stat_item;",
                "",
                "static stat_item *g_stats = NULL;",
                "static size_t g_cap = 0, g_sz = 0;",
                "static pthread_mutex_t g_mu = PTHREAD_MUTEX_INITIALIZER;",
                "static int g_dumped = 0;",
                "static FILE *g_trace_fp = NULL;",
                "static int g_trace_first = 1;",
                "",
                "void ta_set_priority(int prio) {",
                "    if (prio <= 0) return;",
                "    struct sched_param param; param.sched_priority = prio;",
                "    int ret = pthread_setschedparam(pthread_self(), SCHED_FIFO, &param);",
                "    (void)ret; // ignore failure if lacking permission",
                "}",
                "",
                "static void ensure_cap(void) {",
                "    if (g_sz < g_cap) return;",
                "    size_t nc = g_cap ? g_cap * 2 : 256;",
                "    stat_item *np = (stat_item*)realloc(g_stats, nc * sizeof(stat_item));",
                "    if (!np) exit(2);",
                "    for (size_t i = g_cap; i < nc; ++i) {",
                "        np[i].key[0] = 0;",
                "        np[i].total_ns = np[i].count = np[i].max_ns = 0;",
                "        np[i].min_ns = ~0ull;",
                "    }",
                "    g_stats = np; g_cap = nc;",
                "}",
                "",
                "uint64_t now_ns(void) {",
                "    struct timespec ts;",
                "    clock_gettime(CLOCK_MONOTONIC, &ts);",
                "    return (uint64_t)ts.tv_sec * 1000000000ull + (uint64_t)ts.tv_nsec;",
                "}",
                "",
                "static stat_item* get_slot(const char* key) {",
                "    for (size_t i = 0; i < g_sz; ++i) {",
                "        if (strcmp(g_stats[i].key, key) == 0) return &g_stats[i];",
                "    }",
                "    ensure_cap();",
                "    strncpy(g_stats[g_sz].key, key, sizeof(g_stats[g_sz].key) - 1);",
                "    g_stats[g_sz].key[sizeof(g_stats[g_sz].key) - 1] = 0;",
                "    g_stats[g_sz].total_ns = 0;",
                "    g_stats[g_sz].count = 0;",
                "    g_stats[g_sz].max_ns = 0;",
                "    g_stats[g_sz].min_ns = ~0ull;",
                "    return &g_stats[g_sz++];",
                "}",
                "",
                "static void trace_init_locked(void) {",
                "    if (g_trace_fp) return;",
                '    g_trace_fp = fopen("thread_trace.json", "w");',
                "    if (!g_trace_fp) return;",
                '    fputs(\"[\\n\", g_trace_fp);',
                "    g_trace_first = 1;",
                "}",
                "",
                "void time_trace(const char* key, uint64_t start_ns, uint64_t dur_ns) {",
                "    pthread_mutex_lock(&g_mu);",
                "    trace_init_locked();",
                "    if (g_trace_fp) {",
                "        if (!g_trace_first) fputs(\",\\n\", g_trace_fp);",
                "        g_trace_first = 0;",
                "        fprintf(",
                '            g_trace_fp, "  {\\"key\\": \\"%s\\", \\"start_ns\\": %llu, \\"dur_ns\\": %llu}",',
                "            key,",
                "            (unsigned long long)start_ns,",
                "            (unsigned long long)dur_ns",
                "        );",
                "    }",
                "    pthread_mutex_unlock(&g_mu);",
                "}",
                "",
                "void time_account(const char* key, uint64_t dur_ns) {",
                "    pthread_mutex_lock(&g_mu);",
                "    stat_item* s = get_slot(key);",
                "    s->total_ns += dur_ns;",
                "    s->count += 1;",
                "    if (dur_ns > s->max_ns) s->max_ns = dur_ns;",
                "    if (dur_ns < s->min_ns) s->min_ns = dur_ns;",
                "    pthread_mutex_unlock(&g_mu);",
                "}",
                "",
                "static void dump_json_locked(void) {",
                "    if (g_dumped) return;",
                "    g_dumped = 1;",
                '    FILE *fp = fopen("time_result.json", "w");',
                "    if (!fp) return;",
                '    fprintf(fp, "{\\n");',
                "    for (size_t i = 0; i < g_sz; ++i) {",
                "        unsigned long long avg = g_stats[i].count ? (g_stats[i].total_ns / g_stats[i].count) : 0ull;",
                '        fprintf(fp,',
                '            "  \\"%s\\": {\\"total_ns\\": %llu, \\"count\\": %llu, \\"avg_ns\\": %llu, \\"max_ns\\": %llu, \\"min_ns\\": %llu}%s\\n",',
                "            g_stats[i].key,",
                "            g_stats[i].total_ns,",
                "            g_stats[i].count,",
                "            avg,",
                "            g_stats[i].max_ns,",
                "            (g_stats[i].min_ns == ~0ull ? 0ull : g_stats[i].min_ns),",
                "            (i + 1 == g_sz) ? \"\" : \",\"",
                "        );",
                "    }",
                '    fprintf(fp, "}\\n");',
                "    fclose(fp);",
                "}",
                "",
                "static void dump_trace_locked(void) {",
                "    if (!g_trace_fp) return;",
                '    fputs(\"\\n]\\n\", g_trace_fp);',
                "    fclose(g_trace_fp);",
                "    g_trace_fp = NULL;",
                "}",
                "",
                "__attribute__((destructor))",
                "static void at_exit_dump(void) {",
                "    pthread_mutex_lock(&g_mu);",
                "    dump_json_locked();",
                "    dump_trace_locked();",
                "    pthread_mutex_unlock(&g_mu);",
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _copy_project(src_root: Path, dest_root: Path) -> Path:
    """复制整个项目目录到目标（覆盖已存在）。"""
    if dest_root.exists():
        shutil.rmtree(dest_root)
    shutil.copytree(src_root, dest_root, dirs_exist_ok=False, ignore=shutil.ignore_patterns("*.o", "*.so", "*.a", "__pycache__", "*.png", "*.dot"))
    return dest_root


def _inject_metrics(
    meta_path: Path,
    result_map: Dict[str, Dict],
    log: List[str],
    warnings: List[str],
    instrumented_keys: set,
) -> Dict[str, Dict[str, int]]:
    """将统计结果写回原始 mycalls_meta_internal.json，并返回线程汇总。"""
    try:
        data = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception as e:
        raise RuntimeError(f"无法读取 meta_json: {e}") from e

    thread_summary: Dict[str, Dict[str, int]] = {}

    def update_obj(obj: Dict, thread_name: Optional[str] = None):
        for k, v in obj.items():
            if not isinstance(v, dict):
                continue
            if {"file", "line"} <= set(v.keys()):
                # 优先使用原始键名（与 time_account 标签一致），兼容旧格式则回退到 func@file:line
                file_name = Path(str(v.get("file"))).name
                line_no = v.get("line")
                func = _infer_func_from_key(k, v)
                key_str = k
                metrics = result_map.get(key_str)
                if metrics is None:
                    key_str = f"{func}@{file_name}:{line_no}"
                    metrics = result_map.get(key_str)
                if metrics:
                    total = int(metrics.get("total_ns", 0))
                    count = int(metrics.get("count", 0))
                    v.update(
                        {
                            "total_ns": total,
                            "count": count,
                            "avg_ns": int(metrics.get("avg_ns", 0)),
                            "max_ns": int(metrics.get("max_ns", 0)),
                            "min_ns": int(metrics.get("min_ns", 0)),
                            "miss": False,
                            "executed": True,
                            "skip_reason": "",
                        }
                    )
                    # 顶层线程名累加
                    th = thread_name or k
                    thread_summary.setdefault(th, {"total_ns": 0, "count": 0})
                    thread_summary[th]["total_ns"] += total
                    thread_summary[th]["count"] += count
                else:
                    if key_str in instrumented_keys:
                        # 已插桩但未执行
                        v.update(
                            {
                                "total_ns": 0,
                                "count": 0,
                                "avg_ns": 0,
                                "max_ns": 0,
                                "min_ns": 0,
                                "miss": True,
                                "executed": False,
                                "skip_reason": "",
                            }
                        )
                    else:
                        # 未插桩（如文件缺失或非C文件）
                        v.update(
                            {
                                "total_ns": 0,
                                "count": 0,
                                "avg_ns": 0,
                                "max_ns": 0,
                                "min_ns": 0,
                                "miss": True,
                                "executed": False,
                                "skip_reason": v.get("skip_reason", "not_instrumented"),
                            }
                        )
                    # 汇总仅统计 miss=False 的条目，因此这里不累加
            else:
                next_thread = thread_name if thread_name is not None else k
                update_obj(v, thread_name=next_thread)

    update_obj(data, thread_name=None)
    meta_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.append(f"[meta] 回写 {meta_path}")
    return thread_summary


def _compile_project(dest_root: Path, log: List[str]) -> Path:
    """编译 instrumented 项目，返回可执行文件路径。"""
    sources = sorted(str(p) for p in dest_root.rglob("*.c"))
    if not sources:
        raise RuntimeError("未找到任何 .c 文件用于编译")
    cmd = ["gcc", "-O2", "-std=c11", "-pthread", "-I.", "-Iinclude", "-o", "app", *sources, "-lm", "-ldl"]
    log.append(f"[build] {' '.join(cmd)}")
    proc = subprocess.run(cmd, cwd=str(dest_root), capture_output=True, text=True)
    if proc.returncode != 0:
        err = proc.stderr[-200:]
        raise RuntimeError(f"编译失败：{proc.returncode}\n{err}")
    return dest_root / "app"


def _run_app(app_path: Path, log: List[str]) -> None:
    proc = subprocess.run([str(app_path)], cwd=str(app_path.parent), capture_output=True, text=True)
    log.append(f"[run] exit={proc.returncode}")
    if proc.stdout:
        log.append(f"[stdout]\n{proc.stdout}")
    if proc.stderr:
        log.append(f"[stderr]\n{proc.stderr}")
    if proc.returncode != 0:
        raise RuntimeError(f"程序运行失败，退出码 {proc.returncode}")


def _parse_dot_edges_simple(dot_path: Path) -> Tuple[Iterable[str], List[Tuple[str, str]]]:
    """极简解析 DOT，返回节点集合与边列表。"""
    text = dot_path.read_text(encoding="utf-8", errors="replace")
    edges = _EDGE_RE.findall(text)
    nodes = set()
    for u, v in edges:
        nodes.add(u)
        nodes.add(v)
    for name in _NODE_QUOTED_RE.findall(text):
        nodes.add(name)
    nodes.discard("callgraph")
    return nodes, [(u, v) for u, v in edges]


def _render_weighted_dot(
    nodes: Iterable[str],
    edges: Iterable[Tuple[str, str]],
    weights: Dict[str, int],
    *,
    priorities: Optional[Mapping[str, int]] = None,
) -> str:
    """生成只包含节点/边/权重的简化 DOT，可选附加 prio 行。"""
    lines: List[str] = []
    lines.append("digraph callgraph {")
    lines.append('  node [shape=box, style="rounded,filled", fontname="Consolas", fontsize=10, fillcolor="#F6F6F6"];')
    for n in sorted(nodes):
        w = int(weights.get(n, 0) or 0)
        if priorities is not None:
            label = f"{n}\\n{w} ns\\nprio={int(priorities.get(n, 0) or 0)}"
        else:
            label = f"{n}\\n{w} ns"
        lines.append(f'  "{n}" [label="{label}"];')
    for u, v in edges:
        lines.append(f'  "{u}" -> "{v}";')
    lines.append("}")
    return "\n".join(lines) + "\n"


def _write_metrics(
    result_map: Dict[str, Dict],
    thread_summary_path: Path,
    output_dir: Path,
    *,
    filename: str = "metrics.json",
) -> Path:
    """生成指标文件：program_total_ns（节点 total_ns 求和）+ 线程汇总。"""
    program_total_ns = sum(int(v.get("total_ns", 0) or 0) for v in result_map.values() if isinstance(v, dict))
    thread_summary: Dict[str, Dict] = {}
    if thread_summary_path.exists():
        thread_summary = json.loads(thread_summary_path.read_text(encoding="utf-8"))
    # 若线程汇总缺失，按 callsite 前缀聚合
    if not thread_summary:
        agg: Dict[str, Dict[str, int]] = {}
        for k, v in result_map.items():
            if not isinstance(v, dict):
                continue
            thread = k.split("/", 1)[0] if "/" in k else k
            agg.setdefault(thread, {"total_ns": 0, "count": 0})
            agg[thread]["total_ns"] += int(v.get("total_ns", 0) or 0)
            agg[thread]["count"] += int(v.get("count", 0) or 0)
        thread_summary = agg

    metrics = {
        "program_total_ns": int(program_total_ns),
        "thread_time_ns": {
            t: {
                "total_ns": int(info.get("total_ns", 0) or 0),
                "count": int(info.get("count", 0) or 0),
                "avg_ns": int(info.get("total_ns", 0) or 0) // max(1, int(info.get("count", 0) or 0)),
            }
            for t, info in thread_summary.items()
            if isinstance(info, dict)
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / filename
    out_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def run_time_analysis(
    source_file: Path,
    meta_json: Path,
    base_dir: Path,
    priorities: Optional[Mapping[str, int]] = None,
    *,
    cpc_mode: bool = False,
) -> InstrumentResult:
    """对项目目录执行时间分析插桩+编译+运行。"""
    if not source_file.exists():
        raise FileNotFoundError(f"源文件不存在: {source_file}")
    if not meta_json.exists():
        raise FileNotFoundError(f"未找到 JSON: {meta_json}")

    base_dir = base_dir.resolve()
    src_root = source_file.resolve().parent
    base_name = _infer_base_name_from_meta(meta_json, base_dir) or source_file.stem
    ta_dir_name = "时间分析_cpc" if cpc_mode else "时间分析"
    output_root = base_dir / "中间结果" / base_name / ta_dir_name
    log_file_name = "time_analysis_cpc.log" if cpc_mode else "time_analysis.log"
    log_path = base_dir / "中间结果" / base_name / "生成dag图" / "debug" / log_file_name
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log: List[str] = []
    warnings: List[str] = []
    skipped: List[str] = []
    analysis_error: Optional[str] = None

    dest_project: Optional[Path] = None
    app_path: Optional[Path] = None
    result_json: Optional[Path] = None
    prio_result_json: Optional[Path] = None
    prio_weighted_dot: Optional[Path] = None
    metrics_json: Optional[Path] = None
    instrumented_files: List[Path] = []

    try:
        # 1) 复制项目
        dest_project = output_root / src_root.name
        _copy_project(src_root, dest_project)
        log.append(f"[copy] {src_root} -> {dest_project}")

        # 2) 拷贝 runtime
        _write_time_stat(dest_project)
        log.append("[runtime] 写入 time_stat.c/h")

        # 3) 读取 JSON
        sites = load_call_sites(meta_json)
        if not sites:
            raise RuntimeError("JSON 中未找到有效调用点")
        # 按文件分组
        by_file: Dict[Path, List[CallSite]] = {}
        for s in sites:
            by_file.setdefault(s.file, []).append(s)

        instrumented_keys_all: List[str] = []
        supported_suffixes = {".c"}  # 当前仅支持 C；C++ 需另行实现

        for rel_path, file_sites in by_file.items():
            # meta 中的 file 可能是绝对路径（例如 PX4 工程），此处做最小映射：
            # 优先按 basename 映射到复制后的项目目录内同名文件。
            if rel_path.is_absolute():
                candidate = dest_project / rel_path.name
                target_file = candidate if candidate.exists() else (dest_project / rel_path)
            else:
                target_file = dest_project / rel_path

            if not target_file.exists():
                warnings.append(f"[warn] 未找到文件 {rel_path}，跳过 {len(file_sites)} 个调用点")
                continue
            if target_file.suffix.lower() not in supported_suffixes:
                skipped.append(f"[skip] 非 C 文件 {target_file} (from {rel_path})")
                continue

            new_lines, w, inst_keys = instrument_file(target_file, file_sites, log)
            warnings.extend(w)
            instrumented_keys_all.extend(inst_keys)
            target_file.write_text("".join(new_lines), encoding="utf-8")
            instrumented_files.append(target_file)

        if not instrumented_files:
            raise RuntimeError("未对任何文件完成插桩：当前仅支持 .c，且 meta_json 的 file 需能映射到项目内源码。")

        # 4) 编译 & 运行
        app_path = _compile_project(dest_project, log)
        _run_app(app_path, log)

        result_json = dest_project / "time_result.json"
        if not result_json.exists():
            raise RuntimeError("未找到 time_result.json（程序未正常输出）")

        # 将统计结果回写到原始 meta_json
        try:
            result_map = json.loads(result_json.read_text(encoding="utf-8"))
            if priorities:
                prio_map: Dict[str, Dict] = {}
                for k, v in result_map.items():
                    if isinstance(v, dict):
                        v = dict(v)
                        v["priority"] = int(priorities.get(k, 0) or 0)
                        prio_map[k] = v
                prio_result_json = result_json.parent / "time_result_prio.json"
                prio_result_json.write_text(json.dumps(prio_map, ensure_ascii=False, indent=2), encoding="utf-8")
                log.append(f"[prio] 写入 {prio_result_json}")
            summary = _inject_metrics(meta_json, result_map, log, warnings, set(instrumented_keys_all))
            # 写线程汇总
            if summary:
                summary_path = meta_json.parent / "thread_time_summary.json"
                summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
                log.append(f"[summary] 线程耗时汇总 -> {summary_path}")
            log.append(f"[update] 已回写统计到 {meta_json}")
            # 指标文件：节点 total_ns 求和 + 线程汇总
            try:
                metrics_json = _write_metrics(
                    result_map,
                    meta_json.parent / "thread_time_summary.json",
                    result_json.parent,
                    filename="metrics_prio.json" if priorities else "metrics.json",
                )
                log.append(f"[metrics] -> {metrics_json}")
            except Exception as me:
                warnings.append(f"[warn] 写指标文件失败: {me}")
            # 生成带权 DAG（节点标签附 total_ns），存放在 time_result 同目录
            try:
                weights = {k: int(v.get("total_ns", 0) or 0) for k, v in result_map.items() if isinstance(v, dict)}
                dag_path = base_dir / "中间结果" / base_name / "生成dag图" / "dag.dot"
                if dag_path.exists():
                    nodes, edges = _parse_dot_edges_simple(dag_path)
                    weighted_text = _render_weighted_dot(nodes, edges, weights)
                    weighted_path = result_json.parent / "dag_weighted.dot"
                    weighted_path.write_text(weighted_text, encoding="utf-8")
                    log.append(f"[weighted_dag] {dag_path} + time_result -> {weighted_path}")
                    if priorities:
                        weighted_prio_text = _render_weighted_dot(nodes, edges, weights, priorities=priorities)
                        prio_weighted_dot = result_json.parent / "dag_weighted_prio.dot"
                        prio_weighted_dot.write_text(weighted_prio_text, encoding="utf-8")
                        log.append(f"[weighted_dag_prio] -> {prio_weighted_dot}")
                else:
                    warnings.append(f"[warn] 未找到原始 dag.dot（{dag_path}），跳过生成带权 DAG")
            except Exception as gen_err:
                warnings.append(f"[warn] 生成带权 DAG 失败: {gen_err}")
        except Exception as e:  # pragma: no cover - 保底
            warnings.append(f"[warn] 回写统计失败: {e}")

        return InstrumentResult(
            instrumented_dir=output_root,
            app_path=app_path,
            result_json=result_json,
            prio_result_json=prio_result_json,
            prio_weighted_dot=prio_weighted_dot,
            metrics_json=metrics_json,
            log_path=log_path,
            instrumented_files=instrumented_files,
            warnings=warnings,
            skipped=skipped,
        )
    except Exception as e:
        analysis_error = str(e)
        raise
    finally:
        # 写日志（无论成功失败都落盘）
        log_content = "\n".join(log + warnings + skipped + ([f"[error] {analysis_error}"] if analysis_error else []))
        log_path.write_text(log_content, encoding="utf-8")
