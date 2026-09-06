"""CPU pool management"""

import threading 
from typing import List ,Optional 


class CpuPool :
    """CPU core pool, manages the allocation and release of CPU cores"""

    def __init__ (self ,cpus :List [int ])->None :
        """Initialize CPU pool\n        \n        Args:\ncpus: list of available CPU cores\n        """
        self ._cpus =cpus [:]
        self ._lock =threading .Lock ()
        self ._leased :List [List [int ]]=[]

    def try_acquire_group (self ,k :int ,preferred :Optional [List [int ]]=None )->Optional [List [int ]]:
        """try toget k CPU cores\n        \n        Args:\nk: number of cores needed\npreferred: priority use core list (if cpu_list is specified)\n            \n        Returns:\nifSuccess, returns the allocated core list; otherwise returns None\n        """
        with self ._lock :
            free =[c for c in self ._cpus if all (c not in g for g in self ._leased )]

            # if specifies a priority list, use the core of it first
            if preferred :
                preferred_available =[c for c in preferred if c in free ]
                if len (preferred_available )>=k :
                    group =preferred_available [:k ]
                    self ._leased .append (group )
                    return group 

                    # otherwiseSelect from idle cores
            if len (free )<k :
                return None 
            group =free [:k ]
            self ._leased .append (group )
            return group 

    def release_group (self ,group :List [int ])->None :
        """Release CPU core group\n        \n        Args:\ngroup: list of cores to be released\n        """
        with self ._lock :
            self ._leased =[g for g in self ._leased if g !=group ]

    def free_count (self )->int :
        """getcurrentThe number of idle cores"""
        with self ._lock :
            used ={c for g in self ._leased for c in g }
            return len ([c for c in self ._cpus if c not in used ])

    def total_count (self )->int :
        """get the total number of cores"""
        return len (self ._cpus )
