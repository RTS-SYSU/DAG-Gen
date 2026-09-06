"""resume modestatus management (persist Completed tasks according to config_files)"""

from __future__ import annotations 

import hashlib 
import json 
import os 
import threading 
from pathlib import Path 
from typing import Any ,Dict ,Optional ,Tuple 


_LOCK =threading .Lock ()
_STATE_VERSION =1 


def compute_task_key (payload :Dict [str ,Any ])->str :
    """Compute stable task key (independent of task_id timestamp)."""
    # Canonical JSON, ensure stable hashing
    txt =json .dumps (payload ,ensure_ascii =False ,sort_keys =True ,separators =(",",":"))
    return hashlib .sha1 (txt .encode ("utf-8")).hexdigest ()


def task_payload_for_key (
*,
baseline_c :Path ,
prio_c :Path ,
work_scale :int ,
repeats :int ,
cores_per_task :int ,
use_sudo :bool ,
cpu_list :Optional [list [int ]],
)->Dict [str ,Any ]:
    return {
    "baseline_c":str (Path (baseline_c ).expanduser ().resolve ()),
    "prio_c":str (Path (prio_c ).expanduser ().resolve ()),
    "work_scale":int (work_scale ),
    "repeats":int (repeats ),
    "cores_per_task":int (cores_per_task ),
    "use_sudo":bool (use_sudo ),
    "cpu_list":list (cpu_list )if cpu_list else None ,
    }


def default_resume_file (config_path :Path ,*,tool_dir :Optional [Path ]=None )->Path :
    """Return the resume statusFilepath corresponding to the config (guaranteed to be writable)."""
    config_path =Path (config_path ).expanduser ().resolve ()
    if tool_dir is None :
        tool_dir =Path (__file__ ).parent .parent .resolve ()# utils -> runtime_compare
    config_dir =(tool_dir /"config_files").resolve ()

    try :
    # ifconfig_files are in the tool configuration directory and are stored directly adjacent to each other.
        config_path .relative_to (config_dir )
        return config_path .with_suffix (".resume.json")
    except Exception :
    # Otherwiseunified is placed under config_files/.resume/, and absolute path hash is used to avoid duplicate names.
        resume_dir =tool_dir /"config_files"/".resume"
        resume_dir .mkdir (parents =True ,exist_ok =True )
        h =hashlib .sha1 (str (config_path ).encode ("utf-8")).hexdigest ()[:10 ]
        return resume_dir /f"{config_path.stem}_{h}.resume.json"


def _atomic_write_text (path :Path ,text :str )->None :
    path .parent .mkdir (parents =True ,exist_ok =True )
    tmp =path .with_name (f".{path.name}.tmp.{os.getpid()}")
    tmp .write_text (text ,encoding ="utf-8")
    tmp .replace (path )


def load_state (path :Path )->Dict [str ,Any ]:
    if not path .exists ():
        return {"version":_STATE_VERSION ,"done":{}}
    try :
        data =json .loads (path .read_text (encoding ="utf-8"))
        if not isinstance (data ,dict ):
            raise ValueError ("resume state must be dict")
        if "done"not in data or not isinstance (data ["done"],dict ):
            data ["done"]={}
        if "version"not in data :
            data ["version"]=_STATE_VERSION 
        return data 
    except Exception :
    # Do not block task running when readfailed, fall back to empty status
        return {"version":_STATE_VERSION ,"done":{}}


def save_state (path :Path ,data :Dict [str ,Any ])->None :
    _atomic_write_text (path ,json .dumps (data ,ensure_ascii =False ,indent =2 ))


def get_done_entry (state :Dict [str ,Any ],task_key :str )->Optional [Dict [str ,Any ]]:
    done =state .get ("done")or {}
    entry =done .get (task_key )
    return entry if isinstance (entry ,dict )else None 


def is_entry_valid (entry :Dict [str ,Any ])->bool :
    out_dir =entry .get ("out_dir")
    if not out_dir :
        return False 
    p =Path (out_dir )
    return p .exists ()and (p /"summary.json").exists ()


def mark_done (
*,
resume_file :Path ,
task_key :str ,
task_id :str ,
out_dir :Path ,
message :str ,
done_at :str ,
payload :Dict [str ,Any ],
)->None :
    with _LOCK :
        state =load_state (resume_file )
        done =state .setdefault ("done",{})
        done [str (task_key )]={
        "task_id":str (task_id ),
        "out_dir":str (out_dir ),
        "message":str (message or ""),
        "done_at":str (done_at ),
        "payload":payload ,
        }
        state ["version"]=_STATE_VERSION 
        save_state (resume_file ,state )


def apply_resume_to_task (task :Any )->Tuple [bool ,Optional [str ]]:
    """If the key corresponding to the task is Completed, mark the task as done and return True."""
    resume_file =getattr (task ,"resume_file",None )
    task_key =getattr (task ,"task_key",None )
    if not resume_file or not task_key :
        return False ,None 

    resume_path =Path (resume_file )
    with _LOCK :
        state =load_state (resume_path )
        entry =get_done_entry (state ,str (task_key ))
    if not entry or not is_entry_valid (entry ):
        return False ,None 

    task .status ="done"
    task .phase ="done"
    task .message =entry .get ("message")or "Completed (skip in resume mode)"
    task .out_dir =Path (entry ["out_dir"])
    # Try to keep task_id unchanged to facilitate WebUI to view logs/directory
    if entry .get ("task_id"):
        task .task_id =entry ["task_id"]
    return True ,str (task .out_dir )
