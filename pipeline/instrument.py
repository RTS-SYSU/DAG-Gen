from __future__ import annotations 

import re 
import shutil 
import subprocess 
from pathlib import Path 
from typing import Dict ,Set 

from ..level1 .instrument_prio_level1 import instrument_prio_program_timing_and_segment_priorities 

from .constants import FINAL_RESULTS_DIR_NAME 
from .errors import StageError 
from .instrument_levelx import instrument_prio_all_segments_by_start_line 
from .io_utils import mark_failed ,mark_running ,mark_success ,read_json ,write_json 
from .schedule_render import build_const_binding ,render_annotated_schedule_dag ,render_annotated_schedule_dag_value 


def _render_dot (dot_text :str ,dot_path :Path ,png_path :Path )->None :
    dot_path .parent .mkdir (parents =True ,exist_ok =True )
    dot_path .write_text (dot_text ,encoding ="utf-8")
    try :
        subprocess .run (["dot","-Tpng",str (dot_path ),"-o",str (png_path )],check =True ,capture_output =True )
    except Exception :
    # Keep dot output even when graphviz is unavailable.
        pass 


def _render_dot_file_to_png (dot_path :Path ,png_path :Path )->None :
    png_path .parent .mkdir (parents =True ,exist_ok =True )
    try :
        subprocess .run (["dot","-Tpng",str (dot_path ),"-o",str (png_path )],check =True ,capture_output =True )
    except Exception as exc :
        raise StageError (f"failed to render dot to png: {dot_path}")from exc 


def _render_round_node_dot_to_png (dot_path :Path ,png_path :Path )->None :
    text =dot_path .read_text (encoding ="utf-8",errors ="ignore")
    if "node [shape=box" in text :
        text =text .replace ('node [shape=box, fontname="Consolas", fontsize=10];','node [shape=ellipse, fontname="Consolas", fontsize=10];',1 )
    elif "node [" in text :
        text =re .sub (r'node\s*\[(.*?)\];',r'node [\1, shape=ellipse];',text ,count =1 ,flags =re .S )
    else :
        text =text .replace ("{","{\n  node [shape=ellipse, fontname=\"Consolas\", fontsize=10];",1 )

    round_dot_path =png_path .with_suffix (".round.dot")
    round_dot_path .write_text (text ,encoding ="utf-8")
    _render_dot_file_to_png (round_dot_path ,png_path )


def _publish_results (
*,
base_dir :Path ,
base_name :str ,
level :str ,
rule_name :str ,
algo_name :str ,
source_file :Path ,
instrumented_source :Path ,
)->Path :
    results_root =base_dir /FINAL_RESULTS_DIR_NAME /base_name
    graphs_dir =results_root /"graphs"
    algorithms_dir =results_root /"algorithms"
    results_dir =algorithms_dir /algo_name
    if results_dir .exists ():
        shutil .rmtree (results_dir )

    source_dir =results_dir /"source"
    meta_dir =results_dir /"meta"
    graphs_dir .mkdir (parents =True ,exist_ok =True )
    algorithms_dir .mkdir (parents =True ,exist_ok =True )
    source_dir .mkdir (parents =True ,exist_ok =True )
    meta_dir .mkdir (parents =True ,exist_ok =True )

    original_dag_dot =base_dir /"intermediate_results"/base_name /"level2"/"merge_post_wait"/"dag_level2_sem.dot"
    original_dag_png =base_dir /"intermediate_results"/base_name /"dag_generation"/"dag.png"
    block_dag =base_dir /"intermediate_results"/base_name /"pipeline"/"blocks"/level /rule_name /"dag_seg.png"
    published_source =source_dir /instrumented_source .name

    if not original_dag_dot .exists ()and not original_dag_png .exists ():
        raise StageError (f"missing original DAG source: {original_dag_dot}")
    if not block_dag .exists ():
        raise StageError (f"missing block DAG png: {block_dag}")
    if not instrumented_source .exists ():
        raise StageError (f"missing instrumented source: {instrumented_source}")

    published_original_dag =graphs_dir /"original_dag.png"
    if original_dag_dot .exists ():
        _render_round_node_dot_to_png (original_dag_dot ,published_original_dag )
    else :
        shutil .copy2 (original_dag_png ,published_original_dag )
    shutil .copy2 (block_dag ,graphs_dir /"block_dag.png")
    shutil .copy2 (instrumented_source ,published_source )

    write_json (
    meta_dir /"summary.json",
    {
    "base_name":base_name ,
    "level":level ,
    "rule_name":rule_name ,
    "algo_name":algo_name ,
    "source_file":str (source_file ),
    "result_dir":str (results_dir ),
    "results_root":str (results_root ),
    "artifacts":{
    "original_dag":str (published_original_dag ),
    "block_dag":str (graphs_dir /"block_dag.png"),
    "instrumented_source":str (published_source ),
    },
    "inputs":{
    "original_dag":str (original_dag_dot if original_dag_dot .exists ()else original_dag_png ),
    "block_dag":str (block_dag ),
    "instrumented_source":str (instrumented_source ),
    },
    },
    )
    return results_dir 


def run_instrument (
*,
base_dir :Path ,
base_name :str ,
level :str ,
rule_name :str ,
algo_name :str ,
instrument_mode :str ="auto",
)->Dict :
    pipeline_root =base_dir /"intermediate_results"/base_name /"pipeline"
    instrument_root =pipeline_root /"instrument"/level /rule_name 

    # v3.0: New directory structure result/ + timing/
    result_root =instrument_root /"result"
    timing_root =instrument_root /"timing"

    # v3.0: clean up legacy algorithm subdirectories kept from older naming schemes.
    _KNOWN_ALGOS ={"LPF","FIFO","heft","t_level","zhao2020","cpf","lpf","wcet_first"}
    if instrument_root .exists ():
        for old_dir in instrument_root .iterdir ():
            if old_dir .is_dir ()and old_dir .name in _KNOWN_ALGOS :
                shutil .rmtree (old_dir ,ignore_errors =True )
    for legacy_root in (result_root ,timing_root ):
        if legacy_root .exists ():
            for old_dir in legacy_root .iterdir ():
                if old_dir .is_dir ()and old_dir .name in _KNOWN_ALGOS :
                    shutil .rmtree (old_dir ,ignore_errors =True )

                # status tracking uses status File under instrument_root
    meta_path =instrument_root /"instrument_status.json"
    mark_running (meta_path ,step ="instrument",extra ={"algo_name":algo_name })

    try :
        block_info =read_json (pipeline_root /"block_info.json")
        source_file =Path (str (block_info ["source_file"])).resolve ()
        dag_json_path =pipeline_root /"blocks"/level /rule_name /"dag_seg.json"
        segments_json_path =pipeline_root /"blocks"/level /rule_name /"segments.json"
        timing_json_path =pipeline_root /"timing"/level /rule_name /"timing.json"
        schedule_json_path =pipeline_root /"schedule"/level /rule_name /algo_name /"schedule.json"
        if not source_file .exists ():
            raise StageError (f"missing source file: {source_file}")
        if not segments_json_path .exists ():
            raise StageError (f"missing segments file: {segments_json_path}")
        if not schedule_json_path .exists ():
            raise StageError (f"missing schedule file: {schedule_json_path}")

        schedule_json =read_json (schedule_json_path )
        priorities =schedule_json .get ("priorities",{})
        if not isinstance (priorities ,dict ):
            raise StageError ("schedule.priorities must be dict")
        priorities ={str (k ):int (v )for k ,v in priorities .items ()}

        # readSource File content
        source_text =source_file .read_text (encoding ="utf-8",errors ="replace")

        # --- generate algorithm instrumentationFile (writetemporary variable, later unified output to result/timing) ---
        import tempfile 
        tmp_instrumented =Path (tempfile .mktemp (suffix =".c"))
        tmp_instrumented .write_text (source_text ,encoding ="utf-8")

        mode =(instrument_mode or "auto").strip ().lower ()
        if mode not in {"auto","specialized","generic"}:
            raise StageError (f"invalid instrument_mode: {instrument_mode}")

        use_specialized =(mode =="specialized")or (mode =="auto"and level =="level1")

        if use_specialized :
            warnings =instrument_prio_program_timing_and_segment_priorities (
            tmp_instrumented ,
            segments_json =segments_json_path ,
            priorities =priorities ,
            out_c =tmp_instrumented ,
            )
        else :
            seg_json =read_json (segments_json_path )
            seg_ids_segments :Set [str ]=set ()
            for seg in seg_json .get ("segments",[]):
                if isinstance (seg ,dict ):
                    seg_id =seg .get ("seg_id")
                    if isinstance (seg_id ,str ):
                        seg_ids_segments .add (seg_id )

            seg_ids_schedule =set (priorities .keys ())
            only_in_schedule =sorted (seg_ids_schedule -seg_ids_segments )
            only_in_segments =sorted (seg_ids_segments -seg_ids_schedule )
            if only_in_schedule or only_in_segments :
                raise StageError (
                "segments/schedule mismatch: "
                f"only_in_schedule={len(only_in_schedule)} sample={only_in_schedule[:5]}, "
                f"only_in_segments={len(only_in_segments)} sample={only_in_segments[:5]}"
                )

            warnings =instrument_prio_all_segments_by_start_line (
            tmp_instrumented ,
            segments_json =segments_json_path ,
            priorities =priorities ,
            out_c =tmp_instrumented ,
            )

            if not dag_json_path .exists ():
                raise StageError (f"missing dag file: {dag_json_path}")
            if not timing_json_path .exists ():
                raise StageError (f"missing timing file: {timing_json_path}")

            dag_json =read_json (dag_json_path )
            timing_json =read_json (timing_json_path )
            const_binding =build_const_binding (
            dag_json =dag_json ,
            segments_json =seg_json ,
            source_text =source_text ,
            )
            annotated_dot =render_annotated_schedule_dag (
            dag_json =dag_json ,
            segments_json =seg_json ,
            timing_json =timing_json ,
            schedule_json =schedule_json ,
            const_binding =const_binding ,
            )
            validation_root =pipeline_root /"validation"/level /rule_name /algo_name 
            _render_dot (
            annotated_dot ,
            validation_root /"dag_seg_annotated.dot",
            validation_root /"dag_seg_annotated.png",
            )
            write_json (validation_root /"const_binding.json",const_binding )

            value_dot =render_annotated_schedule_dag_value (
            dag_json =dag_json ,
            segments_json =seg_json ,
            timing_json =timing_json ,
            schedule_json =schedule_json ,
            source_text =source_text ,
            )
            _render_dot (
            value_dot ,
            validation_root /"dag_seg_annotated_value.dot",
            validation_root /"dag_seg_annotated_value.png",
            )

        instrumented_text =tmp_instrumented .read_text (encoding ="utf-8",errors ="replace")
        try :
            tmp_instrumented .unlink ()
        except OSError :
            pass 

            # === v3.0: output to result/ and timing/ directory ===

            # --- result/ directory: instrumentationresult (excluding timing code) ---
            # Algorithm instrumentation version
        algo_result_dir =result_root /algo_name 
        algo_result_dir .mkdir (parents =True ,exist_ok =True )
        instrumented_source_path =algo_result_dir /f"{algo_name}.c"
        instrumented_source_path .write_text (instrumented_text ,encoding ="utf-8")

        # CFS control group (pure source file)
        cfs_result_dir =result_root /"CFS"
        cfs_result_dir .mkdir (parents =True ,exist_ok =True )
        (cfs_result_dir /"CFS.c").write_text (source_text ,encoding ="utf-8")

        # --- timing/ directory: timing version (add main first and last timing on the basis of result) ---
        # Algorithm timing version
        algo_timing_dir =timing_root /algo_name 
        algo_timing_dir .mkdir (parents =True ,exist_ok =True )
        (algo_timing_dir /f"{algo_name}.c").write_text (
        _inject_main_timing_text (instrumented_text ),encoding ="utf-8"
        )

        # CFS timing version
        cfs_timing_dir =timing_root /"CFS"
        cfs_timing_dir .mkdir (parents =True ,exist_ok =True )
        (cfs_timing_dir /"CFS.c").write_text (
        _inject_main_timing_text (source_text ),encoding ="utf-8"
        )

        published_results_dir =_publish_results (
        base_dir =base_dir ,
        base_name =base_name ,
        level =level ,
        rule_name =rule_name ,
        algo_name =algo_name ,
        source_file =source_file ,
        instrumented_source =instrumented_source_path ,
        )

        payload ={
        "status":"success",
        "base_name":base_name ,
        "level":level ,
        "rule_name":rule_name ,
        "view":"single",
        "algo_name":algo_name ,
        "instrument_mode":mode ,
        "priority_count":len (priorities ),
        "warnings":warnings ,
        "source_original":str (source_file ),
        "source_instrumented":str (instrumented_source_path ),
        "result_dir":str (result_root ),
        "timing_dir":str (timing_root ),
        "results_dir":str (published_results_dir ),
        }
        mark_success (meta_path ,step ="instrument",extra ={"priority_count":len (priorities ),"warnings_count":len (warnings )})
        return payload 
    except Exception as exc :
        mark_failed (meta_path ,step ="instrument",error =str (exc ),extra ={"algo_name":algo_name })
        raise 


def _inject_main_timing_text (source_text :str )->str :
    """Inject the MAIN_ELAPSED_S timing code into the Source File text and return new text.\n    \nOne-time processing, avoid nested { syntax problems caused by multiple instrumentation.\n    """
    if "MAIN_ELAPSED_S"in source_text :
        return source_text # Already contains timing code

    lines =source_text .splitlines (keepends =True )

    # ensure header File exists
    has_time_h =any ("<time.h>"in line for line in lines )
    has_stdio_h =any ("<stdio.h>"in line for line in lines )
    if not has_time_h or not has_stdio_h :
        insert_at =0 
        for i ,line in enumerate (lines ):
            if line .strip ().startswith ('#'):
                insert_at =i +1 
                break 
        if not has_time_h :
            lines .insert (insert_at ,"#include <time.h>\n")
            insert_at +=1 
        if not has_stdio_h :
            lines .insert (insert_at ,"#include <stdio.h>\n")

            # Found main function and insert start timing after {
    main_found =False 
    i =0 
    while i <len (lines )and not main_found :
        if "int main"in lines [i ]:
            for j in range (i ,min (i +10 ,len (lines ))):
                if "{"in lines [j ]:
                    insert_pos =j +1 
                    lines .insert (insert_pos ,"    struct timespec ts_main_begin, ts_main_end;\n")
                    lines .insert (insert_pos +1 ,"    clock_gettime(CLOCK_MONOTONIC, &ts_main_begin);\n")
                    main_found =True 
                    break 
            i =j +1 if main_found else i +1 
        else :
            i +=1 

            # Insert end timing before return 0;
    for i ,line in enumerate (lines ):
        if "return 0;"in line :
            lines .insert (i ,"    clock_gettime(CLOCK_MONOTONIC, &ts_main_end);\n")
            lines .insert (i +1 ,"    {\n")
            lines .insert (i +2 ,'        double main_s = (double)(ts_main_end.tv_sec - ts_main_begin.tv_sec)\n')
            lines .insert (i +3 ,'            + (double)(ts_main_end.tv_nsec - ts_main_begin.tv_nsec) / 1e9;\n')
            lines .insert (i +4 ,'        fprintf(stderr, "MAIN_ELAPSED_S=%.9f\\n", main_s);\n')
            lines .insert (i +5 ,"    }\n")
            break 

    return "".join (lines )
