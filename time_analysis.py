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
from typing import Dict, Iterable, List, Optional, Tuple


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
    log_path: Path
    instrumented_files: List[Path]
    warnings: List[str]
    skipped: List[str]


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
    for i, ln in enumerate(lines):
        stripped = ln.strip()
        if not stripped or stripped.startswith(("//", "/*", "*", "#!")):
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


def _already_instrumented(lines: List[str], start_idx: int) -> bool:
    window = []
    for i in range(max(0, start_idx - 2), min(len(lines), start_idx + 3)):
        window.append(lines[i])
    joined = "\n".join(window)
    return "TA_BEGIN" in joined or "TA_END" in joined


def instrument_file(
    file_path: Path,
    sites: List[CallSite],
    log: List[str],
) -> Tuple[List[str], List[str]]:
    """对单个文件插桩，返回修改后的行、警告列表。"""
    lines = file_path.read_text(encoding="utf-8").splitlines(keepends=True)
    lines, added_include, include_added = _ensure_include(lines)
    if added_include:
        log.append(f"[include] {file_path} 插入 time_stat.h")
    warnings: List[str] = []

    # 按行号降序，避免前面插入影响后续定位
    seq = 1
    base_offset = include_added  # include 插入行数，统一偏移
    for site in sorted(sites, key=lambda s: (s.line, s.col or 0), reverse=True):
        start_idx = site.line - 1 + base_offset
        if start_idx < 0 or start_idx >= len(lines):
            warnings.append(f"[miss] {file_path}:{site.line} 越界，跳过 {site.func}")
            continue
        if _already_instrumented(lines, start_idx):
            log.append(f"[skip] {file_path}:{site.line} 已有 TA 标记，跳过")
            continue

        stmt_end = _find_stmt_end(lines, start_idx)
        if stmt_end is None:
            warnings.append(f"[warn] {file_path}:{site.line} 未找到语句结束，跳过 {site.func}")
            continue

        snippet = "".join(lines[start_idx : stmt_end + 1])
        if _is_control_statement(snippet) or _has_assignment(snippet) or _has_question(snippet):
            warnings.append(f"[warn] {file_path}:{site.line} 复杂语句（if/赋值/?:），跳过 {site.func}")
            continue

        var_name = _sanitize_var_name(file_path.name.replace(".", "_"), site.line, seq)
        seq += 1
        key_str = f'{site.func}@{file_path.name}:{site.line}'
        begin_lines = [
            f"// TA_BEGIN: {file_path.name}:{site.line} {site.func}\n",
            "do {\n",
            f"uint64_t {var_name} = now_ns();\n",
        ]
        end_lines = [
            f"// TA_END: {file_path.name}:{site.line} {site.func}\n",
            f'time_account("{key_str}", now_ns() - {var_name});\n',
            "} while (0);\n",
        ]

        # 插入：先 BEGIN，再 END（END 位置需 +2 偏移）
        lines[start_idx:start_idx] = begin_lines
        stmt_end += len(begin_lines)
        end_insert_at = stmt_end + 1
        lines[end_insert_at:end_insert_at] = end_lines
        log.append(f"[ok] {file_path}:{site.line} {site.func}")

    return lines, warnings


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
                "static void dump_json(void) {",
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
                "__attribute__((destructor))",
                "static void at_exit_dump(void) { dump_json(); }",
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


def run_time_analysis(source_file: Path, meta_json: Path, base_dir: Path) -> InstrumentResult:
    """对项目目录执行时间分析插桩+编译+运行。"""
    if not source_file.exists():
        raise FileNotFoundError(f"源文件不存在: {source_file}")
    if not meta_json.exists():
        raise FileNotFoundError(f"未找到 JSON: {meta_json}")

    base_dir = base_dir.resolve()
    src_root = source_file.resolve().parent
    base_name = source_file.stem
    output_root = base_dir / "中间结果" / base_name / "时间分析"
    log_path = base_dir / "中间结果" / base_name / "生成dag图" / "debug" / "time_analysis.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    log: List[str] = []
    warnings: List[str] = []
    skipped: List[str] = []

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

    instrumented_files: List[Path] = []
    for rel_path, file_sites in by_file.items():
        target_file = dest_project / rel_path
        if not target_file.exists():
            warnings.append(f"[warn] 未找到文件 {rel_path}，跳过 {len(file_sites)} 个调用点")
            continue
        if target_file.suffix.lower() != ".c":
            skipped.append(f"[skip] 非 C 文件 {rel_path}")
            continue
        new_lines, w = instrument_file(target_file, file_sites, log)
        warnings.extend(w)
        target_file.write_text("".join(new_lines), encoding="utf-8")
        instrumented_files.append(target_file)

    if not instrumented_files:
        raise RuntimeError("未对任何文件完成插桩，请检查 JSON 与源代码路径")

    # 4) 编译 & 运行
    app_path = _compile_project(dest_project, log)
    _run_app(app_path, log)

    result_json = dest_project / "time_result.json"
    if not result_json.exists():
        raise RuntimeError("未找到 time_result.json（程序未正常输出）")

    # 写日志
    log_content = "\n".join(log + warnings + skipped)
    log_path.write_text(log_content, encoding="utf-8")

    return InstrumentResult(
        instrumented_dir=output_root,
        app_path=app_path,
        result_json=result_json,
        log_path=log_path,
        instrumented_files=instrumented_files,
        warnings=warnings,
        skipped=skipped,
    )
