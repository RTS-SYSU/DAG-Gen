# -*- coding: utf-8 -*-
# !/usr/bin/python
#
#  Copyright 2018, Eelco Chaudron
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
#  Files name:
#    mkcg.py
#
#  Description:
#    Make callgraph .dot file from GCC's rtl data
#
#  Author:
#    Eelco Chaudron
#
#  Initial Created:
#    29 March 2018
#
#  Notes:
#

#
# Imports
#
import argparse
import copy
import fileinput
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

from .thread_map import resolve_join_edges, collect_thread_edges

#
# Unit tests for the dump_path() function.
# Invoke as: cally.py --unit-test dummy
#
# - Add --unit-test option
#
#
#   Main -> A --> B --> C --> D
#           A        |_ [E]
#                    |_  F
#                    |_  G --> B
#
# \_  H --> I --> J --> D
#
#
#
#

unit_test_full_dump_output = [
    'strict digraph callgraph {',
    '"A" -> "A";', '"A" -> "B";',
    '"B" -> "C";', '"B" -> "E";',
    '"E" [style=dashed]', '"B" -> "F";',
    '"B" -> "G";', '"B" -> "H";',
    '"C" -> "D";', '"D"', '"F"',
    '"G" -> "B";', '"H" -> "I";',
    '"I" -> "J";', '"J" -> "D";',
    '"main" -> "A";',
    '}'
]
unit_test_full_caller_output = [
    '"A" -> "A";',
    '"A" -> "B" -> "H" -> "I" -> "J" -> "D";',
    '"A" -> "B" -> "C" -> "D";',
    '"A" -> "B" -> "E";\n"E" [style=dashed];',
    '"A" -> "B" -> "G" -> "B";',
    '"A" -> "B" -> "F";'
]
unit_test_noexterns_caller_output = [
    '"A" -> "A";',
    '"A" -> "B" -> "H" -> "I" -> "J" -> "D";',
    '"A" -> "B" -> "C" -> "D";',
    '"B" [color=red];',
    '"A" -> "B" -> "G" -> "B";',
    '"A" -> "B" -> "F";'
]
unit_test_maxdepth2_caller_output = [
    '"A" -> "A";',
    '"A" -> "B";\n"B" [color=red];',
    '"A" -> "B";\n"B" [color=red];',
    '"B" [color=red];',
    '"A" -> "B";\n"B" [color=red];',
    '"A" -> "B";\n"B" [color=red];'
]
unit_test_maxdepth3_caller_output = [
    '"A" -> "A";',
    '"A" -> "B" -> "H";\n"H" [color=red];',
    '"A" -> "B" -> "C";\n"C" [color=red];',
    '"A" -> "B" -> "E";\n"E" [style=dashed];',
    '"A" -> "B" -> "G";\n"G" [color=red];',
    '"A" -> "B" -> "F";'
]
unit_test_regex_caller_output = [
    '"A" -> "A";', '"A" -> "B" -> "H" -> "I" -> "J" -> "D";',
    '"A" -> "B";\n"B" [color=red];',
    '"B" [color=red];',
    '"A" -> "B";\n"B" [color=red];',
    '"A" -> "B" -> "F";']
unit_test_full_callee_output = [
    '"A" -> "A" -> "B";', '"main" -> "A" -> "B";', '"B" -> "G" -> "B";'
]
unit_test_maxdepth4_callee_output = [
    '"A" -> "A" -> "B" -> "C" -> "D";',
    '"A" -> "B" -> "C" -> "D";\n"A" [color=red];',
    '"G" -> "B" -> "C" -> "D";\n"G" [color=red];',
    '"H" -> "I" -> "J" -> "D";\n"H" [color=red];'
]
unit_test_maxdepth5_callee_output = [
    '"A" -> "A" -> "B" -> "C" -> "D";', '"main" -> "A" -> "B" -> "C" -> "D";',
    '"B" -> "G" -> "B" -> "C" -> "D";', '"B" -> "H" -> "I" -> "J" -> "D";'
]


#
# Actual unit test
#
def unit_test():
    #
    # Built test functions dictionary
    #
    functions = dict()
    unit_test_add_call(functions, "main", ["A"])
    unit_test_add_call(functions, "A", ["A", "B"])
    unit_test_add_call(functions, "B", ["C", "E", "F", "G", "H"])
    unit_test_add_call(functions, "C", ["D"])
    unit_test_add_call(functions, "D", [])
    # "E" does not exists, it's an external function
    unit_test_add_call(functions, "F", [])
    unit_test_add_call(functions, "G", ["B"])
    unit_test_add_call(functions, "H", ["I"])
    unit_test_add_call(functions, "I", ["J"])
    unit_test_add_call(functions, "J", ["D"])

    build_callee_info(functions)

    #
    # Execute unit tests
    #
    print_dbg("UNIT TEST START")
    print_dbg("---------------")

    total = 0
    failures = 0

    #
    # Full graph dump
    #
    print_dbg("")
    print_dbg("FULL GRAPH")
    print_dbg("============")
    total += 1
    buffer = list()
    full_call_graph(functions, stdio_buffer=buffer)
    failures += unit_test_check_error("FULL GRAPH",
                                      unit_test_full_dump_output, buffer)
    #
    # Full caller dump
    #
    print_dbg("")
    print_dbg("FULL CALLER")
    print_dbg("===========")
    total += 1
    buffer = list()
    dump_path([], functions, "A",
              max_depth=0,
              exclude=None,
              no_externs=False,
              stdio_buffer=buffer)
    failures += unit_test_check_error("FULL CALLER",
                                      unit_test_full_caller_output, buffer)
    #
    # Full caller dump with no exters
    #
    print_dbg("")
    print_dbg("CALLER NO EXTERNS")
    print_dbg("=================")
    total += 1
    buffer = list()
    dump_path([], functions, "A",
              max_depth=0,
              exclude=None,
              no_externs=True,
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLER, NO_EXTERNS",
                                      unit_test_noexterns_caller_output,
                                      buffer)
    #
    # Caller with limit depth
    #
    print_dbg("")
    print_dbg("CALLER LIMITED DEPTH (2)")
    print_dbg("========================")
    total += 1
    buffer = list()
    dump_path([], functions, "A",
              max_depth=2,
              exclude=None,
              no_externs=False,
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLER, MAX DEPTH 2",
                                      unit_test_maxdepth2_caller_output,
                                      buffer)

    print_dbg("")
    print_dbg("CALLER LIMITED DEPTH (3)")
    print_dbg("========================")
    total += 1
    buffer = list()
    dump_path([], functions, "A",
              max_depth=3,
              exclude=None,
              no_externs=False,
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLER, MAX DEPTH 3",
                                      unit_test_maxdepth3_caller_output,
                                      buffer)
    #
    # Caller with limited by regex
    #
    print_dbg("")
    print_dbg("CALLER REGEX MATCH")
    print_dbg("==================")
    total += 1
    buffer = list()
    dump_path([], functions, "A",
              max_depth=0,
              exclude="C|E|G",
              no_externs=False,
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLER, REGEX",
                                      unit_test_regex_caller_output,
                                      buffer)
    #
    # Full callee
    #
    print_dbg("")
    print_dbg("CALLEE FULL")
    print_dbg("===========")
    total += 1
    buffer = list()
    dump_path([], functions, "B",
              max_depth=0,
              reverse_path=True,
              exclude=None,
              call_index="callee_calls",
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLEE, FULL",
                                      unit_test_full_callee_output,
                                      buffer)
    #
    # Max depth callee
    #
    print_dbg("")
    print_dbg("CALLEE MAX DEPTH 4")
    print_dbg("==================")
    total += 1
    buffer = list()
    dump_path([], functions, "D",
              max_depth=4,
              reverse_path=True,
              exclude=None,
              call_index="callee_calls",
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLEE, MAX DEPTH 4",
                                      unit_test_maxdepth4_callee_output,
                                      buffer)
    print_dbg("")
    print_dbg("CALLEE MAX DEPTH 5")
    print_dbg("==================")
    total += 1
    buffer = list()
    dump_path([], functions, "D",
              max_depth=5,
              reverse_path=True,
              exclude=None,
              call_index="callee_calls",
              stdio_buffer=buffer)
    failures += unit_test_check_error("CALLEE, MAX DEPTH 5",
                                      unit_test_maxdepth5_callee_output,
                                      buffer)
    #
    # Show results
    #
    print_dbg("")
    print_dbg("UNIT TEST END, RESULTS")
    print_dbg("----------------------")
    print_dbg("Total tests run: {}".format(total))
    print_dbg("Total errors   : {}".format(failures))
    if failures > 0:
        print_err("!!! ERRORS WHERE FOUND !!!")

    return 0


#
# unit_test_check_error()
#
def unit_test_check_error(test, ref, results):
    if len(results) == len(ref):
        for i in range(0, len(results)):
            if results[i] != ref[i]:
                print_err("[FAIL] \"{}\" @line {}, \"{}\" vs \"{}\"".
                          format(test, i, results[i], ref[i]))
                return 1
    else:
        print_err("[FAIL] {}".format(test))
        return 1

    return 0


#
# unit_test_add_call
#
def unit_test_add_call(functions, function_name, calls):
    if function_name in functions:
        print("ERROR: Function already defined!!")

    functions[function_name] = dict()
    functions[function_name]["files"] = ["unit_test.c"]
    functions[function_name]["calls"] = dict()
    for call in calls:
        functions[function_name]["calls"][call] = True
    functions[function_name]["refs"] = dict()
    functions[function_name]["callee_calls"] = dict()
    functions[function_name]["callee_refs"] = dict()
    functions[function_name]["mycalls"] = []
    functions[function_name]["myinfo"] = {"tail": function_name}


#
# Add callee to database
#


def build_callee_info(function_db):
    for call, value in function_db.items():
        for callee in value["calls"]:
            if callee in function_db and \
                    call not in function_db[callee]["callee_calls"]:
                function_db[callee]["callee_calls"][call] = 1

        for callee in value["refs"]:
            if callee in function_db and \
                    call not in function_db[callee]["callee_refs"]:
                function_db[callee]["callee_refs"][call] = 1


#
# dump_path_ascii()
#
def dump_path_ascii(path, reverse, **kwargs):
    externs = kwargs.get("externs", False)
    truncated = kwargs.get("truncated", False)
    std_buf = kwargs.get("stdio_buffer", None)

    if len(path) == 0:
        return

    ascii_path = ""
    for function in reversed(path) if reverse else path:
        if ascii_path != "":
            ascii_path += " -> "
        ascii_path += '"' + function + '"'

    if truncated or externs:
        ascii_path += ';\n"{}"{}{}'. \
            format(function if not reverse else path[-1],
                   " [style=dashed]" if externs else "",
                   " [color=red]" if truncated else "")

    print_buf(std_buf, ascii_path + ";")


#
# Dump path as ASCII to stdout
#
def dump_path(path, functions, function_name, **kwargs):
    max_depth = kwargs.get("max_depth", 0)
    reverse_path = kwargs.get("reverse_path", False)
    exclude = kwargs.get("exclude", None)
    call_index = kwargs.get("call_index", "calls")
    no_externs = kwargs.get("no_externs", False)
    std_buf = kwargs.get("stdio_buffer", None)

    #
    # Pass on __seen_in_path as a way to determine if a node in the graph
    # was already processed
    #
    if "__seen_in_path" in kwargs:
        seen_in_path = kwargs["__seen_in_path"]
    else:
        seen_in_path = dict()
        kwargs["__seen_in_path"] = seen_in_path

    #
    # If reached the max depth or need to stop due to exclusion, recursion
    # display the path up till the previous entry.
    #
    if (exclude is not None and re.match(exclude, function_name) is not None) \
            or (max_depth > 0 and len(path) >= max_depth):
        dump_path_ascii(path, reverse_path, stdio_buffer=std_buf,
                        truncated=True)
        return

    #
    # If already seen, we need to terminate the path here...
    #
    if function_name in seen_in_path:
        if (max_depth <= 0 or (len(path) + 1) <= max_depth):
            dump_path_ascii(path + [function_name], reverse_path,
                            stdio_buffer=std_buf)
        return

    seen_in_path[function_name] = True

    #
    # Now walk the path for each child
    #
    children = 0
    for caller in functions[function_name][call_index]:
        #
        # The child is a known function, handle this trough recursion
        #
        if caller in functions:
            children += 1
            if function_name != caller:
                dump_path(path + [function_name],
                          functions, caller, **kwargs)
            else:
                #
                # This is a recurrence for this function, add it once
                #
                dump_path_ascii(path + [function_name, caller], reverse_path,
                                stdio_buffer=std_buf)

        #
        # This is a external child, so we can not handle this recursive.
        # However as there are no more children, we can handle it here
        # (if it can be included).
        #
        elif (exclude is None or re.match(exclude, caller) is None) and \
                (max_depth <= 0 or (len(path) + 2) <= max_depth) and \
                not no_externs:
            children += 1
            dump_path_ascii(path + [function_name, caller], reverse_path,
                            externs=True, stdio_buffer=std_buf)
        else:
            print_buf(std_buf, '"{}" [color=red];'.
                      format(function_name))

    #
    # If there where no children, the path ends here, so dump it.
    #
    if children == 0:
        dump_path_ascii(path + [function_name], reverse_path,
                        stdio_buffer=std_buf)


#
# print_err()
#
def print_err(text):
    sys.stderr.write(text + "\n")


#
# print_dbg()
#
def print_dbg(text):
    sys.stderr.write("DBG: " + text + "\n")


#
# print_buf()
#
def print_buf(buf, text):
    if buf is not None:
        buf.append(text)
    print(text)


def _derive_debug_base(path: Path) -> str:
    name = path.name
    base = name.split(".c", 1)[0] if ".c" in name else path.stem
    parent = path.parent.name if path.parent.name else ""
    if parent and parent not in (".", ""):
        return f"{parent}_{base}"
    return base


def _ensure_debug_dir(config) -> Path:
    """确保debug目录存在（用于中间结果和调试信息）"""
    try:
        first_file = getattr(config, "RTLFILE", [None])[0]
    except Exception:
        first_file = None

    if first_file:
        first_path = Path(first_file)
        # 在输入文件所在目录下创建debug文件夹
        debug_dir = first_path.parent / "debug"
    else:
        # 如果没有输入文件，使用当前工作目录
        debug_dir = Path.cwd() / "debug"

    debug_dir.mkdir(parents=True, exist_ok=True)
    return debug_dir


def _ensure_output_dirs(config) -> Tuple[Path, Path]:
    """
    确保输出目录结构存在（三阶段划分）
    
    阶段1 - 输入：从任意位置读取源文件和expand文件
    阶段2 - 中间结果：程序执行过程中的所有临时文件
    阶段3 - 配置文件：为dag_describe提供的最终输出
    
    返回: (config_dir, intermediate_dir)
    - config_dir: 配置文件目录（最终输出，供dag_describe使用）
    - intermediate_dir: 中间结果目录（处理过程中的临时文件）
    
    配置文件目录结构（阶段3 - 扁平化结构，参考test/配置文件/）：
    mycallypro/配置文件/<basename>/
    ├── circle.txt        # 主配置文件
    ├── <basename>.dot    # DAG图文件
    ├── <basename>.c      # 源代码副本（可选）
    └── <basename>.c.233r.expand  # expand文件副本（可选）
    
    中间结果目录结构（阶段2 - 临时文件）：
    mycallypro/中间结果/<basename>/
    ├── debug/            # 调试JSON文件
    ├── temp/             # 临时DOT文件
    ├── images/           # PNG图片
    └── logs/             # 日志文件
    
    冗余处理模式（混合模式）：
    1. 默认模式：直接覆盖已存在的目录和文件
    2. --smart：智能检测，如果输入文件未修改则跳过重新生成
    3. --clean：清理重建，删除旧目录后重新创建
    4. --force：强制重新生成（与--smart配合使用）
    """
    import shutil
    
    try:
        first_file = getattr(config, "RTLFILE", [None])[0]
    except Exception:
        first_file = None
    
    # 获取基础名称（从expand文件名提取）
    if first_file:
        first_path = Path(first_file)
        # 去除.expand后缀，提取基础名
        base_name = first_path.stem
        if base_name.endswith('.233r'):
            base_name = base_name[:-5]
        # 统一去掉后续的 .cpp/.c 等扩展，避免目录名残留 .cpp
        if '.' in base_name:
            base_name = base_name.split('.')[0]
        
        # 基于mycallypro目录
        if hasattr(config, 'output_base') and config.output_base:
            root = Path(config.output_base).resolve()
        else:
            # 默认使用mycallypro目录
            root = Path(__file__).parent
    else:
        base_name = "default"
        root = Path(__file__).parent
    
    # 配置文件目录：mycallypro/配置文件/basename/（阶段3 - 扁平化结构）
    config_dir = root / "配置文件" / base_name
    
    # 中间结果目录：mycallypro/中间结果/basename/（阶段2 - 临时文件）
    intermediate_dir = root / "中间结果" / base_name
    
    # ========================================================================
    # 冗余处理逻辑（混合模式）
    # ========================================================================
    smart_mode = getattr(config, 'smart', False)
    clean_mode = getattr(config, 'clean', False)
    force_mode = getattr(config, 'force', False)
    
    # 模式1：清理重建模式（--clean）- 只在第一次调用时清理
    if clean_mode and not getattr(config, '_cleaned', False):
        if config_dir.exists():
            if hasattr(config, 'debug') and config.debug:
                print_dbg(f"[CLEAN] Removing existing config directory: {config_dir}")
            shutil.rmtree(config_dir)
        if intermediate_dir.exists():
            if hasattr(config, 'debug') and config.debug:
                print_dbg(f"[CLEAN] Removing existing intermediate directory: {intermediate_dir}")
            shutil.rmtree(intermediate_dir)
        # 标记已清理，避免重复清理
        config._cleaned = True
    
    # 模式2：智能检测模式（--smart）
    elif smart_mode and not force_mode:
        if config_dir.exists() and first_file:
            # 检查输入文件是否被修改
            input_file = Path(first_file)
            circle_txt = config_dir / "circle.txt"
            
            if circle_txt.exists():
                input_mtime = input_file.stat().st_mtime
                output_mtime = circle_txt.stat().st_mtime
                
                # 如果输入文件没有新于输出文件，跳过重新生成
                if input_mtime <= output_mtime:
                    if hasattr(config, 'debug') and config.debug:
                        print_dbg(f"[SMART] Skipping regeneration, files are up-to-date")
                        print_dbg(f"  Input: {input_file} (modified: {input_mtime})")
                        print_dbg(f"  Output: {circle_txt} (modified: {output_mtime})")
                    # 设置一个标志，告诉调用者跳过后续生成
                    config._skip_generation = True
                    return config_dir, intermediate_dir
    
    # 模式3：默认覆盖模式（无额外参数）
    # 直接创建目录，如果已存在则保持，文件会被后续操作覆盖
    
    # 创建配置文件目录
    config_dir.mkdir(parents=True, exist_ok=True)
    
    # 创建中间结果目录及子目录
    intermediate_dir.mkdir(parents=True, exist_ok=True)
    (intermediate_dir / "debug").mkdir(parents=True, exist_ok=True)
    (intermediate_dir / "temp").mkdir(parents=True, exist_ok=True)
    (intermediate_dir / "images").mkdir(parents=True, exist_ok=True)
    (intermediate_dir / "logs").mkdir(parents=True, exist_ok=True)
    
    return config_dir, intermediate_dir


def _write_debug_text(config, tag: str, content: str, suffix: str, *, timestamp: Optional[str] = None) -> None:
    """写入调试文本文件到中间结果目录（阶段2 - 临时文件）"""
    # 所有debug文件都应该存储在中间结果目录
    if hasattr(config, '_intermediate_dir'):
        debug_dir = config._intermediate_dir / "debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
    else:
        debug_dir = _ensure_debug_dir(config)
    
    ts = timestamp or datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    path = debug_dir / f"{ts}_{tag}.{suffix}"
    try:
        path.write_text(content, encoding="utf-8")
    except Exception:
        pass


def _dump_debug_snapshot(config, tag: str, payload: dict) -> None:
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception:
        return
    _write_debug_text(config, tag, text, "json")


def _dump_debug_artifacts(functions, dot_lines, config, tag):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    _write_debug_text(config, tag, "\n".join(dot_lines), "dot", timestamp=timestamp)
    payload = {
        "rtl_files": getattr(config, "RTLFILE", []),
        "caller": getattr(config, "caller", None),
        "callee": getattr(config, "callee", None),
        "exclude": getattr(config, "exclude", None),
        "no_externs": getattr(config, "no_externs", False),
        "max_depth": getattr(config, "max_depth", 0),
        "functions": functions,
    }
    try:
        text = json.dumps(payload, ensure_ascii=False, indent=2)
    except Exception:
        return
    _write_debug_text(config, tag, text, "json", timestamp=timestamp)


#
# Dump function details:
#
def dump_function_info(functions, function, details):
    finfo = functions[function]
    print("  {}() {}".format(function,
                             finfo["files"] if details else ""))
    if details:
        for caller in sorted(finfo["calls"].keys()):
            print("    --> {}".format(caller))

        if len(finfo["calls"]) > 0 and len(finfo["callee_calls"]) > 0:
            print("    ===")

        for caller in sorted(finfo["callee_calls"].keys()):
            print("    <-- {}".format(caller))

        print("\n")


#
# Build full call graph
#


#第一处修改，函数用于打印dot文件，在这里面，我将对if、while、switch进行特殊处理
def full_call_graph(functions, **kwargs):
    exclude = kwargs.get("exclude", None)
    no_externs = kwargs.get("no_externs", False)
    std_buf = kwargs.get("stdio_buffer", None)
    threads_only = kwargs.get("threads_only", False)
    print_buf(std_buf, "strict digraph callgraph {")
    myjoin = re.compile(r"pthread_join")
    switch_re = re.compile(r"switch+(\d+)")
    tail = ""
    #
    # Simply walk all nodes and print the callers
    #
    for func in sorted(functions.keys()):
        # 重置每个函数内的控制流状态，防止跨函数误连
        has_if = 0
        count_if = 0
        count_switch = 0
        start_if = ""
        end_if = ""
        start_switch = ""
        end_switch = ""
        switchlist = dict()
        preswtich = ""
        prenum = 1

        printed_functions = 1
        pre = func
        if exclude is None or \
                re.match(exclude, func) is None:

            for caller in functions[func]["mycalls"]:
                if (not no_externs or caller in functions) and \
                        (exclude is None or
                         re.match(exclude, caller) is None):
                    join_search = re.search(myjoin, caller)#处理pthread——join节点
                    if join_search is not None:
                        for tail, join in resolve_join_edges(functions, func, caller):
                            print_buf(std_buf, '"{}" -> "{}";'.format(tail, join))


                    # if caller not in functions:
                    #     print_buf(std_buf, '"{}" [style=dashed]'.
                    #               format(caller))
                    # if "if" in caller:
                    #     if has_if==0:
                    #         has_if=1
                    #     count_if=count_if+1
                    #     if count_if==1:
                    #         start_if=pre
                    #     print_buf(std_buf, '"{}" [style=dashed]'.
                    #               format(caller))
                    # else:
                    #     if has_if==1:
                    #         has_if=0
                    #         end_if=caller
                    #         print_buf(std_buf, '"{}" -> "{}";'.format(start_if, end_if))
                    #         # print_buf(std_buf, '"{}" [style=dashed]'.
                    #         #           format(start_if))
                    #         # print_buf(std_buf, '"{}" [style=dashed]'.
                    #         #           format(end_if))
                    #     count_if=0
                    #     if "while" in caller:
                    #         print_buf(std_buf, '"{}" [style=dashed]'.
                    #               format(caller))
                    #     elif"switch" in caller:
                    #         print_buf(std_buf, '"{}" [style=dashed]'.
                    #                   format(caller))
                    if not threads_only:
                        # 条件节点处理（仅在非threads_only模式下）
                        if "if" in caller:
                            if count_if==0:
                                count_if=count_if+1
                                start_if=pre
                            print_buf(std_buf, '"{}" -> "{}";'.format(pre, caller))
                            print_buf(std_buf, '"{}" [style=dashed]'.format(caller))
                        elif "while" in caller:
                            print_buf(std_buf, '"{}" -> "{}";'.format(pre, caller))
                            print_buf(std_buf, '"{}" [style=dashed]'.format(caller))
                        elif "switch" in caller:
                            if count_switch==0:
                                count_switch=count_switch+1
                                start_switch=pre
                            switch_re_flag=re.search(switch_re,caller)
                            search_switch="switch"+switch_re_flag.group(1)
                            if prenum!=switch_re_flag.group(1):
                                prenum=switch_re_flag.group(1)
                                preswtich=start_switch
                            else:
                                preswtich=pre
                            switchlist[start_switch]=dict()
                            switchlist[start_switch][search_switch]=list()
                            switchlist[start_switch][search_switch].append(caller)
                            print_buf(std_buf, '"{}" -> "{}";'.format(start_switch, caller))
                            print_buf(std_buf, '"{}" [style=dashed]'.format(caller))
                        else:
                            if count_if>0:
                                count_if=0
                                end_if=caller
                                print_buf(std_buf, '"{}" -> "{}";'.format(pre, end_if))
                                print_buf(std_buf, '"{}" -> "{}";'.format(start_if, end_if))
                            elif count_switch>0:#switch与最后节点相连的元素
                                end_switch=caller
                                for key in switchlist[start_switch]:
                                    print_buf(std_buf, '"{}" -> "{}";'.format(key[-1], end_switch))
                                count_switch=0
                                prenum=1
                            else:
                                  print_buf(std_buf, '"{}" -> "{}";'.format(pre, caller))
                    else:
                        # threads_only模式：只处理普通调用，不处理条件节点
                        print_buf(std_buf, '"{}" -> "{}";'.format(pre, caller))
                    printed_functions += 1
                    pre = caller
            if printed_functions == 0:
                print_buf(std_buf, '"{}"'.format(func))
    print_buf(std_buf, "}")


def conditions_call_graph(functions, **kwargs):
    """Render a DOT that focuses on condition-prefixed calls only.

    - Only emits nodes whose names contain "if/", "while/", or start with "switch".
    - Connects consecutive conditional nodes within the same function in order.
    - Skips thread join/create edges on purpose.
    """
    exclude = kwargs.get("exclude", None)
    no_externs = kwargs.get("no_externs", False)
    std_buf = kwargs.get("stdio_buffer", None)

    print_buf(std_buf, "strict digraph callgraph {")
    cond_prefix = ("if/", "while/", "switch")

    for func in sorted(functions.keys()):
        if exclude is not None and re.match(exclude, func) is not None:
            continue

        prev_cond = None
        emitted_any = False
        for caller in functions[func]["mycalls"]:
            if (exclude is not None and re.match(exclude, caller) is not None):
                continue
            is_cond = any(part in caller for part in cond_prefix)
            if not is_cond:
                continue

            # only keep nodes belonging to this function or externs allowed
            if no_externs and caller not in functions:
                continue

            if prev_cond is None:
                print_buf(std_buf, f'"{func}" -> "{caller}";')
            else:
                print_buf(std_buf, f'"{prev_cond}" -> "{caller}";')
            print_buf(std_buf, f'"{caller}" [style=dashed]')
            prev_cond = caller
            emitted_any = True

        if not emitted_any:
            # keep the function visible if no conditional nodes were found
            print_buf(std_buf, f'"{func}"')

    print_buf(std_buf, "}")


#
# Main()
#
def main():
    #
    # Data sets
    #
    functions = dict()
    # 全局控制是否添加条件前缀
    add_condition_prefix = True

    #
    # Command line argument parsing
    #
    parser = argparse.ArgumentParser()

    parser.add_argument("-d", "--debug",
                        help="Enable debugging", action="store_true")
    parser.add_argument("-f", "--functions", metavar="FUNCTION",
                        help="Dump functions name(s)",
                        type=str, default="&None", const="&all",
                        action='store', nargs='?')
    parser.add_argument("--callee",
                        help="Callgraph for the function being called",
                        type=str, metavar="FUNCTION", action='append')
    parser.add_argument("--caller",
                        help="Callgraph for functions being called by",
                        type=str, metavar="FUNCTION", action='append')
    parser.add_argument("-e", "--exclude",
                        help="RegEx for functions to exclude",
                        type=str, metavar="REGEX")
    parser.add_argument("--no-externs",
                        help="Do not show external functions",
                        action="store_true")
    parser.add_argument("--no-warnings",
                        help="Do not show warnings on the console",
                        action="store_true")
    parser.add_argument("--max-depth", metavar="DEPTH",
                        help="Maximum tree depth traversal, default no depth",
                        type=int, default=0)
    parser.add_argument("--unit-test", help=argparse.SUPPRESS,
                        action="store_true")
    parser.add_argument("--conditions-only",
                        help="Render only condition-prefixed nodes (if/while/switch)",
                        action="store_true")
    parser.add_argument("--threads-only",
                        help="Render only thread edges without condition nodes",
                        action="store_true")
    parser.add_argument("--export-txt",
                        help="Export circle.txt config file to specified path",
                        type=str, metavar="PATH")
    parser.add_argument("--source-file",
                        help="Source code file path for extracting line numbers",
                        type=str, metavar="PATH")
    parser.add_argument("--output-base",
                        help="Base directory for output (配置文件 and 中间结果)",
                        type=str, metavar="PATH")
    
    # 冗余处理模式参数（混合模式）
    parser.add_argument("--smart",
                        help="Smart mode: skip regeneration if input files unchanged",
                        action="store_true")
    parser.add_argument("--clean",
                        help="Clean mode: remove existing directories before regeneration",
                        action="store_true")
    parser.add_argument("--force",
                        help="Force mode: force regeneration even in smart mode",
                        action="store_true")

    parser.add_argument("RTLFILE", help="GCCs RTL .expand file", nargs="+")

    parser.parse_args()
    config = parser.parse_args()
    
    #
    # If the unit test option is specified jump straight into it...
    #
    if config.unit_test:
        return unit_test()

    #
    # Additional option checks
    #
    if config.caller and config.callee:
        print_err("ERROR: Either --caller or --callee option should be given, "
                  "not both!")
        return 1

    if config.exclude is not None:
        try:
            exclude_regex = re.compile(config.exclude)
        except Exception as e:
            print_err("ERROR: Invalid --exclude regular expression, "
                      "\"{}\" -> \"{}\"!".
                      format(config.exclude, e))
            return 1
    else:
        exclude_regex = None

    if not config.caller and not config.callee and config.max_depth:
        print_err("ERROR: The --max_depth option is only valid with "
                  "--caller or --callee!")
        return 1

    #
    # Check if all files exist
    #
    for file in config.RTLFILE:
        if not os.path.isfile(file) or not os.access(file, os.R_OK):
            print_err("ERROR: Can't open rtl file, \"{}\"!".format(file))
            return 1

    #
    # Regex to extract functions
    #
    #第二处修改，这里为读取模块，将读取的信息存入数据结构，便于进行打印
    function = re.compile(
        r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)(,.*)?\).*$")
    call = re.compile(
        r"^.*\(call.*\"(?P<target>.*)\".*$")
    symbol_ref = re.compile(r"^.*\(symbol_ref.*\"(?P<target>.*)\".*$")
    mytaskset = re.compile(r".*\(set\s+\(reg:DI\s+1\s+dx\)")
    mytask = re.compile(r".*\(symbol_ref:DI \(\"(?P<target>.*?)\"[^\"]*\)")
    mythreadset = re.compile(r".*\(set\s+\(reg:DI\s+5\s+di\)")
    mythread = re.compile(r".*\(symbol_ref:DI \(\"(?P<target>.*?)\"\)")
    myjointhread = re.compile(r".*\(reg:DI \d+ \[ (thread\d*).*\]")
    condition_myjump = re.compile(r"\(jump_insn\s+(\d+)")
    condition_if = re.compile(r".*\(if_then_else")
    condition_jump = re.compile(r".*\(label_ref\s+(\d+)")
    condition_barrier = re.compile(r"\(barrier")
    condition_code = re.compile(r"\(code_label\s+(\d+)")
    exist = 0  # 是否出现条件标志,初始状态为1
    exist_flag = 0  # 条件标志位为0代表while循环，条件标志位1代表if条件
    jump_flag=0#用来判断上次是不是出现jump了
    if_flag=0#用来判断上次是不是出现if——then了
    barrier_flag=0#判断上一行是否出现了barrier
    #状态标志
    jump_1=1
    jump_2=0
    jump_3=0
    jump_4=0
    #
    # Parse each line in each file given
    #
    functions_pre=dict()
    function_name = None
    #预读模块
    for line in fileinput.input(config.RTLFILE):
        match = re.match(function, line)
        if match is not None:
            function_name = match.group("function")
            if function_name in functions:#说明重复定义了，正确代码只执行else
                if not config.no_warnings:#是否打印报错信息
                    print_err("WARNING: Function {} defined in multiple"
                              "files \"{}\"!".
                              format(function_name,
                                     ', '.join(map(
                                         str,
                                         functions[function_name]["files"] +
                                         [fileinput.filename()]))))
            else:
                functions_pre[function_name] = list()
        else:
            # 在遇到函数定义前的空行/注释需要跳过
            current_pre = functions_pre.get(function_name)
            if current_pre is None:
                continue
            if jump_1==1:
                condition_myjump_flag=re.match(condition_myjump,line)
                if condition_myjump_flag is not None:
                    jump_2=1
                    jump_1=0
            elif jump_2==1:
                condition_if_flag=re.match(condition_if,line)
                if condition_if_flag is not None:
                    jump_3=1
                    jump_2=0
                else:
                    condition_jump_flag = re.match(condition_jump, line)
                    if condition_jump_flag is not None:
                        num = condition_jump_flag.group(1)
                        current_pre.append(("jump1", num))
                        jump_2 = 0
                        jump_1 = 1
            elif jump_3==1:
                condition_jump_flag=re.match(condition_jump,line)
                if condition_jump_flag is not None:
                    num=condition_jump_flag.group(1)
                    current_pre.append(("jump",num))
                    jump_3=0
                    jump_1=1
            condition_code_flag=re.match(condition_code,line)
            if condition_code_flag is not None:
                    num=condition_code_flag.group(1)
                    current_pre.append(("code",num))
    #对预读模块进行处理
    #对jump1进行处理
    jump_flag=0
    for functions_pre_name in functions_pre:
        jump_flag=0
        for key in functions_pre[functions_pre_name]:
            if key[0]=="jump":
                index=functions_pre[functions_pre_name].index(key)+1
                for key_test in functions_pre[functions_pre_name][index:]:
                    if key_test[0]=="code" and key_test[1]<key[1]:
                        jump_flag=1
            if key[0]=="jump1" and jump_flag==1:
                for key_test in functions_pre[functions_pre_name][index:]:
                    if key_test[0]=="jump1" and key_test[1]==key[1]:
                        newindex=functions_pre[functions_pre_name].index(key_test)
                        functions_pre[functions_pre_name][newindex]=("jump",key_test[1])
                        jump_flag=0

    #对code进行删除
    key_exist=0
    for functions_pre_name in functions_pre:
        for key in functions_pre[functions_pre_name]:
            if key[0]=="code":
                key_exist=0
                for key_test in functions_pre[functions_pre_name]:
                    if key_test[0]=="jump" and key_test[1]==key[1]:
                        key_exist=1
                if key_exist==0:
                    functions_pre[functions_pre_name].remove(key)
            elif key[0]=="jump1":
                functions_pre[functions_pre_name].remove(key)

    _dump_debug_snapshot(
        config,
        "control_prefix",
        {
            "rtl_files": list(getattr(config, "RTLFILE", [])),
            "functions_pre": functions_pre,
        },
    )

    def next_line_generator():
        # 使用 fileinput.input() 打开文件并创建迭代器
        with fileinput.input(files=config.RTLFILE) as file:
            for line in file:
                yield line
                # 由于fileinput.input()返回的是一个迭代器，我们尝试预读取下一行
                try:
                    next_line = next(file)
                except StopIteration:
                    # 没有下一行了
                    next_line = None
                else:
                    # 如果读取下一行成功，暂存它并在下一次迭代中产生
                    yield next_line

    # 使用生成器获取下一行
    next_line_gen = next_line_generator()

    function_name = ""
    mytarget = ""
    thread_num = ""
    start_time = time.time()
    flag = 0
    state_1=1
    state_2=0
    state_3=1
    state_4=0
    state_5=0
    state_6=0
    state_7=0
    state_8=0
    state_9=0
    switch_count=0#判断switch分支
    excuted=0#判断是否执行过第一个判断
    state_count=0  #用来计数当前识别到第几个
    
    # 根据threads_only参数设置是否添加条件前缀
    add_condition_prefix = not getattr(config, "threads_only", False)
    
    for line in next_line_gen:
        #
        # Find function entry point
        #
        match = re.match(function, line)
        if match is not None:
            count = 0
            function_name = match.group("function")
            if function_name in functions:
                if not config.no_warnings:
                    print_err("WARNING: Function {} defined in multiple"
                              "files \"{}\"!".
                              format(function_name,
                                     ', '.join(map(
                                         str,
                                         functions[function_name]["files"] +
                                         [fileinput.filename()]))))
            else:
                functions[function_name] = dict()
                functions[function_name]["files"] = list()
                functions[function_name]["calls"] = dict()
                functions[function_name]["refs"] = dict()
                functions[function_name]["callee_calls"] = dict()
                functions[function_name]["callee_refs"] = dict()
                functions[function_name]["mycalls"] = list()
                functions[function_name]["myinfo"] = dict()
                state_count=0

            functions[function_name]["files"].append(fileinput.filename())
        #
        # find thread
        else:
            #分两边识别
            excuted=0
            if function_name != "":
                length=functions_pre[function_name].__len__()
                if state_count < length:
                    if state_1 == 1:
                        condition_code_flag = re.match(condition_code, line)
                        if condition_code_flag is not None:
                            if condition_code_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                                state_1 = 0
                                state_2 = 1
                                state_3 = 0
                    elif state_2 == 1:
                        condition_jump_flag = re.match(condition_jump, line)
                        if condition_jump_flag is not None:
                            if condition_jump_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                                state_1 = 1
                                state_2 = 0
                                state_3 = 1
                                excuted = 1
                    if state_3 == 1 and excuted == 0:
                        condition_jump_flag = re.match(condition_jump, line)
                        if condition_jump_flag is not None:
                            if condition_jump_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                                state_4 = 1
                                # state_5 = 1
                                state_3 = 0
                                state_1 = 0
                    elif state_4 == 1:
                        condition_code_flag = re.match(condition_code, line)
                        if condition_code_flag is not None:
                            if condition_code_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                                state_4 = 0
                                # state_5 = 0
                                state_3 = 1
                                state_1 = 1#识别出是if
                        else:
                            condition_jump_flag=re.match(condition_jump,line)
                            if condition_jump_flag is not None:
                                if condition_jump_flag.group(1) == functions_pre[function_name][state_count][1]:
                                    state_count = state_count + 1
                                    state_4=0
                                    state_5=1#识别出事Switch，并且读入了第一个jump
                                    switch_count=0
                    elif state_5 == 1:  # 直到识别到code
                        condition_jump_flag = re.match(condition_jump, line)#把jump读干
                        if condition_jump_flag is not None:
                            if condition_jump_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                        else:
                            condition_code_flag = re.match(condition_code, line)
                            if condition_code_flag is not None:
                                if condition_code_flag.group(1) == functions_pre[function_name][state_count][1]:
                                    state_count = state_count + 1
                                    state_6=1
                                    state_5=0
                    elif state_6 == 1:
                        condition_jump_flag = re.match(condition_jump, line)#如果是jump进入7状态，如果是code则结束
                        if condition_jump_flag is not None:
                            if condition_jump_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                                state_7 = 1
                                state_6 = 0
                                switch_count=switch_count+1
                        else:
                            condition_code_flag = re.match(condition_code, line)
                            if condition_code_flag is not None:
                                if condition_code_flag.group(1) == functions_pre[function_name][state_count][1]:
                                    state_count = state_count + 1
                                    state_6 = 0
                                    state_3 = 1
                                    state_1 = 1
                                    switch_count=switch_count+1
                    elif state_7==1:#已经读到code，回到6状态
                        condition_code_flag = re.match(condition_code, line)
                        if condition_code_flag is not None:
                            if condition_code_flag.group(1) == functions_pre[function_name][state_count][1]:
                                state_count = state_count + 1
                                state_7=0
                                state_6=1
            if flag == 0:
                match_mythreadset = re.match(mythreadset, line)
                if match_mythreadset is not None:
                    flag = 1;
            else:
                match_mythread = re.match(mythread, line)
                if match_mythread is not None:
                    thread_num = match_mythread.group("target")
                    flag = 0;
                else:
                    match_mythread = re.match(myjointhread, line)
                    if match_mythread is not None:
                        thread_num = match_mythread.group(1)
                        flag = 0;
                    else:
                        flag += 1

            # Find direct function calls
            match_mytaskset = re.match(mytaskset, line)
            if match_mytaskset is not None:
                try:
                    next_line = next(next_line_gen)  # 获取下一行
                    match_mytask = re.match(mytask, next_line)
                    if match_mytask is not None:
                        mytarget = match_mytask.group("target")
                except StopIteration:
                    next_line = None  # 文件结束，没有下一行
            match = re.match(call, line)
            if match is not None:
                if not function_name:
                    continue
                count += 1
                target = match.group("target")
                if target=="puts":
                    target="printf"
                elif target=="fwrite":
                    target="fprintf"
                origin_target=target
                # if exist==1:
                #     if exist_flag==0:
                #         target="while/"+target
                #     elif exist_flag==1:
                #         target="if/"+target
                if add_condition_prefix:
                    if state_2==1:
                        target = "while/" + target
                    elif state_4==1:
                        target = "if/" + target
                    elif state_6==1:
                        target="switch"+str(switch_count)+"/"+target
                # elif state_7==1:
                #     switch_count=switch_count+1
                if origin_target not in functions:
                    target = function_name + "/" + target + str(count)
                if 'pthread_create' in target:
                    functions[function_name]["calls"][mytarget] = True
                    functions[function_name]["mycalls"].append(target)
                    functions[function_name]["mycalls"].append(mytarget)
                    functions[function_name]["myinfo"]["tail"] = mytarget
                    functions[function_name]["myinfo"][thread_num] = mytarget
                    queue = functions[function_name]["myinfo"].setdefault("__create_queue__", [])
                    queue.append(mytarget)
                else:
                    flag = 0
                    if 'pthread_join' in target:
                        flag = 1
                    functions[function_name]["calls"][origin_target] = True
                    functions[function_name]["mycalls"].append(target)
                    functions[function_name]["myinfo"]["tail"] = target
                    if flag:
                        functions[function_name]["myinfo"][target] = thread_num


            else:
                match = re.match(symbol_ref, line)
                if match is not None:
                    if not function_name:
                        continue
                    target = match.group("target")
                    if not target:
                        continue
                    if target not in functions[function_name]["refs"]:
                        functions[function_name]["refs"][target] = True

    try:
        thread_edges_preview = collect_thread_edges(copy.deepcopy(functions))
    except Exception:
        thread_edges_preview = []

    _dump_debug_snapshot(
        config,
        "post_parse",
        {
            "rtl_files": list(getattr(config, "RTLFILE", [])),
            "functions": functions,
            "thread_edges_preview": thread_edges_preview,
        },
    )

    if config.debug:
        print_dbg("[PERF] Processing {} RTL files took {:.9f} seconds".format(
            len(config.RTLFILE), time.time() - start_time))
        print_dbg("[PERF] Found {} functions".format(len(functions)))
    #
    # Build callee data
    #
    start_time = time.time()

    build_callee_info(functions)

    if config.debug:
        print_dbg("[PERF] Building callee info took {:.9f} seconds".format(
            time.time() - start_time))

    _dump_debug_snapshot(
        config,
        "post_callee_info",
        {
            "rtl_files": list(getattr(config, "RTLFILE", [])),
            "functions": functions,
            "thread_edges_preview": thread_edges_preview,
        },
    )

    #
    # Dump functions if requested
    #
    if config.functions != "&None":
        print("\nFunction dump")
        print("-------------")
        if config.functions == "&all":
            for func in sorted(functions.keys()):
                dump_function_info(functions, func, config.debug)
        else:
            if config.functions in functions:
                dump_function_info(functions, config.functions, config.debug)
            else:
                print_err("ERROR: Can't find callee, \"{}\" in RTL data!".
                          format(config.callee))
                return 1
        return 0

    start_time = time.time()
    #
    # Dump full call graph
    #
    if not config.caller and not config.callee:
        dot_lines = []
        if getattr(config, "conditions_only", False):
            conditions_call_graph(functions,
                                  exclude=config.exclude,
                                  no_externs=config.no_externs,
                                  stdio_buffer=dot_lines)
            _dump_debug_artifacts(functions, dot_lines, config, "conditions")
        else:
            threads_only = getattr(config, "threads_only", False)
            full_call_graph(functions,
                            exclude=config.exclude,
                            no_externs=config.no_externs,
                            threads_only=threads_only,
                            stdio_buffer=dot_lines)
            _dump_debug_artifacts(functions, dot_lines, config, "threads" if threads_only else "full")

    #
    # Build callgraph for callee function
    #
    if config.callee and len(config.callee) != 0:
        for callee in config.callee:
            if callee not in functions:
                print_err("ERROR: Can't find callee \"{}\" in RTL data!".
                          format(callee))
                return 1
        dot_lines = []
        print_buf(dot_lines, "strict digraph callgraph {")
        for callee in config.callee:
            print_buf(dot_lines, '"{}" [color=blue, style=filled];'.format(callee))
            dump_path([], functions, callee,
                      max_depth=config.max_depth,
                      reverse_path=True,
                      exclude=exclude_regex,
                      call_index="callee_calls",
                      stdio_buffer=dot_lines)
        print_buf(dot_lines, "}")
        _dump_debug_artifacts(functions, dot_lines, config, "callee")

    #
    # Build callgraph for caller function
    #
    elif config.caller and len(config.caller) != 0:
        for caller in config.caller:
            if caller not in functions:
                print_err("ERROR: Can't find caller \"{}\" in RTL data!".
                          format(caller))
                return 1
        dot_lines = []
        print_buf(dot_lines, "strict digraph callgraph {")
        for caller in config.caller:
            print_buf(dot_lines, '"{}" [color=blue, style=filled];'.format(caller))
            dump_path([], functions, caller,
                      max_depth=config.max_depth,
                      exclude=exclude_regex,
                      no_externs=config.no_externs,
                      stdio_buffer=dot_lines)
        print_buf(dot_lines, "}")
        _dump_debug_artifacts(functions, dot_lines, config, "caller")

    if config.debug:
        print_dbg("[PERF] Generating .dot file took {:.9f} seconds".format(
            time.time() - start_time))

    # ========================================================================
    # 导出circle.txt配置文件（如果指定）
    # ========================================================================
    if hasattr(config, 'export_txt') and config.export_txt:
        try:
            from .exporters import export_circle_txt
            
            # 始终使用规范的目录结构
            # 如果没有指定output_base，默认使用mycallypro目录
            if not hasattr(config, 'output_base') or not config.output_base:
                config.output_base = str(Path(__file__).parent)
            
            config_dir, intermediate_dir = _ensure_output_dirs(config)
            
            # 检查是否应该跳过生成（智能模式下文件未修改）
            if getattr(config, '_skip_generation', False):
                if config.debug:
                    print_dbg("[INFO] Skipping file generation (smart mode, files up-to-date)")
                return 0
            
            # 在config对象上附加目录信息，供调试函数使用
            config._config_dir = config_dir
            config._intermediate_dir = intermediate_dir
            # circle.txt保存到配置文件目录
            txt_path = config_dir / "circle.txt"
            
            # 获取expand文件路径
            expand_file = Path(config.RTLFILE[0])
            
            # 获取源文件路径（如果提供）
            source_file = None
            if hasattr(config, 'source_file') and config.source_file:
                source_file = Path(config.source_file)
            
            # 导出txt文件
            if config.debug:
                print_dbg(f"[INFO] Exporting circle.txt to: {txt_path}")
            
            export_circle_txt(
                functions=functions,
                expand_file=expand_file,
                output_path=txt_path,
                source_file=source_file
            )
            
            if config.debug:
                print_dbg(f"[INFO] Successfully exported circle.txt")
                
        except Exception as e:
            print_err(f"ERROR: Failed to export circle.txt: {e}")
            if config.debug:
                import traceback
                traceback.print_exc()
    
    # ========================================================================
    # 如果指定了output_base，保存DOT文件和源文件到配置文件目录（扁平结构）
    # ========================================================================
    if hasattr(config, 'output_base') and config.output_base and dot_lines:
        try:
            import shutil
            
            config_dir, intermediate_dir = _ensure_output_dirs(config)
            config._config_dir = config_dir
            config._intermediate_dir = intermediate_dir
            
            # 获取基础名称用于文件命名
            expand_file = Path(config.RTLFILE[0])
            base_name = expand_file.stem
            if base_name.endswith('.233r'):
                base_name = base_name[:-5]
            # 去掉 .cpp/.c 等扩展，保持与中间结果目录一致
            if '.' in base_name:
                base_name = base_name.split('.')[0]
            
            # 保存DOT文件到配置文件根目录（扁平结构）
            dot_filename = f"{base_name}.dot"
            if hasattr(config, 'threads_only') and config.threads_only:
                dot_filename = f"{base_name}_threads.dot"
            elif hasattr(config, 'conditions_only') and config.conditions_only:
                dot_filename = f"{base_name}_full.dot"
            
            dot_path = config_dir / dot_filename
            dot_content = '\n'.join(dot_lines)
            dot_path.write_text(dot_content, encoding='utf-8')
            
            if config.debug:
                print_dbg(f"[INFO] Saved DOT file to: {dot_path}")
            
            # 复制expand文件到配置文件根目录
            if expand_file.exists():
                expand_dest = config_dir / expand_file.name
                shutil.copy2(expand_file, expand_dest)
                if config.debug:
                    print_dbg(f"[INFO] Copied expand file to: {expand_dest}")
            
            # 复制源文件到配置文件根目录（如果提供）
            if hasattr(config, 'source_file') and config.source_file:
                source_file = Path(config.source_file)
                if source_file.exists():
                    source_dest = config_dir / source_file.name
                    shutil.copy2(source_file, source_dest)
                    if config.debug:
                        print_dbg(f"[INFO] Copied source file to: {source_dest}")
            
            # 如果需要生成PNG，保存到中间结果的images目录
            # PNG文件不属于dag_describe需要的配置文件
                
        except Exception as e:
            print_err(f"ERROR: Failed to save files: {e}")

    return 0


#
# Start main() as default entry point...
#
if __name__ == '__main__':
    exit(main())
