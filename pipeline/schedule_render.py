from __future__ import annotations 

import re 
from typing import Dict ,List ,Tuple 

from .errors import ValidationError 


def _dot_escape_id (value :object )->str :
    text =str (value )
    return text .replace ("\\","\\\\").replace ('"','\\"')


def _dot_escape_label (value :object )->str :
    text =str (value )
    return text .replace ("\\","\\\\").replace ('"','\\"').replace ("\n","\\n")


def _load_node_ids (dag_json :Dict ,segments_json :Dict )->List [str ]:
    segments =segments_json .get ("segments")
    if not isinstance (segments ,list ):
        raise ValidationError ("segments.segments must be a list")

    seg_ids :List [str ]=[]
    for item in segments :
        if not isinstance (item ,dict ):
            raise ValidationError ("segments item must be dict")
        seg_id =item .get ("seg_id")
        if not isinstance (seg_id ,str )or not seg_id :
            raise ValidationError ("segments item missing seg_id")
        seg_ids .append (seg_id )

    if len (set (seg_ids ))!=len (seg_ids ):
        raise ValidationError ("segments contain duplicate seg_id")

    dag_nodes =dag_json .get ("nodes")
    if dag_nodes is None :
        return seg_ids 
    if not isinstance (dag_nodes ,list ):
        raise ValidationError ("dag.nodes must be a list")
    if not all (isinstance (node ,str )and node for node in dag_nodes ):
        raise ValidationError ("dag.nodes must only contain non-empty string seg_id")

    dag_node_ids =list (dag_nodes )
    if len (set (dag_node_ids ))!=len (dag_node_ids ):
        raise ValidationError ("dag.nodes contain duplicate seg_id")
    if set (dag_node_ids )!=set (seg_ids ):
        raise ValidationError ("dag.nodes and segments.seg_id mismatch")
    return dag_node_ids 


def _load_edges (dag_json :Dict ,node_set :set [str ])->List [Tuple [str ,str ]]:
    raw_edges =dag_json .get ("edges")
    if not isinstance (raw_edges ,list ):
        raise ValidationError ("dag.edges must be a list")

    edges :List [Tuple [str ,str ]]=[]
    for item in raw_edges :
        if not isinstance (item ,dict ):
            raise ValidationError ("dag edge must be dict")
        src =item .get ("src")
        dst =item .get ("dst")
        if not isinstance (src ,str )or not isinstance (dst ,str ):
            raise ValidationError ("dag edge src/dst must be string")
        if src not in node_set or dst not in node_set :
            raise ValidationError (f"dag edge references unknown node: {src}->{dst}")
        edges .append ((src ,dst ))
    return edges 


def _load_avg_ns (timing_json :Dict ,node_ids :List [str ])->Dict [str ,int ]:
    weights =timing_json .get ("weights")
    if not isinstance (weights ,dict ):
        raise ValidationError ("timing.weights must be dict")

    out :Dict [str ,int ]={}
    for seg_id in node_ids :
        metric =weights .get (seg_id )
        if not isinstance (metric ,dict ):
            raise ValidationError (f"timing weight for {seg_id} must be dict")
        if "avg_ns"not in metric :
            raise ValidationError (f"timing weight for {seg_id} missing avg_ns")
        try :
            out [seg_id ]=int (metric ["avg_ns"])
        except Exception as exc :
            raise ValidationError (f"timing weight for {seg_id} has invalid avg_ns")from exc 
    return out 


def _load_priorities (schedule_json :Dict ,node_ids :List [str ])->Dict [str ,int ]:
    priorities =schedule_json .get ("priorities")
    if not isinstance (priorities ,dict ):
        raise ValidationError ("schedule.priorities must be dict")

    node_set =set (node_ids )
    extra =[seg_id for seg_id in priorities .keys ()if seg_id not in node_set ]
    if extra :
        raise ValidationError (f"schedule priority contains unknown segment: {extra[0]}")

    out :Dict [str ,int ]={}
    for seg_id in node_ids :
        if seg_id not in priorities :
            raise ValidationError (f"schedule priority missing segment: {seg_id}")
        try :
            out [seg_id ]=int (priorities [seg_id ])
        except Exception as exc :
            raise ValidationError (f"schedule priority for {seg_id} is invalid")from exc 
    return out 


def build_const_binding (*,dag_json :Dict ,segments_json :Dict ,source_text :str )->Dict [str ,Dict ]:
    if not isinstance (source_text ,str ):
        raise ValidationError ("source_text must be string")

    node_ids =_load_node_ids (dag_json ,segments_json )
    seg_map :Dict [str ,Dict ]={}
    for item in segments_json .get ("segments",[]):
        if isinstance (item ,dict )and isinstance (item .get ("seg_id"),str ):
            seg_map [item ["seg_id"]]=item 

    lines =source_text .splitlines ()
    pattern =re .compile (r"busy_wait_seconds\s*\(\s*(C\d+)\s*\)")
    binding :Dict [str ,Dict ]={}

    for seg_id in node_ids :
        seg =seg_map .get (seg_id )
        if not isinstance (seg ,dict ):
            raise ValidationError (f"missing segment definition for: {seg_id}")
        try :
            start_line =int (seg ["start_line"])
            end_line =int (seg ["end_line"])
        except Exception as exc :
            raise ValidationError (f"segment {seg_id} has invalid line range")from exc 
        if start_line <1 or end_line <start_line :
            raise ValidationError (f"segment {seg_id} has invalid line range: {start_line}-{end_line}")

        matches :List [Tuple [str ,int ]]=[]
        if start_line <=len (lines ):
            safe_end =min (end_line ,len (lines ))
            for ln in range (start_line ,safe_end +1 ):
                for m in pattern .finditer (lines [ln -1 ]):
                    matches .append ((m .group (1 ),ln ))

        uniq =sorted ({name for name ,_ in matches })
        if not uniq :
            binding [seg_id ]={"const_name":"NA","line":None ,"const_names":[]}
        elif len (uniq )==1 :
            const_name =uniq [0 ]
            line =next (ln for name ,ln in matches if name ==const_name )
            binding [seg_id ]={"const_name":const_name ,"line":line ,"const_names":[const_name ]}
        else :
            binding [seg_id ]={
            "const_name":"|".join (uniq ),
            "line":min (ln for _ ,ln in matches ),
            "const_names":uniq ,
            }
    return binding 


def render_annotated_schedule_dag (
*,
dag_json :Dict ,
segments_json :Dict ,
timing_json :Dict ,
schedule_json :Dict ,
const_binding :Dict [str ,Dict ]|None =None ,
)->str :
    node_ids =_load_node_ids (dag_json ,segments_json )
    node_set =set (node_ids )
    edges =_load_edges (dag_json ,node_set )
    avg_ns =_load_avg_ns (timing_json ,node_ids )
    priorities =_load_priorities (schedule_json ,node_ids )

    lines :List [str ]=[]
    lines .append ("digraph dag_seg_annotated {")
    lines .append ("  rankdir=LR;")
    lines .append ('  node [shape=box, style="rounded,filled", fillcolor="#F8FAFC", color="#334155", fontsize=10];')
    lines .append ('  edge [color="#475569"];')

    for seg_id in node_ids :
        if const_binding is None :
            label =f"{seg_id}\navg_ns={avg_ns[seg_id]}\nprio={priorities[seg_id]}"
        else :
            item =const_binding .get (seg_id )
            if not isinstance (item ,dict ):
                raise ValidationError (f"const binding for {seg_id} must be dict")
            const_name =item .get ("const_name")
            if not isinstance (const_name ,str )or not const_name :
                raise ValidationError (f"const binding for {seg_id} missing const_name")
            label =f"{seg_id}\nconst={const_name}\navg_ns={avg_ns[seg_id]}\nprio={priorities[seg_id]}"
        lines .append (f'  "{_dot_escape_id(seg_id)}" [label="{_dot_escape_label(label)}"];')

    for src ,dst in edges :
        lines .append (f'  "{_dot_escape_id(src)}" -> "{_dot_escape_id(dst)}";')

    lines .append ("}")
    lines .append ("")
    return "\n".join (lines )


def _parse_constant_values (source_text :str )->Dict [str ,float ]:
    """Constant value mapping from source codeparse #define Cxxx value"""
    import re 
    const_values :Dict [str ,float ]={}
    pattern =re .compile (r"^#define\s+(C\d+)\s+([0-9.]+)",re .MULTILINE )

    for match in pattern .finditer (source_text ):
        const_name =match .group (1 )
        try :
            value =float (match .group (2 ))
            const_values [const_name ]=value 
        except ValueError :
            continue 

            # Also handles WORK_SCALE
    ws_pattern =re .compile (r"#define\s+WORK_SCALE\s+([0-9]+)",re .MULTILINE )
    for match in ws_pattern .finditer (source_text ):
        try :
            const_values ["WORK_SCALE"]=float (match .group (1 ))
        except ValueError :
            pass 

    return const_values 


def render_annotated_schedule_dag_value (
*,
dag_json :Dict ,
segments_json :Dict ,
timing_json :Dict ,
schedule_json :Dict ,
source_text :str ,
)->str :
    """Generate a simplified version of the DAG graph, including mapping information from constant names to constant values."""
    node_ids =_load_node_ids (dag_json ,segments_json )
    node_set =set (node_ids )
    edges =_load_edges (dag_json ,node_set )
    avg_ns =_load_avg_ns (timing_json ,node_ids )
    priorities =_load_priorities (schedule_json ,node_ids )
    const_values =_parse_constant_values (source_text )

    # use existing binding logic get constant name
    const_binding :Dict ={}
    try :
        const_binding =build_const_binding (
        dag_json =dag_json ,
        segments_json =segments_json ,
        source_text =source_text ,
        )
    except Exception :
        const_binding ={}

    lines :List [str ]=[]
    lines .append ("digraph dag_seg_annotated_value {")
    lines .append ("  rankdir=LR;")
    lines .append ('  node [shape=box, style="rounded,filled", fillcolor="#E6F3FF", color="#1976D2", fontsize=10];')
    lines .append ('  edge [color="#1976D2"];')

    for seg_id in node_ids :
    # get constant information
        binding =const_binding .get (seg_id ,{})
        const_name =binding .get ("const_name","NA")
        const_names =binding .get ("const_names",[])

        # build constant value information
        const_info_parts =[]
        if const_names :
            for cname in const_names :
                value =const_values .get (cname ,0.0 )
                const_info_parts .append (f"{cname}={value:.1f}")
        else :
            const_info_parts .append (f"{const_name}=?")

        const_info =" | ".join (const_info_parts )

        label =f"{seg_id}\n{const_info}\navg_ns={avg_ns.get(seg_id, 0)}\nprio={priorities.get(seg_id, 0)}"
        lines .append (f'  "{_dot_escape_id(seg_id)}" [label="{_dot_escape_label(label)}"];')

    for src ,dst in edges :
        lines .append (f'  "{_dot_escape_id(src)}" -> "{_dot_escape_id(dst)}";')

    lines .append ("}")
    lines .append ("")
    return "\n".join (lines )
