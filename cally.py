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
import fileinput
import os
import re
import sys
import time

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
#                    \_  H --> I --> J --> D
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
def full_call_graph(functions, **kwargs):
    exclude = kwargs.get("exclude", None)
    no_externs = kwargs.get("no_externs", False)
    std_buf = kwargs.get("stdio_buffer", None)
    print_buf(std_buf, "strict digraph callgraph {")
    myjoin = re.compile(r"pthread_join")
    tail = ""
    has_if=0#判断当前是否出现if，为0则没有
    count_if=0#计数出现了几次if标志
    start_if=""#记录if开始关键词
    end_if=""#记录if结束关键词
    #
    # Simply walk all nodes and print the callers
    #
    for func in sorted(functions.keys()):
        printed_functions = 1
        pre = func
        if exclude is None or \
                re.match(exclude, func) is None:

            for caller in functions[func]["mycalls"]:
                if (not no_externs or caller in functions) and \
                        (exclude is None or
                         re.match(exclude, caller) is None):
                    join_search = re.search(myjoin, caller)
                    if join_search is not None:
                        myg_thread = functions[func]["myinfo"][caller]
                        myg_task = functions[func]["myinfo"][myg_thread]
                        myg_tail = functions[myg_task]["myinfo"]["tail"]
                        print_buf(std_buf, '"{}" -> "{}"'.format(myg_tail, caller))
                    print_buf(std_buf, '"{}" -> "{}"'.format(pre, caller))

                    # if caller not in functions:
                    #     print_buf(std_buf, '"{}" [style=dashed]'.
                    #               format(caller))
            #         if "if" in caller:
            #             if has_if==0:
            #                 has_if=1
            #             count_if=count_if+1
            #             if count_if==1:
            #                 start_if=pre
            #             print_buf(std_buf, '"{}" [style=dashed]'.
            #                       format(caller))
            #         else:
            #             if has_if==1:
            #                 has_if=0
            #                 end_if=caller
            #                 print_buf(std_buf, '"{}" -> "{}";'.format(start_if, end_if))
            #                 # print_buf(std_buf, '"{}" [style=dashed]'.
            #                 #           format(start_if))
            #                 # print_buf(std_buf, '"{}" [style=dashed]'.
            #                 #           format(end_if))
            #             count_if=0
            #             if "while" in caller:
            #                 print_buf(std_buf, '"{}" [style=dashed]'.
            #                       format(caller))
            #
            #         printed_functions += 1
            #         pre = caller
            # if printed_functions == 0:
            #     print_buf(std_buf, '"{}"'.format(func))
            print_buf(std_buf, ';')
    print_buf(std_buf, "}")


#
# Main()
#
def main():
    #
    # Data sets
    #
    functions = dict()

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
    condition_jump = re.compile(r"\(jump_insn\s+(\d+)")
    condition_if = re.compile(r".*\(if_then_else")
    condition_label = re.compile(r".*\(label_ref\s+(\d+)")
    condition_barrier = re.compile(r"\(barrier")
    condition_codelabel = re.compile(r"\(code_label\s+\d+")
    exist = 0  # 是否出现条件标志,初始状态为1
    exist_flag = 0  # 条件标志位为0代表while循环，条件标志位1代表if条件
    jump_flag=0#用来判断上次是不是出现jump了
    if_flag=0#用来判断上次是不是出现if——then了
    barrier_flag=0#判断上一行是否出现了barrier
    #
    # Parse each line in each file given
    #

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

            functions[function_name]["files"].append(fileinput.filename())
        #
        # find thread
        else:
            search_barrier=re.search(condition_barrier,line)
            if search_barrier is not None:
                next_line = next(next_line_gen)
                search_codelabel=re.search(condition_codelabel,next_line)
                if search_codelabel is not None:
                    if exist==0:
                        exist=1
                        exist_flag=0
                    elif exist==1:
                        exist=0

            if if_flag==1:
                search_label=re.search(condition_label,line)
                if search_label is not None:
                    if exist==0:
                        exist=1
                        exist_flag=1
                    elif exist==1:
                        exist=0
                    if_flag=0
            if jump_flag==1:
                search_if=re.search(condition_if,line)
                if search_if is not None:
                    jump_flag=0
                    if_flag=1
                jump_flag=0
            search_jump=re.search(condition_jump,line)
            if search_jump is not None:
                jump_flag=1
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
                count += 1
                target = match.group("target")
                if target=="puts":
                    target="printf"
                elif target=="fwrite":
                    target="fprintf"
                origin_target=target
                if exist==1:
                    if exist_flag==0:
                        target="while/"+target
                    elif exist_flag==1:
                        target="if/"+target
                if origin_target not in functions:
                    target = function_name + "/" + target + str(count)
                if 'pthread_create' in target:
                    functions[function_name]["calls"][mytarget] = True
                    functions[function_name]["mycalls"].append(target)
                    functions[function_name]["mycalls"].append(mytarget)
                    functions[function_name]["myinfo"]["tail"] = mytarget
                    functions[function_name]["myinfo"][thread_num] = mytarget
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
                    target = match.group("target")
                    if target not in functions[function_name]["refs"]:
                        functions[function_name]["refs"][target] = True

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
        full_call_graph(functions, exclude=config.exclude,
                        no_externs=config.no_externs)

    #
    # Build callgraph for callee function
    #
    if config.callee and len(config.callee) != 0:
        for callee in config.callee:
            if callee not in functions:
                print_err("ERROR: Can't find callee \"{}\" in RTL data!".
                          format(callee))
                return 1
        print("strict digraph callgraph {")
        for callee in config.callee:
            print('"{}" [color=blue, style=filled];'.format(callee))
            dump_path([], functions, callee,
                      max_depth=config.max_depth,
                      reverse_path=True,
                      exclude=exclude_regex,
                      call_index="callee_calls")
        print("}")

    #
    # Build callgraph for caller function
    #
    elif config.caller and len(config.caller) != 0:
        for caller in config.caller:
            if caller not in functions:
                print_err("ERROR: Can't find caller \"{}\" in RTL data!".
                          format(caller))
                return 1
        print("strict digraph callgraph {")
        for caller in config.caller:
            print('"{}" [color=blue, style=filled];'.format(caller))
            dump_path([], functions, caller,
                      max_depth=config.max_depth,
                      exclude=exclude_regex,
                      no_externs=config.no_externs)
        print("}")

    if config.debug:
        print_dbg("[PERF] Generating .dot file took {:.9f} seconds".format(
            time.time() - start_time))

    return 0


#
# Start main() as default entry point...
#
if __name__ == '__main__':
    exit(main())
