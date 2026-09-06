from __future__ import annotations 

import hashlib 
import re 
from pathlib import Path 
from typing import Dict ,List ,Optional ,Tuple 

from .constants import CONFIG_DIR_NAME ,GEN_DIR_NAME ,PIPELINE_DIR_NAME ,RESULTS_ROOT_NAME ,SCHEMA_VERSION 
from .errors import StageError 
from .io_utils import mark_failed ,mark_running ,mark_success ,write_json 

_MU_LOCK_RE =re .compile (r"(^|/)pthread_mutex_lock(\d+)?$")
_MU_UNLOCK_RE =re .compile (r"(^|/)pthread_mutex_unlock(\d+)?$")


def _parse_sem_pairs (circle_path :Path )->List [Dict [str ,str ]]:
    if not circle_path .exists ():
        return []
    pairs :Dict [str ,Dict [str ,Optional [str ]]]={}
    block =None 
    for line in circle_path .read_text (encoding ="utf-8",errors ="ignore").splitlines ():
        s =line .strip ()
        if not s :
            continue 
        if s =="mutex":
            block ="mutex"
            continue 
        if s =="semaphore":
            block ="sem"
            continue 
        if block !="sem":
            continue 
        parts =s .split ()
        if len (parts )<3 :
            continue 
        node =parts [0 ]
        idx =parts [2 ]
        rec =pairs .setdefault (idx ,{"post":None ,"wait":None })
        if "sem_post"in node :
            rec ["post"]=node 
        elif "sem_wait"in node :
            rec ["wait"]=node 
    out :List [Dict [str ,str ]]=[]
    for idx ,rec in pairs .items ():
        if rec ["post"]and rec ["wait"]:
            out .append ({"idx":idx ,"post_node":str (rec ["post"]),"wait_node":str (rec ["wait"])})
    return out 


def _parse_mutex_intervals (internal_meta_path :Path )->Dict [str ,List [Tuple [int ,int ]]]:
    if not internal_meta_path .exists ():
        return {}
    import json 

    data =json .loads (internal_meta_path .read_text (encoding ="utf-8"))
    if not isinstance (data ,dict ):
        return {}

    intervals :Dict [str ,List [Tuple [int ,int ]]]={}
    for fn ,meta_map in data .items ():
        if not isinstance (fn ,str )or not isinstance (meta_map ,dict ):
            continue 
        stack :List [int ]=[]
        for node ,meta in meta_map .items ():
            if not isinstance (node ,str )or not isinstance (meta ,dict ):
                continue 
            line =meta .get ("line")
            if not isinstance (line ,int ):
                continue 
            if _MU_LOCK_RE .search (node ):
                stack .append (line )
            elif _MU_UNLOCK_RE .search (node ):
                if not stack :
                    continue 
                lock_line =stack .pop ()
                if lock_line <=line :
                    intervals .setdefault (fn ,[]).append ((lock_line ,line ))
    for fn in list (intervals .keys ()):
        intervals [fn ].sort ()
    return intervals 


def collect_block_info (*,base_dir :Path ,base_name :str ,source_file :Path )->Dict :
    results_root =base_dir /RESULTS_ROOT_NAME /base_name 
    pipeline_root =results_root /PIPELINE_DIR_NAME 
    pipeline_root .mkdir (parents =True ,exist_ok =True )
    meta_path =pipeline_root /"block_info_meta.json"
    mark_running (meta_path ,step ="collector")

    gen_root =results_root /GEN_DIR_NAME 
    config_root =results_root /CONFIG_DIR_NAME 

    dag_dot =gen_root /"dag.dot"
    functions_full =gen_root /"functions_full.json"
    functions_ranges =gen_root /"functions_ranges.json"
    internal_meta =gen_root /"debug"/"mycalls_meta_internal.json"
    circle_txt =config_root /"circle.txt"

    # Best-effort: keep a frozen copy of the source under config_files for traceability/debugging.
    # This does NOT replace the need to regenerate dag_generation outputs when the source changes.
    resolved_source =source_file .resolve ()
    config_root .mkdir (parents =True ,exist_ok =True )
    config_source_guess =config_root /resolved_source .name 
    try :
        import shutil 

        if resolved_source .exists ():
            shutil .copy2 (resolved_source ,config_source_guess )
    except Exception :
    # Non-fatal; collector is primarily a validator/deriver stage.
        pass 

    required =[dag_dot ,functions_full ,functions_ranges ,internal_meta ,circle_txt ]
    missing =[str (p )for p in required if not p .exists ()]
    if missing :
        error =f"missing required inputs: {', '.join(missing)}"
        mark_failed (meta_path ,step ="collector",error =error )
        raise StageError (error )

        # Consistency guard: generation artifacts (functions_ranges/internal_meta) must match the source_file
        # used by later stages. If the user edited the source after running "dag_generation", line numbers in
        # mycalls_meta_internal.json can drift and cause incorrect segmentation.
    import json 

    ranges_obj =json .loads (functions_ranges .read_text (encoding ="utf-8",errors ="replace"))
    ranges_source =ranges_obj .get ("source")
    ranges_source_path :Optional [Path ]=None 
    if isinstance (ranges_source ,str )and ranges_source .strip ():
    # functions_ranges.json typically records a project-relative path like "mycallyplus_v1/Source File/xxx.c"
        ranges_source_path =Path (ranges_source )
        if not ranges_source_path .is_absolute ():
        # If it already includes the base_dir name prefix, resolve from base_dir.parent to avoid
        # duplicating ".../mycallyplus_v1/mycallyplus_v1/...".
            parts =ranges_source_path .parts 
            if parts and parts [0 ]==base_dir .name :
                ranges_source_path =(base_dir .parent /ranges_source_path ).resolve ()
            else :
                ranges_source_path =(base_dir /ranges_source_path ).resolve ()

    if ranges_source_path and ranges_source_path !=resolved_source :
        error =(
        "source mismatch between pipeline input and generation artifacts:\n"
        f"- collector source_file: {resolved_source}\n"
        f"- functions_ranges.json source: {ranges_source_path}\n"
        "Please rerun the DAG generation step with the same source, or pass the correct --source."
        )
        mark_failed (meta_path ,step ="collector",error =error )
        raise StageError (error )

        # If the source file is newer than generation artifacts, refuse to proceed to avoid mixed-code runs.
    newest_gen_mtime =max (p .stat ().st_mtime for p in (dag_dot ,functions_full ,functions_ranges ,internal_meta ))
    if resolved_source .exists ()and resolved_source .stat ().st_mtime >newest_gen_mtime :
        error =(
        "source file is newer than generation artifacts under intermediate_results/<base>/dag_generation.\n"
        f"- source_file: {resolved_source}\n"
        f"- generation dir: {gen_root}\n"
        "Rerun the DAG generation step (dag_generation / one-click generateconfig_files) to regenerate dag.dot,"
        "functions_*.json, and mycalls_meta_internal.json, then rerun the pipeline."
        )
        mark_failed (meta_path ,step ="collector",error =error )
        raise StageError (error )

    sem_pairs =_parse_sem_pairs (circle_txt )
    mutex_intervals =_parse_mutex_intervals (internal_meta )

    derived_dir =pipeline_root /"derived"
    derived_dir .mkdir (parents =True ,exist_ok =True )
    if sem_pairs :
        write_json (derived_dir /"sem_pairs.json",{"pairs":sem_pairs })
    if mutex_intervals :
        write_json (derived_dir /"mutex_intervals.json",{"intervals":mutex_intervals })

    def _sha256_16 (p :Path )->Optional [str ]:
        if not p .exists ()or not p .is_file ():
            return None 
        h =hashlib .sha256 ()
        with p .open ("rb")as f :
            for chunk in iter (lambda :f .read (1024 *1024 ),b""):
                h .update (chunk )
        return h .hexdigest ()[:16 ]

    block_info ={
    "schema_version":SCHEMA_VERSION ,
    "base_name":base_name ,
    "source_file":str (source_file .resolve ()),
    "source_checks":{
    "functions_ranges_source":str (ranges_source_path )if ranges_source_path else None ,
    "sha256_16":_sha256_16 (resolved_source ),
    "config_copy":str (config_source_guess )if config_source_guess .exists ()else None ,
    "config_copy_sha256_16":_sha256_16 (config_source_guess )if config_source_guess .exists ()else None ,
    },
    "inputs":{
    "dag_dot":str (dag_dot ),
    "functions_full":str (functions_full ),
    "functions_ranges":str (functions_ranges ),
    "mycalls_meta_internal":str (internal_meta ),
    "circle_txt":str (circle_txt ),
    },
    "capabilities":{"has_circle_txt":circle_txt .exists ()},
    }
    write_json (pipeline_root /"block_info.json",block_info )
    mark_success (
    meta_path ,
    step ="collector",
    extra ={"has_circle_txt":circle_txt .exists (),"sem_pairs":len (sem_pairs ),"mutex_functions":len (mutex_intervals )},
    )
    return block_info 
