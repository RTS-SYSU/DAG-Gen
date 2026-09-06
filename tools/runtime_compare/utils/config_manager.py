"""config_files management module"""

import json 
import uuid 
from datetime import datetime 
from pathlib import Path 
from typing import Dict ,List ,Optional ,Any 

from ..core .task import Task 
from ..utils .datetime_utils import now_ts_safe 
from ..utils .resume_state import compute_task_key ,default_resume_file ,task_payload_for_key 


def save_config (
tasks :List [Task ],
config_path :Optional [Path ]=None ,
queue_mode :bool =False ,
mode :str ="append"
)->Path :
    """Save task configuration to a JSON file\n    \n    Args:\n        tasks: task list\n        config_path: config_files path (if `None`, generate automatically)\n        queue_mode: whether queue mode is enabled\nmode: save mode, \"append\" (append) or \"overwrite\" (cover)\n        \n    Returns:\n        config_filespath\n    """
    if config_path is None :
    # automaticgeneratepath：tools/runtime_compare/config_files/tasks_<timestamp>.json
        tool_dir =Path (__file__ ).parent .parent # utils -> runtime_compare
        config_dir =tool_dir /"config_files"
        config_dir .mkdir (parents =True ,exist_ok =True )
        config_path =config_dir /f"tasks_{now_ts_safe()}.json"

    config_path =Path (config_path ).expanduser ().resolve ()
    config_path .parent .mkdir (parents =True ,exist_ok =True )

    # Convert to dictionary format
    tasks_data =[]
    for task in tasks :
        task_dict ={
        "baseline_c":str (task .baseline_c ),
        "prio_c":str (task .prio_c ),
        "work_scale":task .work_scale ,
        "repeats":task .repeats ,
        "cores_per_task":task .cores_per_task ,
        "use_sudo":task .use_sudo ,
        }
        if task .cpu_list :
            task_dict ["cpu_list"]=task .cpu_list 
        tasks_data .append (task_dict )

    config ={
    "tasks":tasks_data ,
    "queue_mode":queue_mode ,
    "created_at":datetime .now ().isoformat (),
    }

    # Append mode: read the existing config and merge tasks
    if mode =="append"and config_path .exists ():
        try :
            existing =load_config (config_path )
            # Merge task lists (remove duplicates)
            existing_task_ids ={
            (
            t ["baseline_c"],
            t ["prio_c"],
            t ["work_scale"],
            t ["repeats"],
            t ["cores_per_task"],
            bool (t .get ("use_sudo",False )),
            tuple (t .get ("cpu_list")or []),
            )
            for t in existing .get ("tasks",[])
            }
            new_tasks =[
            t for t in tasks_data 
            if (
            t ["baseline_c"],
            t ["prio_c"],
            t ["work_scale"],
            t ["repeats"],
            t ["cores_per_task"],
            bool (t .get ("use_sudo",False )),
            tuple (t .get ("cpu_list")or []),
            )
            not in existing_task_ids 
            ]
            config ["tasks"]=existing .get ("tasks",[])+new_tasks 
        except Exception :
        # If reading fails, fall back to overwrite mode
            pass 

            # writeFile
    with open (config_path ,"w",encoding ="utf-8")as f :
        json .dump (config ,f ,ensure_ascii =False ,indent =2 )

    return config_path 


def load_config (config_path :Path )->Dict [str ,Any ]:
    """Load task configuration from a JSON file
    
    Args:
        config_path: config_filespath
        
    Returns:
        config dictionary
    """
    config_path =Path (config_path ).expanduser ().resolve ()
    if not config_path .exists ():
        raise FileNotFoundError (f"config_filesdoes not exist: {config_path}")

    with open (config_path ,"r",encoding ="utf-8")as f :
        config =json .load (f )

    validate_config (config )
    return config 


def validate_config (config :Dict [str ,Any ])->None :
    """Validate the config_files format
    
    Args:
        config: config dictionary
        
    Raises:
        ValueError: if the config format is invalid
    """
    if not isinstance (config ,dict ):
        raise ValueError ("config_files must be a JSON object")

    if "tasks"not in config :
        raise ValueError ("config_files is missing the `tasks` field")

    if not isinstance (config ["tasks"],list ):
        raise ValueError ("`tasks` must be an array")

    required_fields =["baseline_c","prio_c","work_scale","repeats","cores_per_task"]
    for i ,task in enumerate (config ["tasks"]):
        if not isinstance (task ,dict ):
            raise ValueError (f"Task {i} must be an object")
        for field in required_fields :
            if field not in task :
                raise ValueError (f"Task {i} is missing required field: {field}")

                # Validate file paths
        baseline =Path (task ["baseline_c"]).expanduser ()
        prio =Path (task ["prio_c"]).expanduser ()
        if not baseline .exists ():
            raise ValueError (f"Task {i} baseline_c file does not exist: {baseline}")
        if not prio .exists ():
            raise ValueError (f"Task {i} prio_c file does not exist: {prio}")


def tasks_from_config (
config :Dict [str ,Any ],
config_name :Optional [str ]=None ,
config_path :Optional [Path ]=None ,
)->List [Task ]:
    """Create list of Task objects from config dictionary\n    \n    Args:\n        config: config dictionary\n        config_name: config_files name (without extension), used for result-directory naming\n        config_path: config_files path, used to locate the resume-mode status file\n        \n    Returns:\n        list of Task objects\n    """
    from ..utils .datetime_utils import now_ts_safe 

    tasks =[]
    resume_file =default_resume_file (config_path ,tool_dir =Path (__file__ ).parent .parent )if config_path else None 
    for task_data in config ["tasks"]:
        baseline_c =Path (task_data ["baseline_c"]).expanduser ().resolve ()
        prio_c =Path (task_data ["prio_c"]).expanduser ().resolve ()

        task_id =(
        f"{baseline_c.parent.name}_{baseline_c.stem}_vs_{prio_c.stem}_"
        f"{now_ts_safe()}_{uuid.uuid4().hex[:8]}"
        )
        payload =task_payload_for_key (
        baseline_c =baseline_c ,
        prio_c =prio_c ,
        work_scale =int (task_data ["work_scale"]),
        repeats =int (task_data ["repeats"]),
        cores_per_task =int (task_data ["cores_per_task"]),
        use_sudo =bool (task_data .get ("use_sudo",False )),
        cpu_list =task_data .get ("cpu_list"),
        )
        task_key =compute_task_key (payload )

        task =Task (
        task_id =task_id ,
        baseline_c =baseline_c ,
        prio_c =prio_c ,
        work_scale =int (task_data ["work_scale"]),
        repeats =int (task_data ["repeats"]),
        cores_per_task =int (task_data ["cores_per_task"]),
        use_sudo =bool (task_data .get ("use_sudo",False )),
        cpu_list =task_data .get ("cpu_list"),# optional
        config_name =config_name ,# set the config_files name
        task_key =task_key ,
        resume_file =resume_file ,
        )
        tasks .append (task )

    return tasks 
