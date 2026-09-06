"""CLI command-line mode"""

import argparse 
import logging 
import sys 
import time 
import uuid 
from pathlib import Path 
from queue import Queue 
from typing import List ,Optional 

from .core .task import Task 
from .core .cpu_pool import CpuPool 
from .core .task_runner import TaskRunner 
from .config .defaults import DEFAULT_MAX_WORKERS 
from .utils .cpu import read_cpu_online 
from .utils .config_manager import load_config ,tasks_from_config ,save_config 
from .utils .resume_state import apply_resume_to_task ,default_resume_file 
from .utils .file_ops import ensure_dir 


class CLIManager :
    """CLI mode manager"""

    def __init__ (self ,base_dir :Path ,queue_mode :bool =False ,results_root :Optional [Path ]=None ):
        """Initialize the CLI manager

        Args:
            base_dir: Project root directory
            queue_mode: Whether to enable queue mode
            results_root: Experiment results root directory (default: tools/runtime_compare/experimentresult)
        """
        self .base_dir =base_dir 
        self .queue_mode =queue_mode 

        # Compute tool directory path (tools/runtime_compare/)
        self .tool_dir =Path (__file__ ).parent .resolve ()

        # Experiment results root directory
        rr =Path (results_root ).expanduser ()if results_root else (self .tool_dir /"experimentresult")
        if not rr .is_absolute ():
            rr =(self .tool_dir /rr ).resolve ()
        else :
            rr =rr .resolve ()
        self .results_root =rr 

        # Initialize CPU pool and task queue
        self .cpu_list =read_cpu_online ()
        self .cpu_pool =CpuPool (self .cpu_list )
        self .task_q :Queue [Task ]=Queue ()
        self .tasks :List [Task ]=[]

        # Serial semaphore
        import threading 
        self .serial_sem =threading .Semaphore (1 )

        # Log directory (defaults to follow experiment results directory)
        try :
            self .log_dir =self .results_root /"logs"
            ensure_dir (self .log_dir )
        except Exception :
            self .log_dir =self .tool_dir /"experimentresult"/"logs"
            ensure_dir (self .log_dir )

            # Setup logging
        self ._setup_logging ()

        # Start worker threads
        self .runners :List [TaskRunner ]=[]
        max_workers =min (DEFAULT_MAX_WORKERS ,max (1 ,len (self .cpu_list )))
        for i in range (max_workers ):
            r =TaskRunner (
            base_dir =self .base_dir ,
            cpu_pool =self .cpu_pool ,
            task_q =self .task_q ,
            on_update =self ._on_task_update ,
            serial_sem =self .serial_sem ,
            queue_mode_fn =lambda :self .queue_mode ,
            results_root_fn =lambda :self .results_root ,
            )
            r .start ()
            self .runners .append (r )

    def _setup_logging (self ):
        """Setup logging"""
        log_file =self .log_dir /"cli.log"
        logging .basicConfig (
        level =logging .INFO ,
        format ='%(asctime)s [%(levelname)s] %(message)s',
        handlers =[
        logging .FileHandler (log_file ,encoding ='utf-8'),
        logging .StreamHandler (sys .stdout ),
        ]
        )
        self .logger =logging .getLogger (__name__ )

    def _on_task_update (self ,task :Task ):
        """Task update callback"""
        self .logger .info (
        f"Task {task.task_id}: {task.status} - {task.phase} - {task.message}"
        )
        if task .status in ("done","error"):
            self .logger .info (f"Task {task.task_id} Completedd: {task.message}")
            if task .out_dir :
                self .logger .info (f"Result directory: {task.out_dir}")

    def load_from_config (self ,config_path :Path ,*,resume :bool =True )->int :
        """Load tasks from config_files

        Args:
            config_path: config_files path (can be absolute, relative, or filename)
            resume: Whether to enable resume mode (skip already-Completedd tasks)

        Returns:
            Number of tasks loaded
        """
        # Handle config_files path: if just a filename or relative path, look in config_files directory
        config_path =Path (config_path ).expanduser ()
        if not config_path .is_absolute ():
        # Try looking in the config_files directory
            config_dir =self .tool_dir /"config_files"
            potential_path =config_dir /config_path 
            if potential_path .exists ():
                config_path =potential_path 
            else :
            # If not in config_files directory, try relative to current working directory
                config_path =config_path .resolve ()

        if not config_path .exists ():
            raise FileNotFoundError (f"config_files not found: {config_path}")

        self .logger .info (f"Loading config_files: {config_path}")
        config =load_config (config_path )

        # Extract config_files name (without extension)
        config_name =config_path .stem 
        resume_file =default_resume_file (config_path ,tool_dir =self .tool_dir )
        if resume :
            self .logger .info (f"Resume mode: enabled (state={resume_file})")
        else :
            self .logger .info ("Resume mode: disabled")

            # Set queue mode
        if "queue_mode"in config :
            self .queue_mode =bool (config ["queue_mode"])
            self .logger .info (f"Queue mode: {'enabled' if self.queue_mode else 'disabled'}")

            # Create tasks (pass config_files name)
        tasks =tasks_from_config (config ,config_name =config_name ,config_path =config_path )
        self .logger .info (f"Loaded {len(tasks)} tasks from config_files")

        # Resume mode: mark Completedd tasks, skip re-queuing
        resumed =0 
        if resume :
            for t in tasks :
                ok ,_ =apply_resume_to_task (t )
                if ok :
                    resumed +=1 
        if resumed :
            self .logger .info (f"Resume: skipped {resumed} already-Completedd tasks")

            # Add to queue (serial execution / only inCompleted tasks)
        for task in tasks :
            self .tasks .append (task )
            if task .status !="done":
                self .task_q .put (task )
                self .logger .info (f"Task added: {task.task_id}")
            else :
                self .logger .info (f"Completed task (skipped): {task.task_id} -> {task.out_dir}")

        return len (tasks )

    def add_task (
    self ,
    baseline_c :Path ,
    prio_c :Path ,
    work_scale :int ,
    repeats :int ,
    cores_per_task :int ,
    cpu_list :Optional [List [int ]]=None ,
    use_sudo :bool =False ,
    )->Task :
        """Add a single task

        Args:
            baseline_c: baseline C file path
            prio_c: prio C file path
            work_scale: work scale
            repeats: repeat count
            cores_per_task: cores per task
            cpu_list: optional manually-specified CPU core list
            use_sudo: whether to use sudo

        Returns:
            The created Task object
        """
        from .utils .datetime_utils import now_ts_safe 

        baseline_c =Path (baseline_c ).expanduser ().resolve ()
        prio_c =Path (prio_c ).expanduser ().resolve ()

        task_id =(
        f"{baseline_c.parent.name}_{baseline_c.stem}_vs_{prio_c.stem}_"
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
        )

        self .tasks .append (task )
        self .task_q .put (task )
        self .logger .info (f"Task added: {task_id}")

        return task 

    def list_tasks (self ):
        """List all tasks"""
        if not self .tasks :
            print ("No tasks")
            return 

        print (f"\nTask list ({len(self.tasks)} total):")
        print ("-"*100 )
        print (f"{'Task ID':<40} {'Status':<10} {'Phase':<15} {'CPU':<15} {'Message':<30}")
        print ("-"*100 )

        for task in self .tasks :
            cpu_str =",".join (map (str ,task .cpu_set ))if task .cpu_set else "-"
            print (
            f"{task.task_id:<40} {task.status:<10} {task.phase:<15} {cpu_str:<15} {task.message[:30]:<30}"
            )

    def cancel_task (self ,task_id :str )->bool :
        """cancel a task（queued or running）\n        \n        Args:\ntask_id: task ID\n            \n        Returns:\n            whether cancel succeeded\n        """
        for task in self .tasks :
            if task .task_id ==task_id :
                if task .status in ("done","error","cancelled"):
                    self .logger .warning (f"the task has already finished and cannot be canceled: {task.status}")
                    return False 
                if task .status =="queued":
                    task .status ="cancelled"
                    task .phase ="cancelled"
                    task .cancel_requested =True 
                    task .cancel_evt .set ()
                    task .cancel_reason ="canceled by user"
                    self .logger .info (f"Canceled task: {task_id}")
                    return True 
                if task .status in ("running","cancelling"):
                    task .status ="cancelling"
                    task .cancel_requested =True 
                    task .cancel_evt .set ()
                    task .cancel_reason ="canceled by user"
                    task .message ="canceled by user，stopping..."
                    self .logger .info (f"Requested task interruption: {task_id}")
                    return True 
                    # other statuses (such as wait_cpu)
                task .status ="cancelled"
                task .phase ="cancelled"
                task .cancel_requested =True 
                task .cancel_evt .set ()
                task .cancel_reason ="canceled by user"
                self .logger .info (f"Canceled task: {task_id}")
                return True 
        self .logger .error (f"task does not exist: {task_id}")
        return False 

    def status (self ):
        """display system status"""
        running =sum (1 for t in self .tasks if t .status =="running")
        queued =sum (1 for t in self .tasks if t .status =="queued")
        done =sum (1 for t in self .tasks if t .status =="done")
        error =sum (1 for t in self .tasks if t .status =="error")

        print (f"\nSystem status:")
        print (f"  Online CPUs: {len(self.cpu_list)} ({', '.join(map(str, self.cpu_list))})")
        print (f"  Idle CPUs: {self.cpu_pool.free_count()} / {self.cpu_pool.total_count()}")
        print (f"  Queue mode: {'enabled' if self.queue_mode else 'disabled'}")
        print (f"\nTask statistics:")
        print (f"  running: {running}")
        print (f"  waiting: {queued}")
        print (f"Completed: {done}")
        print (f"  failed: {error}")
        print (f"  total: {len(self.tasks)}")

    def wait_all (self ):
        """waitallTaskCompleted"""
        self .logger .info ("waitallTaskCompleted...")
        while True :
            running =[t for t in self .tasks if t .status in ("running","queued")]
            if not running :
                break 
            time .sleep (1 )
        self .logger .info ("all tasks are Completed")

    def shutdown (self ):
        """Close the manager"""
        self .logger .info ("Close CLI Manager...")
        for runner in self .runners :
            runner .stop ()
        for runner in self .runners :
            runner .join (timeout =2 )


def main_cli (args ):
    """Main CLI function"""
    # Determine the project root directory
    if args .base_dir :
        base_dir =Path (args .base_dir ).resolve ()
    else :
    # Automatically detect by walking two levels up from tools/runtime_compare
        base_dir =Path (__file__ ).parent .parent .parent .resolve ()

    manager =CLIManager (base_dir ,queue_mode =args .queue_mode ,results_root =getattr (args ,"results_root",None ))

    try :
        if args .config :
        # Load from config files (load_from_config will handle pathfind)
            config_path =Path (args .config )
            count =manager .load_from_config (config_path ,resume =not args .no_resume )
            print (f"Loaded {count}  tasks")

            # waitall taskCompleted(run serially)
            if args .wait :
                manager .wait_all ()
                manager .shutdown ()
            else :
                print ("Tasks are already running in the background")
                print ("Info: use --wait option wait task Completed, or use --status to view status")
                # Wait briefly to let tasks start
                import time 
                time .sleep (2 )
                manager .shutdown ()

        elif args .add_task :
        # Add single tasks (from JSON File)
            task_config =Path (args .add_task ).expanduser ().resolve ()
            config =load_config (task_config )
            if len (config ["tasks"])!=1 :
                print (f"Error: Tasks config_files should contain exactly 1 tasks, there are actually {len(config['tasks'])}")
                return 1 
                # Reuse the resume logic
            tasks =tasks_from_config (config ,config_name =task_config .stem ,config_path =task_config )
            t =tasks [0 ]
            if not args .no_resume :
                apply_resume_to_task (t )
            manager .tasks .append (t )
            if t .status !="done":
                manager .task_q .put (t )
            if args .wait :
                manager .wait_all ()
                manager .shutdown ()
            else :
                import time 
                time .sleep (2 )
                manager .shutdown ()

        elif args .list :
            manager .list_tasks ()
            manager .shutdown ()

        elif args .cancel :
            result =manager .cancel_task (args .cancel )
            manager .shutdown ()
            return 0 if result else 1 

        elif args .status :
            manager .status ()
            manager .shutdown ()

        else :
            print ("Please specify an action (`--config`, `--add-task`, `--list`, `--cancel`, or `--status`)")
            manager .shutdown ()
            return 1 

        return 0 

    except KeyboardInterrupt :
        print ("\nUser interrupted")
        manager .shutdown ()
        return 1 
    except Exception as e :
        print (f"Error: {e}")
        import traceback 
        traceback .print_exc ()
        manager .shutdown ()
        return 1 


def create_cli_parser ():
    """Create the CLI argument parser"""
    parser =argparse .ArgumentParser (
    description ="Runtime Compare Tool - CLI mode",
    formatter_class =argparse .RawDescriptionHelpFormatter ,
    epilog ="""\nExamples:\n# Load from config files task\n  python3 main.py --cli --config tasks.json --wait\n  \n#Add single tasks\n  python3 main.py --cli --add-task task.json\n  \n  # List tasks\n  python3 main.py --cli --list\n  \n# Check System status\n  python3 main.py --cli --status\n  \n  # cancel a task\n  python3 main.py --cli --cancel <task_id>\n        """
    )

    parser .add_argument ("--base-dir",type =Path ,help ="project root directory (default: auto-detect)")
    parser .add_argument ("--queue-mode",action ="store_true",help ="enabledSingle concurrent Queue mode")
    parser .add_argument ("--wait",action ="store_true",help ="waitallTaskCompleted")
    parser .add_argument ("--no-resume",action ="store_true",help ="disabledresume mode (default will skip completed tasks)")

    # Operation options (mutually exclusive)
    group =parser .add_mutually_exclusive_group (required =True )
    group .add_argument ("--config",type =Path ,help ="Load from config files task")
    group .add_argument ("--add-task",type =Path ,help ="Add single tasks (from JSON File)")
    group .add_argument ("--list",action ="store_true",help ="List all tasks")
    group .add_argument ("--cancel",type =str ,help ="cancel a task (task ID)")
    group .add_argument ("--status",action ="store_true",help ="display system status")

    return parser 
