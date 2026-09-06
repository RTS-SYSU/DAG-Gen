"""
Time-analysis tool with call-site instrumentation.

Implementation notes are based on `time_analysis_CallSite_V1_implementation_spec.md`：
- read mycalls_meta_internal.json，locate call sites by `(file, line)`
- insert timing code before and after call statements(`TA_BEGIN` / `TA_END` markers)
- automatically copy the runtime library time_stat.c/h, compile, run, and produce `time_result.json`
- Only C is supported; complex expressions or statements with unclear boundaries are skipped and recorded as warnings
"""
from __future__ import annotations 

import json 
import re 
import shutil 
import subprocess 
from dataclasses import dataclass 
from pathlib import Path 
from typing import Dict ,Iterable ,List ,Optional ,Tuple ,Mapping 

# Lightweight DOT parsing regex（compatible with legacy output）
_EDGE_RE =re .compile (r'"([^"]+)"\s*->\s*"([^"]+)"')
_NODE_QUOTED_RE =re .compile (r'"([^"]+)"')


@dataclass 
class CallSite :
    file :Path 
    line :int 
    col :Optional [int ]
    func :str 
    raw_key :str 


@dataclass 
class InstrumentResult :
    instrumented_dir :Path 
    app_path :Path 
    result_json :Path 
    prio_result_json :Optional [Path ]
    prio_weighted_dot :Optional [Path ]
    metrics_json :Optional [Path ]
    log_path :Path 
    instrumented_files :List [Path ]
    warnings :List [str ]
    skipped :List [str ]


def _infer_base_name_from_meta (meta_json :Path ,base_dir :Path )->Optional [str ]:
    """If `meta_json` is located under `<base_dir>/intermediate_results/<basename>/...`, return `<basename>`."""
    try :
        meta_json =meta_json .resolve ()
        base_dir =base_dir .resolve ()
        rel =meta_json .relative_to (base_dir )
    except Exception :
        return None 
    parts =rel .parts 
    if len (parts )>=2 and parts [0 ]=="intermediate_results":
        return parts [1 ]
    return None 


def _flatten_meta (obj :Dict )->List [Tuple [str ,Dict ]]:
    """Expand the hierarchical structure of mycalls_meta_internal and return a list of `(key, meta)` pairs."""
    out :List [Tuple [str ,Dict ]]=[]
    for k ,v in obj .items ():
        if isinstance (v ,dict )and {"file","line"}<=set (v .keys ()):
            out .append ((k ,v ))
        elif isinstance (v ,dict ):
            out .extend (_flatten_meta (v ))
    return out 


def _infer_func_from_key (raw_key :str ,meta :Dict )->str :
    """Infer the function name from the key or meta and strip trailing digits."""
    if isinstance (meta ,dict ):
        fn =meta .get ("func")
        if isinstance (fn ,str )and fn .strip ():
            return fn .strip ()
    tail =raw_key .split ("/")[-1 ]
    m =re .match (r"([A-Za-z_][A-Za-z0-9_]*?)(\d*)$",tail )
    return m .group (1 )if m else tail 


def load_call_sites (json_path :Path )->List [CallSite ]:
    """Parse mycalls_meta_internal.json and generate the CallSite list."""
    data =json .loads (json_path .read_text (encoding ="utf-8"))
    sites :List [CallSite ]=[]
    for raw_key ,meta in _flatten_meta (data ):
        if not isinstance (meta ,dict ):
            continue 
        file_field =meta .get ("file")
        line =meta .get ("line")
        if not file_field or not line :
            continue 
        col =meta .get ("col")
        func =_infer_func_from_key (raw_key ,meta )
        sites .append (
        CallSite (
        file =Path (str (file_field )),
        line =int (line ),
        col =int (col )if col is not None else None ,
        func =func ,
        raw_key =raw_key ,
        )
        )
    return sites 


def _strip_strings (text :str )->str :
    """Remove string/character literal content to avoid false positives when detecting assignments or ternary expressions."""
    res =[]
    it =iter (range (len (text )))
    i =0 
    in_str =None 
    while i <len (text ):
        ch =text [i ]
        if in_str :
            if ch =="\\":
                i +=2 
                continue 
            if ch ==in_str :
                in_str =None 
            i +=1 
            continue 
        if ch in ("\"","'"):
            in_str =ch 
            i +=1 
            continue 
        res .append (ch )
        i +=1 
    return "".join (res )


def _has_assignment (expr :str )->bool :
    """Roughly determine whether an assignment `=` exists, ignoring `==`, `<=`, `>=`, and `!=`."""
    expr =_strip_strings (expr )
    return re .search (r"(?<![=!<>])=(?![=])",expr )is not None 


def _has_question (expr :str )->bool :
    expr =_strip_strings (expr )
    return "?"in expr 


def _is_control_statement (expr :str )->bool :
    s =expr .lstrip ()
    return s .startswith (("if","while","for","switch","return"))


def _find_stmt_end (lines :List [str ],start_idx :int )->Optional [int ]:
    """Scan down from start_idx to find the line number where the statement ends with a semicolon (when parenthesis depth returns to zero)."""
    depth =0 
    for idx in range (start_idx ,len (lines )):
        line =lines [idx ]
        for ch in line :
            if ch =="(":
                depth +=1 
            elif ch ==")":
                depth =max (0 ,depth -1 )
        if ";"in line and depth ==0 :
            return idx 
    return None 


def _ensure_include (lines :List [str ])->Tuple [List [str ],bool ,int ]:
    """Ensure `time_stat.h` is included and return the new lines, whether it was newly inserted, and the added line count before the insertion point."""
    include_marker ='time_stat.h"  // TA_INCLUDE'
    if any (include_marker in ln for ln in lines ):
        return lines ,False ,0 
        # Insert before the first non-empty, non-comment line
    insert_at =0 
    feature_def_re =re .compile (r"^\s*#\s*define\s+_(GNU|DEFAULT|POSIX|XOPEN|BSD|SVID)_SOURCE\b")
    for i ,ln in enumerate (lines ):
        stripped =ln .strip ()
        if not stripped or stripped .startswith (("//","/*","*","#!")):
            continue 
            # Feature macros at the top should remain before all includes
        if feature_def_re .match (ln ):
            continue 
        insert_at =i 
        break 
    new_lines =(
    lines [:insert_at ]
    +['#include "time_stat.h"  // TA_INCLUDE\n']
    +lines [insert_at :]
    )
    return new_lines ,True ,1 


def _sanitize_var_name (basename :str ,line :int ,seq :int )->str :
    safe_base =re .sub (r"[^A-Za-z0-9_]","_",basename )
    return f"__ta_t0_{safe_base}_{line}_{seq}"


def _find_call_span (text :str ,func :str )->Optional [Tuple [int ,int ]]:
    """Find the start and end position of `func(...)` in the text and return `(start, end)`."""
    pattern =re .compile (rf"\b{re.escape(func)}\s*\(")
    m =pattern .search (text )
    if not m :
        return None 
    start =m .start ()
    depth =0 
    for idx in range (m .end (),len (text )):
        ch =text [idx ]
        if ch =="(":
            depth +=1 
        elif ch ==")":
            if depth ==0 :
                return start ,idx +1 
            depth -=1 
    return None 


def _already_instrumented (lines :List [str ],start_idx :int ,file_name :str ,line_no :int ,func :str )->bool :
    """Determine whether the line has already been instrumented for the same call site, including the function name."""
    token =f"TA_BEGIN: {file_name}:{line_no} {func}"
    for i in range (max (0 ,start_idx -3 ),min (len (lines ),start_idx +4 )):
        if token in lines [i ]:
            return True 
    return False 


def instrument_file (
file_path :Path ,
sites :List [CallSite ],
log :List [str ],
*,
priorities :Optional [Mapping [str ,int ]]=None ,
cpc_mode :bool =False ,
)->Tuple [List [str ],List [str ],List [str ]]:
    """Instrument a single file and return the modified lines, warning list, and successfully instrumented keys."""
    lines =file_path .read_text (encoding ="utf-8").splitlines (keepends =True )
    lines ,added_include ,include_added =_ensure_include (lines )
    if added_include :
        log .append (f"[include] {file_path} inserted `time_stat.h`")
    warnings :List [str ]=[]
    instrumented_keys :List [str ]=[]

    # Process in descending line-number order to avoid earlier insertions shifting later locations
    seq =1 
    seen_prefix_prio :Dict [str ,int ]={}
    base_offset =include_added # include inserted line count, unified offset
    for site in sorted (sites ,key =lambda s :(s .line ,s .col or 0 ),reverse =True ):
    # Skip compiler-generated or otherwise non-instrumentable internal symbols to avoid breaking source code across function boundaries
        if (
        site .func .startswith ("__stack_chk")
        or "__stack_chk"in site .raw_key 
        or site .func .startswith ("__builtin_")
        ):
            warnings .append (f"[skipgen] {file_path}:{site.line} skip compiler-internal call {site.raw_key}")
            continue 
        start_idx =site .line -1 +base_offset 
        if start_idx <0 or start_idx >=len (lines ):
            warnings .append (f"[miss] {file_path}:{site.line} out of range, skip {site.func}")
            continue 
        key_str =site .raw_key 
        if _already_instrumented (lines ,start_idx ,file_path .name ,site .line ,site .func ):
            log .append (f"[skip] {file_path}:{site.line} existing TA marker, skip")
            continue 

        stmt_end =_find_stmt_end (lines ,start_idx )
        if stmt_end is None :
            warnings .append (f"[warn] {file_path}:{site.line} statement end not found, skip {site.func}")
            continue 

        var_name =_sanitize_var_name (site .raw_key ,site .line ,seq )
        seq +=1 
        snippet ="".join (lines [start_idx :stmt_end +1 ])
        stripped =snippet .lstrip ()
        if stripped .startswith (("if","while","for")):
            span =_find_call_span (snippet ,site .func )
            if not span :
                warnings .append (f"[warn] {file_path}:{site.line} call not found inside the control statement {site.func}")
                continue 

                # Parse the conditional-parenthesis range of control statements and wrap the expression only when the call lies inside the condition
            kw_m =re .match (r"\s*(if|while|for)\b",snippet )
            cond_span :Optional [Tuple [int ,int ]]=None 
            if kw_m :
                kw_end =kw_m .end ()
                open_idx =snippet .find ("(",kw_end )
                if open_idx !=-1 :
                    depth =0 
                    for j in range (open_idx +1 ,len (snippet )):
                        ch =snippet [j ]
                        if ch =="(":
                            depth +=1 
                        elif ch ==")":
                            if depth ==0 :
                                cond_span =(open_idx ,j +1 )
                                break 
                            depth -=1 

            call_text =snippet [span [0 ]:span [1 ]]
            in_cond =cond_span is not None and span [0 ]>=cond_span [0 ]and span [1 ]<=cond_span [1 ]

            if in_cond :
                wrapped =(
                f"(__extension__({{ uint64_t {var_name} = now_ns(); "
                f"__auto_type __ta_ret = {call_text}; "
                f"uint64_t {var_name}_dur = now_ns() - {var_name}; "
                f'time_account("{key_str}", {var_name}_dur); '
                f'time_trace("{key_str}", {var_name}, {var_name}_dur); '
                f"__ta_ret; }}))"
                )
                new_snippet =snippet [:span [0 ]]+wrapped +snippet [span [1 ]:]
                new_lines =new_snippet .splitlines (keepends =True )
                lines [start_idx :stmt_end +1 ]=new_lines 
                log .append (f"[ok] {file_path}:{site.line} {site.func} (cond-expr)")
                instrumented_keys .append (key_str )
                base_offset +=len (new_lines )-(stmt_end +1 -start_idx )
                continue 

                # Calls outside the condition: the current version does not specially detect or rewrite this kind of "same-line control-statement" case
            warnings .append (
            f"[skip] {file_path}:{site.line} Calls outside the control-statement condition are not instrumented yet: {site.raw_key}"
            )
            continue 

        prio =0 
        thread_prefix =key_str .split ("/",1 )[0 ]
        if priorities :
            prio =int (priorities .get (key_str ,0 )or 0 )
            if prio <=0 :
                prio =int (priorities .get (thread_prefix ,0 )or 0 )

                # Set priority only on the first instrumentation for each thread prefix to avoid a system call on every invocation
        maybe_prio_line =""
        if cpc_mode and prio >0 and thread_prefix not in seen_prefix_prio :
            maybe_prio_line =f"ta_set_priority({prio});\n"
            seen_prefix_prio [thread_prefix ]=prio 

        begin_lines =[
        f"// TA_BEGIN: {file_path.name}:{site.line} {site.func}\n",
        "; /* TA_PAD */\n",
        maybe_prio_line ,
        f"uint64_t {var_name} = now_ns();\n",
        ]
        end_lines =[
        f"// TA_END: {file_path.name}:{site.line} {site.func}\n",
        f"uint64_t {var_name}_dur = now_ns() - {var_name};\n",
        f'time_account("{key_str}", {var_name}_dur);\n',
        f'time_trace("{key_str}", {var_name}, {var_name}_dur);\n',
        ]

        # Insertion order: BEGIN first, then END (END needs a +2 offset)
        lines [start_idx :start_idx ]=begin_lines 
        stmt_end +=len (begin_lines )
        end_insert_at =stmt_end +1 
        lines [end_insert_at :end_insert_at ]=end_lines 
        log .append (f"[ok] {file_path}:{site.line} {site.func}")
        instrumented_keys .append (key_str )

    return lines ,warnings ,instrumented_keys 


def _write_time_stat (dest_dir :Path )->None :
    """write time_stat.c/h。"""
    dest_dir .mkdir (parents =True ,exist_ok =True )
    (dest_dir /"time_stat.h").write_text (
    "\n".join (
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
    encoding ="utf-8",
    )
    (dest_dir /"time_stat.c").write_text (
    "\n".join (
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
    encoding ="utf-8",
    )


def _copy_project (src_root :Path ,dest_root :Path )->Path :
    """Copy the entire project directory to the target, overwriting existing content."""
    if dest_root .exists ():
        shutil .rmtree (dest_root )
    shutil .copytree (src_root ,dest_root ,dirs_exist_ok =False ,ignore =shutil .ignore_patterns ("*.o","*.so","*.a","__pycache__","*.png","*.dot"))
    return dest_root 


def _inject_metrics (
meta_path :Path ,
result_map :Dict [str ,Dict ],
log :List [str ],
warnings :List [str ],
instrumented_keys :set ,
)->Dict [str ,Dict [str ,int ]]:
    """Write statistics back to the original mycalls_meta_internal.json and return the thread summary."""
    try :
        data =json .loads (meta_path .read_text (encoding ="utf-8"))
    except Exception as e :
        raise RuntimeError (f"Unable to read meta_json: {e}")from e 

    thread_summary :Dict [str ,Dict [str ,int ]]={}

    def update_obj (obj :Dict ,thread_name :Optional [str ]=None ):
        for k ,v in obj .items ():
            if not isinstance (v ,dict ):
                continue 
            if {"file","line"}<=set (v .keys ()):
            # Prefer the original key name(consistent with the `time_account` tag), or fall back to `func@file:line` for old formats
                file_name =Path (str (v .get ("file"))).name 
                line_no =v .get ("line")
                func =_infer_func_from_key (k ,v )
                key_str =k 
                metrics =result_map .get (key_str )
                if metrics is None :
                    key_str =f"{func}@{file_name}:{line_no}"
                    metrics =result_map .get (key_str )
                if metrics :
                    total =int (metrics .get ("total_ns",0 ))
                    count =int (metrics .get ("count",0 ))
                    v .update (
                    {
                    "total_ns":total ,
                    "count":count ,
                    "avg_ns":int (metrics .get ("avg_ns",0 )),
                    "max_ns":int (metrics .get ("max_ns",0 )),
                    "min_ns":int (metrics .get ("min_ns",0 )),
                    "miss":False ,
                    "executed":True ,
                    "skip_reason":"",
                    }
                    )
                    # accumulate top-level thread names
                    th =thread_name or k 
                    thread_summary .setdefault (th ,{"total_ns":0 ,"count":0 })
                    thread_summary [th ]["total_ns"]+=total 
                    thread_summary [th ]["count"]+=count 
                else :
                    if key_str in instrumented_keys :
                    # instrumented but not executed
                        v .update (
                        {
                        "total_ns":0 ,
                        "count":0 ,
                        "avg_ns":0 ,
                        "max_ns":0 ,
                        "min_ns":0 ,
                        "miss":True ,
                        "executed":False ,
                        "skip_reason":"",
                        }
                        )
                    else :
                    # not instrumented (for example, file missing or non-C file)
                        v .update (
                        {
                        "total_ns":0 ,
                        "count":0 ,
                        "avg_ns":0 ,
                        "max_ns":0 ,
                        "min_ns":0 ,
                        "miss":True ,
                        "executed":False ,
                        "skip_reason":v .get ("skip_reason","not_instrumented"),
                        }
                        )
                        # Only entries with `miss=False` are included in the statistics summary, so nothing is accumulated here
            else :
                next_thread =thread_name if thread_name is not None else k 
                update_obj (v ,thread_name =next_thread )

    update_obj (data ,thread_name =None )
    meta_path .write_text (json .dumps (data ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
    log .append (f"[meta] write back {meta_path}")
    return thread_summary 


def _compile_project (dest_root :Path ,log :List [str ])->Path :
    """Compile the instrumented project and return the executable path."""
    sources =sorted (str (p )for p in dest_root .rglob ("*.c"))
    if not sources :
        raise RuntimeError ("No `.c` files were found for compilation")
    cmd =["gcc","-O2","-std=c11","-pthread","-I.","-Iinclude","-o","app",*sources ,"-lm","-ldl"]
    log .append (f"[build] {' '.join(cmd)}")
    proc =subprocess .run (cmd ,cwd =str (dest_root ),capture_output =True ,text =True )
    if proc .returncode !=0 :
        err =proc .stderr [-200 :]
        raise RuntimeError (f"compilefailed：{proc.returncode}\n{err}")
    return dest_root /"app"


def _run_app (app_path :Path ,log :List [str ])->None :
    proc =subprocess .run ([str (app_path )],cwd =str (app_path .parent ),capture_output =True ,text =True )
    log .append (f"[run] exit={proc.returncode}")
    if proc .stdout :
        log .append (f"[stdout]\n{proc.stdout}")
    if proc .stderr :
        log .append (f"[stderr]\n{proc.stderr}")
    if proc .returncode !=0 :
        raise RuntimeError (f"Program execution failed with exit code {proc.returncode}")


def _parse_dot_edges_simple (dot_path :Path )->Tuple [Iterable [str ],List [Tuple [str ,str ]]]:
    """Minimally parse DOT and return the node set and edge list."""
    text =dot_path .read_text (encoding ="utf-8",errors ="replace")
    edges =_EDGE_RE .findall (text )
    nodes =set ()
    for u ,v in edges :
        nodes .add (u )
        nodes .add (v )
    for name in _NODE_QUOTED_RE .findall (text ):
        nodes .add (name )
    nodes .discard ("callgraph")
    return nodes ,[(u ,v )for u ,v in edges ]


def _render_weighted_dot (
nodes :Iterable [str ],
edges :Iterable [Tuple [str ,str ]],
weights :Dict [str ,int ],
*,
priorities :Optional [Mapping [str ,int ]]=None ,
)->str :
    """Generate a simplified DOT containing only nodes, edges, and weights, with an optional appended priority line."""
    lines :List [str ]=[]
    lines .append ("digraph callgraph {")
    lines .append ('  node [shape=box, style="rounded,filled", fontname="Consolas", fontsize=10, fillcolor="#F6F6F6"];')
    for n in sorted (nodes ):
        w =int (weights .get (n ,0 )or 0 )
        if priorities is not None :
            label =f"{n}\\n{w} ns\\nprio={int(priorities.get(n, 0) or 0)}"
        else :
            label =f"{n}\\n{w} ns"
        lines .append (f'  "{n}" [label="{label}"];')
    for u ,v in edges :
        lines .append (f'  "{u}" -> "{v}";')
    lines .append ("}")
    return "\n".join (lines )+"\n"


def _write_metrics (
result_map :Dict [str ,Dict ],
thread_summary_path :Path ,
output_dir :Path ,
*,
filename :str ="metrics.json",
)->Path :
    """Generate the metrics file: `program_total_ns` (sum of node `total_ns`) plus thread summary."""
    program_total_ns =sum (int (v .get ("total_ns",0 )or 0 )for v in result_map .values ()if isinstance (v ,dict ))
    thread_summary :Dict [str ,Dict ]={}
    if thread_summary_path .exists ():
        thread_summary =json .loads (thread_summary_path .read_text (encoding ="utf-8"))
        # If the thread summary is missing, aggregate by call-site prefix
    if not thread_summary :
        agg :Dict [str ,Dict [str ,int ]]={}
        for k ,v in result_map .items ():
            if not isinstance (v ,dict ):
                continue 
            thread =k .split ("/",1 )[0 ]if "/"in k else k 
            agg .setdefault (thread ,{"total_ns":0 ,"count":0 })
            agg [thread ]["total_ns"]+=int (v .get ("total_ns",0 )or 0 )
            agg [thread ]["count"]+=int (v .get ("count",0 )or 0 )
        thread_summary =agg 

    metrics ={
    "program_total_ns":int (program_total_ns ),
    "thread_time_ns":{
    t :{
    "total_ns":int (info .get ("total_ns",0 )or 0 ),
    "count":int (info .get ("count",0 )or 0 ),
    "avg_ns":int (info .get ("total_ns",0 )or 0 )//max (1 ,int (info .get ("count",0 )or 0 )),
    }
    for t ,info in thread_summary .items ()
    if isinstance (info ,dict )
    },
    }
    output_dir .mkdir (parents =True ,exist_ok =True )
    out_path =output_dir /filename 
    out_path .write_text (json .dumps (metrics ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
    return out_path 


def run_time_analysis (
source_file :Path ,
meta_json :Path ,
base_dir :Path ,
priorities :Optional [Mapping [str ,int ]]=None ,
*,
cpc_mode :bool =False ,
)->InstrumentResult :
    """Run time-analysis instrumentation, compilation, and execution on the project directory."""
    if not source_file .exists ():
        raise FileNotFoundError (f"Source Filedoes not exist: {source_file}")
    if not meta_json .exists ():
        raise FileNotFoundError (f"Not found JSON: {meta_json}")

    base_dir =base_dir .resolve ()
    src_root =source_file .resolve ().parent 
    base_name =_infer_base_name_from_meta (meta_json ,base_dir )or source_file .stem 
    ta_dir_name ="time_analysis_cpc"if cpc_mode else "time_analysis"
    output_root =base_dir /"intermediate_results"/base_name /ta_dir_name 
    log_file_name ="time_analysis_cpc.log"if cpc_mode else "time_analysis.log"
    log_path =base_dir /"intermediate_results"/base_name /"dag_generation"/"debug"/log_file_name 
    log_path .parent .mkdir (parents =True ,exist_ok =True )

    log :List [str ]=[]
    warnings :List [str ]=[]
    skipped :List [str ]=[]
    analysis_error :Optional [str ]=None 

    dest_project :Optional [Path ]=None 
    app_path :Optional [Path ]=None 
    result_json :Optional [Path ]=None 
    prio_result_json :Optional [Path ]=None 
    prio_weighted_dot :Optional [Path ]=None 
    metrics_json :Optional [Path ]=None 
    instrumented_files :List [Path ]=[]

    try :
    # 1) copyproject
        dest_project =output_root /src_root .name 
        _copy_project (src_root ,dest_project )
        log .append (f"[copy] {src_root} -> {dest_project}")

        # 2) copy the runtime
        _write_time_stat (dest_project )
        log .append ("[runtime] write time_stat.c/h")

        # 3) read JSON
        sites =load_call_sites (meta_json )
        if not sites :
            raise RuntimeError ("No valid call sites were found in the JSON")
            # group by file
        by_file :Dict [Path ,List [CallSite ]]={}
        for s in sites :
            by_file .setdefault (s .file ,[]).append (s )

        instrumented_keys_all :List [str ]=[]
        supported_suffixes ={".c"}# Currently only C is supported; C++ would require a separate implementation

        for rel_path ,file_sites in by_file .items ():
        # The `file` field in meta may be an absolute path (for example in a PX4 project); perform minimal mapping here:
        # Prefer mapping by basename to files with the same name in the copied project directory.
            if rel_path .is_absolute ():
                candidate =dest_project /rel_path .name 
                target_file =candidate if candidate .exists ()else (dest_project /rel_path )
            else :
                target_file =dest_project /rel_path 

            if not target_file .exists ():
                warnings .append (f"[warn] File not found: {rel_path}; skip {len(file_sites)}  call sites")
                continue 
            if target_file .suffix .lower ()not in supported_suffixes :
                skipped .append (f"[skip] Non-C file {target_file} (from {rel_path})")
                continue 

            new_lines ,w ,inst_keys =instrument_file (target_file ,file_sites ,log )
            warnings .extend (w )
            instrumented_keys_all .extend (inst_keys )
            target_file .write_text ("".join (new_lines ),encoding ="utf-8")
            instrumented_files .append (target_file )

        if not instrumented_files :
            raise RuntimeError ("No files completed instrumentation: only `.c` is currently supported, and the `file` field in `meta_json` must map to source code inside the project.")

            # 4) compile & run
        app_path =_compile_project (dest_project ,log )
        _run_app (app_path ,log )

        result_json =dest_project /"time_result.json"
        if not result_json .exists ():
            raise RuntimeError ("`time_result.json` was not found (the program did not output normally)")

            # Write statistics back to the original meta_json
        try :
            result_map =json .loads (result_json .read_text (encoding ="utf-8"))
            if priorities :
                prio_map :Dict [str ,Dict ]={}
                for k ,v in result_map .items ():
                    if isinstance (v ,dict ):
                        v =dict (v )
                        v ["priority"]=int (priorities .get (k ,0 )or 0 )
                        prio_map [k ]=v 
                prio_result_json =result_json .parent /"time_result_prio.json"
                prio_result_json .write_text (json .dumps (prio_map ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
                log .append (f"[prio] write {prio_result_json}")
            summary =_inject_metrics (meta_json ,result_map ,log ,warnings ,set (instrumented_keys_all ))
            # Write thread summary
            if summary :
                summary_path =meta_json .parent /"thread_time_summary.json"
                summary_path .write_text (json .dumps (summary ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
                log .append (f"[summary] Thread time summary -> {summary_path}")
            log .append (f"[update] Wrote statistics back to {meta_json}")
            # metrics file: sum of node `total_ns` plus thread summary
            try :
                metrics_json =_write_metrics (
                result_map ,
                meta_json .parent /"thread_time_summary.json",
                result_json .parent ,
                filename ="metrics_prio.json"if priorities else "metrics.json",
                )
                log .append (f"[metrics] -> {metrics_json}")
            except Exception as me :
                warnings .append (f"[warn] failed to write the metrics file: {me}")
                # generate the weighted DAG (node labels include `total_ns`) and store it in the same directory as `time_result`
            try :
                weights ={k :int (v .get ("total_ns",0 )or 0 )for k ,v in result_map .items ()if isinstance (v ,dict )}
                dag_path =base_dir /"intermediate_results"/base_name /"dag_generation"/"dag.dot"
                if dag_path .exists ():
                    nodes ,edges =_parse_dot_edges_simple (dag_path )
                    weighted_text =_render_weighted_dot (nodes ,edges ,weights )
                    weighted_path =result_json .parent /"dag_weighted.dot"
                    weighted_path .write_text (weighted_text ,encoding ="utf-8")
                    log .append (f"[weighted_dag] {dag_path} + time_result -> {weighted_path}")
                    if priorities :
                        weighted_prio_text =_render_weighted_dot (nodes ,edges ,weights ,priorities =priorities )
                        prio_weighted_dot =result_json .parent /"dag_weighted_prio.dot"
                        prio_weighted_dot .write_text (weighted_prio_text ,encoding ="utf-8")
                        log .append (f"[weighted_dag_prio] -> {prio_weighted_dot}")
                else :
                    warnings .append (f"[warn] Original `dag.dot` not found ({dag_path}); skip weighted-DAG generation")
            except Exception as gen_err :
                warnings .append (f"[warn] generate the weighted DAG failed: {gen_err}")
        except Exception as e :# pragma: no cover - final safeguard
            warnings .append (f"[warn] Failed to write back statistics: {e}")

        return InstrumentResult (
        instrumented_dir =output_root ,
        app_path =app_path ,
        result_json =result_json ,
        prio_result_json =prio_result_json ,
        prio_weighted_dot =prio_weighted_dot ,
        metrics_json =metrics_json ,
        log_path =log_path ,
        instrumented_files =instrumented_files ,
        warnings =warnings ,
        skipped =skipped ,
        )
    except Exception as e :
        analysis_error =str (e )
        raise 
    finally :
    # Write logs to disk regardless of success or failure
        log_content ="\n".join (log +warnings +skipped +([f"[error] {analysis_error}"]if analysis_error else []))
        log_path .write_text (log_content ,encoding ="utf-8")
