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
from collections import defaultdict 
from pathlib import Path 
import re 
import sys 
import time 
from datetime import datetime 
from pathlib import Path 
from typing import Optional ,Tuple 

# Support direct execution: if relative import fails, adjust `sys.path` and import again
try :
    from .thread_map import resolve_join_edges ,collect_thread_edges 
    from .source_binder import create_targets_from_source 
    from ..core .func_ranges import extract_func_ranges 
    from ..level1 .segment_dag import build_stage1_segments_and_dag 
except ImportError :
    sys .path .append (str (Path (__file__ ).resolve ().parent .parent ))
    from generation .thread_map import resolve_join_edges ,collect_thread_edges 
    from generation .source_binder import create_targets_from_source 
    from core .func_ranges import extract_func_ranges 
    from level1 .segment_dag import build_stage1_segments_and_dag 

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

unit_test_full_dump_output =[
'strict digraph callgraph {',
'"A" -> "A";','"A" -> "B";',
'"B" -> "C";','"B" -> "E";',
'"E" [style=dashed]','"B" -> "F";',
'"B" -> "G";','"B" -> "H";',
'"C" -> "D";','"D"','"F"',
'"G" -> "B";','"H" -> "I";',
'"I" -> "J";','"J" -> "D";',
'"main" -> "A";',
'}'
]
#Global variable used to store tail-node binding info
tail_map ={}
def _serialize_functions_for_dump (functions :dict )->dict :
    """Convert the `functions` structure into a JSON-serializable form."""
    out ={}
    for fn ,data in functions .items ():
        out [fn ]={
        "files":list (data .get ("files",[])),
        "calls":list (data .get ("calls",{}).keys ()),
        "refs":list (data .get ("refs",{}).keys ()),
        "callee_calls":list (data .get ("callee_calls",{}).keys ()),
        "callee_refs":list (data .get ("callee_refs",{}).keys ()),
        "mycalls":list (data .get ("mycalls",[])),
        "myinfo":data .get ("myinfo",{}),
        "mycalls_meta":data .get ("mycalls_meta",{}),
        "call_src":data .get ("call_src",{}),
        "call_src_full":data .get ("call_src_full",{}),
        }
    return out 
unit_test_full_caller_output =[
'"A" -> "A";',
'"A" -> "B" -> "H" -> "I" -> "J" -> "D";',
'"A" -> "B" -> "C" -> "D";',
'"A" -> "B" -> "E";\n"E" [style=dashed];',
'"A" -> "B" -> "G" -> "B";',
'"A" -> "B" -> "F";'
]
unit_test_noexterns_caller_output =[
'"A" -> "A";',
'"A" -> "B" -> "H" -> "I" -> "J" -> "D";',
'"A" -> "B" -> "C" -> "D";',
'"B" [color=red];',
'"A" -> "B" -> "G" -> "B";',
'"A" -> "B" -> "F";'
]
unit_test_maxdepth2_caller_output =[
'"A" -> "A";',
'"A" -> "B";\n"B" [color=red];',
'"A" -> "B";\n"B" [color=red];',
'"B" [color=red];',
'"A" -> "B";\n"B" [color=red];',
'"A" -> "B";\n"B" [color=red];'
]
unit_test_maxdepth3_caller_output =[
'"A" -> "A";',
'"A" -> "B" -> "H";\n"H" [color=red];',
'"A" -> "B" -> "C";\n"C" [color=red];',
'"A" -> "B" -> "E";\n"E" [style=dashed];',
'"A" -> "B" -> "G";\n"G" [color=red];',
'"A" -> "B" -> "F";'
]
unit_test_regex_caller_output =[
'"A" -> "A";','"A" -> "B" -> "H" -> "I" -> "J" -> "D";',
'"A" -> "B";\n"B" [color=red];',
'"B" [color=red];',
'"A" -> "B";\n"B" [color=red];',
'"A" -> "B" -> "F";']
unit_test_full_callee_output =[
'"A" -> "A" -> "B";','"main" -> "A" -> "B";','"B" -> "G" -> "B";'
]
unit_test_maxdepth4_callee_output =[
'"A" -> "A" -> "B" -> "C" -> "D";',
'"A" -> "B" -> "C" -> "D";\n"A" [color=red];',
'"G" -> "B" -> "C" -> "D";\n"G" [color=red];',
'"H" -> "I" -> "J" -> "D";\n"H" [color=red];'
]
unit_test_maxdepth5_callee_output =[
'"A" -> "A" -> "B" -> "C" -> "D";','"main" -> "A" -> "B" -> "C" -> "D";',
'"B" -> "G" -> "B" -> "C" -> "D";','"B" -> "H" -> "I" -> "J" -> "D";'
]


def instfunctions (functions :dict ):
    """Generate instances for functions called more than once and update caller references.

    Rules:
    - original function namePreserve the first call。
    - Append additional calls according to the global counter `@instanceN`。
    - Only handle user-defined functions inside `functions`; library functions not present in `functions` are ignored.
    - Do not expand recursion/loops; self-calls receive no special handling.
    """
    if not functions :
        return 

    call_count =defaultdict (int )
    for finfo in functions .values ():
        for target in finfo .get ("mycalls",[]):
            if target in functions :
                call_count [target ]+=1 

    clones ={}
    for fn ,cnt in call_count .items ():
        if cnt >1 :
            clones [fn ]=[f"{fn}@instance{i}"for i in range (1 ,cnt )]

    if not clones :
        return 

    for fn ,inst_names in clones .items ():
        if fn not in functions :
            continue 
        for inst_name in inst_names :
            functions [inst_name ]=copy .deepcopy (functions [fn ])

    seen =defaultdict (int )

    for fn ,finfo in functions .items ():
        mycalls =finfo .get ("mycalls",[])
        meta_map =finfo .get ("mycalls_meta",{})or {}
        call_src_full_map =finfo .get ("call_src_full",{})or {}

        new_calls =[]
        new_meta ={}
        new_call_src_full ={}

        for call in mycalls :
            target =call 
            if call in clones :
                seen [call ]+=1 
                idx =seen [call ]
                if idx >1 :
                    inst_list =clones [call ]
                    inst_idx =min (idx -2 ,len (inst_list )-1 )
                    target =inst_list [inst_idx ]
            new_calls .append (target )

            if call in meta_map :
                new_meta [target ]=meta_map [call ]
            elif target in meta_map :
                new_meta [target ]=meta_map [target ]

            if call in call_src_full_map :
                new_call_src_full [target ]=call_src_full_map [call ]
            elif target in call_src_full_map :
                new_call_src_full [target ]=call_src_full_map [target ]

        finfo ["mycalls"]=new_calls 
        finfo ["mycalls_meta"]=new_meta 
        finfo ["call_src_full"]=new_call_src_full 


        #
        # Actual unit test
        #
def unit_test ():
#
# Built test functions dictionary
#
    functions =dict ()
    unit_test_add_call (functions ,"main",["A"])
    unit_test_add_call (functions ,"A",["A","B"])
    unit_test_add_call (functions ,"B",["C","E","F","G","H"])
    unit_test_add_call (functions ,"C",["D"])
    unit_test_add_call (functions ,"D",[])
    # "E" does not exists, it's an external function
    unit_test_add_call (functions ,"F",[])
    unit_test_add_call (functions ,"G",["B"])
    unit_test_add_call (functions ,"H",["I"])
    unit_test_add_call (functions ,"I",["J"])
    unit_test_add_call (functions ,"J",["D"])

    build_callee_info (functions )

    #
    # Execute unit tests
    #
    print_dbg ("UNIT TEST START")
    print_dbg ("---------------")

    total =0 
    failures =0 

    #
    # Full graph dump
    #
    print_dbg ("")
    print_dbg ("FULL GRAPH")
    print_dbg ("============")
    total +=1 
    buffer =list ()
    full_call_graph (functions ,stdio_buffer =buffer )
    failures +=unit_test_check_error ("FULL GRAPH",
    unit_test_full_dump_output ,buffer )
    #
    # Full caller dump
    #
    print_dbg ("")
    print_dbg ("FULL CALLER")
    print_dbg ("===========")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"A",
    max_depth =0 ,
    exclude =None ,
    no_externs =False ,
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("FULL CALLER",
    unit_test_full_caller_output ,buffer )
    #
    # Full caller dump with no exters
    #
    print_dbg ("")
    print_dbg ("CALLER NO EXTERNS")
    print_dbg ("=================")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"A",
    max_depth =0 ,
    exclude =None ,
    no_externs =True ,
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLER, NO_EXTERNS",
    unit_test_noexterns_caller_output ,
    buffer )
    #
    # Caller with limit depth
    #
    print_dbg ("")
    print_dbg ("CALLER LIMITED DEPTH (2)")
    print_dbg ("========================")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"A",
    max_depth =2 ,
    exclude =None ,
    no_externs =False ,
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLER, MAX DEPTH 2",
    unit_test_maxdepth2_caller_output ,
    buffer )

    print_dbg ("")
    print_dbg ("CALLER LIMITED DEPTH (3)")
    print_dbg ("========================")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"A",
    max_depth =3 ,
    exclude =None ,
    no_externs =False ,
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLER, MAX DEPTH 3",
    unit_test_maxdepth3_caller_output ,
    buffer )
    #
    # Caller with limited by regex
    #
    print_dbg ("")
    print_dbg ("CALLER REGEX MATCH")
    print_dbg ("==================")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"A",
    max_depth =0 ,
    exclude ="C|E|G",
    no_externs =False ,
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLER, REGEX",
    unit_test_regex_caller_output ,
    buffer )
    #
    # Full callee
    #
    print_dbg ("")
    print_dbg ("CALLEE FULL")
    print_dbg ("===========")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"B",
    max_depth =0 ,
    reverse_path =True ,
    exclude =None ,
    call_index ="callee_calls",
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLEE, FULL",
    unit_test_full_callee_output ,
    buffer )
    #
    # Max depth callee
    #
    print_dbg ("")
    print_dbg ("CALLEE MAX DEPTH 4")
    print_dbg ("==================")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"D",
    max_depth =4 ,
    reverse_path =True ,
    exclude =None ,
    call_index ="callee_calls",
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLEE, MAX DEPTH 4",
    unit_test_maxdepth4_callee_output ,
    buffer )
    print_dbg ("")
    print_dbg ("CALLEE MAX DEPTH 5")
    print_dbg ("==================")
    total +=1 
    buffer =list ()
    dump_path ([],functions ,"D",
    max_depth =5 ,
    reverse_path =True ,
    exclude =None ,
    call_index ="callee_calls",
    stdio_buffer =buffer )
    failures +=unit_test_check_error ("CALLEE, MAX DEPTH 5",
    unit_test_maxdepth5_callee_output ,
    buffer )
    #
    # Show results
    #
    print_dbg ("")
    print_dbg ("UNIT TEST END, RESULTS")
    print_dbg ("----------------------")
    print_dbg ("Total tests run: {}".format (total ))
    print_dbg ("Total errors   : {}".format (failures ))
    if failures >0 :
        print_err ("!!! ERRORS WHERE FOUND !!!")

    return 0 


    #
    # unit_test_check_error()
    #
def unit_test_check_error (test ,ref ,results ):
    if len (results )==len (ref ):
        for i in range (0 ,len (results )):
            if results [i ]!=ref [i ]:
                print_err ("[FAIL] \"{}\" @line {}, \"{}\" vs \"{}\"".
                format (test ,i ,results [i ],ref [i ]))
                return 1 
    else :
        print_err ("[FAIL] {}".format (test ))
        return 1 

    return 0 


    #
    # unit_test_add_call
    #
def unit_test_add_call (functions ,function_name ,calls ):
    if function_name in functions :
        print ("ERROR: Function already defined!!")

    functions [function_name ]=dict ()
    functions [function_name ]["files"]=["unit_test.c"]
    functions [function_name ]["calls"]=dict ()
    for call in calls :
        functions [function_name ]["calls"][call ]=True 
    functions [function_name ]["refs"]=dict ()
    functions [function_name ]["callee_calls"]=dict ()
    functions [function_name ]["callee_refs"]=dict ()
    functions [function_name ]["mycalls"]=[]
    functions [function_name ]["myinfo"]={"tail":function_name }


    #
    # Add callee to database
    #


def build_callee_info (function_db ):
    for call ,value in function_db .items ():
        for callee in value ["calls"]:
            if callee in function_db and call not in function_db [callee ]["callee_calls"]:
                function_db [callee ]["callee_calls"][call ]=1 

        for callee in value ["refs"]:
            if callee in function_db and call not in function_db [callee ]["callee_refs"]:
                function_db [callee ]["callee_refs"][call ]=1 


                #
                # dump_path_ascii()
                #
def dump_path_ascii (path ,reverse ,**kwargs ):
    externs =kwargs .get ("externs",False )
    truncated =kwargs .get ("truncated",False )
    std_buf =kwargs .get ("stdio_buffer",None )

    if len (path )==0 :
        return 

    ascii_path =""
    for function in reversed (path )if reverse else path :
        if ascii_path !="":
            ascii_path +=" -> "
        ascii_path +='"'+function +'"'

    if truncated or externs :
        ascii_path +=';\n"{}"{}{}'.format (function if not reverse else path [-1 ],
        " [style=dashed]"if externs else "",
        " [color=red]"if truncated else "")

    print_buf (std_buf ,ascii_path +";")


    #
    # Dump path as ASCII to stdout
    #
def dump_path (path ,functions ,function_name ,**kwargs ):
    max_depth =kwargs .get ("max_depth",0 )
    reverse_path =kwargs .get ("reverse_path",False )
    exclude =kwargs .get ("exclude",None )
    call_index =kwargs .get ("call_index","calls")
    no_externs =kwargs .get ("no_externs",False )
    std_buf =kwargs .get ("stdio_buffer",None )

    #
    # Pass on __seen_in_path as a way to determine if a node in the graph
    # was already processed
    #
    if "__seen_in_path"in kwargs :
        seen_in_path =kwargs ["__seen_in_path"]
    else :
        seen_in_path =dict ()
        kwargs ["__seen_in_path"]=seen_in_path 

        #
        # If reached the max depth or Need to stop due to exclusion, recursion
        # display the path up till the previous entry.
        #
    if (exclude is not None and re .match (exclude ,function_name )is not None )or (max_depth >0 and len (path )>=max_depth ):
        dump_path_ascii (path ,reverse_path ,stdio_buffer =std_buf ,
        truncated =True )
        return 

        #
        # If already seen, we Need to terminate the path here...
        #
    if function_name in seen_in_path :
        if (max_depth <=0 or (len (path )+1 )<=max_depth ):
            dump_path_ascii (path +[function_name ],reverse_path ,
            stdio_buffer =std_buf )
        return 

    seen_in_path [function_name ]=True 

    #
    # Now walk the path for each child
    #
    children =0 
    for caller in functions [function_name ][call_index ]:
    #
    # The child is a known function, handle this trough recursion
    #
        if caller in functions :
            children +=1 
            if function_name !=caller :
                dump_path (path +[function_name ],
                functions ,caller ,**kwargs )
            else :
            #
            # This is a recurrence for this function, add it once
            #
                dump_path_ascii (path +[function_name ,caller ],reverse_path ,
                stdio_buffer =std_buf )

                #
                # This is a external child, so we can not handle this recursive.
                # However as there are no more children, we can handle it here
                # (if it can be included).
                #
        elif (exclude is None or re .match (exclude ,caller )is None )and (max_depth <=0 or (len (path )+2 )<=max_depth )and not no_externs :
            children +=1 
            dump_path_ascii (path +[function_name ,caller ],reverse_path ,
            externs =True ,stdio_buffer =std_buf )
        else :
            print_buf (std_buf ,'"{}" [color=red];'.
            format (function_name ))

            #
            # If there where no children, the path ends here, so dump it.
            #
    if children ==0 :
        dump_path_ascii (path +[function_name ],reverse_path ,
        stdio_buffer =std_buf )


        #
        # print_err()
        #
def print_err (text ):
    sys .stderr .write (text +"\n")


    #
    # print_dbg()
    #
def print_dbg (text ):
    sys .stderr .write ("DBG: "+text +"\n")


    #
    # print_buf()
    #
def print_buf (buf ,text ):
    if buf is not None :
        buf .append (text )
    print (text )


def _derive_debug_base (path :Path )->str :
    name =path .name 
    base =name .split (".c",1 )[0 ]if ".c"in name else path .stem 
    parent =path .parent .name if path .parent .name else ""
    if parent and parent not in (".",""):
        return f"{parent}_{base}"
    return base 


def _ensure_debug_dir (config )->Path :
    """Ensure the debug directory exists (for intermediate results and debug information)"""
    try :
        first_file =getattr (config ,"RTLFILE",[None ])[0 ]
    except Exception :
        first_file =None 

    if first_file :
        first_path =Path (first_file )
        # Create the debug folder in the input-file directory
        debug_dir =first_path .parent /"debug"
    else :
    # If there is no input file, use the current working directory
        debug_dir =Path .cwd ()/"debug"

    debug_dir .mkdir (parents =True ,exist_ok =True )
    return debug_dir 


def _ensure_output_dirs (config )->Tuple [Path ,Path ]:
    """
    Ensure the output-directory structure exists (three-stage layout)
    
    Stage 1 - Input: read source files and expand files from any location
    Stage 2 - intermediate_results: all temporary files produced during execution
    Stage 3 - config_files: final output provided to `dag_describe`
    
    Returns: `(config_dir, intermediate_dir)`
    - config_dir: config_files directory（final output used by `dag_describe`）
    - intermediate_dir: intermediate_resultsdirectory（temporary files created during processing）
    
    config_files directory structure (Stage 3 - flat layout, see `test/config_files/`):
    mycallypro/intermediate_results/<basename>/config_files/
    ├── circle.txt        # main config file
    ├── <basename>.dot    # DAGgraphFile
    ├── <basename>.c      # source codecopy (optional)
    └── <basename>.c.233r.expand  # expandFilecopy (optional)

    intermediate_resultsdirectory structure (Stage 2 - temporary files):
    mycallypro/intermediate_results/<basename>/
    ├── debug/            # debug JSON files
    ├── temp/             # temporaryDOT File
    ├── images/           # PNG images
    └── logs/             # log files
    
    Redundancy handling modes (hybrid mode):
    1. Default mode: directly overwrite existing directories and files
    2. `--smart`: smart detection; skip regeneration if the input file is unchanged
    3. `--clean`: clean rebuild; delete old directories before recreating them
    4. `--force`: force regeneration (used together with `--smart`)
    """
    import shutil 

    try :
        first_file =getattr (config ,"RTLFILE",[None ])[0 ]
    except Exception :
        first_file =None 

        # Get the base name (extracted from the expand filename)
    if first_file :
        first_path =Path (first_file )
        # Strip the `.expand` suffix to extract the base name
        base_name =first_path .stem 
        if base_name .endswith ('.233r'):
            base_name =base_name [:-5 ]
            # Uniformly strip trailing `.cpp`/`.c` extensions to avoid leaving `.cpp` in directory names
        if '.'in base_name :
            base_name =base_name .split ('.')[0 ]

            # Based on the `mycallypro` directory
        if hasattr (config ,'output_base')and config .output_base :
            root =Path (config .output_base ).resolve ()
        else :
        # defaultusemycallyprodirectory
            root =Path (__file__ ).parent 
    else :
        base_name ="default"
        root =Path (__file__ ).parent 

        # config_files directory：mycallypro/intermediate_results/basename/config_files（Stage 3 - flat layout）
    config_dir =root /"intermediate_results"/base_name /"config_files"

    # intermediate_resultsdirectory：mycallypro/intermediate_results/basename/（Stage 2 - temporary files）
    intermediate_dir =root /"intermediate_results"/base_name 

    # ========================================================================
    # Redundancy-handling logic (hybrid mode)
    # ========================================================================
    smart_mode =getattr (config ,'smart',False )
    clean_mode =getattr (config ,'clean',False )
    force_mode =getattr (config ,'force',False )

    # Mode 1: clean-rebuild mode (`--clean`) - clean only on the first call
    if clean_mode and not getattr (config ,'_cleaned',False ):
        if config_dir .exists ():
            if hasattr (config ,'debug')and config .debug :
                print_dbg (f"[CLEAN] Removing existing config directory: {config_dir}")
            shutil .rmtree (config_dir )
        if intermediate_dir .exists ():
            if hasattr (config ,'debug')and config .debug :
                print_dbg (f"[CLEAN] Removing existing intermediate directory: {intermediate_dir}")
            shutil .rmtree (intermediate_dir )
            # Mark as cleaned to avoid duplicate cleanup
        config ._cleaned =True 

        # Mode 2: smart-detection mode (`--smart`)
    elif smart_mode and not force_mode :
        if config_dir .exists ()and first_file :
        # Check whether the input file has been modified
            input_file =Path (first_file )
            circle_txt =config_dir /"circle.txt"

            if circle_txt .exists ():
                input_mtime =input_file .stat ().st_mtime 
                output_mtime =circle_txt .stat ().st_mtime 

                # If the input file is not newer than the output file, skip regeneration
                if input_mtime <=output_mtime :
                    if hasattr (config ,'debug')and config .debug :
                        print_dbg (f"[SMART] Skipping regeneration, files are up-to-date")
                        print_dbg (f"  Input: {input_file} (modified: {input_mtime})")
                        print_dbg (f"  Output: {circle_txt} (modified: {output_mtime})")
                        # Set a flag telling the caller to skip subsequent generation
                    config ._skip_generation =True 
                    return config_dir ,intermediate_dir 

                    # Mode 3: default overwrite mode (no extra arguments)
                    # Create directories directly; if they already exist, keep them, and later operations will overwrite files

                    # createconfig_files directory
    config_dir .mkdir (parents =True ,exist_ok =True )

    # Create the intermediate_results directory and its subdirectories
    intermediate_dir .mkdir (parents =True ,exist_ok =True )
    (intermediate_dir /"debug").mkdir (parents =True ,exist_ok =True )
    (intermediate_dir /"temp").mkdir (parents =True ,exist_ok =True )
    (intermediate_dir /"images").mkdir (parents =True ,exist_ok =True )
    (intermediate_dir /"logs").mkdir (parents =True ,exist_ok =True )

    return config_dir ,intermediate_dir 


def _write_debug_text (config ,tag :str ,content :str ,suffix :str ,*,timestamp :Optional [str ]=None )->None :
    """Write debug text files to the intermediate_results directory (Stage 2 - temporary files)"""
    # All debug files should be stored in the intermediate_results directory
    if hasattr (config ,'_intermediate_dir'):
        debug_dir =config ._intermediate_dir /"debug"
        debug_dir .mkdir (parents =True ,exist_ok =True )
    else :
        debug_dir =_ensure_debug_dir (config )

    ts =timestamp or datetime .now ().strftime ("%Y%m%d_%H%M%S_%f")
    path =debug_dir /f"{ts}_{tag}.{suffix}"
    try :
        path .write_text (content ,encoding ="utf-8")
    except Exception :
        pass 


def _dump_debug_snapshot (config ,tag :str ,payload :dict )->None :
    try :
        text =json .dumps (payload ,ensure_ascii =False ,indent =2 )
    except Exception :
        return 
    _write_debug_text (config ,tag ,text ,"json")


def _dump_debug_artifacts (functions ,dot_lines ,config ,tag ):
    timestamp =datetime .now ().strftime ("%Y%m%d_%H%M%S_%f")
    _write_debug_text (config ,tag ,"\n".join (dot_lines ),"dot",timestamp =timestamp )
    payload ={
    "rtl_files":getattr (config ,"RTLFILE",[]),
    "caller":getattr (config ,"caller",None ),
    "callee":getattr (config ,"callee",None ),
    "exclude":getattr (config ,"exclude",None ),
    "no_externs":getattr (config ,"no_externs",False ),
    "max_depth":getattr (config ,"max_depth",0 ),
    "functions":functions ,
    }
    try :
        text =json .dumps (payload ,ensure_ascii =False ,indent =2 )
    except Exception :
        return 
    _write_debug_text (config ,tag ,text ,"json",timestamp =timestamp )


    #
    # Dump function details:
    #
def dump_function_info (functions ,function ,details ):
    finfo =functions [function ]
    print ("  {}() {}".format (function ,
    finfo ["files"]if details else ""))
    if details :
        for caller in sorted (finfo ["calls"].keys ()):
            print ("    --> {}".format (caller ))

        if len (finfo ["calls"])>0 and len (finfo ["callee_calls"])>0 :
            print ("    ===")

        for caller in sorted (finfo ["callee_calls"].keys ()):
            print ("    <-- {}".format (caller ))

        print ("\n")


        #
        # Build full call graph
        #


        #The first modification is that function is used to print dotFile. Here, I will perform special processing on if, while, and switch.
def full_call_graph (functions ,**kwargs ):
    exclude =kwargs .get ("exclude",None )
    no_externs =kwargs .get ("no_externs",False )
    std_buf =kwargs .get ("stdio_buffer",None )
    threads_only =kwargs .get ("threads_only",False )
    extern_only =kwargs .get ("extern_only",False )
    print_buf (std_buf ,"strict digraph callgraph {")
    myjoin =re .compile (r"pthread_join")
    switch_re =re .compile (r"switch+(\d+)")
    tail =""

    #
    # Simply walk all nodes and print the callers
    #
    for func in sorted (functions .keys ()):
    # resetControl-flow state within each function to prevent cross-function mislinking
        has_if =0 
        count_if =0 
        count_switch =0 
        start_if =""
        end_if =""
        start_switch =""
        end_switch =""
        switchlist =dict ()
        preswtich =""
        prenum =1 
        meta_map =functions [func ].get ("mycalls_meta",{})
        myinfo =functions [func ].get ("myinfo",{})or {}
        create_targets =list (myinfo .get ("__create_queue__",[]))
        create_idx =0 
        printed_functions =1 
        pre =func 
        if exclude is None or re .match (exclude ,func )is None :

            callers =functions [func ]["mycalls"]
            idx =0 
            while idx <len (callers ):
                caller =callers [idx ]
                # In extern_only mode, calls with extern!=1 are filtered out based on mycalls_meta
                if extern_only :
                    meta =meta_map .get (caller ,{})
                    if not isinstance (meta ,dict )or meta .get ("extern")!=0 :
                        idx +=1 
                        continue 
                if (not no_externs or caller in functions )and (exclude is None or 
                re .match (exclude ,caller )is None ):
                # join_search = re.search(myjoin, caller)#Processing pthread——joinnode
                # if join_search is not None:
                #     for tail, join in resolve_join_edges(functions, func, caller):
                #         print_buf(std_buf, '"{}" -> "{}";'.format(tail, join))
                    if 'pthread_create'in caller :
                    # create special patch edge: create -> thread name node, and create -> call side next nodes
                        inline_next =callers [idx +1 ]if idx +1 <len (callers )else None 
                        has_inline_thread =bool (
                        inline_next and inline_next in functions and "/"not in inline_next 
                        )

                        next_thread_node =inline_next if has_inline_thread else None 
                        if not next_thread_node and create_idx <len (create_targets ):
                            next_thread_node =create_targets [create_idx ]
                        create_idx +=1 

                        if has_inline_thread :
                            caller_next =callers [idx +2 ]if idx +2 <len (callers )else None 
                        else :
                            caller_next =callers [idx +1 ]if idx +1 <len (callers )else None 

                        if pre !=caller :
                          print_buf (std_buf ,'"{}" -> "{}";'.format (pre ,caller ))
                        if next_thread_node :
                            print_buf (std_buf ,'"{}" -> "{}";'.format (caller ,next_thread_node ))
                        if caller_next and caller_next !=next_thread_node :
                            print_buf (std_buf ,'"{}" -> "{}";'.format (caller ,caller_next ))
                            pre =caller_next 
                            idx +=2 if has_inline_thread else 1 
                        else :
                            pre =caller 
                            idx +=2 if has_inline_thread else 1 
                        printed_functions +=1 
                        continue 

                    if not threads_only :
                    # conditionalnodehandling (only in non-threads-only mode)
                        if "if"in caller :
                            if count_if ==0 :
                                count_if =count_if +1 
                                start_if =pre 
                            print_buf (std_buf ,'"{}" -> "{}";'.format (pre ,caller ))
                            print_buf (std_buf ,'"{}" [style=dashed]'.format (caller ))
                        elif "while"in caller :
                            print_buf (std_buf ,'"{}" -> "{}";'.format (pre ,caller ))
                            print_buf (std_buf ,'"{}" [style=dashed]'.format (caller ))
                        elif "switch"in caller :
                            if count_switch ==0 :
                                count_switch =count_switch +1 
                                start_switch =pre 
                            switch_re_flag =re .search (switch_re ,caller )
                            search_switch ="switch"+switch_re_flag .group (1 )
                            if prenum !=switch_re_flag .group (1 ):
                                prenum =switch_re_flag .group (1 )
                                preswtich =start_switch 
                            else :
                                preswtich =pre 
                            switchlist [start_switch ]=dict ()
                            switchlist [start_switch ][search_switch ]=list ()
                            switchlist [start_switch ][search_switch ].append (caller )
                            print_buf (std_buf ,'"{}" -> "{}";'.format (start_switch ,caller ))
                            print_buf (std_buf ,'"{}" [style=dashed]'.format (caller ))
                        else :
                            if count_if >0 :
                                count_if =0 
                                end_if =caller 
                                print_buf (std_buf ,'"{}" -> "{}";'.format (pre ,end_if ))
                                print_buf (std_buf ,'"{}" -> "{}";'.format (start_if ,end_if ))
                            elif count_switch >0 :#switch the element connected to the last node
                                end_switch =caller 
                                for key in switchlist [start_switch ]:
                                    print_buf (std_buf ,'"{}" -> "{}";'.format (key [-1 ],end_switch ))
                                count_switch =0 
                                prenum =1 
                            else :
                                  print_buf (std_buf ,'"{}" -> "{}";'.format (pre ,caller ))
                    else :
                    # threads-only mode: only handle normal calls, not conditionalnode
                        if pre !=caller :
                          print_buf (std_buf ,'"{}" -> "{}";'.format (pre ,caller ))
                    printed_functions +=1 
                    pre =caller 
                idx +=1 
            if printed_functions ==0 :
                print_buf (std_buf ,'"{}"'.format (func ))
                #Complete patch edges here
    append_join_edges (functions ,std_buf )
    print_buf (std_buf ,"}")


def conditions_call_graph (functions ,**kwargs ):
    """Render a DOT that focuses on condition-prefixed calls only.

    - Only emits nodes whose names contain "if/", "while/", or start with "switch".
    - Connects consecutive conditional nodes within the same function in order.
    - Skips thread join/create edges on purpose.
    """
    exclude =kwargs .get ("exclude",None )
    no_externs =kwargs .get ("no_externs",False )
    std_buf =kwargs .get ("stdio_buffer",None )

    print_buf (std_buf ,"strict digraph callgraph {")
    cond_prefix =("if/","while/","switch")

    for func in sorted (functions .keys ()):
        if exclude is not None and re .match (exclude ,func )is not None :
            continue 

        prev_cond =None 
        emitted_any =False 
        for caller in functions [func ]["mycalls"]:
            if (exclude is not None and re .match (exclude ,caller )is not None ):
                continue 
            is_cond =any (part in caller for part in cond_prefix )
            if not is_cond :
                continue 

                # only keep nodes belonging to this function or externs allowed
            if no_externs and caller not in functions :
                continue 

            if prev_cond is None :
                print_buf (std_buf ,f'"{func}" -> "{caller}";')
            else :
                print_buf (std_buf ,f'"{prev_cond}" -> "{caller}";')
            print_buf (std_buf ,f'"{caller}" [style=dashed]')
            prev_cond =caller 
            emitted_any =True 

        if not emitted_any :
        # keep the function visible if no conditional nodes were found
            print_buf (std_buf ,f'"{func}"')

    print_buf (std_buf ,"}")


def mark_extern_by_selected (functions ,selected_file =None ,workspace_root =None ):
    """Mark the `extern` field in `mycalls_meta`.
    
    Logic:
    - Match selected files by filename only; successful matches are internal (`extern=0`), mismatches are external (`extern=1`)
    - If `selected_file` is not provided, default all calls to external (`extern=1`)

    Args:
        functions: Main data structure containing the `mycalls_meta` dictionary.
        selected_file: Selected source-file path (internal source file), optional string.
        workspace_root: Optional workspace root used to normalize relative paths.
    """
    # onlyCompare filenames only and ignore directories
    sel_name =Path (selected_file ).name if selected_file else None 

    for finfo in functions .values ():
        if "mycalls_meta"not in finfo :
            continue 
            # mycalls_meta is now a dictionary: {target_name: {file, line, col, extern}}
        for target_name ,meta in finfo ["mycalls_meta"].items ():
            file_path =meta .get ("file")
            if not file_path :
                meta ["extern"]=1 
                continue 

            if sel_name is None :
            # If no selected file is specified, default all calls to external
                meta ["extern"]=1 
            else :
                cur_name =Path (file_path ).name 
                # Only match by File name: Match = internal call (0), mismatch = external call (1)
                meta ["extern"]=0 if cur_name ==sel_name else 1 

join_binding_map ={
"handle_to_thread":{},
"thread_to_tail":{},
"handle_to_joins":{},
"tail_to_joins":{},
}


def build_join_binding_map (functions :dict )->None :
    """buildfour-level mapping：handle->threadfunction、threadfunction->tail node、handle->join、tail node->join。"""
    global join_binding_map 
    join_binding_map ={
    "handle_to_thread":{},
    "thread_to_tail":{},
    "handle_to_joins":{},
    "tail_to_joins":{},
    }
    for fn_name ,finfo in functions .items ():
        myinfo =finfo .get ("myinfo",{})or {}
        tail_node =myinfo .get ("tail")
        if isinstance (tail_node ,str ):
            join_binding_map ["thread_to_tail"][fn_name ]=tail_node 
            # handle -> threadfunction（handlefrom create records）
        for key ,val in myinfo .items ():
            if key in ("tail","__create_queue__","__source_create_queue__"):
                continue 
            if not isinstance (key ,str )or not isinstance (val ,str ):
                continue 
                # Skip join entries (join_node -> handle); they contain '/' in key
            if "/"in key :
                continue 
            join_binding_map ["handle_to_thread"][key ]=val 
            # handle -> join node（from join records：join_node -> handle）
        for join_node ,join_var in myinfo .items ():
            if join_node in ("tail","__create_queue__","__source_create_queue__"):
                continue 
            if not isinstance (join_var ,str ):
                continue 
                # Only process join entries: key contains 'pthread_join'
            if "pthread_join"not in join_node :
                continue 
            join_binding_map ["handle_to_joins"].setdefault (join_var ,[]).append (join_node )
            # tail node -> join node: handle -> threadfunction -> tail node, and then the join list corresponding to the handle
    for handle ,thread_fn in join_binding_map ["handle_to_thread"].items ():
        tail =join_binding_map ["thread_to_tail"].get (thread_fn )
        if not tail :
            continue 
        joins =join_binding_map ["handle_to_joins"].get (handle ,[])
        if joins :
            join_binding_map ["tail_to_joins"].setdefault (tail ,[]).extend (joins )


def append_join_edges (functions :dict ,std_buf :list ):
    """Append join patch edges according to the global mapping: `tail node -> join node`."""
    global join_binding_map 
    for tail ,joins in join_binding_map .get ("tail_to_joins",{}).items ():
        for j in joins :
            print_buf (std_buf ,f'"{tail}" -> "{j}";')
def preparse_pthread_join_bindings (rtl_files ,*,max_backtrack_lines :int =300 ):
    """Pre-read the RTL file and extract the thread-variable names used by `pthread_join` in appearance order.

    Returns:
        list[str]: join_bindings
            join_bindings[i] corresponds to the  i+1 -th `pthread_join` variable name; return an empty string if parsing fails.
    """
    join_bindings =[]
    try :
        lines =[]
        for rtl in rtl_files :
            lines .extend (Path (rtl ).read_text (encoding ="utf-8",errors ="replace").splitlines (keepends =True ))

        join_call_re =re .compile (r'.*\(call\s+\(mem:QI\s+\(symbol_ref:DI\s+\("pthread_join"\)')
        set_di_re =re .compile (r".*\(set\s+\(reg:DI\s+5\s+di\).*")
        symbol_ref_name_re =re .compile (r'\(symbol_ref:[A-Z]+\s+\("(?P<name>[^"]+)"\)')
        dbg_reg_re =re .compile (r"\(reg:DI\s+(?P<regno>\d+)\s+\[\s+(?P<dbg>[^\]]+)\s+\]\)")
        plain_reg_re =re .compile (r"\(reg:DI\s+(?P<regno>\d+)\b(?!\s+\[)")

        def base_name (raw :str )->str :
            token =raw .strip ().split ()[0 ]
            if "."in token :
                token =token .split (".",1 )[0 ]
            return token 

        def gather_chunk (start :int ,max_lines :int =12 )->str :
            buf =[]
            for k in range (start ,min (len (lines ),start +max_lines )):
                buf .append (lines [k ])
                if "))"in lines [k ]:
                    break 
            return "".join (buf )

        def name_from_chunk (chunk :str ):
            sym =symbol_ref_name_re .search (chunk )
            if sym is not None :
                name =sym .group ("name")
                if not name .startswith ("*.LC"):
                    return name 
            dbg =dbg_reg_re .search (chunk )
            if dbg is not None :
                return base_name (dbg .group ("dbg"))
            return None 

        def rhs_regno (chunk :str ):
            dbg =dbg_reg_re .search (chunk )
            if dbg is not None :
                return int (dbg .group ("regno"))
            plain =plain_reg_re .search (chunk )
            if plain is not None :
                return int (plain .group ("regno"))
            return None 

        def find_prev_set_reg (start :int ,regno :int ):
            needle =f"(set (reg:DI {regno}"
            for j in range (start ,max (-1 ,start -max_backtrack_lines ),-1 ):
                if needle in lines [j ]:
                    return j 
            return None 

        def resolve_join_var (call_idx :int )->str :
            set_di_idx =None 
            for j in range (call_idx ,max (-1 ,call_idx -max_backtrack_lines ),-1 ):
                if set_di_re .match (lines [j ]):
                    set_di_idx =j 
                    break 
            if set_di_idx is None :
                return ""

            chunk =gather_chunk (set_di_idx )
            name =name_from_chunk (chunk )
            if name :
                return name 

            regno =rhs_regno (chunk )
            if regno is None :
                return ""

            visited =set ()
            cur_regno =regno 
            cur_start =set_di_idx -1 
            for _ in range (20 ):
                if cur_regno in visited :
                    return ""
                visited .add (cur_regno )
                prev_set =find_prev_set_reg (cur_start ,cur_regno )
                if prev_set is None :
                    return ""
                prev_chunk =gather_chunk (prev_set )
                name =name_from_chunk (prev_chunk )
                if name :
                    return name 
                next_regno =rhs_regno (prev_chunk )
                if next_regno is None or next_regno ==cur_regno :
                    return ""
                cur_regno =next_regno 
                cur_start =prev_set -1 
            return ""

        for i ,line in enumerate (lines ):
            if join_call_re .match (line )is None :
                continue 
            join_bindings .append (resolve_join_var (i ))
    except Exception :
        return []

    return join_bindings 


    # ---------------------------------------------------------------------------
    # Source-based create/join binding (platform-independent)
    # ---------------------------------------------------------------------------

_SRC_CREATE_RE =re .compile (
r"pthread_create\s*\(\s*(?:&\s*)?(\w+)\s*,"# arg0: &handle
r"\s*[^,]+,\s*(\w+)"# arg2: start_routine
)
_SRC_JOIN_RE =re .compile (
r"pthread_join\s*\(\s*(\w+)"# arg0: handle
)


def _fixup_create_join_bindings_from_source (functions :dict ,config )->None :
    """Post-process: re-derive create/join handle bindings from C source lines.

    For every pthread_create / pthread_join node that has a valid source line
    number in mycalls_meta, read that line from the C source and extract the
    handle variable name and (for create) the task function name.  Then patch
    myinfo, mycalls, and __create_queue__ so that:
      1. build_join_binding_map() can produce correct tail_to_joins (join edges)
      2. full_call_graph() sees correct function names in mycalls (create edges)

    This replaces the old RTL-register-based approach which only worked on
    x86_64.
    """
    # Resolve source file path once
    source_file =getattr (config ,"source_file",None )
    if source_file :
        source_path =Path (str (source_file ))
    else :
        source_path =None 

        # Cache: source path -> list of lines
    _src_cache :dict ={}

    def _read_src_lines (file_hint :str )->list :
        """Read and cache source file lines."""
        # Try source_path first (--source-file), then file_hint from meta
        for candidate in [source_path ,Path (file_hint )if file_hint else None ]:
            if candidate is None :
                continue 
            key =str (candidate )
            if key in _src_cache :
                return _src_cache [key ]
            try :
                lines =candidate .read_text (encoding ="utf-8",errors ="ignore").splitlines ()
                _src_cache [key ]=lines 
                return lines 
            except Exception :
                continue 
        return []

    for fn_name ,finfo in functions .items ():
        meta =finfo .get ("mycalls_meta",{})
        myinfo =finfo .get ("myinfo",{})
        mycalls =finfo .get ("mycalls",[])
        if not meta :
            continue 

            # Collect create bindings: create_node -> (handle, task_fn)
        create_bindings :dict ={}

        for node ,node_meta in meta .items ():
            line_no =node_meta .get ("line")
            file_hint =node_meta .get ("file")
            if not line_no :
                continue 

            is_create ="pthread_create"in node 
            is_join ="pthread_join"in node 
            if not is_create and not is_join :
                continue 

            src_lines =_read_src_lines (file_hint )
            if not src_lines or line_no <1 or line_no >len (src_lines ):
                continue 
            src_line =src_lines [line_no -1 ]

            if is_create :
                m =_SRC_CREATE_RE .search (src_line )
                if m :
                    handle ,task_fn =m .group (1 ),m .group (2 )
                    create_bindings [node ]=(handle ,task_fn )
                    # Patch myinfo: handle -> task_fn
                    myinfo [handle ]=task_fn 

            elif is_join :
                m =_SRC_JOIN_RE .search (src_line )
                if m :
                    handle =m .group (1 )
                    # Patch myinfo: join_node -> handle
                    myinfo [node ]=handle 

                    # --- Fix mycalls and __create_queue__ ---
                    # In mycalls, after each "xxx/pthread_createN" node, the RTL parser
                    # appended resolved_target.  On ARM64 this is the handle variable name
                    # (e.g. "thread_c0") instead of the task function (e.g. "worker_c0").
                    # We Need to replace those handle names with the correct function names.
        if create_bindings :
        # Build handle_name -> task_fn mapping from all create bindings
            handle_to_task ={handle :task for _node ,(handle ,task )in create_bindings .items ()}

            # Fix mycalls: replace handle variable names with function names
            for i ,entry in enumerate (mycalls ):
                if entry in handle_to_task :
                    mycalls [i ]=handle_to_task [entry ]

                    # Rebuild __create_queue__ with correct function names
            new_queue =[]
            for _node ,(handle ,task_fn )in sorted (create_bindings .items ()):
                if task_fn not in new_queue :
                    new_queue .append (task_fn )
            myinfo ["__create_queue__"]=new_queue 


def _resolve_symbol_from_reg_history (lines :list ,reg_num :str ,*,max_hops :int =8 ,scan_window :int =8 )->str :
    """Resolve symbol_ref by backtracking DI register assignments."""
    current =str (reg_num )
    rhs_reg_re =re .compile (r"\(reg:DI\s+(?P<reg>\d+)(?:\s+\w+)?\)")
    rhs_sym_re =re .compile (r'\(symbol_ref:DI\s+\("(?P<target>[^"]+)"\)')

    for _ in range (max_hops ):
        assign_idx =-1 
        assign_re =re .compile (rf"\(set\s+\(reg:DI\s+{re.escape(current)}(?:\s+\w+)?\)")
        for i in range (len (lines )-1 ,-1 ,-1 ):
            if assign_re .search (lines [i ]):
                assign_idx =i 
                break 
        if assign_idx <0 :
            return ""

        end =min (len (lines ),assign_idx +scan_window )
        window ="\n".join (lines [assign_idx :end ])
        m_sym =rhs_sym_re .search (window )
        if m_sym :
            return m_sym .group ("target")

        regs =rhs_reg_re .findall (window )
        next_reg =""
        for r in regs :
            if r !=current :
                next_reg =r 
                break 
        if not next_reg :
            return ""
        current =next_reg 

    return ""


    #
    # Main()
    #
def main ():
#
# Data sets
#
    functions =dict ()
    # Globally control whether conditional prefixes are added
    add_condition_prefix =True 

    #
    # Command line argument parsing
    #
    parser =argparse .ArgumentParser ()

    parser .add_argument ("-d","--debug",
    help ="Enable debugging",action ="store_true")
    parser .add_argument ("-f","--functions",metavar ="FUNCTION",
    help ="Dump functions name(s)",
    type =str ,default ="&None",const ="&all",
    action ='store',nargs ='?')
    parser .add_argument ("--callee",
    help ="Callgraph for the function being called",
    type =str ,metavar ="FUNCTION",action ='append')
    parser .add_argument ("--caller",
    help ="Callgraph for functions being called by",
    type =str ,metavar ="FUNCTION",action ='append')
    parser .add_argument ("-e","--exclude",
    help ="RegEx for functions to exclude",
    type =str ,metavar ="REGEX")
    parser .add_argument ("--no-externs",
    help ="Do not show external functions",
    action ="store_true")
    parser .add_argument ("--no-warnings",
    help ="Do not show warnings on the console",
    action ="store_true")
    parser .add_argument ("--max-depth",metavar ="DEPTH",
    help ="Maximum tree depth traversal, default no depth",
    type =int ,default =0 )
    parser .add_argument ("--unit-test",help =argparse .SUPPRESS ,
    action ="store_true")
    parser .add_argument ("--conditions-only",
    help ="Render only condition-prefixed nodes (if/while/switch)",
    action ="store_true")
    parser .add_argument ("--threads-only",
    help ="Render only thread edges without condition nodes",
    action ="store_true")
    parser .add_argument ("--export-txt",
    help ="Export circle.txt config file to specified path",
    type =str ,metavar ="PATH")
    parser .add_argument ("--source-file",
    help ="Source code file path for extracting line numbers",
    type =str ,metavar ="PATH")
    parser .add_argument ("--output-base",
    help ="Base directory for output (config_files and intermediate_results)",
    type =str ,metavar ="PATH")

    # redundancy-handling mode arguments (hybrid mode)
    parser .add_argument ("--smart",
    help ="Smart mode: skip regeneration if input files unchanged",
    action ="store_true")
    parser .add_argument ("--clean",
    help ="Clean mode: remove existing directories before regeneration",
    action ="store_true")
    parser .add_argument ("--force",
    help ="Force mode: force regeneration even in smart mode",
    action ="store_true")
    parser .add_argument ("--extern-only",
    help ="When generating the source-call graph, only output nodes/edges with `extern==1`",
    action ="store_true")
    parser .add_argument (
    "--level1-stage1",
    help ="Generate Level-1(stage1) segments and segment-DAG (create/join only) under intermediate_results/<base>/dag_generation/",
    action ="store_true",
    )

    parser .add_argument ("RTLFILE",help ="GCCs RTL .expand file",nargs ="+")

    parser .parse_args ()
    config =parser .parse_args ()

    #
    # If the unit test option is specified jump straight into it...
    #
    if config .unit_test :
        return unit_test ()

        #
        # Additional option checks
        #
    if config .caller and config .callee :
        print_err ("ERROR: Either --caller or --callee option should be given, "
        "not both!")
        return 1 

    if config .exclude is not None :
        try :
            exclude_regex =re .compile (config .exclude )
        except Exception as e :
            print_err ("ERROR: Invalid --exclude regular expression, "
            "\"{}\" -> \"{}\"!".
            format (config .exclude ,e ))
            return 1 
    else :
        exclude_regex =None 

    if not config .caller and not config .callee and config .max_depth :
        print_err ("ERROR: The --max_depth option is only valid with "
        "--caller or --callee!")
        return 1 

        #
        # Check if all files exist
        #
    for file in config .RTLFILE :
        if not os .path .isfile (file )or not os .access (file ,os .R_OK ):
            print_err ("ERROR: Can't open rtl file, \"{}\"!".format (file ))
            return 1 

            #
            # Regex to extract functions
            #
            #Second modification: this is the read stage, which stores parsed information in the data structure for later rendering
    function =re .compile (
    r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)(,.*)?\).*$")
    call =re .compile (
    r"^.*\(call.*\"(?P<target>.*)\".*$")
    symbol_ref =re .compile (r"^.*\(symbol_ref.*\"(?P<target>.*)\".*$")#identify function calls
    src_re =re .compile (r'\"(?P<file>[^\"]+)\":(?P<line>\d+):(?P<col>\d+)')#identify source-code location
    mytaskset =re .compile (r".*\(set\s+\(reg:DI\s+1\s+dx\)")#identify the thread-name register
    mytask =re .compile (r".*\(symbol_ref:DI \(\"(?P<target>.*?)\"[^\"]*\)")#identify the thread-create function
    mythreadset =re .compile (r".*\(set\s+\(reg:DI\s+5\s+di\)")#identify the thread-address register
    mythread =re .compile (r".*\(symbol_ref:DI \(\"(?P<target>.*?)\"\)")#identify the thread-address name
    myjointhread =re .compile (r".*\(reg:DI \d+ \[ (thread\d*).*\]")#identify the name corresponding to thread join
    condition_myjump =re .compile (r"\(jump_insn\s+(\d+)")
    condition_if =re .compile (r".*\(if_then_else")
    condition_jump =re .compile (r".*\(label_ref\s+(\d+)")
    condition_barrier =re .compile (r"\(barrier")
    condition_code =re .compile (r"\(code_label\s+(\d+)")
    exist =0 # whether the conditional flag appears; initial state is 1
    exist_flag =0 # conditional flag 0 means a `while` loop, 1 means an `if` condition
    jump_flag =0 #used to determine whether the previous step encountered a jump
    if_flag =0 #used to determine whether the previous step encountered an if-then
    barrier_flag =0 #determine whether the previous line contains a barrier
    #state flags
    jump_1 =1 
    jump_2 =0 
    jump_3 =0 
    jump_4 =0 
    #
    # Parse each line in each file given
    #
    functions_pre =dict ()
    function_name =None 
    join_bindings =[]#store pthread_join binding information and record bound threads in order
    #pre-read stage
    for line in fileinput .input (config .RTLFILE ):
        match =re .match (function ,line )
        if match is not None :
            function_name =match .group ("function")
            if function_name in functions :#note: this is redefined; correct code executes only the `else` branch
                if not config .no_warnings :#whether to print error information
                    print_err ("WARNING: Function {} defined in multiple"
                    "files \"{}\"!".
                    format (function_name ,
                    ', '.join (map (
                    str ,
                    functions [function_name ]["files"]+
                    [fileinput .filename ()]))))
            else :
                functions_pre [function_name ]=list ()
        else :
        # blank lines/comments before a function definition must be skipped
            current_pre =functions_pre .get (function_name )
            if current_pre is None :
                continue 
            if jump_1 ==1 :
                condition_myjump_flag =re .match (condition_myjump ,line )
                if condition_myjump_flag is not None :
                    jump_2 =1 
                    jump_1 =0 
            elif jump_2 ==1 :
                condition_if_flag =re .match (condition_if ,line )
                if condition_if_flag is not None :
                    jump_3 =1 
                    jump_2 =0 
                else :
                    condition_jump_flag =re .match (condition_jump ,line )
                    if condition_jump_flag is not None :
                        num =condition_jump_flag .group (1 )
                        current_pre .append (("jump1",num ))
                        jump_2 =0 
                        jump_1 =1 
            elif jump_3 ==1 :
                condition_jump_flag =re .match (condition_jump ,line )
                if condition_jump_flag is not None :
                    num =condition_jump_flag .group (1 )
                    current_pre .append (("jump",num ))
                    jump_3 =0 
                    jump_1 =1 
            condition_code_flag =re .match (condition_code ,line )
            if condition_code_flag is not None :
                    num =condition_code_flag .group (1 )
                    current_pre .append (("code",num ))
                    #pre-read stage of parsepthread_join
                    #generate code here
    join_bindings =preparse_pthread_join_bindings (config .RTLFILE )
    #code generation ends here
    #Process the pre-read stage
    #process `jump1`
    jump_flag =0 
    for functions_pre_name in functions_pre :
        jump_flag =0 
        for key in functions_pre [functions_pre_name ]:
            if key [0 ]=="jump":
                index =functions_pre [functions_pre_name ].index (key )+1 
                for key_test in functions_pre [functions_pre_name ][index :]:
                    if key_test [0 ]=="code"and key_test [1 ]<key [1 ]:
                        jump_flag =1 
            if key [0 ]=="jump1"and jump_flag ==1 :
                for key_test in functions_pre [functions_pre_name ][index :]:
                    if key_test [0 ]=="jump1"and key_test [1 ]==key [1 ]:
                        newindex =functions_pre [functions_pre_name ].index (key_test )
                        functions_pre [functions_pre_name ][newindex ]=("jump",key_test [1 ])
                        jump_flag =0 

                        #delete the code
    key_exist =0 
    for functions_pre_name in functions_pre :
        for key in functions_pre [functions_pre_name ]:
            if key [0 ]=="code":
                key_exist =0 
                for key_test in functions_pre [functions_pre_name ]:
                    if key_test [0 ]=="jump"and key_test [1 ]==key [1 ]:
                        key_exist =1 
                if key_exist ==0 :
                    functions_pre [functions_pre_name ].remove (key )
            elif key [0 ]=="jump1":
                functions_pre [functions_pre_name ].remove (key )

    _dump_debug_snapshot (
    config ,
    "control_prefix",
    {
    "rtl_files":list (getattr (config ,"RTLFILE",[])),
    "functions_pre":functions_pre ,
    },
    )

    def next_line_generator ():
    # use fileinput.input() open the file and create an iterator
        with fileinput .input (files =config .RTLFILE )as file :
            for line in file :
                yield line 
                # Since fileinput.input() returns an iterator, we try topre-read the next line
                try :
                    next_line =next (file )
                except StopIteration :
                # there is no next line
                    next_line =None 
                else :
                # ifread next line Success, stash it and yield it on the next iteration
                    yield next_line 

                    # use the generator to fetch the next line
    next_line_gen =next_line_generator ()

    function_name =""
    mytarget =""
    thread_num =""#the function read, which may be `create_num` or `join_num`
    create_num =""#used to bind `create` and the number
    join_num =""#Used to bind join and num
    join_index =0 # Which pthread_join (0-based) is used to access join_bindings[join_index]
    start_time =time .time ()
    flag =0 
    state_1 =1 
    state_2 =0 
    state_3 =1 
    state_4 =0 
    state_5 =0 
    state_6 =0 
    state_7 =0 
    state_8 =0 
    state_9 =0 
    switch_count =0 #determine switch branches
    excuted =0 #determine whether the first condition has already executed
    state_count =0 #count which item the current parse step has reached

    # set whether to add the conditional prefix based on the `threads_only` parameter
    add_condition_prefix =not getattr (config ,"threads_only",False )
    current_func =""#record the current line and the last function call encountered
    function_source =0 #marker indicating whether the previous line read a function; if so, record the function source file
    create_flag =0 
    line_history =[]
    for line in next_line_gen :
        line_history .append (line )
        if len (line_history )>300 :
            line_history .pop (0 )
            #
            # Find function entry point
            #
        match =re .match (function ,line )
        if match is not None :
            count =0 
            function_name =match .group ("function")
            if function_name in functions :
                if not config .no_warnings :
                    print_err ("WARNING: Function {} defined in multiple"
                    "files \"{}\"!".
                    format (function_name ,
                    ', '.join (map (
                    str ,
                    functions [function_name ]["files"]+
                    [fileinput .filename ()]))))
            else :
                functions [function_name ]=dict ()
                functions [function_name ]["files"]=list ()
                functions [function_name ]["calls"]=dict ()
                functions [function_name ]["call_src"]=dict ()# original target name -> source file
                functions [function_name ]["call_src_full"]=dict ()# numbered target name -> source file
                functions [function_name ]["refs"]=dict ()
                functions [function_name ]["callee_calls"]=dict ()
                functions [function_name ]["callee_refs"]=dict ()
                functions [function_name ]["mycalls"]=list ()
                functions [function_name ]["myinfo"]=dict ()
                functions [function_name ]["mycalls_meta"]=dict ()# function-call metadata：target -> {file, line, col, extern}
                state_count =0 

            functions [function_name ]["files"].append (fileinput .filename ())
            line_history =[line ]
            #
            # find thread
        else :
        #identify in two edge phases
            excuted =0 
            if function_name !="":
                length =functions_pre [function_name ].__len__ ()
                if state_count <length :
                    if state_1 ==1 :
                        condition_code_flag =re .match (condition_code ,line )
                        if condition_code_flag is not None :
                            if condition_code_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                                state_1 =0 
                                state_2 =1 
                                state_3 =0 
                    elif state_2 ==1 :
                        condition_jump_flag =re .match (condition_jump ,line )
                        if condition_jump_flag is not None :
                            if condition_jump_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                                state_1 =1 
                                state_2 =0 
                                state_3 =1 
                                excuted =1 
                    if state_3 ==1 and excuted ==0 :
                        condition_jump_flag =re .match (condition_jump ,line )
                        if condition_jump_flag is not None :
                            if condition_jump_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                                state_4 =1 
                                # state_5 = 1
                                state_3 =0 
                                state_1 =0 
                    elif state_4 ==1 :
                        condition_code_flag =re .match (condition_code ,line )
                        if condition_code_flag is not None :
                            if condition_code_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                                state_4 =0 
                                # state_5 = 0
                                state_3 =1 
                                state_1 =1 #identified as `if`
                        else :
                            condition_jump_flag =re .match (condition_jump ,line )
                            if condition_jump_flag is not None :
                                if condition_jump_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                    state_count =state_count +1 
                                    state_4 =0 
                                    state_5 =1 #identified as `switch` and read the first jump
                                    switch_count =0 
                    elif state_5 ==1 :# until code is recognized
                        condition_jump_flag =re .match (condition_jump ,line )#consume the jump
                        if condition_jump_flag is not None :
                            if condition_jump_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                        else :
                            condition_code_flag =re .match (condition_code ,line )
                            if condition_code_flag is not None :
                                if condition_code_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                    state_count =state_count +1 
                                    state_6 =1 
                                    state_5 =0 
                    elif state_6 ==1 :
                        condition_jump_flag =re .match (condition_jump ,line )#if it is a jump, enter state 7; if it is code, end
                        if condition_jump_flag is not None :
                            if condition_jump_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                                state_7 =1 
                                state_6 =0 
                                switch_count =switch_count +1 
                        else :
                            condition_code_flag =re .match (condition_code ,line )
                            if condition_code_flag is not None :
                                if condition_code_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                    state_count =state_count +1 
                                    state_6 =0 
                                    state_3 =1 
                                    state_1 =1 
                                    switch_count =switch_count +1 
                    elif state_7 ==1 :#code has been read; return to state 6
                        condition_code_flag =re .match (condition_code ,line )
                        if condition_code_flag is not None :
                            if condition_code_flag .group (1 )==functions_pre [function_name ][state_count ][1 ]:
                                state_count =state_count +1 
                                state_7 =0 
                                state_6 =1 
                                #create uses a trigger mechanism: after reading the register, the next symbol identifies it
            match_mythreadset =re .match (mythreadset ,line )
            if match_mythreadset is not None :
                create_flag =1 ;#marker noting that the next thread name belongs to create
            else :
                match_mythread =re .match (mythread ,line )
                if match_mythread is not None :
                    thread_num =match_mythread .group ("target")
                    if create_flag ==1 :
                        create_num =thread_num #used to bind `create` and the number
                        create_flag =0 ;
                        # join binding no longer depends on pre-reading `symbol_ref` here; uniformly use `join_bindings + join_index`
                        # else:
                        #     match_mythread = re.match(myjointhread, line)
                        #     if match_mythread is not None:
                        #         thread_num = match_mythread.group(1)
                        #         flag = 0;
                        #     else:
                        #         flag += 1

                        # Find direct function calls
                        #find the thread name
            match_mytaskset =re .match (mytaskset ,line )
            if match_mytaskset is not None :
                try :
                    next_line =next (next_line_gen )# get next line
                    if next_line is not None :
                        line_history .append (next_line )
                        if len (line_history )>300 :
                            line_history .pop (0 )
                    match_mytask =re .match (mytask ,next_line )
                    if match_mytask is not None :
                        mytarget =match_mytask .group ("target")
                        #function_source = 1
                except StopIteration :
                    next_line =None # End of File, no next line
            match =re .match (call ,line )
            if match is not None :
                if not function_name :
                    continue 
                count +=1 
                src_match =src_re .search (line )
                src_file =Path (src_match .group ("file")).name if src_match else None 
                target =match .group ("target")
                if target =="puts":
                    target ="printf"
                elif target =="fwrite":
                    target ="fprintf"
                origin_target =target 
                # if exist==1:
                #     if exist_flag==0:
                #         target="while/"+target
                #     elif exist_flag==1:
                #         target="if/"+target
                if add_condition_prefix :
                    if state_2 ==1 :
                        target ="while/"+target 
                    elif state_4 ==1 :
                        target ="if/"+target 
                    elif state_6 ==1 :
                        target ="switch"+str (switch_count )+"/"+target 
                        # elif state_7==1:
                        #     switch_count=switch_count+1
                if origin_target not in functions :
                    target =function_name +"/"+target +str (count )
                if 'pthread_create'in target :
                # Backtrack call arguments from RTL:
                # reg1(dx) carries start routine, reg5(di) carries thread handle.
                    reg_task =_resolve_symbol_from_reg_history (line_history ,"1")
                    reg_handle =_resolve_symbol_from_reg_history (line_history ,"5")
                    if reg_handle :
                        create_num =reg_handle 
                    resolved_target =mytarget 
                    if reg_task :
                        resolved_target =reg_task 
                    if not resolved_target :
                        pending =functions [function_name ]["myinfo"].get ("__source_create_queue__")
                        if pending is None :
                            files =functions [function_name ].get ("files",[])
                            selected_source =getattr (config ,"source_file",None )
                            source_override =Path (selected_source )if selected_source else None 
                            if files :
                                pending =create_targets_from_source (
                                Path (files [0 ]),
                                function_name ,
                                source_override =source_override ,
                                )
                            else :
                                pending =[]
                            functions [function_name ]["myinfo"]["__source_create_queue__"]=pending 
                        if pending :
                            resolved_target =pending .pop (0 )

                    if resolved_target :
                        functions [function_name ]["calls"][resolved_target ]=True 
                    functions [function_name ]["mycalls"].append (target )
                    if resolved_target :
                        functions [function_name ]["mycalls"].append (resolved_target )
                        functions [function_name ]["myinfo"]["tail"]=resolved_target 
                        functions [function_name ]["myinfo"][create_num ]=resolved_target 
                    queue =functions [function_name ]["myinfo"].setdefault ("__create_queue__",[])
                    if resolved_target :
                        queue .append (resolved_target )
                        # add mycalls_meta records
                    functions [function_name ]["mycalls_meta"][target ]={"file":None ,"line":None ,"col":None ,"extern":0 }
                    current_func =target 
                    function_source =1 
                else :
                    is_join =('pthread_join'in target )
                    if is_join :
                        if join_index <len (join_bindings ):
                            join_num =join_bindings [join_index ]
                        else :
                            join_num =""
                        join_index +=1 
                        # record the call and its source file (using the final target name, including numbering/prefix)
                    functions [function_name ]["calls"][origin_target ]=True 
                    # record the source file only when source position parsing succeeds
                    if src_file :
                        functions [function_name ]["call_src"][origin_target ]=src_file 
                        functions [function_name ]["call_src_full"][target ]=src_file 
                    functions [function_name ]["mycalls"].append (target )
                    functions [function_name ]["myinfo"]["tail"]=target 
                    # add mycalls_meta records
                    functions [function_name ]["mycalls_meta"][target ]={"file":None ,"line":None ,"col":None ,"extern":0 }
                    current_func =target 
                    function_source =1 
                    if is_join :
                        functions [function_name ]["myinfo"][target ]=join_num 


            else :
                match =re .match (symbol_ref ,line )
                if match is not None :
                    if not function_name :
                        continue 
                    target =match .group ("target")
                    if not target :
                        continue 
                    if target not in functions [function_name ]["refs"]:
                        functions [function_name ]["refs"][target ]=True 

                        # Rule for recognizing newly created entries: when source-position information is read, bind the current function call to the source-file location
            if function_source ==1 :
                const_loc =re .compile (r'"\s*(?P<file>[^"]+)"\s*:(?P<line>\d+):(?P<col>\d+)')
                match_const_loc =re .search (const_loc ,line )
                if match_const_loc is not None :
                    if current_func in functions [function_name ]["mycalls_meta"]:
                        functions [function_name ]["mycalls_meta"][current_func ]["file"]=match_const_loc .group ("file")
                        functions [function_name ]["mycalls_meta"][current_func ]["line"]=int (match_const_loc .group ("line"))
                        functions [function_name ]["mycalls_meta"][current_func ]["col"]=int (match_const_loc .group ("col"))
                    function_source =0 

    try :
        thread_edges_preview =collect_thread_edges (copy .deepcopy (functions ))
    except Exception :
        thread_edges_preview =[]
        #perform instantiation here
    instfunctions (functions )
    #compute the final table statistics here
    _fixup_create_join_bindings_from_source (functions ,config )
    build_join_binding_map (functions )
    _dump_debug_snapshot (
    config ,
    "post_parse",
    {
    "rtl_files":list (getattr (config ,"RTLFILE",[])),
    "functions":functions ,
    "thread_edges_preview":thread_edges_preview ,
    },
    )

    if config .debug :
        print_dbg ("[PERF] Processing {} RTL files took {:.9f} seconds".format (
        len (config .RTLFILE ),time .time ()-start_time ))
        print_dbg ("[PERF] Found {} functions".format (len (functions )))
        #
        # Build callee data
        #
    start_time =time .time ()

    build_callee_info (functions )

    if config .debug :
        print_dbg ("[PERF] Building callee info took {:.9f} seconds".format (
        time .time ()-start_time ))

        # On every parse, mark the `extern` field in `mycalls_meta`
        # If `source_file` is provided, calls matching that file are internal (`extern=1`); otherwise they are external (`extern=0`)
    workspace_root =os .getcwd ()
    selected_file =getattr (config ,"source_file",None )
    mark_extern_by_selected (functions ,selected_file ,workspace_root =workspace_root )

    _dump_debug_snapshot (
    config ,
    "post_callee_info",
    {
    "rtl_files":list (getattr (config ,"RTLFILE",[])),
    "functions":functions ,
    "thread_edges_preview":thread_edges_preview ,
    },
    )

    # export the full `functions` data structure for debugging
    try :
        base_dir =Path (config .output_base )if getattr (config ,"output_base",None )else Path .cwd ()
        first_rtl =Path (config .RTLFILE [0 ])
        base_name =first_rtl .stem 
        if base_name .endswith (".233r"):
            base_name =base_name [:-5 ]
        if "."in base_name :
            base_name =base_name .split (".")[0 ]
        out_dir =base_dir /"intermediate_results"/base_name /"dag_generation"
        out_dir .mkdir (parents =True ,exist_ok =True )
        functions_path =out_dir /"functions_full.json"
        with functions_path .open ("w",encoding ="utf-8")as f :
            json .dump (_serialize_functions_for_dump (functions ),f ,ensure_ascii =False ,indent =2 )
        if not config .no_warnings :
            print_dbg (f"[INFO] functions_full exported to {functions_path}")

            # Additional debug output: full functions and mycalls_meta
        debug_dir =out_dir /"debug"
        debug_dir .mkdir (parents =True ,exist_ok =True )
        debug_functions_path =debug_dir /"functions_debug.json"
        with debug_functions_path .open ("w",encoding ="utf-8")as f :
            json .dump (_serialize_functions_for_dump (functions ),f ,ensure_ascii =False ,indent =2 )
        mycalls_meta_path =debug_dir /"mycalls_meta.json"
        mycalls_meta_data ={fn :data .get ("mycalls_meta",{})for fn ,data in functions .items ()}
        with mycalls_meta_path .open ("w",encoding ="utf-8")as f :
            json .dump (mycalls_meta_data ,f ,ensure_ascii =False ,indent =2 )
            # additionally export mycalls_meta (internal calls) with extern==0
        internal_meta_path =debug_dir /"mycalls_meta_internal.json"
        internal_meta ={}
        for fn ,meta_map in mycalls_meta_data .items ():
            if not isinstance (meta_map ,dict ):
                continue 
            filtered ={k :v for k ,v in meta_map .items ()if isinstance (v ,dict )and v .get ("extern")==0 }
            internal_meta [fn ]=filtered 
        with internal_meta_path .open ("w",encoding ="utf-8")as f :
            json .dump (internal_meta ,f ,ensure_ascii =False ,indent =2 )
        if not config .no_warnings :
            print_dbg (f"[INFO] debug artifacts exported to {debug_dir}")

            # additionally exportfunction range (used for Level-1 splitting): first_stmt_line / last_stmt_line is preferred
        try :
            source_file =getattr (config ,"source_file",None )
            if source_file :
                src_path =Path (str (source_file ))
                if src_path .exists ()and src_path .suffix .lower ()==".c":
                    ranges =extract_func_ranges (src_path ,functions .keys ())
                    ranges_path =out_dir /"functions_ranges.json"
                    payload ={
                    "source":str (src_path ),
                    "functions":[
                    {
                    "name":r .name ,
                    "base_name":r .base_name ,
                    "start_line":r .start_line ,
                    "body_start_line":r .body_start_line ,
                    "first_stmt_line":r .first_stmt_line ,
                    "end_line":r .end_line ,
                    "last_stmt_line":r .last_stmt_line ,
                    "last_return_line":r .last_return_line ,
                    "level1_start_line":r .first_stmt_line if r .first_stmt_line is not None else r .body_start_line ,
                    "level1_end_line":r .last_stmt_line if r .last_stmt_line is not None else r .end_line ,
                    }
                    for r in ranges 
                    ],
                    "missing":sorted ([n for n in functions .keys ()if n not in {r .name for r in ranges }]),
                    }
                    with ranges_path .open ("w",encoding ="utf-8")as f :
                        json .dump (payload ,f ,ensure_ascii =False ,indent =2 )
                    if not config .no_warnings :
                        print_dbg (f"[INFO] functions_ranges exported to {ranges_path}")
        except Exception as e :
            if not config .no_warnings :
                print_err (f"WARNING: failed to export functions_ranges: {e}")

                # Level-1(stage1): segments + segment DAG (create/join only)
        try :
            if getattr (config ,"level1_stage1",False ):
                segments_json ,dag_json =build_stage1_segments_and_dag (base_dir =base_dir ,base_name =base_name )
                level1_dir =base_dir /"intermediate_results"/base_name /"level1"/"stage1"
                level1_dir .mkdir (parents =True ,exist_ok =True )
                seg_path =level1_dir /"segments_stage1.json"
                dag_path =level1_dir /"dag_stage1_seg.json"
                dot_path =level1_dir /"dag_stage1_seg.dot"
                seg_path .write_text (json .dumps (segments_json ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
                dag_path .write_text (json .dumps (dag_json ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
                # Render dot inline (no graphviz dependency here)
                try :
                    from ..level1 .segment_dag import _render_seg_dag_dot # type: ignore
                except Exception :
                    try :
                        from level1 .segment_dag import _render_seg_dag_dot # type: ignore
                    except Exception :
                        _render_seg_dag_dot =None # type: ignore
                if _render_seg_dag_dot is not None :
                    dot_path .write_text (_render_seg_dag_dot (dag_json ),encoding ="utf-8")# type: ignore[misc]
                if not config .no_warnings :
                    print_dbg (f"[INFO] level1 stage1 exported: {seg_path}, {dag_path}, {dot_path}")
        except Exception as e :
            if not config .no_warnings :
                print_err (f"WARNING: failed to export level1 stage1: {e}")
    except Exception as e :
        if not config .no_warnings :
            print_err (f"WARNING: failed to export functions_full: {e}")

            #
            # Dump functions if requested
            #
    if config .functions !="&None":
        print ("\nFunction dump")
        print ("-------------")
        if config .functions =="&all":
            for func in sorted (functions .keys ()):
                dump_function_info (functions ,func ,config .debug )
        else :
            if config .functions in functions :
                dump_function_info (functions ,config .functions ,config .debug )
            else :
                print_err ("ERROR: Can't find callee, \"{}\" in RTL data!".
                format (config .callee ))
                return 1 
        return 0 

    start_time =time .time ()

    # additionally export call_src_full mapping table (numbered target name -> Source File)
    try :
        base_dir =Path (config .output_base )if getattr (config ,"output_base",None )else Path .cwd ()
        # use the first RTL file to infer the base name
        first_rtl =Path (config .RTLFILE [0 ])
        base_name =first_rtl .stem 
        if base_name .endswith (".233r"):
            base_name =base_name [:-5 ]
        if "."in base_name :
            base_name =base_name .split (".")[0 ]
        out_dir =base_dir /"intermediate_results"/base_name /"dag_generation"
        out_dir .mkdir (parents =True ,exist_ok =True )
        call_src_full_path =out_dir /"call_src_full.json"
        call_src_full_data ={fn :data .get ("call_src_full",{})for fn ,data in functions .items ()}
        with call_src_full_path .open ("w",encoding ="utf-8")as f :
            json .dump (call_src_full_data ,f ,ensure_ascii =False ,indent =2 )
        if not config .no_warnings :
            print_dbg (f"[INFO] call_src_full exported to {call_src_full_path}")
    except Exception as e :
        if not config .no_warnings :
            print_err (f"WARNING: failed to export call_src_full: {e}")
            #
            # Dump full call graph
            #
    if not config .caller and not config .callee :
        dot_lines =[]
        if getattr (config ,"conditions_only",False ):
            conditions_call_graph (functions ,
            exclude =config .exclude ,
            no_externs =config .no_externs ,
            stdio_buffer =dot_lines )
            _dump_debug_artifacts (functions ,dot_lines ,config ,"conditions")
        else :
            threads_only =getattr (config ,"threads_only",False )
            full_call_graph (functions ,
            exclude =config .exclude ,
            no_externs =config .no_externs ,
            threads_only =threads_only ,
            extern_only =getattr (config ,"extern_only",False ),
            stdio_buffer =dot_lines )
            _dump_debug_artifacts (functions ,dot_lines ,config ,"threads"if threads_only else "full")

            #
            # Build callgraph for callee function
            #
    if config .callee and len (config .callee )!=0 :
        for callee in config .callee :
            if callee not in functions :
                print_err ("ERROR: Can't find callee \"{}\" in RTL data!".
                format (callee ))
                return 1 
        dot_lines =[]
        print_buf (dot_lines ,"strict digraph callgraph {")
        for callee in config .callee :
            print_buf (dot_lines ,'"{}" [color=blue, style=filled];'.format (callee ))
            dump_path ([],functions ,callee ,
            max_depth =config .max_depth ,
            reverse_path =True ,
            exclude =exclude_regex ,
            call_index ="callee_calls",
            stdio_buffer =dot_lines )
        print_buf (dot_lines ,"}")
        _dump_debug_artifacts (functions ,dot_lines ,config ,"callee")

        #
        # Build callgraph for caller function
        #
    elif config .caller and len (config .caller )!=0 :
        for caller in config .caller :
            if caller not in functions :
                print_err ("ERROR: Can't find caller \"{}\" in RTL data!".
                format (caller ))
                return 1 
        dot_lines =[]
        print_buf (dot_lines ,"strict digraph callgraph {")
        for caller in config .caller :
            print_buf (dot_lines ,'"{}" [color=blue, style=filled];'.format (caller ))
            dump_path ([],functions ,caller ,
            max_depth =config .max_depth ,
            exclude =exclude_regex ,
            no_externs =config .no_externs ,
            stdio_buffer =dot_lines )
        print_buf (dot_lines ,"}")
        _dump_debug_artifacts (functions ,dot_lines ,config ,"caller")

    if config .debug :
        print_dbg ("[PERF] Generating .dot file took {:.9f} seconds".format (
        time .time ()-start_time ))

        # ========================================================================
        # Export the `circle.txt` config files.
        #
        # Rule: when generation uses `output_base` to enter the canonical output directory, `circle.txt` should always stay synchronized with
        # The latest expand / DAG be refreshed together; callers should not Need to pass `--export-txt` explicitly.
        # ========================================================================
    should_export_circle =bool (getattr (config ,"export_txt",None )or getattr (config ,"output_base",None ))
    if should_export_circle :
        try :
            try :
                from .exporters import export_circle_txt 
            except ImportError :
                sys .path .append (str (Path (__file__ ).resolve ().parent .parent ))
                from generation .exporters import export_circle_txt 

                # always use the canonical directory structure
                # if `output_base` is not specified, default to the mycallypro directory
            if not hasattr (config ,'output_base')or not config .output_base :
                config .output_base =str (Path (__file__ ).parent )

            config_dir ,intermediate_dir =_ensure_output_dirs (config )

            # Check whether generation should be skipped (file unchanged in smart mode)
            if getattr (config ,'_skip_generation',False ):
                if config .debug :
                    print_dbg ("[INFO] Skipping file generation (smart mode, files up-to-date)")
                return 0 

                # attach directory information to the config object for debugging functions
            config ._config_dir =config_dir 
            config ._intermediate_dir =intermediate_dir 
            # Save `circle.txt` to the config_files directory
            txt_path =config_dir /"circle.txt"

            # getexpandFilepath
            expand_file =Path (config .RTLFILE [0 ])

            # Get the source-file path (if provided)
            source_file =None 
            if hasattr (config ,'source_file')and config .source_file :
                source_file =Path (config .source_file )

                # export the txt file
            if config .debug :
                print_dbg (f"[INFO] Exporting circle.txt to: {txt_path}")

            export_circle_txt (
            functions =functions ,
            expand_file =expand_file ,
            output_path =txt_path ,
            source_file =source_file 
            )

            if config .debug :
                print_dbg (f"[INFO] Successfully exported circle.txt")

        except Exception as e :
            print_err (f"ERROR: Failed to export circle.txt: {e}")
            if config .debug :
                import traceback 
                traceback .print_exc ()

                # ========================================================================
                # if output_base is specified, save the DOT file and source file to the config_files directory (flat structure)
                # ========================================================================
    if hasattr (config ,'output_base')and config .output_base and dot_lines :
        try :
            import shutil 

            config_dir ,intermediate_dir =_ensure_output_dirs (config )
            config ._config_dir =config_dir 
            config ._intermediate_dir =intermediate_dir 

            # Get the base name for naming files
            expand_file =Path (config .RTLFILE [0 ])
            base_name =expand_file .stem 
            if base_name .endswith ('.233r'):
                base_name =base_name [:-5 ]
                # Strip `.cpp`/`.c` and similar extensions to keep it consistent with the intermediate_results directory
            if '.'in base_name :
                base_name =base_name .split ('.')[0 ]

                # Save the DOT file to the config_files root directory (flat structure)
            dot_filename =f"{base_name}.dot"
            if hasattr (config ,'threads_only')and config .threads_only :
                dot_filename =f"{base_name}_threads.dot"
            elif hasattr (config ,'conditions_only')and config .conditions_only :
                dot_filename =f"{base_name}_full.dot"

            dot_path =config_dir /dot_filename 
            dot_content ='\n'.join (dot_lines )
            dot_path .write_text (dot_content ,encoding ='utf-8')

            if config .debug :
                print_dbg (f"[INFO] Saved DOT file to: {dot_path}")

                # copy the expand file to the config_files root directory
            if expand_file .exists ():
                expand_dest =config_dir /expand_file .name 
                try :
                    if expand_file .resolve ()!=expand_dest .resolve ():
                        shutil .copy2 (expand_file ,expand_dest )
                        if config .debug :
                            print_dbg (f"[INFO] Copied expand file to: {expand_dest}")
                    else :
                        if config .debug :
                            print_dbg (f"[INFO] Expand file already in place: {expand_dest}")
                except Exception as e :
                    print_err (f"WARNING: failed to copy expand file: {e}")

                    # Copy the source file to the config_files root directory (if provided)
            if hasattr (config ,'source_file')and config .source_file :
                source_file =Path (config .source_file )
                if source_file .exists ():
                    source_dest =config_dir /source_file .name 
                    try :
                        if source_file .resolve ()!=source_dest .resolve ():
                            shutil .copy2 (source_file ,source_dest )
                            if config .debug :
                                print_dbg (f"[INFO] Copied source file to: {source_dest}")
                        else :
                            if config .debug :
                                print_dbg (f"[INFO] Source file already in place: {source_dest}")
                    except Exception as e :
                        print_err (f"WARNING: failed to copy source file: {e}")

                        # If PNG generation is needed, save it to the `images` directory under intermediate_results
                        # PNG files are not part of the config files needed by dag_describe

        except Exception as e :
            print_err (f"ERROR: Failed to save files: {e}")

    return 0 


    #
    # Start main() as default entry point...
    #
if __name__ =='__main__':
    exit (main ())
