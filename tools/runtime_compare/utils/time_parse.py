from __future__ import annotations 

"""Time parse tool function"""

import re 
from typing import Optional 


def parse_internal_time_seconds (stdout :str ,stderr :str ="")->Optional [float ]:
    """Parse internal timing time (seconds) from program output\n    \nSupport three formats:\n- MAIN_ELAPSED_S=... (pipeline new timing version)\n- PROGRAM_TOTAL_NS=... (ns to seconds)\n- \"total time\" line\n    \nPrioritize using pipeline's new format, which is compatible with old runtime tool output. Also scan stdout/stderr.\n    \n    Args:\nstdout: standard output of the program\nstderr: the standard Erroroutput of the program\n        \n    Returns:\nParse time (seconds), ifparsefailed returns None\n    """
    ns_candidates :list [int ]=[]
    time_candidates :list [float ]=[]
    for stream_text in (stdout or "",stderr or ""):
        for ln in stream_text .splitlines ():
        # support pipeline new format MAIN_ELAPSED_S=...
            m =re .search (r"MAIN_ELAPSED_S=([\d.]+)",ln )
            if m :
                try :
                    time_candidates .append (float (m .group (1 )))
                except Exception :
                    pass 
                continue 
            m =re .search (r"PROGRAM_TOTAL_NS=(\d+)",ln )
            if m :
                try :
                    ns_candidates .append (int (m .group (1 )))
                except Exception :
                    pass 
                continue 
            low =ln .lower ()
            if "total time"not in low :
                continue 
            m =re .search (r"([0-9]+(?:\.[0-9]+)?)",ln )
            if not m :
                continue 
            try :
                time_candidates .append (float (m .group (1 )))
            except Exception :
                continue 
    if ns_candidates :
        return ns_candidates [-1 ]/1e9 
    if time_candidates :
        return time_candidates [-1 ]
    return None 
