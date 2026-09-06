"""CPU affinity related utility functions"""

import os 
import re 
import subprocess 
import time 
import signal 
from pathlib import Path 
from typing import Callable ,Dict ,List ,Optional ,Tuple 


def rewrite_sched_setaffinity_cpu_set (source :str ,cpu_set :List [int ])->Tuple [str ,bool ]:
    """Rewrite the sched_setaffinity CPU_SET call in the source code\n    \nReplace the hard-coded CPU_SET in the source code with the specified CPU set to prevent the program from overwriting the CPU isolation assigned by the tool.\n    \n    Args:\nsource: C source code content\ncpu_set: List of CPU numbers to be set\n        \n    Returns:\n(Modified source code, whether any modifications have occurred)\n    """
    if "sched_setaffinity"not in source :
        return source ,False 

        # Detect the variable name used with CPU_ZERO (e.g. &set, &cpu_set, &cpuset)
    m_zero =re .search (r"CPU_ZERO\s*\(\s*&(\w+)\s*\)",source )
    if not m_zero :
        return source ,False 
    var_name =m_zero .group (1 )

    lines =source .splitlines (keepends =True )
    out :List [str ]=[]
    in_block =False 
    inserted =False 
    changed =False 

    cpu_set_lines =[f"    CPU_SET({c}, &{var_name});\n"for c in cpu_set ]
    zero_pattern =f"CPU_ZERO(&{var_name})"
    set_pattern =re .compile (
    r"^\s*CPU_SET\(\s*\d+\s*,\s*&"+re .escape (var_name )+r"\s*\)\s*;\s*$"
    )

    for ln in lines :
        if zero_pattern in ln :
            in_block =True 
            inserted =False 
            out .append (ln )
            continue 

        if in_block :
            if set_pattern .match (ln ):
                changed =True 
                continue 

            if (not inserted )and ("sched_setaffinity"in ln ):
                out .extend (cpu_set_lines )
                inserted =True 
                if cpu_set_lines :
                    changed =True 
                out .append (ln )
                in_block =False 
                continue 

            out .append (ln )
            continue 

        out .append (ln )

    return "".join (out ),changed 


def run_with_affinity (
cmd :List [str ],
*,
cwd :Path ,
env :Dict [str ,str ],
cpu_set :List [int ],
use_sudo :bool ,
cancel_check :Optional [Callable [[],bool ]]=None ,
kill_grace_s :float =1.0 ,
)->Tuple [int ,str ,str ,int ]:
    """Runs a command on a specified set of CPU cores\n    \n    Args:\ncmd: command to be executed\n        cwd: working directory\nenv: environment variable\ncpu_set: CPU core set\nuse_sudo: whether to use sudo to run\n        \n    Returns:\n(return code, stdout, stderr, wall_time_ns)\n    """
    full_cmd =cmd [:]
    if use_sudo and os .geteuid ()!=0 :
    # Non-interactive: require passwordless sudo.
        full_cmd =["sudo","-n"]+full_cmd 

    def preexec ()->None :
    # Ensure the child (and thus its threads) stay within the CPU set.
        os .sched_setaffinity (0 ,set (cpu_set ))
        # New session so we can kill the whole process group on cancel.
        os .setsid ()

    t0 =time .monotonic_ns ()
    proc =subprocess .Popen (
    full_cmd ,
    cwd =str (cwd ),
    env =env ,
    stdout =subprocess .PIPE ,
    stderr =subprocess .PIPE ,
    text =True ,
    preexec_fn =preexec ,
    )

    def terminate_group ()->None :
        try :
            os .killpg (proc .pid ,signal .SIGTERM )
        except Exception :
            try :
                proc .terminate ()
            except Exception :
                pass 

    def kill_group ()->None :
        try :
            os .killpg (proc .pid ,signal .SIGKILL )
        except Exception :
            try :
                proc .kill ()
            except Exception :
                pass 

    out =""
    err =""
    try :
        while True :
            if cancel_check and cancel_check ():
                terminate_group ()
                try :
                    out ,err =proc .communicate (timeout =max (0.1 ,kill_grace_s ))
                except subprocess .TimeoutExpired :
                    kill_group ()
                    out ,err =proc .communicate ()
                break 
            try :
                out ,err =proc .communicate (timeout =0.2 )
                break 
            except subprocess .TimeoutExpired :
                continue 
    finally :
        t1 =time .monotonic_ns ()

    rc =proc .returncode if proc .returncode is not None else -9 
    return int (rc ),out or "",err or "",(t1 -t0 )
