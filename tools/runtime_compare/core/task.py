"""Task data class"""

from dataclasses import dataclass ,field 
from pathlib import Path 
from typing import List ,Optional 
import threading 


@dataclass 
class Task :
    """experiment task\n    \n    v3.0: supportsingle-file mode（source_c + algo_name）\nCompatible with the old mode (baseline_c + prio_c), the two modes coexist during the transition period.\n    """

    task_id :str 
    # v3.0 new field: single-file mode
    source_c :Optional [Path ]=None # Source Filepath of single-file mode
    algo_name :Optional [str ]=None # Algorithm name (CFS/FIFO/LPF/heft/...)
    # Old fields: remain compatible (transition period)
    baseline_c :Optional [Path ]=None 
    prio_c :Optional [Path ]=None 

    work_scale :int =100 
    repeats :int =10 
    cores_per_task :int =2 
    use_sudo :bool =False 
    cpu_list :Optional [List [int ]]=None # Optional: Manually specify the CPU core list
    config_name :Optional [str ]=None # Optional: config_files name (without extension), used for resultdirectory naming
    batch_name :Optional [str ]=None # The group name during batch submit (such as zhang1), used in the result subdirectory
    batch_ts :Optional [str ]=None # Unified timestamp when batch submit, shared by all algorithms in the same batch
    # resume mode: stable key + resume statusFile
    task_key :Optional [str ]=None 
    resume_file :Optional [Path ]=None 

    status :str ="queued"# queued|running|cancelling|cancelled|done|error
    message :str =""
    cpu_set :List [int ]=field (default_factory =list )
    start_ns :Optional [int ]=None 
    end_ns :Optional [int ]=None 

    out_dir :Optional [Path ]=None 

    # Progress detail: (phase, i, n)
    phase :str ="queued"
    progress_i :int =0 
    progress_n :int =0 

    # Cancellation (shared across threads)
    cancel_requested :bool =False 
    cancel_reason :str =""
    cancel_evt :threading .Event =field (default_factory =threading .Event ,repr =False )

    @property 
    def is_single_mode (self )->bool :
        """Whether it is v3.0 single-file mode"""
        return self .source_c is not None 
