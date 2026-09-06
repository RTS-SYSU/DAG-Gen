#!/usr/bin/env python3
"""\nFrom .expand generate \"source codecallgraph\": only retain call points to edges whose Source File name is consistent with the specified Source File name.\n\nusage:\n    python -m mycallyplus.source_only --expand path/to/file.233r.expand --source <basename> --output out.dot\n"""

from __future__ import annotations 

import argparse 
import re 
from pathlib import Path 
from typing import Dict ,Set 


def parse_expand (expand_path :Path ,source_basename :str )->Dict [str ,Set [str ]]:
    """parse expand, returns only the calledge collection from the specified Source File, with legacy numbering.\n\nReturn two sets of edges at the same time:\n- all_edges: does not filterSource File\n- filtered_edges: only keep calls whose Source File matches source_basename\n    """
    func_re =re .compile (r"^;; Function (?P<mangle>.*)\s+\((?P<function>\S+)")
    call_target_re =re .compile (r'\(call.*?"(?P<target>[^"]+)"')
    src_re =re .compile (r'"(?P<file>[^"]+)":(?P<line>\d+):(?P<col>\d+)')

    # First collect the function names defined by all
    defined :Set [str ]=set ()
    for line in expand_path .read_text (encoding ="utf-8",errors ="ignore").splitlines ():
        m_func =func_re .match (line )
        if m_func :
            defined .add (m_func .group ("function"))

    edges :Dict [str ,Set [str ]]={}
    current_fn :str |None =None 
    pending_target :str |None =None 
    call_counter :Dict [str ,int ]={}# Number count for each caller

    with expand_path .open ("r",encoding ="utf-8",errors ="ignore")as f :
        for line in f :
            m_func =func_re .match (line )
            if m_func :
                current_fn =m_func .group ("function")
                edges .setdefault (current_fn ,set ())
                pending_target =None 
                continue 

            if current_fn is None :
                continue 

                # capture call target
            m_target =call_target_re .search (line )
            if m_target :
            # A new call appears. If the previous call does not match the source bit, it will be overwritten.
                raw_target =m_target .group ("target")
                # Application Number Rules: Undefined target plus caller prefix and sequence number
                if raw_target in defined :
                    pending_target =raw_target 
                else :
                    call_counter [current_fn ]=call_counter .get (current_fn ,0 )+1 
                    pending_target =f"{current_fn}/{raw_target}{call_counter[current_fn]}"

                    # Peers with source bits directly match
                m_src_inline =src_re .search (line )
                if m_src_inline and Path (m_src_inline .group ("file")).name ==source_basename :
                    edges .setdefault (current_fn ,set ()).add (pending_target )
                    pending_target =None 
                continue 

                # In suspended status, try to match the source bit in subsequent lines
            if pending_target :
                m_src =src_re .search (line )
                if m_src and Path (m_src .group ("file")).name ==source_basename :
                    edges .setdefault (current_fn ,set ()).add (pending_target )
                    pending_target =None 
                    # If it is not the target Source File, keep hangs and waits for subsequent possible source lines.

    return edges 


def write_dot (edges :Dict [str ,Set [str ]],output :Path )->None :
    lines =["strict digraph callgraph {\n"]
    for caller ,callees in edges .items ():
        for callee in sorted (callees ):
            lines .append (f"\"{caller}\" -> \"{callee}\";\n")
    lines .append ("}\n")
    output .write_text ("".join (lines ),encoding ="utf-8")


def _derive_default_paths (expand :Path )->tuple [Path ,Path ,Path ]:
    """Derive the outputdirectory and File name based on the expand path."""
    base_dir =expand .parents [2 ]if len (expand .parents )>=3 else expand .parent 
    base_name =expand .stem 
    if base_name .endswith (".233r"):
        base_name =base_name [:-5 ]
    if "."in base_name :
        base_name =base_name .split (".")[0 ]
    out_dir =base_dir /"intermediate_results"/base_name /"dag_generation"
    out_dir .mkdir (parents =True ,exist_ok =True )
    dot_path =out_dir /"dag_source_only.dot"
    filt_dot_path =out_dir /"dag_source_only_filt.dot"
    png_path =out_dir /"dag_source_only_filt.png"
    return dot_path ,filt_dot_path ,png_path 


def main ()->int :
    ap =argparse .ArgumentParser (description ="generateonly contains the DOT of the specified Source Filecall")
    ap .add_argument ("--expand",required =True ,type =Path ,help =".233r.expand Filepath")
    ap .add_argument ("--source",required =True ,help ="Source File basename, such as FixedwingRateControl.cpp")
    ap .add_argument ("--output",type =Path ,help ="output dot path (optional, default is placed in intermediate_results/<base name>/dag_generation)")
    args =ap .parse_args ()

    # Derive outputpath
    if args .output :
        dot_path =args .output 
        out_dir =dot_path .parent 
        filt_dot_path =out_dir /"dag_source_only_filt.dot"
        png_path =out_dir /"dag_source_only_filt.png"
        out_dir .mkdir (parents =True ,exist_ok =True )
    else :
        dot_path ,filt_dot_path ,png_path =_derive_default_paths (args .expand )

    edges =parse_expand (args .expand ,args .source )
    write_dot (edges ,dot_path )
    print (f"Generatedsource codecallgraph: {dot_path}")

    # Before and after retaining the filter: The filter version is currently directlycopy, retaining the number
    import shutil ,subprocess 
    shutil .copy2 (dot_path ,filt_dot_path )

    # Render PNG
    try :
        subprocess .run (
        ["dot","-Tpng",str (filt_dot_path ),"-o",str (png_path )],
        check =True ,
        capture_output =True ,
        )
        print (f"Rendered: {png_path}")
    except Exception as e :
        print (f"Rendering PNG failed: {e}")

    return 0 


if __name__ =="__main__":
    raise SystemExit (main ())
