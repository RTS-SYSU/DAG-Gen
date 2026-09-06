from __future__ import annotations 

"""API routes"""

from flask import jsonify ,request ,render_template ,send_file 
from pathlib import Path 
from typing import Dict ,List 
import os 
import json 
import platform 
import subprocess 
import shutil 
import uuid 

from ...core .task import Task 
from ...core .cpu_pool import CpuPool 
from ...core .task_runner import TaskRunner 
from ...config .defaults import DEFAULT_MAX_WORKERS 
from ...utils .cpu import read_cpu_online ,get_cpu_info ,benchmark_core_speed ,recommend_test_params 
from ...utils .datetime_utils import now_ts_safe 
from ...utils .config_manager import save_config ,load_config ,tasks_from_config 
from ...utils .resume_state import apply_resume_to_task ,default_resume_file 


# Global state (a better state-management approach should be used in production)
_task_manager :Dict ={
'tasks':[],
'task_q':None ,
'cpu_pool':None ,
'runners':[],
'queue_mode':False ,
'serial_sem':None ,
'results_root':None ,
}


def register_routes (app ):
    """register all routes"""

    def _default_results_root ()->Path :
        tool_dir =Path (__file__ ).parent .parent .parent # web -> ui -> runtime_compare
        return (tool_dir /"experimentresult").resolve ()

    def _get_results_root ()->Path :
        rr =_task_manager .get ('results_root')
        if rr :
            try :
                return Path (rr ).expanduser ().resolve ()
            except Exception :
                pass 
        return _default_results_root ()

    def _set_results_root (path :Path )->Path :
        path =Path (path ).expanduser ()
        if not path .is_absolute ():
        # Resolve relative paths from the tool directory to support inputs like experiment_results/xxx
            tool_dir =Path (__file__ ).parent .parent .parent 
            path =(tool_dir /path ).resolve ()
        else :
            path =path .resolve ()
        path .mkdir (parents =True ,exist_ok =True )
        if not (path .exists ()and path .is_dir ()):
            raise ValueError (f"not a valid directory: {path}")
        if not os .access (str (path ),os .W_OK |os .X_OK ):
            raise PermissionError (f"directory is not writable: {path}")
        _task_manager ['results_root']=path 
        return path 

    @app .route ('/')
    def index ():
        """home page"""
        return render_template ('index.html')

    @app .route ('/api/system',methods =['GET'])
    def get_system_info ():
        """get system information"""
        cpu_info =get_cpu_info ()
        cpu_list =cpu_info ['cpu_list']
        cpu_pool =_task_manager .get ('cpu_pool')
        if cpu_pool :
            free_count =cpu_pool .free_count ()
            total_count =cpu_pool .total_count ()
        else :
            free_count =len (cpu_list )
            total_count =len (cpu_list )

        return jsonify ({
        'cpu_online':cpu_list ,
        'cpu_total':total_count ,
        'cpu_free':free_count ,
        'queue_mode':_task_manager .get ('queue_mode',False ),
        'cpu_info':cpu_info ,
        'core_bench':benchmark_core_speed (cpu_list [:min (4 ,len (cpu_list ))])if cpu_list else {},
        'hostname':platform .node (),
        'results_root':str (_get_results_root ()),
        'recommend':recommend_test_params (cpu_info ),
        })

    @app .route ('/api/results-root',methods =['GET'])
    def get_results_root ():
        """get the current experiment-results directory(applies to subsequent tasks)"""
        cur =_get_results_root ()
        return jsonify ({
        'results_root':str (cur ),
        'default_root':str (_default_results_root ()),
        }),200 

    @app .route ('/api/results-root',methods =['POST'])
    def set_results_root ():
        """set the experiment-results directory(applies to subsequent tasks)"""
        try :
            data =request .get_json ()or {}
            p =(data .get ('path')or '').strip ()
            if not p :
                return jsonify ({'error':'missing path'}),400 
            new_rr =_set_results_root (Path (p ))
            return jsonify ({'results_root':str (new_rr )}),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),400 

    @app .route ('/api/results-root/new',methods =['POST'])
    def create_results_root ():
        """create a subdirectory under the given parent directory and set it as the results directory(applies to subsequent tasks)"""
        try :
            data =request .get_json ()or {}
            parent =(data .get ('parent')or '').strip ()
            name =(data .get ('name')or '').strip ()
            if not name :
                return jsonify ({'error':'missing name'}),400 
            if any (sep in name for sep in ('/','\\'))or name in ('.','..')or '..'in name :
                return jsonify ({'error':'invalid directory name'}),400 

            parent_path =Path (parent ).expanduser ()if parent else _get_results_root ()
            if not parent_path .is_absolute ():
                tool_dir =Path (__file__ ).parent .parent .parent 
                parent_path =(tool_dir /parent_path ).resolve ()
            else :
                parent_path =parent_path .resolve ()
            if not parent_path .exists ()or not parent_path .is_dir ():
                return jsonify ({'error':f'parent directory does not exist: {parent_path}'}),400 

            new_dir =parent_path /name 
            new_rr =_set_results_root (new_dir )
            return jsonify ({'results_root':str (new_rr )}),201 
        except Exception as e :
            return jsonify ({'error':str (e )}),400 

    @app .route ('/api/system/save',methods =['POST'])
    def save_system_info ():
        """save system information to a file"""
        cpu_info =get_cpu_info ()
        cpu_list =cpu_info .get ('cpu_list',[])
        bench =benchmark_core_speed (cpu_list [:min (4 ,len (cpu_list ))])if cpu_list else {}

        payload ={
        'timestamp':now_ts_safe (),
        'hostname':platform .node (),
        'cpu_info':cpu_info ,
        'core_bench':bench ,
        'queue_mode':_task_manager .get ('queue_mode',False ),
        }

        tool_dir =Path (__file__ ).parent .parent .parent 
        out_dir =tool_dir /"system information"
        out_dir .mkdir (parents =True ,exist_ok =True )

        fname =f"{payload['timestamp']}_{payload['hostname'] or 'system'}.json"
        out_path =out_dir /fname 
        out_path .write_text (json .dumps (payload ,ensure_ascii =False ,indent =2 ),encoding ='utf-8')

        return jsonify ({'status':'saved','file':str (out_path )}),201 

    @app .route ('/api/system/queue-mode',methods =['POST'])
    def set_queue_mode ():
        """set queue mode"""
        data =request .get_json ()or {}
        queue_mode =bool (data .get ('queue_mode',False ))
        _task_manager ['queue_mode']=queue_mode 
        return jsonify ({
        'queue_mode':queue_mode ,
        'status':'updated'
        }),200 

    @app .route ('/api/tasks',methods =['GET'])
    def get_tasks ():
        """get all task statuses"""
        tasks =_task_manager .get ('tasks',[])
        return jsonify ({
        'tasks':[_task_to_dict (t )for t in tasks ]
        })

    @app .route ('/api/tasks',methods =['POST'])
    def add_task ():
        """add a new task（support v3.0 single-file mode and the legacy mode）"""
        data =request .get_json ()

        # v3.0 single-file mode：source_c + algo_name
        if 'source_c'in data :
            source_c =Path (data ['source_c']).expanduser ().resolve ()
            if not source_c .exists ()or source_c .suffix .lower ()!='.c':
                return jsonify ({'error':'Invalid source file'}),400 

            algo_name =data .get ('algo_name',source_c .stem )
            task_id =(
            f"{algo_name}_{now_ts_safe()}_{uuid.uuid4().hex[:8]}"
            )
            cpu_list =data .get ('cpu_list')

            task =Task (
            task_id =task_id ,
            source_c =source_c ,
            algo_name =algo_name ,
            work_scale =int (data .get ('work_scale',100 )),
            repeats =int (data .get ('repeats',10 )),
            cores_per_task =int (data .get ('cores_per_task',2 )),
            use_sudo =bool (data .get ('use_sudo',False )),
            cpu_list =cpu_list ,
            config_name =(data .get ('config_name')or '').strip ()or None ,
            batch_name =(data .get ('batch_name')or '').strip ()or None ,
            )

            _task_manager ['tasks'].append (task )
            _task_manager ['task_q'].put (task )
            return jsonify ({'task_id':task_id ,'status':'queued'}),201 

            # legacy-mode compatibility：baseline_c + prio_c
        required =['baseline_c','prio_c','work_scale','repeats','cores_per_task']
        for field in required :
            if field not in data :
                return jsonify ({'error':f'Missing required field: {field}'}),400 

        baseline_c =Path (data ['baseline_c']).expanduser ().resolve ()
        prio_c =Path (data ['prio_c']).expanduser ().resolve ()

        if not baseline_c .exists ()or baseline_c .suffix .lower ()!='.c':
            return jsonify ({'error':'Invalid baseline C file'}),400 
        if not prio_c .exists ()or prio_c .suffix .lower ()!='.c':
            return jsonify ({'error':'Invalid priority C file'}),400 

        task_id =(
        f"{baseline_c.parent.name}_{baseline_c.stem}_vs_{prio_c.stem}_"
        f"{now_ts_safe()}_{uuid.uuid4().hex[:8]}"
        )
        cpu_list =data .get ('cpu_list')

        task =Task (
        task_id =task_id ,
        baseline_c =baseline_c ,
        prio_c =prio_c ,
        work_scale =int (data ['work_scale']),
        repeats =int (data ['repeats']),
        cores_per_task =int (data ['cores_per_task']),
        use_sudo =bool (data .get ('use_sudo',False )),
        cpu_list =cpu_list ,
        config_name =(data .get ('config_name')or '').strip ()or None ,
        )

        _task_manager ['tasks'].append (task )
        _task_manager ['task_q'].put (task )

        return jsonify ({'task_id':task_id ,'status':'queued'}),201 

    @app .route ('/api/batch_submit',methods =['POST'])
    def batch_submit ():
        """Batch submit: scan all algorithms under the `timing/` directory and automatically generate one task per result.\n\n        request body example：\n        {\n          \"entries\": [\n            {\n              \"folder\": \"/path/to/intermediate_results/zhang1\",\n              \"work_scale\": 100,\n              \"repeats\": 10,\n              \"cores_per_task\": 2,\n              \"cpu_list\": [0, 1],\n              \"use_sudo\": false\n            },\n            ...\n          ],\n          \"results_root\": \"/path/to/output\"   // optional, overrides the current `results_root`\n        }\n\n        v3.0 scan path：{folder}/pipeline/instrument/level2/effective_line_merge/timing/*/\n        For each subdirectory, find the `.c` file with the same name as the directory and generate an independent task.\n        batch_name = folder the last directory name（for example `zhang1`）\nalgo_name = subdirectory name (such as CFS/FIFO/LPF/heft/...)\n        """
        data =request .get_json ()or {}
        entries =data .get ('entries',[])
        if not entries :
            return jsonify ({'error':'missing entries field'}),400 

            # Optional: temporarily override `results_root`
        override_root =data .get ('results_root','').strip ()
        if override_root :
            try :
                rr =Path (override_root ).expanduser ().resolve ()
                rr .mkdir (parents =True ,exist_ok =True )
                _task_manager ['results_root']=str (rr )
            except Exception as e :
                return jsonify ({'error':f'results_root invalid: {e}'}),400 

        added =[]
        errors =[]

        for entry in entries :
            folder =entry .get ('folder','').strip ()
            if not folder :
                errors .append ({'entry':entry ,'error':'missing folder field'})
                continue 

            folder_path =Path (folder ).expanduser ().resolve ()
            if not folder_path .is_dir ():
                errors .append ({'entry':entry ,'error':f'directorydoes not exist: {folder_path}'})
                continue 

                # v3.0: scan the timing/ directory first
            timing_dir =folder_path /'pipeline'/'instrument'/'level2'/'effective_line_merge'/'timing'
            # Legacy-compatible structure: if `timing/` does not exist, fall back to the old scan method
            instrument_dir =folder_path /'pipeline'/'instrument'/'level2'/'effective_line_merge'

            batch_name =folder_path .name # for example `zhang1`
            work_scale =int (entry .get ('work_scale',100 ))
            repeats =int (entry .get ('repeats',10 ))
            cores_per_task =int (entry .get ('cores_per_task',2 ))
            use_sudo =bool (entry .get ('use_sudo',False ))
            cpu_list =entry .get ('cpu_list')or None 

            # result folder naming：{base_name}_ws{ws}_r{r}_cpu{cores}
            cpu_tag ="".join (str (c )for c in sorted (cpu_list ))if cpu_list else f"{cores_per_task}core"
            batch_name =f"{batch_name}_ws{work_scale}_r{repeats}_cpu{cpu_tag}"
            # Unified timestamp: shared by all algorithms in the same batch
            batch_ts =now_ts_safe ()

            if timing_dir .is_dir ():
            # v3.0 New mode: scan subdirectories under `timing/`
                algo_dirs =sorted (p for p in timing_dir .iterdir ()if p .is_dir ())
                if not algo_dirs :
                    errors .append ({'entry':entry ,'error':f'timing directorycontains no algorithm subdirectories: {timing_dir}'})
                    continue 

                for algo_dir in algo_dirs :
                    algo_name =algo_dir .name 
                    # Find the `.c` file with the same name as the directory
                    source_c =algo_dir /f"{algo_name}.c"
                    if not source_c .exists ():
                    # Fallback: find the only `.c` file in the directory
                        c_files =list (algo_dir .glob ("*.c"))
                        if len (c_files )==1 :
                            source_c =c_files [0 ]
                        else :
                            errors .append ({
                            'entry':entry ,
                            'error':f'{algo_name}: Not found {algo_name}.c(the directory contains {len(c_files)} `.c` files)'
                            })
                            continue 

                    task_id =(
                    f"{batch_name}_{algo_name}_"
                    f"{now_ts_safe()}_{uuid.uuid4().hex[:8]}"
                    )
                    task =Task (
                    task_id =task_id ,
                    source_c =source_c ,
                    algo_name =algo_name ,
                    work_scale =work_scale ,
                    repeats =repeats ,
                    cores_per_task =cores_per_task ,
                    use_sudo =use_sudo ,
                    cpu_list =cpu_list ,
                    batch_name =batch_name ,
                    batch_ts =batch_ts ,
                    )
                    _task_manager ['tasks'].append (task )
                    _task_manager ['task_q'].put (task )
                    added .append ({'task_id':task_id ,'batch_name':batch_name ,'algo':algo_name })

            elif instrument_dir .is_dir ():
            # legacy-mode compatibility: scan source_original.c/source_instrumented.c under the algorithm subdirectory
                algo_dirs =sorted (p for p in instrument_dir .iterdir ()if p .is_dir ()and p .name not in ('result','timing'))
                if not algo_dirs :
                    errors .append ({'entry':entry ,'error':f'instrument directorycontains no algorithm subdirectories: {instrument_dir}'})
                    continue 

                for algo_dir in algo_dirs :
                    baseline_c =algo_dir /'source_original.c'
                    prio_c =algo_dir /'source_instrumented.c'
                    if not baseline_c .exists ()or not prio_c .exists ():
                        errors .append ({
                        'entry':entry ,
                        'error':f'{algo_dir.name}: Missing `source_original.c` or `source_instrumented.c`'
                        })
                        continue 

                    algo_name =algo_dir .name 
                    task_id =(
                    f"{batch_name}_{algo_name}_vs_prio_"
                    f"{now_ts_safe()}_{uuid.uuid4().hex[:8]}"
                    )
                    task =Task (
                    task_id =task_id ,
                    baseline_c =baseline_c ,
                    prio_c =prio_c ,
                    work_scale =work_scale ,
                    repeats =repeats ,
                    cores_per_task =cores_per_task ,
                    use_sudo =use_sudo ,
                    cpu_list =cpu_list ,
                    batch_name =batch_name ,
                    algo_name =algo_name ,
                    )
                    _task_manager ['tasks'].append (task )
                    _task_manager ['task_q'].put (task )
                    added .append ({'task_id':task_id ,'batch_name':batch_name ,'algo':algo_name })
            else :
                errors .append ({'entry':entry ,'error':f'Not found instrument or timing directory: {instrument_dir}'})
                continue 

        return jsonify ({'added':added ,'errors':errors ,'total':len (added )}),201 

    @app .route ('/api/fs/list',methods =['GET'])
    def list_filesystem ():
        """list directory contents（allow browsing any local directory）"""
        try :
            base_dir =Path (app .config ['BASE_DIR']).resolve ()
            req_path =(request .args .get ('path')or "").strip ()
            suffix =(request .args .get ('suffix')or ".c").strip ()

            if req_path :
                req =Path (req_path ).expanduser ()
                if req .is_absolute ():
                    current =req .resolve ()
                else :
                    current =(base_dir /req ).resolve ()
            else :
                current =base_dir 

            if not current .exists ():
                return jsonify ({'error':f'pathdoes not exist: {current}'}),404 
            if not current .is_dir ():
                if current .is_file ():
                    current =current .parent 
                else :
                    return jsonify ({'error':f'not a directory: {current}'}),400 

            dirs =[]
            files =[]
            for child in sorted (current .iterdir (),key =lambda x :(not x .is_dir (),x .name .lower ())):
                if child .is_dir ():
                    dirs .append ({'name':child .name ,'path':str (child )})
                elif child .is_file ():
                    if not suffix or child .suffix .lower ()==suffix .lower ():
                        files .append ({'name':child .name ,'path':str (child )})

            parent =None 
            if current .parent !=current :
                parent =str (current .parent )

            return jsonify ({
            'base_dir':str (base_dir ),
            'current':str (current ),
            'parent':parent ,
            'suffix':suffix ,
            'dirs':dirs ,
            'files':files ,
            }),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/fs/pick-file',methods =['POST'])
    def pick_file_with_system_dialog ():
        """invoke the system file manager/file picker and return the selected file path."""
        try :
            base_dir =Path (app .config ['BASE_DIR']).resolve ()
            data =request .get_json ()or {}
            suffix =(data .get ('suffix')or '.c').strip ()
            title =(data .get ('title')or 'SelectFile').strip ()

            # prefer the system file picker（Linux common desktop dialog）
            candidates =[
            ["zenity","--file-selection","--title",title ],
            ["yad","--file-selection","--title",title ],
            ["qarma","--file-selection","--title",title ],
            ]
            if suffix :
                f =f"*{suffix}"
                candidates [0 ].extend (["--file-filter",f ])
                candidates [1 ].extend (["--file-filter",f ])
                candidates [2 ].extend (["--file-filter",f ])

            picked =None 
            for cmd in candidates :
                if not shutil .which (cmd [0 ]):# type: ignore[name-defined]
                    continue 
                proc =subprocess .run (cmd ,capture_output =True ,text =True )
                if proc .returncode ==0 and proc .stdout .strip ():
                    picked =proc .stdout .strip ()
                    break 

                    # fallback: tk file dialog（only try when a desktop session is available）
            if not picked and (os .environ .get ("DISPLAY")or os .environ .get ("WAYLAND_DISPLAY")):
                try :
                    import tkinter as tk # Delayed import to avoid errors in non-GUI environments
                    from tkinter import filedialog 

                    root =tk .Tk ()
                    root .withdraw ()
                    patterns =[(f"*{suffix} File",f"*{suffix}")]if suffix else [("All files","*.*")]
                    picked_tmp =filedialog .askopenfilename (
                    title =title ,
                    initialdir =str (base_dir ),
                    filetypes =patterns ,
                    )
                    root .destroy ()
                    if picked_tmp :
                        picked =picked_tmp 
                except Exception :
                    picked =None 

            if not picked :
                return jsonify ({'error':'no file selected, or the system file picker is unavailable (use the Browse button instead)'}),400 

            p =Path (picked ).expanduser ().resolve ()
            if suffix and p .suffix .lower ()!=suffix .lower ():
                return jsonify ({'error':f'Please select {suffix} File'}),400 
            return jsonify ({'path':str (p )}),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/fs/pick-dir',methods =['POST'])
    def pick_dir_with_system_dialog ():
        """invoke the system directory picker and return the selected directory path."""
        try :
            base_dir =Path (app .config ['BASE_DIR']).resolve ()
            data =request .get_json ()or {}
            title =(data .get ('title')or 'Selectdirectory').strip ()

            candidates =[
            ["zenity","--file-selection","--directory","--title",title ],
            ["yad","--file-selection","--directory","--title",title ],
            ["qarma","--file-selection","--directory","--title",title ],
            ]

            picked =None 
            for cmd in candidates :
                if not shutil .which (cmd [0 ]):
                    continue 
                proc =subprocess .run (cmd ,capture_output =True ,text =True )
                if proc .returncode ==0 and proc .stdout .strip ():
                    picked =proc .stdout .strip ()
                    break 

            if not picked and (os .environ .get ("DISPLAY")or os .environ .get ("WAYLAND_DISPLAY")):
                try :
                    import tkinter as tk 
                    from tkinter import filedialog 

                    root =tk .Tk ()
                    root .withdraw ()
                    picked_tmp =filedialog .askdirectory (
                    title =title ,
                    initialdir =str (base_dir ),
                    )
                    root .destroy ()
                    if picked_tmp :
                        picked =picked_tmp 
                except Exception :
                    picked =None 

            if not picked :
                return jsonify ({'error':'no directory selected, or the system directory picker is unavailable (browse manually in the page)'}),400 

            p =Path (picked ).expanduser ().resolve ()
            if not p .exists ()or not p .is_dir ():
                return jsonify ({'error':f'not a valid directory: {p}'}),400 
            return jsonify ({'path':str (p )}),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/tasks/<task_id>',methods =['DELETE'])
    def cancel_task (task_id ):
        """cancel a task（queued or running）"""
        tasks =_task_manager .get ('tasks',[])
        for task in tasks :
            if task .task_id ==task_id :
                if task .status in ('done','error','cancelled'):
                    return jsonify ({'error':f'the task has already finished and cannot be canceled: {task.status}'}),400 
                if task .status =='queued':
                    task .status ='cancelled'
                    task .phase ='cancelled'
                    task .cancel_requested =True 
                    task .cancel_evt .set ()
                    task .cancel_reason ='canceled by user'
                    task .message ='canceled by user'
                    return jsonify ({'status':'cancelled'}),200 
                if task .status in ('running','cancelling'):
                    task .status ='cancelling'
                    task .cancel_requested =True 
                    task .cancel_evt .set ()
                    task .cancel_reason ='canceled by user'
                    task .message ='canceled by user，stopping...'
                    return jsonify ({'status':'cancelling'}),200 
                task .status ='cancelled'
                task .phase ='cancelled'
                task .cancel_requested =True 
                task .cancel_evt .set ()
                task .cancel_reason ='canceled by user'
                task .message ='canceled by user'
                return jsonify ({'status':'cancelled'}),200 
        return jsonify ({'error':'task does not exist'}),404 

    @app .route ('/api/tasks/<task_id>/log',methods =['GET'])
    def get_task_log (task_id ):
        """get task log"""
        tasks =_task_manager .get ('tasks',[])
        for task in tasks :
            if task .task_id ==task_id and task .out_dir :
                log_file =task .out_dir /'run.log'
                if log_file .exists ():
                    return log_file .read_text (encoding ='utf-8'),200 ,{'Content-Type':'text/plain'}
        return jsonify ({'error':'log does not exist'}),404 

    @app .route ('/api/summary_all',methods =['POST'])
    def generate_summary_all ():
        """generate the summary_all.csv file。
        
        scan summary.json for all Completedd tasks under the specified batch，
        aggregate per-algorithm averages into a CSV file。
        
        Request body：{"batch_name": "zhang3"}  or  {"results_dir": "/path/to/batch_dir"}
        """
        data =request .get_json ()or {}
        batch_name =data .get ('batch_name','').strip ()
        results_dir =data .get ('results_dir','').strip ()

        if results_dir :
            batch_dir =Path (results_dir ).expanduser ().resolve ()
        elif batch_name :
            exp_root =_get_results_root ()
            batch_dir =exp_root /batch_name 
        else :
            return jsonify ({'error':'batch_name or results_dir is required'}),400 

        if not batch_dir .is_dir ():
            return jsonify ({'error':f'directorydoes not exist: {batch_dir}'}),404 

            # Scan `summary.json` files in subdirectories
            # The same algorithm may have multiple rounds of results (with timestamps); use the latest one (last by directory name sort order)
        algo_latest :Dict ={}# algo_name -> (dir_name, row_dict)
        for sub in sorted (batch_dir .iterdir ()):
            if not sub .is_dir ():
                continue 
            summary_path =sub /'summary.json'
            if not summary_path .exists ():
                continue 
            try :
                summary =json .loads (summary_path .read_text (encoding ='utf-8'))
                algo =summary .get ('algo_name',sub .name )
                stats =summary .get ('stats',{})
                row ={
                'algorithm':algo ,
                'avg_s':stats .get ('mean_s',0.0 ),
                'min_s':stats .get ('min_s',0.0 ),
                'max_s':stats .get ('max_s',0.0 ),
                'median_s':stats .get ('median_s',0.0 ),
                'n':stats .get ('n',0 ),
                'dir':sub .name ,
                }
                # The same algorithm selects the directory with the largest name (i.e. latest timestamp)
                if algo not in algo_latest or sub .name >algo_latest [algo ][0 ]:
                    algo_latest [algo ]=(sub .name ,row )
            except Exception :
                continue 

        rows =[v [1 ]for v in sorted (algo_latest .values (),key =lambda x :x [1 ]['algorithm'])]

        if not rows :
            return jsonify ({'error':'Not foundCompletedd task results'}),404 

            # write summary_all.csv
        csv_lines =["algorithm,avg_s,min_s,max_s,median_s,n\n"]
        for r in rows :
            csv_lines .append (
            f"{r['algorithm']},{r['avg_s']:.9f},{r['min_s']:.9f},{r['max_s']:.9f},{r['median_s']:.9f},{r['n']}\n"
            )
        csv_path =batch_dir /"summary_all.csv"
        csv_path .write_text ("".join (csv_lines ),encoding ="utf-8")

        return jsonify ({
        'path':str (csv_path ),
        'algorithms':len (rows ),
        'rows':rows ,
        }),200 

        # ========== config_files management API ==========

    def _get_config_dir ()->Path :
        """getconfig_files directory"""
        tool_dir =Path (__file__ ).parent .parent .parent # web -> ui -> runtime_compare
        config_dir =tool_dir /"config_files"
        config_dir .mkdir (parents =True ,exist_ok =True )
        return config_dir 

    @app .route ('/api/config/list',methods =['GET'])
    def list_configs ():
        """list all config files"""
        try :
            config_dir =_get_config_dir ()
            configs =[]
            for f in sorted (config_dir .glob ("*.json"),key =lambda x :x .stat ().st_mtime ,reverse =True ):
                stat =f .stat ()
                configs .append ({
                'filename':f .name ,
                'size':stat .st_size ,
                'modified':stat .st_mtime ,
                'path':str (f ),
                })
            return jsonify ({'configs':configs })
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/config/download/<filename>',methods =['GET'])
    def download_config (filename ):
        """download config files"""
        try :
            config_dir =_get_config_dir ()
            config_path =config_dir /filename 
            if not config_path .exists ()or not config_path .is_file ():
                return jsonify ({'error':'config_filesdoes not exist'}),404 
            return send_file (str (config_path ),as_attachment =True ,download_name =filename )
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/config/delete/<filename>',methods =['DELETE'])
    def delete_config (filename ):
        """deleteconfig_files"""
        try :
            config_dir =_get_config_dir ()
            config_path =config_dir /filename 
            if not config_path .exists ():
                return jsonify ({'error':'config_filesdoes not exist'}),404 
            config_path .unlink ()
            return jsonify ({'status':'deleted'}),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/config/export',methods =['POST'])
    def export_config ():
        """manually export config files"""
        try :
            data =request .get_json ()or {}
            config_name =data .get ('config_name')# optional: user-specified config name

            config_dir =_get_config_dir ()
            if config_name :
                config_path =config_dir /f"{config_name}.json"
            else :
                config_path =config_dir /f"web_tasks_{now_ts_safe()}.json"

            tasks =_task_manager .get ('tasks',[])
            save_config (
            tasks ,
            config_path ,
            queue_mode =_task_manager .get ('queue_mode',False ),
            mode ="overwrite"# manual export uses overwrite mode
            )

            return jsonify ({
            'config_path':str (config_path ),
            'filename':config_path .name ,
            'download_url':f'/api/config/download/{config_path.name}'
            }),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),500 

    @app .route ('/api/config/import',methods =['POST'])
    def import_config ():
        """import config files"""
        try :
        # support file upload or JSON data
            if 'file'in request .files :
                file =request .files ['file']
                if file .filename =='':
                    return jsonify ({'error':'no file selected'}),400 
                if not file .filename .endswith ('.json'):
                    return jsonify ({'error':'the file must be in JSON format'}),400 

                    # save to the tool config directory so resume state can persist
                config_dir =_get_config_dir ()
                config_dir .mkdir (parents =True ,exist_ok =True )
                safe_name =Path (file .filename ).name 
                config_path =(config_dir /safe_name ).resolve ()
                # if the same name already exists, append a timestamp automatically to avoid overwriting the user file
                if config_path .exists ():
                    config_path =(config_dir /f"{Path(safe_name).stem}_{now_ts_safe()}.json").resolve ()
                file .save (str (config_path ))
            elif request .is_json :
                data =request .get_json ()
                if 'config_path'in data :
                    config_path =Path (data ['config_path']).expanduser ().resolve ()
                else :
                    return jsonify ({'error':'a file or config path is required'}),400 
            else :
                return jsonify ({'error':'a file or JSON data payload is required'}),400 

            if not config_path .exists ():
                return jsonify ({'error':'config_filesdoes not exist'}),404 

                # load configuration
            config =load_config (config_path )
            config_name =config_path .stem # filename without extension
            resume_file =default_resume_file (config_path )

            # create task objects
            new_tasks =tasks_from_config (config ,config_name =config_name ,config_path =config_path )
            resumed =0 
            for t in new_tasks :
                ok ,_ =apply_resume_to_task (t )
                if ok :
                    resumed +=1 

                    # deduplication check: check whether a task with the same parameters already exists
            existing_tasks =_task_manager .get ('tasks',[])
            existing_keys =set ()
            for t in existing_tasks :
                if t .is_single_mode :
                    existing_keys .add ((
                    t .source_c ,
                    t .algo_name ,
                    t .work_scale ,
                    t .repeats ,
                    t .cores_per_task ,
                    bool (t .use_sudo ),
                    tuple (t .cpu_list or []),
                    ))
                else :
                    existing_keys .add ((
                    t .baseline_c ,
                    t .prio_c ,
                    t .work_scale ,
                    t .repeats ,
                    t .cores_per_task ,
                    bool (t .use_sudo ),
                    tuple (t .cpu_list or []),
                    ))

            added_count =0 
            queued_count =0 
            for task in new_tasks :
                if task .is_single_mode :
                    task_key =(
                    task .source_c ,
                    task .algo_name ,
                    task .work_scale ,
                    task .repeats ,
                    task .cores_per_task ,
                    bool (task .use_sudo ),
                    tuple (task .cpu_list or []),
                    )
                else :
                    task_key =(
                    task .baseline_c ,
                    task .prio_c ,
                    task .work_scale ,
                    task .repeats ,
                    task .cores_per_task ,
                    bool (task .use_sudo ),
                    tuple (task .cpu_list or []),
                    )
                if task_key not in existing_keys :
                    _task_manager ['tasks'].append (task )
                    if task .status !="done":
                        _task_manager ['task_q'].put (task )
                        queued_count +=1 
                    existing_keys .add (task_key )
                    added_count +=1 

            return jsonify ({
            'imported':added_count ,
            'total':len (new_tasks ),
            'queued':queued_count ,
            'resumed_done':resumed ,
            'resume_file':str (resume_file ),
            'message':f'Successfully imported {added_count}/{len(new_tasks)}  tasks (already-completed skipped: {resumed}; queued: {queued_count}）'
            }),200 
        except Exception as e :
            return jsonify ({'error':str (e )}),500 


def _task_to_dict (task :Task )->Dict :
    """convert a Task object to a dictionary"""
    elapsed =""
    if task .start_ns :
        end =task .end_ns if task .end_ns else None 
        if end :
            elapsed =f"{(end - task.start_ns) / 1e9:.1f}s"

    d ={
    'task_id':task .task_id ,
    'status':task .status ,
    'phase':task .phase ,
    'progress':f"{task.progress_i}/{task.progress_n}"if task .progress_n else "",
    'cpu_set':task .cpu_set ,
    'elapsed':elapsed ,
    'message':task .message ,
    'out_dir':str (task .out_dir )if task .out_dir else "",
    'work_scale':task .work_scale ,
    'repeats':task .repeats ,
    'cores_per_task':task .cores_per_task ,
    'batch_name':task .batch_name or "",
    'algo_name':task .algo_name or "",
    'single_mode':task .is_single_mode ,
    }
    if task .is_single_mode :
        d ['source_c']=str (task .source_c )if task .source_c else ""
        d ['baseline_c']=""
        d ['prio_c']=""
    else :
        d ['source_c']=""
        d ['baseline_c']=str (task .baseline_c )if task .baseline_c else ""
        d ['prio_c']=str (task .prio_c )if task .prio_c else ""
    return d 


def init_task_manager (base_dir :Path ,queue_mode :bool =False ,results_root :Path |None =None ):
    """initialize the task manager
    
    Args:
        base_dir: projectroot directory
        queue_mode: whether queue mode is enabled
        results_root: experiment-results root directory (optional)
    """
    import threading 
    from queue import Queue 

    cpu_list =read_cpu_online ()
    cpu_pool =CpuPool (cpu_list )
    task_q :Queue [Task ]=Queue ()
    tasks :List [Task ]=[]
    serial_sem =threading .Semaphore (1 )

    # Create `_task_manager` first so `queue_mode_fn` can access it
    tool_dir =Path (__file__ ).parent .parent .parent # web -> ui -> runtime_compare
    rr =Path (results_root ).expanduser ()if results_root else (tool_dir /"experimentresult")
    if not rr .is_absolute ():
        rr =(tool_dir /rr ).resolve ()
    else :
        rr =rr .resolve ()
    rr .mkdir (parents =True ,exist_ok =True )

    _task_manager .update ({
    'tasks':tasks ,
    'task_q':task_q ,
    'cpu_pool':cpu_pool ,
    'runners':[],
    'queue_mode':queue_mode ,
    'serial_sem':serial_sem ,
    'results_root':rr ,
    })

    def queue_mode_fn ():
    # dynamically read the current queue-mode setting
        return _task_manager .get ('queue_mode',False )

    def results_root_fn ():
        return _task_manager .get ('results_root')or rr 

    def on_update (task :Task ):
    # In Web mode, updates are queried through the API; this can be left empty or used for logging
        pass 

        # start the worker thread
    max_workers =min (DEFAULT_MAX_WORKERS ,max (1 ,len (cpu_list )))
    runners :List [TaskRunner ]=[]
    for _ in range (max_workers ):
        r =TaskRunner (
        base_dir =base_dir ,
        cpu_pool =cpu_pool ,
        task_q =task_q ,
        on_update =on_update ,
        serial_sem =serial_sem ,
        queue_mode_fn =queue_mode_fn ,
        results_root_fn =results_root_fn ,
        )
        r .start ()
        runners .append (r )

        # update the runners list
    _task_manager ['runners']=runners 
