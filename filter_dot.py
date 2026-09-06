#!/usr/bin/env python3
"""\nMycallyplus built-in DOT filter: simplify node names and remove scope prefix/parameter list/compiler suffix.\n\nusage:\n    python -m mycallyplus.filter_dot path/to/dag.dot\n\nOutput:\nGenerate dag_filt.dot in the same directory (append _filt after the source file name).\n"""

from __future__ import annotations 

import re 
import sys 
from pathlib import Path 
from typing import Iterable 


THUNK_PREFIX_RE =re .compile (
r"^(?:non-virtual thunk to |virtual thunk to |covariant return thunk to )"
)

SUFFIX_RE =re .compile (
r"(?:\.(?:part|constprop|isra)\.\d+|\.(?:cold|llvm\.[A-Za-z0-9_]+)|\[(?:clone [^\]]+)\])$"
)


def drop_outer_template (name :str )->str :
    """Remove the <...> template arguments at the end (only the last paragraph is processed, nested <> is supported)."""
    if not name .endswith (">"):
        return name 
    depth =0 
    for i in range (len (name )-1 ,-1 ,-1 ):
        ch =name [i ]
        if ch ==">":
            depth +=1 
        elif ch =="<":
            depth -=1 
            if depth ==0 :
                return name [:i ].rstrip ()
    return name 


def strip_params_and_trailing (name :str )->str :
    """Remove the parameter list and subsequent qualifications/attributes."""
    if "("in name :
        name =name .split ("(",1 )[0 ]
    name =re .sub (
    r"(?:\s+const|\s+volatile|\s+const volatile|\s+[&]{1,2}|\s+noexcept.*|\s+throw\(.*\))$",
    "",
    name ,
    )
    return name .strip ()


def clean_symbol (raw :str )->str :
    """Simplify original node names to core function names (preserving operator/constructor/destructor flags)."""
    name =THUNK_PREFIX_RE .sub ("",raw .strip ())
    name =SUFFIX_RE .sub ("",name )
    name =strip_params_and_trailing (name )
    core =name .split ("::")[-1 ].strip ()
    core =drop_outer_template (core )
    return core or name 


def simplify_node (node :str )->str :
    """Process compound nodes in the shape of A/B/C, simplify each section and then put it back together."""
    parts =[clean_symbol (p )for p in node .split ("/")]
    return "/".join (parts )


def process_lines (lines :Iterable [str ])->Iterable [str ]:
    """Replace node names line by line with dot content."""
    node_re =re .compile (r'"([^"]+)"')
    for line in lines :
        def repl (match :re .Match [str ])->str :
            original =match .group (1 )
            simplified =simplify_node (original )
            return f'"{simplified}"'

        yield node_re .sub (repl ,line )


def filter_file (src :Path ,dst :Path )->None :
    with src .open ("r",encoding ="utf-8")as f :
        lines =list (process_lines (f ))
    with dst .open ("w",encoding ="utf-8")as f :
        f .writelines (lines )


def main ()->None :
    if len (sys .argv )!=2 :
        print ("Usage: python -m mycallyplus.filter_dot path/to/dag.dot",file =sys .stderr )
        sys .exit (1 )

    src =Path (sys .argv [1 ]).expanduser ()
    if not src .is_file ():
        print (f"File does not exist: {src}",file =sys .stderr )
        sys .exit (1 )

    dst =src .with_name (src .stem +"_filt"+src .suffix )
    filter_file (src ,dst )
    print (f"Generated: {dst}")


if __name__ =="__main__":
    main ()
