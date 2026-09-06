"""Task runner"""

from __future__ import annotations 

import json 
import os 
import re 
import shutil 
import subprocess 
import threading 
import time 
import signal 
from pathlib import Path 
from queue import Queue 
from typing import Dict ,List ,Optional ,Tuple 

from ..config .defaults import GCC_FLAGS 
from ..core .task import Task 
from ..core .cpu_pool import CpuPool 
from ..utils .affinity import rewrite_sched_setaffinity_cpu_set ,run_with_affinity 
from ..utils .cpu import format_cpu_set 
from ..utils .file_ops import ensure_writable_dir 
from ..utils .sudo import has_passwordless_sudo 
from ..utils .time_parse import parse_internal_time_seconds 
from ..utils .datetime_utils import now_ts_safe 
from ..utils .resume_state import mark_done ,task_payload_for_key 


class TaskRunner (threading .Thread ):
    """Task runnerthread"""

    def __init__ (
    self ,
    *,
    base_dir :Path ,
    cpu_pool :CpuPool ,
    task_q :Queue [Task ],
    on_update :callable ,
    serial_sem :threading .Semaphore ,
    queue_mode_fn :callable ,
    results_root_fn :Optional [callable ]=None ,
    )->None :
        """Initialize task runner\n        \n        Args:\n            base_dir: projectroot directory\n            cpu_pool: CPU pool\n            task_q: task queue\n            on_update: task update callback\n            serial_sem: serial-mode semaphore\n            queue_mode_fn: function used to determine whether queue mode is enabled\n        """
        super ().__init__ (daemon =True )
        self ._base_dir =base_dir 
        # Compute the tool-directory path（tools/runtime_compare/）
        self ._tool_dir =Path (__file__ ).parent .parent .resolve ()
        self ._repo_root =self ._tool_dir .parent .parent 
        self ._cpu_pool =cpu_pool 
        self ._task_q =task_q 
        self ._on_update =on_update 
        self ._stop_evt =threading .Event ()
        self ._serial_sem =serial_sem 
        self ._queue_mode_fn =queue_mode_fn 
        self ._results_root_fn =results_root_fn or (lambda :(self ._tool_dir /"experimentresult"))

    def stop (self )->None :
        """stopTask runner"""
        self ._stop_evt .set ()

    def run (self )->None :
        """Main loop: get tasks from the queue and execute them"""
        while not self ._stop_evt .is_set ():
            try :
                task =self ._task_q .get (timeout =0.2 )
            except Exception :
                continue 
            self ._run_one (task )
            self ._task_q .task_done ()

    def _run_one (self ,task :Task )->None :
        """Execute a single task"""
        if task .is_single_mode :
            return self ._run_one_single (task )
        return self ._run_one_legacy (task )

    def _run_one_single (self ,task :Task )->None :
        """v3.0 single-file mode: compile runs one .c files, independent statistics"""
        acquired_serial =False 
        try :
            def cancel_check ()->bool :
                return (
                task .cancel_requested 
                or task .cancel_evt .is_set ()
                or task .status in ("cancelling","cancelled")
                )

            class _Cancelled (Exception ):
                pass 

            def raise_if_cancelled (phase :Optional [str ]=None )->None :
                if cancel_check ():
                    if phase :
                        task .phase =phase 
                    raise _Cancelled ()

            if task .status =="cancelled"or task .cancel_evt .is_set ()or task .cancel_requested :
                task .status ="cancelled"
                task .phase ="cancelled"
                task .message =task .message or (task .cancel_reason or "canceled by user")
                task .end_ns =time .monotonic_ns ()
                self ._on_update (task )
                return 

            if self ._queue_mode_fn ():
                self ._serial_sem .acquire ()
                acquired_serial =True 

            raise_if_cancelled ("wait_cpu")
            group =self ._cpu_pool .try_acquire_group (
            task .cores_per_task ,
            preferred =task .cpu_list 
            )
            if group is None :
                if cancel_check ():
                    task .status ="cancelled"
                    task .phase ="cancelled"
                    task .message =task .cancel_reason or "canceled by user"
                    task .end_ns =time .monotonic_ns ()
                    self ._on_update (task )
                    return 
                task .status ="queued"
                task .phase ="wait_cpu"
                task .message =f"Waiting for CPU: need {task.cores_per_task} cores, currently free {self._cpu_pool.free_count()}"
                self ._on_update (task )
                time .sleep (0.5 )
                self ._task_q .put (task )
                return 

            task .cpu_set =group 
            task .status ="running"
            task .phase ="setup"
            task .start_ns =time .monotonic_ns ()
            self ._on_update (task )

            if task .use_sudo and not has_passwordless_sudo ():
                task .status ="error"
                task .message ="Running with sudo enabled but unavailable in the current environment（Run this tool with `sudo`, or configure `sudo NOPASSWD`）。"
                self ._on_update (task )
                return 

                # Prepare the output directory
            exp_root =Path (self ._results_root_fn ()).expanduser ()
            if not exp_root .is_absolute ():
                exp_root =(self ._tool_dir /exp_root ).resolve ()
            else :
                exp_root =exp_root .resolve ()
            ensure_writable_dir (exp_root ,use_sudo =task .use_sudo )

            ts =task .batch_ts or now_ts_safe ()
            algo_str =task .algo_name or "unknown"

            if task .batch_name :
                batch_dir =exp_root /f"{task.batch_name}_{ts}"
                ensure_writable_dir (batch_dir ,use_sudo =task .use_sudo )
                out_dir =batch_dir /algo_str 
            else :
                config_name =task .config_name if task .config_name else "web_tasks"
                config_dir =exp_root /config_name 
                ensure_writable_dir (config_dir ,use_sudo =task .use_sudo )
                out_dir =config_dir /f"{algo_str}_ws{task.work_scale}_r{task.repeats}_{ts}"

            ensure_writable_dir (out_dir ,use_sudo =task .use_sudo )
            task .out_dir =out_dir 

            # copySource Filedirectory
            task .phase ="copy"
            task .progress_i =0 
            task .progress_n =0 
            self ._on_update (task )
            raise_if_cancelled ("copy")

            src_root =task .source_c .parent 
            work_dir =out_dir /"src"
            if work_dir .exists ():
                shutil .rmtree (work_dir )
            shutil .copytree (src_root ,work_dir )

            # ensure prio_runtime.h available
            prio_runtime_candidates =[
            self ._base_dir /"level1"/"prio_runtime.h",
            self ._repo_root /"level1"/"prio_runtime.h",
            ]
            prio_runtime_src =next ((p for p in prio_runtime_candidates if p .exists ()),None )
            if prio_runtime_src :
                dst =work_dir /"prio_runtime.h"
                if not dst .exists ():
                    shutil .copy2 (prio_runtime_src ,dst )

                    # Rewrite CPU affinity
            patched_affinity =False 
            patch_error :Optional [str ]=None 
            try :
                src_file =work_dir /task .source_c .name 
                if src_file .exists ():
                    txt =src_file .read_text (encoding ="utf-8",errors ="replace")
                    new_txt ,changed =rewrite_sched_setaffinity_cpu_set (txt ,task .cpu_set )
                    if changed :
                        src_file .write_text (new_txt ,encoding ="utf-8")
                        patched_affinity =True 
            except Exception as e :
                patch_error =str (e )

                # compile
            task .phase ="compile"
            task .progress_i =0 
            task .progress_n =1 
            self ._on_update (task )
            raise_if_cancelled ("compile")

            app_bin =out_dir /f"app_{algo_str}"
            entry_c_name =task .source_c .name 
            c_files =[entry_c_name ]

            include_dirs :List [str ]=[str (work_dir )]
            if prio_runtime_src and prio_runtime_src .exists ():
                include_dirs .append (str (prio_runtime_src .parent ))
            include_flags :List [str ]=[]
            for inc in include_dirs :
                include_flags .extend (["-I",inc ])

            cmd_parts =[
            "gcc",
            *GCC_FLAGS ,
            *include_flags ,
            f"-DWORK_SCALE={task.work_scale}",
            *c_files ,
            "-o",
            str (app_bin ),
            ]

            def preexec ()->None :
                os .setsid ()

            proc =subprocess .Popen (
            cmd_parts ,
            cwd =str (work_dir ),
            stdout =subprocess .PIPE ,
            stderr =subprocess .PIPE ,
            text =True ,
            preexec_fn =preexec ,
            )
            try :
                while True :
                    raise_if_cancelled ("compile")
                    try :
                        so ,se =proc .communicate (timeout =0.2 )
                        rc =int (proc .returncode or 0 )
                        break 
                    except subprocess .TimeoutExpired :
                        continue 
            except _Cancelled :
                try :
                    os .killpg (proc .pid ,signal .SIGTERM )
                except Exception :
                    try :
                        proc .terminate ()
                    except Exception :
                        pass 
                try :
                    proc .communicate (timeout =1.0 )
                except Exception :
                    try :
                        os .killpg (proc .pid ,signal .SIGKILL )
                    except Exception :
                        try :
                            proc .kill ()
                        except Exception :
                            pass 
                    proc .communicate ()
                raise 

            cmd_txt =" ".join (cmd_parts )

            # Fallback: if __wrap_main symbol is missing, remove --wrap=main and try again
            if rc !=0 and "__wrap_main"in se :
                filtered_flags =[f for f in GCC_FLAGS if f !="-Wl,--wrap=main"]
                cmd_parts2 =[
                "gcc",
                *filtered_flags ,
                *include_flags ,
                f"-DWORK_SCALE={task.work_scale}",
                *c_files ,
                "-o",
                str (app_bin ),
                ]
                proc2 =subprocess .Popen (
                cmd_parts2 ,cwd =str (work_dir ),
                stdout =subprocess .PIPE ,stderr =subprocess .PIPE ,text =True ,
                )
                so2 ,se2 =proc2 .communicate ()
                rc =int (proc2 .returncode or 0 )
                cmd_txt +="\nRETRY(no --wrap=main): "+" ".join (cmd_parts2 )
                so +=so2 
                se +="\n[retry]\n"+se2 

            (out_dir /"compile.log").write_text ("CMD: "+cmd_txt +"\n"+so +se ,encoding ="utf-8")
            task .progress_i =1 
            self ._on_update (task )

            if rc !=0 :
                raise RuntimeError (f"{algo_str} compilefailed：{se[-500:]}")

                # Run N times
            task .phase ="run"
            task .progress_i =0 
            task .progress_n =task .repeats 
            self ._on_update (task )
            raise_if_cancelled ("run")

            env =dict (os .environ )
            env ["WORK_SCALE"]=str (task .work_scale )

            times :List [float ]=[]
            runs :List [Dict ]=[]
            run_log =[]

            for i in range (task .repeats ):
                raise_if_cancelled ("run")
                rc_run ,out_txt ,err_txt ,wall_ns =run_with_affinity (
                [str (app_bin )],
                cwd =app_bin .parent ,
                env =env ,
                cpu_set =task .cpu_set ,
                use_sudo =task .use_sudo ,
                cancel_check =cancel_check ,
                )
                raise_if_cancelled ("run")
                run_log .append (f"=== {algo_str} run #{i+1} (rc={rc_run}) ===\n")
                run_log .append (out_txt )
                if err_txt :
                    run_log .append ("\n[stderr]\n")
                    run_log .append (err_txt )
                run_log .append ("\n")

                t =parse_internal_time_seconds (out_txt ,err_txt )
                if t is None :
                    raise RuntimeError (f"{algo_str} run failed：Unable to parse MAIN_ELAPSED_S / PROGRAM_TOTAL_NS")
                if rc_run !=0 :
                    raise RuntimeError (f"{algo_str} run failed：rc={rc_run}, stderr_tail={err_txt[-400:]}")

                times .append (float (t ))
                runs .append ({
                "algo":algo_str ,
                "iter":int (i ),
                "time_s":float (t ),
                "wall_s":float (wall_ns /1e9 ),
                "cpu_set":task .cpu_set ,
                "returncode":int (rc_run ),
                })
                task .progress_i =i +1 
                self ._on_update (task )

                # statistics
            times_sorted =sorted (times )
            n =len (times_sorted )
            mean_s =sum (times_sorted )/max (1 ,n )
            min_s =times_sorted [0 ]if n else 0.0 
            max_s =times_sorted [-1 ]if n else 0.0 
            median_s =times_sorted [n //2 ]if n else 0.0 

            stat ={
            "n":n ,
            "mean_s":mean_s ,
            "min_s":min_s ,
            "max_s":max_s ,
            "median_s":median_s ,
            }

            summary ={
            "task_id":task .task_id ,
            "algo_name":algo_str ,
            "created_at":ts ,
            "cpu_set":task .cpu_set ,
            "cores_per_task":task .cores_per_task ,
            "work_scale":task .work_scale ,
            "repeats":task .repeats ,
            "source_c":str (task .source_c ),
            "compile_cmd":cmd_txt .strip (),
            "affinity_rewritten":patched_affinity ,
            "stats":stat ,
            "times_s":times ,
            "runs":runs ,
            }
            if patch_error :
                summary ["affinity_patch_error"]=patch_error 
            (out_dir /"summary.json").write_text (json .dumps (summary ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
            (out_dir /"run.log").write_text ("".join (run_log ),encoding ="utf-8")

            # CSV output
            try :
                csv_lines =["run,time_s,wall_s\n"]
                for r in runs :
                    csv_lines .append (f"{r['iter']+1},{r['time_s']:.9f},{r['wall_s']:.9f}\n")
                csv_lines .append (f"avg,{mean_s:.9f},\n")
                csv_lines .append (f"min,{min_s:.9f},\n")
                csv_lines .append (f"max,{max_s:.9f},\n")
                (out_dir /"runs.csv").write_text ("".join (csv_lines ),encoding ="utf-8")
            except Exception :
                pass 

            task .status ="done"
            task .phase ="done"
            task .message =f"Completed: {algo_str} mean={mean_s:.3f}s ({n} runs)"
            task .end_ns =time .monotonic_ns ()

            # resume mode
            try :
                if task .resume_file and task .task_key and task .out_dir :
                    payload =task_payload_for_key (
                    baseline_c =task .source_c ,
                    prio_c =task .source_c ,
                    work_scale =task .work_scale ,
                    repeats =task .repeats ,
                    cores_per_task =task .cores_per_task ,
                    use_sudo =task .use_sudo ,
                    cpu_list =task .cpu_list ,
                    )
                    mark_done (
                    resume_file =Path (task .resume_file ),
                    task_key =str (task .task_key ),
                    task_id =task .task_id ,
                    out_dir =task .out_dir ,
                    message =task .message ,
                    done_at =now_ts_safe (),
                    payload =payload ,
                    )
            except Exception :
                pass 
            self ._on_update (task )
        except Exception as e :
            if isinstance (e ,type )and e .__class__ .__name__ =="_Cancelled":
                task .status ="cancelled"
                task .phase ="cancelled"
                task .message =task .cancel_reason or "canceled by user"
            elif "Cancelled"in type (e ).__name__ :
                task .status ="cancelled"
                task .phase ="cancelled"
                task .message =task .cancel_reason or "canceled by user"
            else :
                task .status ="error"
                task .phase ="error"
                task .message =str (e )
            task .end_ns =time .monotonic_ns ()
            self ._on_update (task )
        finally :
            if task .cpu_set :
                self ._cpu_pool .release_group (task .cpu_set )
            if acquired_serial :
                self ._serial_sem .release ()

    def _run_one_legacy (self ,task :Task )->None :
        """Old model: baseline + prio comparison (preserve compatibility)"""
        acquired_serial =False 
        try :
            def cancel_check ()->bool :
                return (
                task .cancel_requested 
                or task .cancel_evt .is_set ()
                or task .status in ("cancelling","cancelled")
                )

            class _Cancelled (Exception ):
                pass 

            def raise_if_cancelled (phase :Optional [str ]=None )->None :
                if cancel_check ():
                    if phase :
                        task .phase =phase 
                    raise _Cancelled ()

                    # If cancelled before start (e.g. user cancelled while queued), short-circuit.
            if task .status =="cancelled"or task .cancel_evt .is_set ()or task .cancel_requested :
                task .status ="cancelled"
                task .phase ="cancelled"
                task .message =task .message or (task .cancel_reason or "canceled by user")
                task .end_ns =time .monotonic_ns ()
                self ._on_update (task )
                return 

            if self ._queue_mode_fn ():
                self ._serial_sem .acquire ()
                acquired_serial =True 

                # Acquire CPU group (prefer `task.cpu_list` if specified)
            raise_if_cancelled ("wait_cpu")
            group =self ._cpu_pool .try_acquire_group (
            task .cores_per_task ,
            preferred =task .cpu_list 
            )
            if group is None :
            # Temporary shortage: keep it queued and try again later.
                if cancel_check ():
                    task .status ="cancelled"
                    task .phase ="cancelled"
                    task .message =task .cancel_reason or "canceled by user"
                    task .end_ns =time .monotonic_ns ()
                    self ._on_update (task )
                    return 
                task .status ="queued"
                task .phase ="wait_cpu"
                task .message =f"Waiting for CPU: need {task.cores_per_task} cores, currently free {self._cpu_pool.free_count()}"
                self ._on_update (task )
                time .sleep (0.5 )
                self ._task_q .put (task )
                return 

            task .cpu_set =group 
            task .status ="running"
            task .phase ="setup"
            task .start_ns =time .monotonic_ns ()
            self ._on_update (task )

            if task .use_sudo and not has_passwordless_sudo ():
                task .status ="error"
                task .message ="Running with sudo enabled but unavailable in the current environment（Run this tool with `sudo`, or configure `sudo NOPASSWD`）。"
                self ._on_update (task )
                return 

                # Prepare output directories
            exp_root =Path (self ._results_root_fn ()).expanduser ()
            if not exp_root .is_absolute ():
                exp_root =(self ._tool_dir /exp_root ).resolve ()
            else :
                exp_root =exp_root .resolve ()
            ensure_writable_dir (exp_root ,use_sudo =task .use_sudo )

            ts =now_ts_safe ()

            if task .batch_name :
            # Batch mode：{exp_root}/{batch_name}_{ts}/{algo}/
                batch_dir =exp_root /f"{task.batch_name}_{ts}"
                ensure_writable_dir (batch_dir ,use_sudo =task .use_sudo )
                cpu_str ="cpu"+"".join (str (c )for c in sorted (task .cpu_list ))if task .cpu_list else "cpuX"
                algo_str =task .algo_name or task .baseline_c .parent .name 
                out_dir =batch_dir /algo_str 
            else :
            # Single-task mode (original logic)：{exp_root}/{config_name}/{ts}_ws{ws}_r{r}/
                config_name =task .config_name if task .config_name else "web_tasks"
                config_dir =exp_root /config_name 
                ensure_writable_dir (config_dir ,use_sudo =task .use_sudo )
                out_dir =config_dir /f"{ts}_ws{task.work_scale}_r{task.repeats}"

            ensure_writable_dir (out_dir ,use_sudo =task .use_sudo )
            task .out_dir =out_dir 

            # Copy source directories to keep local headers.
            task .phase ="copy"
            task .progress_i =0 
            task .progress_n =0 
            self ._on_update (task )
            raise_if_cancelled ("copy")

            baseline_src_root =task .baseline_c .parent 
            prio_src_root =task .prio_c .parent 

            baseline_dir =out_dir /"baseline"/baseline_src_root .name 
            prio_dir =out_dir /"prio"/prio_src_root .name 
            if baseline_dir .exists ():
                shutil .rmtree (baseline_dir )
            if prio_dir .exists ():
                shutil .rmtree (prio_dir )
            shutil .copytree (baseline_src_root ,baseline_dir )
            shutil .copytree (prio_src_root ,prio_dir )

            # Ensure total-time helpers exist even for plain instrument output directories
            # such as .../effective_line_merge/<algo>/ that only contain source files.
            timer_helper_roots =[
            self ._base_dir /"level1",
            self ._repo_root /"level1",
            ]
            helper_map ={}
            for helper_name in ("prog_timer.c","prog_timer.h","wrap_main.c"):
                helper_src =next ((root /helper_name for root in timer_helper_roots if (root /helper_name ).exists ()),None )
                if helper_src is not None :
                    helper_map [helper_name ]=helper_src 

            for helper_name ,helper_src in helper_map .items ():
                for dst_dir in (baseline_dir ,prio_dir ):
                    dst =dst_dir /helper_name 
                    if not dst .exists ():
                        shutil .copy2 (helper_src ,dst )

                        # Enforce CPU isolation inside the program too, if it sets affinity on its own.
            patched_affinity ={"baseline":False ,"prio":False }
            patch_error :Optional [str ]=None 
            try :
                b_src =baseline_dir /task .baseline_c .name 
                if b_src .exists ():
                    txt =b_src .read_text (encoding ="utf-8",errors ="replace")
                    new_txt ,changed =rewrite_sched_setaffinity_cpu_set (txt ,task .cpu_set )
                    if changed :
                        b_src .write_text (new_txt ,encoding ="utf-8")
                        patched_affinity ["baseline"]=True 
                p_src =prio_dir /task .prio_c .name 
                if p_src .exists ():
                    txt =p_src .read_text (encoding ="utf-8",errors ="replace")
                    new_txt ,changed =rewrite_sched_setaffinity_cpu_set (txt ,task .cpu_set )
                    if changed :
                        p_src .write_text (new_txt ,encoding ="utf-8")
                        patched_affinity ["prio"]=True 
            except Exception as e :
                patch_error =str (e )

                # Compile both
            task .phase ="compile"
            task .progress_i =0 
            task .progress_n =2 
            self ._on_update (task )
            raise_if_cancelled ("compile")

            baseline_bin =out_dir /"baseline"/"app_baseline"
            prio_bin =out_dir /"prio"/"app_prio"

            # Ensure priority runtime header can be resolved for instrumented sources.
            # Prefer `base_dir/level1`; if `base_dir` is misconfigured, fall back to inferring the path from the repository root directory.
            prio_runtime_candidates =[
            self ._base_dir /"level1"/"prio_runtime.h",
            self ._tool_dir .parent .parent /"level1"/"prio_runtime.h",
            ]
            prio_runtime_src =next ((p for p in prio_runtime_candidates if p .exists ()),prio_runtime_candidates [0 ])
            prio_include ='#include "prio_runtime.h"'

            def _requires_prio_runtime (src_path :Path )->bool :
                try :
                    txt =src_path .read_text (encoding ="utf-8",errors ="replace")
                except Exception :
                    return False 
                return prio_include in txt 

            baseline_needs_prio =_requires_prio_runtime (baseline_dir /task .baseline_c .name )
            prio_needs_prio =_requires_prio_runtime (prio_dir /task .prio_c .name )
            need_runtime_header =baseline_needs_prio or prio_needs_prio 
            if need_runtime_header and not prio_runtime_src .exists ():
                missing_in =[]
                if baseline_needs_prio :
                    missing_in .append ("baseline")
                if prio_needs_prio :
                    missing_in .append ("prio")
                raise RuntimeError (
                "Missing `prio_runtime.h`: "
                f"Tried {', '.join(str(p) for p in prio_runtime_candidates)}。"
                f"This header is required by source files: {','.join(missing_in)}。"
                "Please confirm that `level1/prio_runtime.h` exists, or remove the include from the source code."
                )

            if prio_runtime_src .exists ():
                for _dir in (baseline_dir ,prio_dir ):
                    dst =_dir /"prio_runtime.h"
                    if not dst .exists ():
                        try :
                            shutil .copy2 (prio_runtime_src ,dst )
                        except Exception :
                            pass 

            def _run_compile (cmd_parts :List [str ],*,cwd :Path )->Tuple [int ,str ,str ]:
            # New process group so we can cancel compile too.
                def preexec ()->None :
                    os .setsid ()

                proc =subprocess .Popen (
                cmd_parts ,
                cwd =str (cwd ),
                stdout =subprocess .PIPE ,
                stderr =subprocess .PIPE ,
                text =True ,
                preexec_fn =preexec ,
                )
                try :
                    while True :
                        raise_if_cancelled ("compile")
                        try :
                            out ,err =proc .communicate (timeout =0.2 )
                            return int (proc .returncode or 0 ),out or "",err or ""
                        except subprocess .TimeoutExpired :
                            continue 
                except _Cancelled :
                    try :
                        os .killpg (proc .pid ,signal .SIGTERM )
                    except Exception :
                        try :
                            proc .terminate ()
                        except Exception :
                            pass 
                    try :
                        out ,err =proc .communicate (timeout =1.0 )
                    except Exception :
                        try :
                            os .killpg (proc .pid ,signal .SIGKILL )
                        except Exception :
                            try :
                                proc .kill ()
                            except Exception :
                                pass 
                        out ,err =proc .communicate ()
                        # Propagate cancellation to outer handler
                    raise 

            def compile_one (src_dir :Path ,entry_c_name :str ,out_bin :Path )->Tuple [int ,str ,str ,str ]:
            # Compile the selected entry file plus known timing helpers when present.
            # Avoid globbing all .c files here because some experiment directories
            # also contain standalone test programs with their own main().
                c_files =[entry_c_name ]
                for helper_name in ("wrap_main.c","prog_timer.c"):
                    helper_path =src_dir /helper_name 
                    if helper_path .exists ():
                        c_files .append (helper_name )
                include_dirs :List [str ]=[str (src_dir )]
                if prio_runtime_src .exists ():
                    include_dirs .append (str (prio_runtime_src .parent ))
                include_flags :List [str ]=[]
                for inc in include_dirs :
                    include_flags .extend (["-I",inc ])
                cmd_parts =[
                "gcc",
                *GCC_FLAGS ,
                *include_flags ,
                f"-DWORK_SCALE={task.work_scale}",
                *c_files ,
                "-o",
                str (out_bin ),
                ]
                rc ,so ,se =_run_compile (cmd_parts ,cwd =src_dir )
                cmd_txt =" ".join (cmd_parts )

                # Fallback: if main-wrapper symbol is missing, retry without --wrap=main.
                if rc !=0 and "__wrap_main"in se :
                    filtered_flags =[f for f in GCC_FLAGS if f !="-Wl,--wrap=main"]
                    cmd_parts2 =[
                    "gcc",
                    *filtered_flags ,
                    *include_flags ,
                    f"-DWORK_SCALE={task.work_scale}",
                    *c_files ,
                    "-o",
                    str (out_bin ),
                    ]
                    rc2 ,so2 ,se2 =_run_compile (cmd_parts2 ,cwd =src_dir )
                    cmd_txt =cmd_txt +"\nRETRY(no --wrap=main): "+" ".join (cmd_parts2 )
                    so =so +so2 
                    se =se +"\n[retry]\n"+se2 
                    return rc2 ,so ,se ,cmd_txt 

                return rc ,so ,se ,cmd_txt 

            rc ,so ,se ,bcmd =compile_one (baseline_dir ,task .baseline_c .name ,baseline_bin )
            task .progress_i =1 
            self ._on_update (task )
            (out_dir /"baseline"/"compile.log").write_text ("CMD: "+bcmd +"\n"+so +se ,encoding ="utf-8")
            if rc !=0 :
                raise RuntimeError (f"baseline compilefailed：{se[-500:]}")

            rc ,so ,se ,pcmd =compile_one (prio_dir ,task .prio_c .name ,prio_bin )
            task .progress_i =2 
            self ._on_update (task )
            (out_dir /"prio"/"compile.log").write_text ("CMD: "+pcmd +"\n"+so +se ,encoding ="utf-8")
            if rc !=0 :
                raise RuntimeError (f"prio compilefailed：{se[-500:]}")

                # Run repeats
            task .phase ="run"
            task .progress_i =0 
            task .progress_n =task .repeats *2 
            self ._on_update (task )
            raise_if_cancelled ("run")

            env =dict (os .environ )
            env ["WORK_SCALE"]=str (task .work_scale )

            baseline_times :List [float ]=[]
            prio_times :List [float ]=[]
            runs :List [Dict ]=[]

            run_log =[]

            def run_prog (label :str ,bin_path :Path ,iter_idx :int )->float :
                rc ,out ,err ,wall_ns =run_with_affinity (
                [str (bin_path )],
                cwd =bin_path .parent ,
                env =env ,
                cpu_set =task .cpu_set ,
                use_sudo =task .use_sudo ,
                cancel_check =cancel_check ,
                )
                raise_if_cancelled ("run")
                run_log .append (f"=== {label} run (rc={rc}) ===\n")
                run_log .append (out )
                if err :
                    run_log .append ("\n[stderr]\n")
                    run_log .append (err )
                run_log .append ("\n")
                block_lines =[f"----- [{label}] run #{iter_idx+1} (rc={rc}) -----\n",out ]
                if err :
                    block_lines .append ("\n[stderr]\n")
                    block_lines .append (err )
                block ="".join (block_lines )
                parsed =True 
                t =parse_internal_time_seconds (out ,err )
                if t is None :
                    parsed =False 
                    msg ="failed to parse internal time: missing PROGRAM_TOTAL_NS in program output"
                    run_log .append (f"[error] {msg}\n\n")
                    block +=f"\n[error] {msg}\n"
                    raise RuntimeError (f"{label} run failed：{msg}")
                if rc !=0 :
                    raise RuntimeError (f"{label} run failed：rc={rc}, stderr_tail={err[-400:]}")
                runs .append (
                {
                "program":label ,
                "iter":int (iter_idx ),
                "time_s":float (t ),
                "wall_s":float (wall_ns /1e9 ),
                "parsed_from_stdout":bool (parsed ),
                "parsed_from_program_output":bool (parsed ),
                "cpu_set":task .cpu_set ,
                "returncode":int (rc ),
                "log_text":block ,
                }
                )
                return float (t )

            for i in range (task .repeats ):
                raise_if_cancelled ("run")
                t =run_prog ("baseline",baseline_bin ,i )
                baseline_times .append (t )
                task .progress_i +=1 
                self ._on_update (task )

                raise_if_cancelled ("run")
                t =run_prog ("prio",prio_bin ,i )
                prio_times .append (t )
                task .progress_i +=1 
                self ._on_update (task )

                # Summarize
            def stats (xs :List [float ])->Dict [str ,float ]:
                xs2 =xs [:]
                xs2 .sort ()
                n =len (xs2 )
                mean =sum (xs2 )/max (1 ,n )
                med =xs2 [n //2 ]if n else 0.0 
                return {
                "n":float (n ),
                "min_s":float (xs2 [0 ])if n else 0.0 ,
                "max_s":float (xs2 [-1 ])if n else 0.0 ,
                "mean_s":float (mean ),
                "median_s":float (med ),
                }

            baseline_stat =stats (baseline_times )
            prio_stat =stats (prio_times )

            # Three-column mean calculation (precomputed for use in text output and messages)
            cfs_mean =baseline_stat ['mean_s']
            fifo_mean =baseline_stat ['mean_s']
            prio_mean =prio_stat ['mean_s']
            timing_dir =None 
            for candidate in [
            out_dir /"baseline"/(task .algo_name or "")/"timing",
            out_dir /"prio"/(task .algo_name or "")/"timing",
            out_dir /"timing",
            ]:
                if candidate .exists ():
                    timing_dir =candidate 
                    break 
            if timing_dir and (timing_dir /"compile_and_run.sh").exists ():
                try :
                    sh_env =dict (os .environ )
                    sh_env ["WORK_SCALE"]=str (task .work_scale )
                    result =subprocess .run (
                    ["timeout","20",str (timing_dir /"compile_and_run.sh")],
                    cwd =timing_dir ,
                    capture_output =True ,
                    text =True ,
                    timeout =25 ,
                    env =sh_env ,
                    )
                    main_elapsed_times :List [float ]=[]
                    for line in result .stdout .splitlines ():
                        m =re .search (r"MAIN_ELAPSED_S=([\d.]+)",line )
                        if m :
                            try :
                                main_elapsed_times .append (float (m .group (1 )))
                            except Exception :
                                pass 
                    if main_elapsed_times :
                    # Output order: baseline_FIFO, baseline_CFS, prio
                        fifo_mean =main_elapsed_times [0 ]
                        if len (main_elapsed_times )>=2 :
                            cfs_mean =main_elapsed_times [1 ]
                        if len (main_elapsed_times )>=3 :
                            prio_mean =main_elapsed_times [2 ]
                        else :
                            prio_mean =main_elapsed_times [-1 ]
                except Exception :
                    pass 

            delta_mean =prio_stat ["mean_s"]-baseline_stat ["mean_s"]
            improve =None 
            if baseline_stat ["mean_s"]>1e-12 :
                improve =(baseline_stat ["mean_s"]-prio_stat ["mean_s"])/baseline_stat ["mean_s"]

            summary ={
            "task_id":task .task_id ,
            "created_at":ts ,
            "cpu_set":task .cpu_set ,
            "cores_per_task":task .cores_per_task ,
            "work_scale":task .work_scale ,
            "repeats":task .repeats ,
            "affinity_rewritten_in_source":patched_affinity ,
            "baseline":{
            "c_file":str (task .baseline_c ),
            "compile_cmd":bcmd .strip (),
            "stats":baseline_stat ,
            "times_s":baseline_times ,
            },
            "prio":{
            "c_file":str (task .prio_c ),
            "compile_cmd":pcmd .strip (),
            "stats":prio_stat ,
            "times_s":prio_times ,
            },
            "runs":runs ,
            "delta_mean_s":float (delta_mean ),
            "improvement_ratio":float (improve )if improve is not None else None ,
            }
            if patch_error :
                summary ["affinity_patch_error"]=patch_error 
            (out_dir /"summary.json").write_text (json .dumps (summary ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
            (out_dir /"run.log").write_text ("".join (run_log ),encoding ="utf-8")

            # CSV output
            try :
                csv_lines =["program,iter,time_s,wall_s,parsed_from_stdout,cpu_set\n"]
                for r in runs :
                    csv_lines .append (
                    f"{r['program']},{r['iter']},{r['time_s']:.9f},{r['wall_s']:.9f},{int(r['parsed_from_stdout'])},\"{format_cpu_set(r['cpu_set'])}\"\n"
                    )
                (out_dir /"runs.csv").write_text ("".join (csv_lines ),encoding ="utf-8")
            except Exception :
                pass 

                # txt summary (run.sh style)
            try :
                txt_name =f"run_results_{ts}_ws{task.work_scale}_r{task.repeats}.txt"
                txt_path =out_dir /txt_name 
                lines :List [str ]=[]
                lines .append (f"=== RUN at {ts} (WORK_SCALE={task.work_scale}, REPEATS={task.repeats}) ===\n")
                lines .append (f"baseline_bin={baseline_bin}\n")
                lines .append (f"prio_bin={prio_bin}\n\n")
                lines .append ("=== PAIRED RESULTS (program-reported time, seconds) ===\n")
                lines .append ("run\tbaseline\tprio\tdelta(prio-baseline)\n")
                for i in range (task .repeats ):
                    b =baseline_times [i ]
                    p =prio_times [i ]
                    lines .append (f"{i+1}\t{b:.6f}\t{p:.6f}\t{(p-b):+.6f}\n")
                lines .append ("\n=== BASELINE STATS (program time) ===\n")
                lines .append (f"times_s={[round(x,6) for x in baseline_times]}\n")
                lines .append (f"mean={baseline_stat['mean_s']:.6f}s min={baseline_stat['min_s']:.6f}s max={baseline_stat['max_s']:.6f}s rcs={[r['returncode'] for r in runs if r['program']=='baseline']}\n")
                lines .append ("\n=== PRIO STATS (program time) ===\n")
                lines .append (f"times_s={[round(x,6) for x in prio_times]}\n")
                lines .append (f"mean={prio_stat['mean_s']:.6f}s min={prio_stat['min_s']:.6f}s max={prio_stat['max_s']:.6f}s rcs={[r['returncode'] for r in runs if r['program']=='prio']}\n")

                # Three-column statistics（`MAIN_ELAPSED_S` from the timing script）
                lines .append (f"\n=== THREE COLUMN STATS (MAIN_ELAPSED_S from timing/) ===\n")
                lines .append (f"CFS mean={cfs_mean:.6f}s, FIFO mean={fifo_mean:.6f}s, PRIO mean={prio_mean:.6f}s\n")
                if patch_error :
                    lines .append (f"\n[warn] affinity rewrite failed: {patch_error}\n")
                elif not any (patched_affinity .values ()):
                    lines .append ("\n[warn] affinity rewrite not applied (no sched_setaffinity pattern found)\n")
                lines .append ("\n=== LOGS (raw program output) ===\n")
                for r in runs :
                    prog_s =r ["time_s"]
                    lines .append (f"\n----- [{r['program']}] run #{r['iter']+1} (program={prog_s:.6f}s, rc={r['returncode']}) -----\n")
                    lines .append (r .get ("log_text",""))
                    if not r .get ("log_text"):
                        lines .append ("(log missing)\n")
                txt_path .write_text ("".join (lines ),encoding ="utf-8")
            except Exception :
                pass 

            task .status ="done"
            task .phase ="done"

            # Three-column message (mean value has been calculated previously)
            task .message =f"Completed: CFS mean={cfs_mean:.3f}s, FIFO mean={fifo_mean:.3f}s, prio mean={prio_mean:.3f}s (three-column mode)"
            task .end_ns =time .monotonic_ns ()
            # resume mode: records completed tasks and can be skipped after restarting
            try :
                if task .resume_file and task .task_key and task .out_dir :
                    payload =task_payload_for_key (
                    baseline_c =task .baseline_c ,
                    prio_c =task .prio_c ,
                    work_scale =task .work_scale ,
                    repeats =task .repeats ,
                    cores_per_task =task .cores_per_task ,
                    use_sudo =task .use_sudo ,
                    cpu_list =task .cpu_list ,
                    )
                    mark_done (
                    resume_file =Path (task .resume_file ),
                    task_key =str (task .task_key ),
                    task_id =task .task_id ,
                    out_dir =task .out_dir ,
                    message =task .message ,
                    done_at =now_ts_safe (),
                    payload =payload ,
                    )
            except Exception :
                pass 
            self ._on_update (task )
        except _Cancelled :
            task .status ="cancelled"
            task .phase ="cancelled"
            task .message =task .cancel_reason or "canceled by user"
            task .end_ns =time .monotonic_ns ()
            self ._on_update (task )
        except Exception as e :
            task .status ="error"
            task .phase ="error"
            task .message =str (e )
            task .end_ns =time .monotonic_ns ()
            self ._on_update (task )
        finally :
            if task .cpu_set :
                self ._cpu_pool .release_group (task .cpu_set )
            if acquired_serial :
                self ._serial_sem .release ()
