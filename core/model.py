from __future__ import annotations 

"""data model（used by the modernized interface）

This file provides a clearer、annotatable data types，for easier use in tools/unit tests
Build/render the call graph with lower coupling. The legacy implementation still retains the original
dict structure to preserve compatibility.
"""

from dataclasses import dataclass ,field 
from typing import Dict ,List ,Optional ,Set ,Tuple 


@dataclass 
class Function :
    """Function node information (modernized).

    - files: Set of RTL files from which the function originates
    - calls: Set of directly called callee functions (dictionary used as a set)
    - refs: Set of directly referenced symbols (dictionary used as a set)
    - call_sequence: Call names recorded in appearance order inside the function body (useful for inferring the tail node)
    - callee_calls/refs: Reverse indexes populated by the builder
    - meta: Reserved extra information
    """

    name :str 
    files :Set [str ]=field (default_factory =set )
    calls :Dict [str ,bool ]=field (default_factory =dict )
    refs :Dict [str ,bool ]=field (default_factory =dict )
    call_sequence :List [str ]=field (default_factory =list )
    callee_calls :Dict [str ,bool ]=field (default_factory =dict )
    callee_refs :Dict [str ,bool ]=field (default_factory =dict )
    meta :Dict [str ,str ]=field (default_factory =dict )


@dataclass 
class ThreadInfo :
    """Thread information (modernized).\n\n    - thread_id: Thread-handle identifier (used only in the modernized implementation)\n    - task_function: Thread entry function name\n    - create_site: Function name where create occurs\n- join_site: function name where join occurs (optional)\n- tail_node: tail node inferred within the thread task (optional)\n    """

    thread_id :str 
    task_function :str 
    create_site :str 
    join_site :Optional [str ]=None 
    tail_node :Optional [str ]=None 


@dataclass 
class CallGraph :
    """Call graph (modernized).

    - functions: function table
    - thread_infos/thread_edges: cache related to thread patch edges
    - thread_create_queue: auxiliary structure used as a lightweight queue fallback
    """

    functions :Dict [str ,Function ]=field (default_factory =dict )
    thread_infos :Dict [str ,ThreadInfo ]=field (default_factory =dict )
    thread_edges :List [Tuple [str ,str ]]=field (default_factory =list )
    thread_create_queue :List [str ]=field (default_factory =list )

    def ensure_function (self ,name :str )->Function :
        """Create an empty function entry if it does not exist and return it."""
        if name not in self .functions :
            self .functions [name ]=Function (name =name )
        return self .functions [name ]


@dataclass 
class RenderOptions :
    """Set of rendering switches, kept consistent with legacy semantics."""

    exclude :Optional [str ]=None 
    no_externs :bool =False 
    max_depth :int =0 
    reverse_path :bool =False 
