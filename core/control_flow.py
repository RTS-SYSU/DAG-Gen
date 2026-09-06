from __future__ import annotations 

"""Control flow context extraction (compatible with legacy logic).\n\nlegacy implements if/while/switch recognition through multiple status machines, and in mycalls\nAdd `if/`, `while/`, `switchK/` and other prefixes. In order to keep compatible with, we\nThis logic is replicated in this module, but the output structured result is used by the numbering stage.\n"""

from dataclasses import dataclass 
from typing import Dict ,List ,Tuple 


@dataclass 
class ControlEntry :
    prefix :str 


ControlMap =Dict [str ,List [ControlEntry ]]


def build_control_prefix_map (functions_pre :Dict [str ,List [Tuple [str ,str ]]])->ControlMap :
    """Convert legacy readahead results to an ordered prefix list."""

    mapping :ControlMap ={}
    for func_name ,entries in functions_pre .items ():
        mapping [func_name ]=[ControlEntry (prefix =kind )for kind ,_ in entries ]
    return mapping 
