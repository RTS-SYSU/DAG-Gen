# -*- coding: utf-8 -*-
"""
Mycallyplus GUI v3.0 - Status Panel Driven Design
Redesigned GUI using the Status Panel mechanism, with manual step-by-step click workflow
"""

import sys 
import os 
import tkinter as tk 
from tkinter import filedialog ,messagebox ,simpledialog 
from pathlib import Path 
from typing import Optional ,Dict ,List ,Tuple 
from dataclasses import dataclass 
import subprocess 
import shutil 
import random 
import re 
import json 
import socket 
import time 
import webbrowser 
try :
    import pwd 
except ImportError :  # pragma: no cover - unavailable on Windows
    pwd =None  # type: ignore

try :
    from PIL import Image ,ImageTk 
    _PIL_READY =True 
except Exception :
    Image =None # type: ignore
    ImageTk =None # type: ignore
    _PIL_READY =False 

    # Use in-package modules to avoid dependency on legacy package names
from ..import filter_dot ,scheduler ,time_analysis ,time_charts 
from ..level1 import instrument_prio_level1 as level1_prio_instrument 
from ..level1 import lpf_thread as level1_lpf_thread 
from ..level1 import time_analysis_level1 as level1_time_analysis 
from ..level2 import segment_dag_level2 as level2_segment_dag 
from ..pipeline import runner as pipeline_runner 
from ..pipeline .algo_registry import list_algos as pipeline_list_algos 
from ..pipeline .rules_registry import list_rules as pipeline_list_rules 
from ..runtime_env import PROJECT_ROOT ,module_cmd ,module_env ,package_module_name 

try :
    import networkx as nx 
except ImportError :
    nx =None 

try :# Graphviz parsing optional dependency
    import pydot # type: ignore
except Exception :# pragma: no cover - optional dependency
    pydot =None 


@dataclass 
class MutexRecord :
    """Mutex lock record"""
    lock :str 
    unlock :str 
    var :str 
    idx :str 
    lock_line :Optional [int ]=None 
    unlock_line :Optional [int ]=None 
    lock_file :Optional [str ]=None 
    unlock_file :Optional [str ]=None 
    covered :List [str ]=None 

    def __post_init__ (self ):
        if self .covered is None :
            self .covered =[]


@dataclass 
class SemRecord :
    """Semaphore record"""
    post :str 
    wait :str 
    var :str 
    idx :str 
    post_line :Optional [int ]=None 
    wait_line :Optional [int ]=None 
    post_file :Optional [str ]=None 
    wait_file :Optional [str ]=None 


class FileState :
    """File state management"""
    def __init__ (self ):
        self .source_file :Optional [Path ]=None # .c file
        self .expand_file :Optional [Path ]=None # .233r.expand file
        self .dot_file :Optional [Path ]=None # .dot file (latest)
        self .txt_file :Optional [Path ]=None # circle.txt file
        self .work_dir :Optional [Path ]=None # working directory

    def get_base_name (self )->Optional [str ]:
        """Extract base name from expand file"""
        if not self .expand_file :
            return None 
        name =self .expand_file .stem # remove .expand
        # Compatible with GCC version differences: .233r / .245r / other *.Nr
        name =re .sub (r"\.\d+r$","",name )
        # Remove trailing language extension (.c / .cpp / other)
        if '.'in name :
            name =name .split ('.')[0 ]
        return name 

    def clear (self ):
        """Clear all state"""
        self .source_file =None 
        self .expand_file =None 
        self .dot_file =None 
        self .txt_file =None 
        self .work_dir =None 


class MycallyplusGUIv3 :
    def __init__ (self ,root :tk .Tk ):
        self .root =root 
        self .root .title ("Mycallyplus v3.0 - Status Panel Driven [PipeDAG]")
        self .root .geometry ("1400x900")
        self .root .configure (bg ="#ECEFF1")

        # Working path - set to mycallyplus directory
        self .base_dir =PROJECT_ROOT 
        self .base_dir .mkdir (parents =True ,exist_ok =True )

        # If launched via `sudo`, prefer running heavy steps (gcc/python pipeline) as the original user.
        # This avoids root-owned outputs and missing user-site Python deps (e.g. Pillow).
        self ._sudo_user :Optional [str ]=None 
        self ._sudo_uid :Optional [int ]=None 
        self ._sudo_gid :Optional [int ]=None 
        try :
            if hasattr (os ,"geteuid")and os .geteuid ()==0 :
                cand =os .environ .get ("SUDO_USER")
                if cand and pwd is not None :
                    info =pwd .getpwnam (cand )
                    self ._sudo_user =cand 
                    self ._sudo_uid =int (info .pw_uid )
                    self ._sudo_gid =int (info .pw_gid )
        except Exception :
            self ._sudo_user =None 
            self ._sudo_uid =None 
            self ._sudo_gid =None 

            # File state
        self .state =FileState ()
        self .filtered_dot_dir =self .base_dir /"intermediate_results"/"filtered_dot"
        self .filtered_dot_dir .mkdir (parents =True ,exist_ok =True )

        # Currently displayed image
        self .current_image :Optional [Path ]=None 
        self .tk_img =None 
        self .original_image =None # Save original PIL image for scaling
        self .canvas_scale =1.0 # Current zoom scale
        self ._pil_warned =False 

        # Mutex lock analysis state
        self .mutex_prepared =False 
        self .mutex_records :List [MutexRecord ]=[]
        self .G =None # networkxgraph object
        self .sem_records :List [SemRecord ]=[]
        self .thread_color_map :Dict [str ,str ]={}
        self .cycle_data :Dict [str ,Dict [str ,List [str ]]]={}
        self .sccs :List [set ]=[]
        self .cached_images :Dict [str ,Optional [Path ]]={
        "original":None ,
        "tarjan":None ,
        "threads":None ,
        "mutex":None ,
        }
        # time_analysis selection state
        self .ta_source_file :Optional [Path ]=None 
        self .ta_json_file :Optional [Path ]=None 
        # PipeDAG state
        self .pipeline_level ="-"
        self .pipeline_rule ="-"
        self .pipeline_view ="-"
        self .pipeline_algo ="-"
        self .pipeline_last_outputs :Dict [str ,Path ]={}
        self .pipeline_output_buttons :Dict [str ,tk .Button ]={}
        self .pipeline_status_labels :Dict [str ,tk .Label ]={}
        self .runtime_web_host ="127.0.0.1"
        self .runtime_web_port =5000 
        self .runtime_web_proc :Optional [subprocess .Popen ]=None 
        self .runtime_web_log =self .base_dir /"intermediate_results"/"runtime_compare_web.log"
        self .runtime_web_log_handle =None 

        # Mutex lock color configuration
        self .MUTEX_COLORS =[
        "#FFB74D","#81C784","#64B5F6","#BA68C8",
        "#E57373","#4DB6AC","#FFD54F","#9575CD",
        "#4FC3F7","#AED581","#FF8A65","#B39DDB"
        ]

        self .THREAD_COLORS =[
        "#90CAF9","#A5D6A7","#FFE082","#F48FB1",
        "#CE93D8","#FFAB91","#80CBC4","#B39DDB"
        ]

        # Build UI
        self .root .protocol ("WM_DELETE_WINDOW",self ._on_close )
        self ._build_ui ()
        self ._update_status_display ()

    def _as_original_user_cmd (self ,cmd :List [str ])->List [str ]:
        """When running as root via sudo, re-exec commands as the original user."""
        if self ._sudo_user :
            return ["sudo","-u",self ._sudo_user ,"-H",*cmd ]
        return cmd 

    def _run (self ,cmd :List [str ],*,cwd :Optional [Path ]=None ,**kwargs )->subprocess .CompletedProcess :
        env =kwargs .pop ("env",None )
        return subprocess .run (self ._as_original_user_cmd (cmd ),cwd =str (cwd )if cwd else None ,env =module_env (env ),**kwargs )

    def _popen (self ,cmd :List [str ],*,cwd :Optional [Path ]=None ,**kwargs )->subprocess .Popen :
        env =kwargs .pop ("env",None )
        return subprocess .Popen (self ._as_original_user_cmd (cmd ),cwd =str (cwd )if cwd else None ,env =module_env (env ),**kwargs )

    def _module_cmd (self ,relative_module :str )->List [str ]:
        return module_cmd (relative_module ,python_executable =sys .executable )

    def _chown_to_original_user (self ,path :Path )->None :
        if self ._sudo_uid is None or self ._sudo_gid is None :
            return 
        try :
            os .chown (str (path ),self ._sudo_uid ,self ._sudo_gid )
        except Exception :
            pass 

    def _ensure_dir_for_original_user (self ,path :Path )->None :
        path .mkdir (parents =True ,exist_ok =True )
        self ._chown_to_original_user (path )
        try :
            path .chmod (0o775 )
        except Exception :
            pass 

            # Path helper: unified config directory (new location)
    def _config_dir_for_base (self ,base_name :str )->Path :
        return self .base_dir /"intermediate_results"/base_name /"config_files"

        # Path helper: compatible with old config directory (read-only)
    def _iter_config_dirs (self ,base_name :str ):
    # New directory first
        yield self ._config_dir_for_base (base_name )
        # Old directory compatibility
        yield self .base_dir /"config_files"/base_name 

    def _infer_base_from_path (self ,path :Path )->Optional [str ]:
        """Infer base from any path (prefer matching 'intermediate_results/<base>/' segment)."""
        try :
            parts =path .resolve ().parts 
            if "intermediate_results"in parts :
                i =parts .index ("intermediate_results")
                if i +1 <len (parts ):
                    return parts [i +1 ]
        except Exception :
            pass 
            # Fallback: infer from current state or filename
        return self .state .get_base_name ()or (self .state .source_file .stem if self .state .source_file else None )

    def _build_ui (self ):
        """Build the UI layout"""
        # Main container
        main_frame =tk .Frame (self .root ,bg ="#ECEFF1")
        main_frame .pack (fill =tk .BOTH ,expand =True ,padx =10 ,pady =10 )

        # Left button area (scrollable)
        left_frame =tk .LabelFrame (
        main_frame ,
        text ="Operations",
        bg ="#CFD8DC",
        font =("Microsoft YaHei",10 ,"bold"),
        padx =10 ,
        pady =10 
        )
        left_frame .pack (side =tk .LEFT ,fill =tk .Y ,padx =8 ,pady =8 )
        left_canvas =tk .Canvas (left_frame ,bg ="#CFD8DC",highlightthickness =0 ,width =220 )
        left_scrollbar =tk .Scrollbar (left_frame ,orient =tk .VERTICAL ,command =left_canvas .yview )
        left_canvas .configure (yscrollcommand =left_scrollbar .set )
        left_scrollbar .pack (side =tk .RIGHT ,fill =tk .Y )
        left_canvas .pack (side =tk .LEFT ,fill =tk .BOTH ,expand =True )
        left_inner =tk .Frame (left_canvas ,bg ="#CFD8DC")
        left_window =left_canvas .create_window ((0 ,0 ),window =left_inner ,anchor ="nw")
        left_inner .bind (
        "<Configure>",
        lambda e :left_canvas .configure (scrollregion =left_canvas .bbox ("all")),
        )
        left_canvas .bind (
        "<Configure>",
        lambda e :left_canvas .itemconfigure (left_window ,width =e .width ),
        )

        # Function buttons (rename and reorder only; callbacks unchanged)
        buttons =[
        ("Select Source File",self .select_source_file ),
        ("Select Expand File",self .select_expand_file ),
        ("Select DOT File",self .select_dot_file ),
        ("Select config_files",self .select_config_folder ),
        ("filtered_dot file",self .filter_dot_file ),
        ("Generate Expand File",self .generate_expand_from_source ),
        ("dag_generation",self .generate_dag ),
        ("Modular Experiment",self .pipeline_entry ),
        ("One-click Full Pipeline",self .pipeline_full_run ),
        ("View Condition Nodes",self .view_conditions ),
        ("Generate Source Call Graph",self .generate_source_only_dag ),
        ("View Mutex Locks",self .view_mutex ),
        ("Generate Semaphore Graph",self .generate_semaphore ),
        ("Runtime Comparison (Web)",self .open_runtime_compare_web ),
        ("time_analysis",self .time_analysis_entry ),
        ("scheduling",self .scheduler_entry ),
        ]

        for text ,cmd in buttons :
            tk .Button (
            left_inner ,
            text =text ,
            command =cmd ,
            width =22 ,
            height =2 ,
            bg ="#ECEFF1",
            relief =tk .RAISED ,
            activebackground ="#CFD8DC",
            font =("Microsoft YaHei",9 )
            ).pack (pady =5 )

            # Right display area
        right_frame =tk .LabelFrame (
        main_frame ,
        text ="Visualization",
        bg ="#FFFFFF",
        font =("Microsoft YaHei",10 ,"bold")
        )
        right_frame .pack (side =tk .RIGHT ,fill =tk .BOTH ,expand =True ,padx =10 )

        # Status Panel (shows currently loaded files)
        status_frame =tk .LabelFrame (
        right_frame ,
        text ="Status Panel - Currently Loaded Files",
        bg ="#E3F2FD",
        font =("Microsoft YaHei",9 ,"bold"),
        padx =10 ,
        pady =5 
        )
        status_frame .pack (fill =tk .X ,padx =5 ,pady =5 )

        # Status display labels
        self .status_labels ={}
        status_items =[
        ("source","Source file: "),
        ("expand","Expand file: "),
        ("dot","DOT file: "),
        ("txt","config_files: "),
        ]

        for key ,label_text in status_items :
            frame =tk .Frame (status_frame ,bg ="#E3F2FD")
            frame .pack (fill =tk .X ,pady =2 )

            tk .Label (
            frame ,
            text =label_text ,
            bg ="#E3F2FD",
            font =("Microsoft YaHei",9 ,"bold"),
            anchor ="w",
            width =12 
            ).pack (side =tk .LEFT )

            label =tk .Label (
            frame ,
            text ="<Not loaded>",
            bg ="#E3F2FD",
            font =("Consolas",9 ),
            anchor ="w",
            fg ="#666666"
            )
            label .pack (side =tk .LEFT ,fill =tk .X ,expand =True )
            self .status_labels [key ]=label 

        pipe_frame =tk .Frame (status_frame ,bg ="#E3F2FD")
        pipe_frame .pack (fill =tk .X ,pady =2 )
        tk .Label (
        pipe_frame ,
        text ="PipeDAG: ",
        bg ="#E3F2FD",
        font =("Microsoft YaHei",9 ,"bold"),
        anchor ="w",
        width =12 ,
        ).pack (side =tk .LEFT )
        for key ,text in [
        ("level","level"),
        ("rule","rule"),
        ("view","view"),
        ("algo","algo"),
        ]:
            label =tk .Label (
            pipe_frame ,
            text =f"{text}=-",
            bg ="#E3F2FD",
            font =("Consolas",9 ),
            anchor ="w",
            fg ="#455A64",
            padx =4 ,
            )
            label .pack (side =tk .LEFT )
            self .pipeline_status_labels [key ]=label 

        outputs_frame =tk .Frame (status_frame ,bg ="#E3F2FD")
        outputs_frame .pack (fill =tk .X ,pady =2 )
        tk .Label (
        outputs_frame ,
        text ="Recent Artifacts: ",
        bg ="#E3F2FD",
        font =("Microsoft YaHei",9 ,"bold"),
        anchor ="w",
        width =12 ,
        ).pack (side =tk .LEFT )
        for key ,text in [
        ("block_info","block_info"),
        ("segments","segments"),
        ("segments_png","segments_png"),
        ("timing","timing"),
        ("schedule","schedule"),
        ("source_original","source_original"),
        ("source_instrumented","source_instrumented"),
        ]:
            btn =tk .Button (
            outputs_frame ,
            text =text ,
            width =16 ,
            bg ="#ECEFF1",
            activebackground ="#CFD8DC",
            font =("Microsoft YaHei",8 ),
            state =tk .DISABLED ,
            command =lambda k =key :self ._pipeline_open_output (k ),
            )
            btn .pack (side =tk .LEFT ,padx =2 )
            self .pipeline_output_buttons [key ]=btn 

            # Source call graph statistics bar (shows extern statistics)
        self .call_stats_label =tk .Label (
        right_frame ,
        text ="",
        bg ="#FFF3E0",
        font =("Microsoft YaHei",9 ,"bold"),
        anchor ="w",
        padx =8 ,
        pady =4 
        )
        self .call_stats_label .pack (fill =tk .X ,padx =5 ,pady =4 )

        # Image display area (Canvas)
        self .canvas =tk .Canvas (
        right_frame ,
        bg ="#FAFAFA",
        highlightthickness =1 ,
        relief =tk .SUNKEN 
        )
        self .canvas .pack (fill =tk .BOTH ,expand =True ,padx =5 ,pady =5 )

        # Sub-function area (dynamically shown)
        self .subfunc_frame =tk .Frame (right_frame ,bg ="#ECEFF1")
        self ._subfunc_visible =False 

        # Canvas interaction - drag and zoom
        self .canvas .bind ("<ButtonPress-1>",self ._start_move )
        self .canvas .bind ("<B1-Motion>",self ._on_move )
        self .canvas .bind ("<MouseWheel>",self ._on_zoom )
        self .canvas .bind ("<Button-4>",self ._on_zoom )# Linux scroll up
        self .canvas .bind ("<Button-5>",self ._on_zoom )# Linux scroll down

        # ===================== Status Update =====================

    def _build_subfunc_toolbar (self ,specs :List [Tuple ])->None :
        """Build the sub-function toolbar
        
        Args:
            specs: [(button text, callback), ...]
        """
        # Clear existing buttons
        for child in self .subfunc_frame .winfo_children ():
            child .destroy ()

            # Create new buttons
        for spec in specs :
            if len (spec )==2 :
                text ,cmd =spec 
                enabled =True 
            elif len (spec )==3 :
                text ,cmd ,enabled =spec 
            else :
                raise ValueError ("invalid toolbar spec")
            tk .Button (
            self .subfunc_frame ,
            text =text ,
            command =cmd ,
            width =18 ,
            bg ="#ECEFF1",
            activebackground ="#CFD8DC",
            font =("Microsoft YaHei",9 ),
            state =(tk .NORMAL if enabled else tk .DISABLED ),
            ).pack (side =tk .LEFT ,padx =4 )

    def _toggle_subfunc_toolbar (self ,show :bool )->None :
        """Show or hide the sub-function toolbar"""
        if show and not self ._subfunc_visible :
            self .subfunc_frame .pack (fill =tk .X ,pady =8 ,before =self .canvas )
            self ._subfunc_visible =True 
        elif not show and self ._subfunc_visible :
            self .subfunc_frame .pack_forget ()
            self ._subfunc_visible =False 

    def _set_subfunc_toolbar (self ,specs :Optional [List [Tuple ]])->None :
        """Configure the sub-function toolbar
        
        Args:
            specs: `None` means hide it; otherwise show the specified buttons
        """
        if specs :
            self ._build_subfunc_toolbar (specs )
            self ._toggle_subfunc_toolbar (True )
        else :
            self ._toggle_subfunc_toolbar (False )

    def _update_status_display (self ):
        """updateStatus Paneldisplay"""
        self .status_labels ["source"].config (
        text =self .state .source_file .name if self .state .source_file else "<Not loaded>",
        fg ="#000000"if self .state .source_file else "#666666"
        )
        self .status_labels ["expand"].config (
        text =self .state .expand_file .name if self .state .expand_file else "<Not loaded>",
        fg ="#000000"if self .state .expand_file else "#666666"
        )
        self .status_labels ["dot"].config (
        text =self .state .dot_file .name if self .state .dot_file else "<Not loaded>",
        fg ="#000000"if self .state .dot_file else "#666666"
        )
        self .status_labels ["txt"].config (
        text =self .state .txt_file .name if self .state .txt_file else "<Not loaded>",
        fg ="#000000"if self .state .txt_file else "#666666"
        )
        self .pipeline_status_labels ["level"].config (text =f"level={self.pipeline_level}")
        self .pipeline_status_labels ["rule"].config (text =f"rule={self.pipeline_rule}")
        self .pipeline_status_labels ["view"].config (text =f"view={self.pipeline_view}")
        self .pipeline_status_labels ["algo"].config (text =f"algo={self.pipeline_algo}")
        for key ,btn in self .pipeline_output_buttons .items ():
            p =self .pipeline_last_outputs .get (key )
            btn .config (state =(tk .NORMAL if p and p .exists ()else tk .DISABLED ))

    def _pipeline_open_output (self ,key :str ):
        output =self .pipeline_last_outputs .get (key )
        if not output :
            self ._show_message ("Info",f"No {key} artifact。",is_error =False )
            return 
        self ._open_file_with_system (output )

    def _pipeline_set_context (
    self ,
    *,
    level :Optional [str ]=None ,
    rule :Optional [str ]=None ,
    view :Optional [str ]=None ,
    algo :Optional [str ]=None ,
    ):
        if level is not None :
            self .pipeline_level =level 
        if rule is not None :
            self .pipeline_rule =rule 
        if view is not None :
            self .pipeline_view =view 
        if algo is not None :
            self .pipeline_algo =algo 
        self ._update_status_display ()

    def _pipeline_record_outputs (self ,mapping :Dict [str ,Path ]):
        self .pipeline_last_outputs .update (mapping )
        self ._update_status_display ()

    def _pipeline_missing_paths (self ,base_name :str ,stage :str )->List [Path ]:
        root =self .base_dir /"intermediate_results"/base_name /"pipeline"
        if stage =="collect":
            return []
        if stage =="blocks":
            block_info =root /"block_info.json"
            return []if block_info .exists ()else [block_info ]
        if stage =="timing":
            return []if self ._pipeline_list_block_targets (base_name )else [root /"blocks"]
        if stage =="schedule":
            return []if self ._pipeline_list_timing_targets (base_name )else [root /"timing"]
        if stage =="instrument":
            return []if self ._pipeline_list_schedule_targets (base_name )else [root /"schedule"]
        return []

    def _pipeline_stage_enabled (self ,base_name :Optional [str ],stage :str )->bool :
        if not base_name :
            return stage =="collect"
        return not self ._pipeline_missing_paths (base_name ,stage )

    def _update_call_stats (self ,internal :int =0 ,external :int =0 ,visible :bool =False ):
        """updatesource-call statistics bar"""
        if visible :
            self .call_stats_label .config (
            text =f"Source function calls: {internal}  |  External function calls: {external}"
            )
        else :
            self .call_stats_label .config (text ="")

    def _show_message (self ,title :str ,message :str ,is_error :bool =False ):
        """Display a message"""
        if is_error :
            messagebox .showerror (title ,message )
        else :
            messagebox .showinfo (title ,message )

    def _pipeline_notice (self ,message :str ):
        """Silent notice for modular experiments: do not show a dialog, only update the info bar."""
        self .call_stats_label .config (text =message )

    def _open_file_with_system (self ,path :Path ):
        """Open the file with the system default application"""
        if not path .exists ():
            self ._show_message ("Error",f"File does not exist: {path}",is_error =True )
            return 
        try :
            if sys .platform .startswith ("darwin"):
                subprocess .run (["open",str (path )],check =False )
            elif os .name =="nt":
                os .startfile (str (path ))# type: ignore
            else :
                subprocess .run (["xdg-open",str (path )],check =False )
        except Exception as e :
            self ._show_message ("Error",f"Unable to open the file: {e}",is_error =True )

    def _is_tcp_open (self ,host :str ,port :int )->bool :
        try :
            with socket .create_connection ((host ,port ),timeout =0.5 ):
                return True 
        except Exception :
            return False 

    def _runtime_web_url (self )->str :
        return f"http://{self.runtime_web_host}:{self.runtime_web_port}"

    def open_runtime_compare_web (self ):
        """Start runtime_compare Web UI and open the browser automatically."""
        url =self ._runtime_web_url ()

        # If the port is already listening, open the browser directly and support externally started services
        if self ._is_tcp_open (self .runtime_web_host ,self .runtime_web_port ):
            webbrowser .open (url )
            self ._pipeline_notice (f"Runtime Compare Web is ready: {url}")
            return 

            # If a recorded child process has already exited, clear the reference
        if self .runtime_web_proc is not None and self .runtime_web_proc .poll ()is not None :
            self .runtime_web_proc =None 

            # Start the web service
        if shutil .which (sys .executable )is None :
            self ._show_message ("Error",f"Python interpreter is unavailable：{sys.executable}",is_error =True )
            return 

        try :
            self ._run (
            [sys .executable ,"-c","import flask"],
            check =True ,
            stdout =subprocess .DEVNULL ,
            stderr =subprocess .DEVNULL ,
            )
        except Exception :
            self ._show_message (
            "Error",
            "Runtime Compare Web dependency missing：flask。\n"
            "Run this first: python3 -m pip install flask",
            is_error =True ,
            )
            return 

        cmd =[
        sys .executable ,
        "-m",
        "tools.runtime_compare.main",
        "--web",
        "--host",
        self .runtime_web_host ,
        "--port",
        str (self .runtime_web_port ),
        ]
        try :
            if self .runtime_web_proc is None :
                self ._ensure_dir_for_original_user (self .runtime_web_log .parent )
                self .runtime_web_log_handle =open (self .runtime_web_log ,"w",encoding ="utf-8")
                self ._chown_to_original_user (self .runtime_web_log )
                self .runtime_web_proc =self ._popen (
                cmd ,
                cwd =str (self .base_dir ),
                stdout =self .runtime_web_log_handle ,
                stderr =self .runtime_web_log_handle ,
                )

                # Wait up to 15 seconds, confirm the port is open, then launch the browser
            deadline =time .time ()+15.0 
            while time .time ()<deadline :
                if self .runtime_web_proc is not None and self .runtime_web_proc .poll ()is not None :
                    details =""
                    try :
                        if self .runtime_web_log .exists ():
                            lines =self .runtime_web_log .read_text (encoding ="utf-8",errors ="replace").splitlines ()
                            details ="\n".join (lines [-12 :])
                    except Exception :
                        details =""
                    msg =f"Runtime Compare Web failed to start, exit code={self.runtime_web_proc.returncode}"
                    if details :
                        msg +=f"\n\nRecent log：\n{details}"
                    self ._show_message ("Error",msg ,is_error =True )
                    self .runtime_web_proc =None 
                    try :
                        if self .runtime_web_log_handle is not None :
                            self .runtime_web_log_handle .close ()
                    except Exception :
                        pass 
                    self .runtime_web_log_handle =None 
                    return 
                if self ._is_tcp_open (self .runtime_web_host ,self .runtime_web_port ):
                    webbrowser .open (url )
                    self ._pipeline_notice (f"Runtime Compare Web started: {url}")
                    return 
                time .sleep (0.2 )

            details =""
            try :
                if self .runtime_web_log .exists ():
                    lines =self .runtime_web_log .read_text (encoding ="utf-8",errors ="replace").splitlines ()
                    details ="\n".join (lines [-12 :])
            except Exception :
                details =""
            msg =f"Runtime Compare Web startup timed out: {url}"
            if details :
                msg +=f"\n\nRecent log：\n{details}"
            self ._show_message ("Error",msg ,is_error =True )
            try :
                if self .runtime_web_proc is not None and self .runtime_web_proc .poll ()is None :
                    self .runtime_web_proc .terminate ()
            except Exception :
                pass 
            self .runtime_web_proc =None 
            try :
                if self .runtime_web_log_handle is not None :
                    self .runtime_web_log_handle .close ()
            except Exception :
                pass 
            self .runtime_web_log_handle =None 
        except Exception as e :
            self ._show_message ("Error",f"Failed to start Runtime Compare Web: {e}",is_error =True )

    def _on_close (self ):
        """Close the GUI and clean up the runtime_compare Web process started by this window."""
        try :
            if self .runtime_web_proc is not None and self .runtime_web_proc .poll ()is None :
                self .runtime_web_proc .terminate ()
                try :
                    self .runtime_web_proc .wait (timeout =1.0 )
                except Exception :
                    self .runtime_web_proc .kill ()
        except Exception :
            pass 
        try :
            if self .runtime_web_log_handle is not None :
                self .runtime_web_log_handle .close ()
        except Exception :
            pass 
        self .runtime_web_log_handle =None 
        self .root .destroy ()

    def _display_image (self ,image_path :Path ):
        """Display the image on the canvas, with zoom and drag support"""
        try :
            if not _PIL_READY :
                if not self ._pil_warned :
                    self ._show_message (
                    "Info",
                    "the current environment lacks PIL.ImageTk，image preview has been disabled。\n"
                    "Install it with: python3 -m pip install pillow",
                    )
                    self ._pil_warned =True 
                return 
            if not image_path .exists ():
                return 

                # Load the original image
            self .original_image =Image .open (image_path )
            self .current_image =image_path 
            self .canvas_scale =self ._compute_initial_scale (
            self .original_image .width ,
            self .original_image .height ,
            )

            # Display image
            self ._refresh_canvas_image ()

        except Exception as e :
            print (f"Failed to display the image: {e}")

    def _refresh_canvas_image (self ):
        """Refresh the image on the canvas using the current zoom level"""
        if not _PIL_READY :
            return 
        if not self .original_image :
            return 

        try :
        # Compute the scaled size
            width =max (1 ,int (self .original_image .width *self .canvas_scale ))
            height =max (1 ,int (self .original_image .height *self .canvas_scale ))

            # Zoom image
            if self .canvas_scale !=1.0 :
                resized =self .original_image .resize (
                (width ,height ),
                Image .Resampling .LANCZOS 
                )
            else :
                resized =self .original_image 

                # Convert to a format usable by Tkinter
            self .tk_img =ImageTk .PhotoImage (resized )

            # Clear the canvas and display the image
            self .canvas .delete ("all")
            self .canvas .create_image (0 ,0 ,anchor =tk .NW ,image =self .tk_img ,tags ="image")

            # Set the scroll region
            self .canvas .config (scrollregion =(0 ,0 ,width ,height ))

        except Exception as e :
            print (f"Refresh imagefailed: {e}")

    def _display_cached_image (self ,key :str ,*,fallback =None ):
        """Display the cached image. If it does not exist and a fallback is provided, run the fallback first."""
        path =self .cached_images .get (key )
        if path and Path (path ).exists ():
            self ._display_image (Path (path ))
            return True 
        if callable (fallback ):
            fallback ()
            path =self .cached_images .get (key )
            if path and Path (path ).exists ():
                self ._display_image (Path (path ))
                return True 
        if path is None :
            self ._show_message ("Info","The corresponding image has not been generated yet. Run the generation step first.",is_error =False )
        else :
            self ._show_message ("Info",f"Not foundimageFile：{path}",is_error =False )
        return False 

    def _compute_initial_scale (self ,width :int ,height :int )->float :
        """Compute the initial zoom factor from the canvas size and the safety limit."""
        if width <=0 or height <=0 :
            return 1.0 

            # Read the current canvas size and refresh if needed to ensure layout completion
        self .canvas .update_idletasks ()
        canvas_width =self .canvas .winfo_width ()
        canvas_height =self .canvas .winfo_height ()

        if canvas_width <=1 or canvas_height <=1 :
        # The widget has not been laid out yet, so use a conservative virtual canvas size
            canvas_width =1600 
            canvas_height =1200 

            # Reserve border space for the image
        max_width =max (canvas_width -40 ,200 )
        max_height =max (canvas_height -40 ,200 )

        scale =min (max_width /width ,max_height /height ,1.0 )

        if scale <=0 :
        # If the original image is very large or the calculation above fails, fall back to a fixed threshold
            safe_scale =min (1600 /max (width ,1 ),1200 /max (height ,1 ))
            scale =max (safe_scale ,0.1 )

        return scale 

        # ===================== Button1: Select source file =====================

    def select_source_file (self ):
        """Button1: Select source file（update status only）"""
        file_path =filedialog .askopenfilename (
        title ="Select C/C++ source file",
        filetypes =[("C/C++Source File","*.c *.cpp"),("All files","*.*")]
        )

        if not file_path :
            return 

        source_path =Path (file_path )
        # update status only，without triggering compilation or directory creation
        # After switching the source file, clear the old expand/DOT context to avoid using stale inputs.
        if self .state .source_file and self .state .source_file !=source_path :
            self .state .expand_file =None 
            self .state .dot_file =None 
        self .state .source_file =source_path 
        self .state .work_dir =source_path .parent 
        self ._update_status_display ()

        # ===================== Button1.5: Select expand file =====================

    def select_expand_file (self ):
        """Button1.5: Select expand file（update status only）"""
        file_path =filedialog .askopenfilename (
        title ="Select expand file",
        filetypes =[("Expand File","*.expand"),("All files","*.*")]
        )

        if not file_path :
            return 
        expand_src =Path (file_path )
        self .state .expand_file =expand_src 
        self .state .work_dir =expand_src .parent 
        self ._update_status_display ()

    def _generate_expand_from_source_impl (self ,*,show_message :bool =True )->Path :
        if not self .state .source_file :
            raise RuntimeError ("PleaseSelect source file")
        source_file =self .state .source_file 
        src_dir =source_file .parent 
        base_name =source_file .stem 
        config_dir =self .base_dir /"config_files"/base_name 
        self ._ensure_dir_for_original_user (config_dir )

        # Auto-detect include directories
        include_dirs =[]
        seen_paths =set ()
        potential_include_paths =[
        src_dir /"include",
        src_dir /"includes",
        src_dir /"../include",
        src_dir /"../includes",
        src_dir /"inc",
        ]
        for inc_path in potential_include_paths :
            if inc_path .exists ()and inc_path .is_dir ():
                resolved_path =str (inc_path .resolve ())
                if resolved_path not in seen_paths :
                    seen_paths .add (resolved_path )
                    include_dirs .extend (["-I",resolved_path ])

        try :
        # Record the set of expand files before compilation, prefer newly created files from this run, and avoid picking historical files
            before_expand ={p .resolve ()for p in src_dir .glob ("*.expand")}

            # temporary .o
            import tempfile 
            with tempfile .NamedTemporaryFile (dir =src_dir ,suffix =".o",delete =False )as tmp :
                obj_name =Path (tmp .name ).name 

            cmd =["gcc","-fdump-rtl-expand",*include_dirs ,"-c",source_file .name ,"-o",obj_name ]
            result =self ._run (
            cmd ,
            cwd =str (src_dir ),
            capture_output =True ,
            text =True ,
            )

            # clean uptemporary .o
            try :
                obj_path =src_dir /obj_name 
                if obj_path .exists ():
                    obj_path .unlink ()
            except Exception :
                pass 

            if result .returncode !=0 :
                raise RuntimeError (result .stderr .strip ()or "Failed to generate the expand file")

                # Prefer newly created expand files from this run; if none exist, fall back to the latest expand file in the directory
            all_expand =sorted (
            src_dir .glob ("*.expand"),
            key =lambda p :p .stat ().st_mtime ,
            reverse =True ,
            )
            new_expand =[p for p in all_expand if p .resolve ()not in before_expand ]
            expand_files =new_expand or all_expand 
            if not expand_files :
                raise RuntimeError ("No generated expand file was found")

            expand_src =expand_files [0 ]
            # Rename uniformly to `<source>.Nr.expand` so that `base_name` stays stable and comes from the source filename
            m =re .search (r"\.(\d+r)\.expand$",expand_src .name )
            rtl_tag =m .group (1 )if m else "233r"
            canonical_name =f"{source_file.name}.{rtl_tag}.expand"
            dst =config_dir /canonical_name 
            if dst .exists ():
                dst .unlink ()
            shutil .move (str (expand_src ),str (dst ))
            self ._chown_to_original_user (dst )

            # Update Status
            self .state .expand_file =dst 
            self .state .work_dir =config_dir 
            self ._update_status_display ()
            if show_message :
                self ._show_message ("Success",f"GeneratedexpandFile：\n{dst}")
            return dst 
        except Exception :
            if show_message :
                import traceback 
                traceback .print_exc ()
            raise 

    def generate_expand_from_source (self ):
        """Button1.6: Generate an expand file from the current source file and store it in the config_files directory."""
        try :
            self ._generate_expand_from_source_impl (show_message =True )
        except Exception as e :
            self ._show_message ("Error",f"Failed to generate the expand file:\n{e}",is_error =True )

            # ===================== Button1.6: Select DOT file =====================

    def select_dot_file (self ):
        """Button1.6: Select DOT file（update status only）"""
        file_path =filedialog .askopenfilename (
        title ="Select DOT file",
        filetypes =[("DOT File","*.dot"),("All files","*.*")]
        )

        if not file_path :
            return 

        dot_src =Path (file_path )
        self .state .dot_file =dot_src 
        self .state .work_dir =dot_src .parent 
        self ._update_status_display ()

        # ===================== Button1.7: Filter DOT file =====================

    def filter_dot_file (self ):
        """Select any DOT file, write the filtered result to the unified directory, and update the status panel to the new DOT."""
        path_str =filedialog .askopenfilename (
        title ="Select the DOT file to filter",
        filetypes =[("DOT File","*.dot"),("All files","*.*")]
        )
        if not path_str :
            return 
        src =Path (path_str )
        if not src .exists ():
            self ._show_message ("Error","Filedoes not exist",is_error =True )
            return 

        try :
            dst =self .filtered_dot_dir /f"{src.stem}_filt{src.suffix}"
            filter_dot .filter_file (src ,dst )

            # Update the status to the new DOT
            self .state .dot_file =dst 
            self ._update_status_display ()
            self ._show_message ("Success",f"Generated filtered DOT:\n{dst}")
        except Exception as e :
            self ._show_message ("Error",f"Failed to filter the DOT file:\n{e}",is_error =True )

    def _compile_to_expand (self ,source_file :Path )->Optional [Path ]:
        """Compile the C file to generate an expand file
        
        Strategy:
        1. First check whether an expand file already exists in the source file directory
        2. If it exists, copy it directly to the rtl directory
        3. If not, try to compile it with gcc and auto-detect include directories
        """
        try :
            rtl_dir =self .state .work_dir /"rtlFile"
            before_expand ={p .resolve ()for p in source_file .parent .glob ("*.expand")}

            # Strategy1：check whether an expand file already exists
            # Look for files in the `main.c.233r.expand` format
            existing_expand =list (source_file .parent .glob ("*.expand"))

            if existing_expand :
                print (f"✅ Found an existing expand file: {existing_expand[0].name}")
                expand_src =existing_expand [0 ]
                canonical_expand_name =f"{source_file.name}.233r.expand"
                expand_dest =rtl_dir /canonical_expand_name 

                import shutil 
                shutil .copy2 (str (expand_src ),str (expand_dest ))
                return expand_dest 

                # Strategy2：usegcccompilegenerate
            print ("⚙️  No existing expand file was found, trying to compile it with gcc...")

            # Auto-detect include directories and support several common layouts
            include_dirs =[]
            seen_paths =set ()
            potential_include_paths =[
            source_file .parent /"include",# same-level include/
            source_file .parent /"includes",# same-level includes/
            source_file .parent /"../include",# parent-level include/
            source_file .parent /"../includes",# parent-level includes/
            source_file .parent /"inc",# same-level inc/
            ]

            for inc_path in potential_include_paths :
                if inc_path .exists ()and inc_path .is_dir ():
                    resolved_path =str (inc_path .resolve ())
                    if resolved_path not in seen_paths :
                        seen_paths .add (resolved_path )
                        include_dirs .extend (["-I",resolved_path ])
                        try :
                            rel_path =inc_path .relative_to (source_file .parent .parent )
                            print (f"   📁 Detected an include directory: {rel_path}")
                        except ValueError :
                            print (f"   📁 Detected an include directory: {inc_path.name}")

                            # Build the gcc command using relative paths and a temporary `.o` file
            import tempfile 

            # Create a temporary `.o` file in the source file directory
            with tempfile .NamedTemporaryFile (dir =source_file .parent ,suffix =".o",delete =False )as tmp :
                obj_name =Path (tmp .name ).name 

            cmd =[
            "gcc",
            "-fdump-rtl-expand",
            *include_dirs ,# Add include paths
            "-c",
            source_file .name ,# Use a relative path with only the filename
            "-o",obj_name 
            ]

            print (f"   🔨 GCC command: {' '.join(cmd)}")

            result =subprocess .run (
            cmd ,
            cwd =str (source_file .parent ),# Run in the source file directory
            capture_output =True ,
            text =True 
            )

            # clean uptemporary.oFile
            obj_file =source_file .parent /obj_name 
            try :
                if obj_file .exists ():
                    obj_file .unlink ()
            except :
                pass 

            if result .returncode !=0 :
                print (f"❌ GCC compilation failed: {result.stderr}")
                print ("\n💡 Info: If the source file requires special compiler options,")
                print ("       it is recommended to generate the expand file manually first,")
                print (f"       then place it in: {source_file.parent}")
                return None 

                # prefer expand files created in this run; if none exist, fall back to the latest expand file in the directory
            all_expand =sorted (
            source_file .parent .glob ("*.expand"),
            key =lambda p :p .stat ().st_mtime ,
            reverse =True 
            )
            new_expand =[p for p in all_expand if p .resolve ()not in before_expand ]
            expand_files =new_expand or all_expand 

            if not expand_files :
                print ("❌ No generated expand file was found")
                return None 

                # Move the expand file to the rtl directory
            expand_src =expand_files [0 ]
            canonical_expand_name =f"{source_file.name}.233r.expand"
            expand_dest =rtl_dir /canonical_expand_name 

            import shutil 
            shutil .move (str (expand_src ),str (expand_dest ))

            return expand_dest 

        except Exception as e :
            print (f"Failed to compile the expand file: {e}")
            import traceback 
            traceback .print_exc ()
            return None 

            # ===================== Button2: dag_generation =====================

    def _generate_dag_impl (self ,*,force_regenerate :bool =False ,show_message :bool =True )->Path :
        self ._update_call_stats (visible =False )
        self ._set_subfunc_toolbar (None )
        try :
        # Prefer an existing DOT file
            if not force_regenerate and self .state .dot_file and self .state .dot_file .exists ():
                dot_path =self .state .dot_file 
                target_dir =(
                self .state .work_dir /"dag_generation"
                if self .state .work_dir else dot_path .parent 
                )
                self ._ensure_dir_for_original_user (target_dir )
                png_path =target_dir /"dag.png"
                self ._run (
                ["dot","-Tpng",str (dot_path ),"-o",str (png_path )],
                check =True ,
                capture_output =True 
                )
                self ._display_image (png_path )
                if show_message :
                    self ._show_message ("Success",f"Directly rendered the current DOT：{dot_path.name}")
                return dot_path 

            if not self .state .expand_file :
                raise RuntimeError ("Please select a source file or load a DOT file")

                # call legacy DAG generation into the config_files directory
            cmd =[
            *self ._module_cmd ("generation.legacy"),
            str (self .state .expand_file ),
            "--threads-only",
            "--source-file",str (self .state .source_file )if self .state .source_file else "",
            "--output-base",str (self .base_dir )
            ]
            # remove empty arguments to avoid passing empty strings when no source file is selected
            cmd =[x for x in cmd if x !=""]

            result =subprocess .run (
            self ._as_original_user_cmd (cmd ),
            cwd =str (self .base_dir .parent ),
            capture_output =True ,
            text =True 
            )

            if result .returncode !=0 :
                raise RuntimeError (result .stderr .strip ()or "dag_generationfailed")

                # find generated files in the config_files directory
            source_name =(
            self .state .source_file .stem 
            if self .state .source_file 
            else self .state .get_base_name ()
            )
            config_dir =None 
            for cand in self ._iter_config_dirs (source_name ):
                if cand .exists ():
                    config_dir =cand 
                    break 
            if config_dir is None :
                raise RuntimeError (f"Config directory not found\npath: {self._config_dir_for_base(source_name)}")

            dot_files =list (config_dir .glob ("*_threads.dot"))

            if not dot_files :
                raise RuntimeError (f"`threads.dot` file not found\ndirectory: {config_dir}")

            source_dot =dot_files [0 ]

            # Unified storage path: intermediate_results/<base_name>/dag_generation/
            base_name =self .state .get_base_name ()or source_name 
            root_dir =self .base_dir /"intermediate_results"/base_name 
            target_dir =root_dir /"dag_generation"
            self ._ensure_dir_for_original_user (target_dir )
            target_dot =target_dir /"dag.dot"

            import shutil 
            shutil .copy (source_dot ,target_dot )
            self ._chown_to_original_user (target_dot )

            # Update the working directory to the unified path so later modules do not accidentally use the config directory
            self .state .work_dir =root_dir 
            self .state .dot_file =target_dot 

            # Also generate the `circle.txt` required by the modular experiment flow (collector dependency)
            # expected output：intermediate_results/<base>/config_files/circle.txt
            config_dir2 =self ._config_dir_for_base (base_name )
            self ._ensure_dir_for_original_user (config_dir2 )
            circle_txt =config_dir2 /"circle.txt"
            cmd_txt =[
            *self ._module_cmd ("generation.legacy"),
            str (self .state .expand_file ),
            "--export-txt",str (circle_txt ),
            "--output-base",str (self .base_dir ),
            ]
            if self .state .source_file :
                cmd_txt .extend (["--source-file",str (self .state .source_file )])
                # Force overwrite: always export `circle.txt` again to avoid old files causing inconsistent semaphore dependencies or block results
            try :
                circle_txt .unlink (missing_ok =True )
            except Exception :
                pass 
            result_txt =subprocess .run (
            self ._as_original_user_cmd (cmd_txt ),
            cwd =str (self .base_dir .parent ),
            capture_output =True ,
            text =True ,
            )
            if result_txt .returncode !=0 :
                print (f"⚠️  Failed to generate `circle.txt`: {result_txt.stderr}")
            else :
                self ._chown_to_original_user (circle_txt )

            if circle_txt .exists ():
                self .state .txt_file =circle_txt 

                # Generate and display the PNG image (requires the Graphviz `dot` command to be installed locally)
            png_path =target_dir /"dag.png"
            self ._run (
            ["dot","-Tpng",str (target_dot ),"-o",str (png_path )],
            check =True ,
            capture_output =True ,
            )
            self ._display_image (png_path )
            self ._update_status_display ()
            if show_message :
                self ._show_message ("Success",f"DAG image generated successfully：\n{png_path}")
            return target_dot 

        except Exception :
            raise 

    def generate_dag (self ):
        """Button2: dag_generation
        
        Workflow:
        - If the status panel already has a DOT file, render and display it directly
        - Otherwise call the legacy flow to generate a threads-only DOT, then copy it to the working directory and render it
        """
        try :
            self ._generate_dag_impl (force_regenerate =False ,show_message =True )
        except Exception as e :
            self ._show_message ("Error",f"dag_generationfailed:\n{e}",is_error =True )

    def generate_source_only_dag (self ):
        """Button2.1: Generate the source-call graph while keeping only calls from the current source file"""
        if not self .state .expand_file or not self .state .source_file :
            self ._show_message ("Error","Please select the source file and the expand file",is_error =True )
            return 

        try :
        # Unified storage path: intermediate_results/<base_name>/dag_generation/
            base_name =self .state .get_base_name ()or self .state .source_file .stem 
            root_dir =self .base_dir /"intermediate_results"/base_name 
            target_dir =root_dir /"dag_generation"
            target_dir .mkdir (parents =True ,exist_ok =True )
            target_dot =target_dir /"dag_source_only.dot"
            filtered_dot =target_dir /"dag_source_only_filt.dot"
            png_path =target_dir /"dag_source_only_filt.png"
            debug_dir =target_dir /"debug"
            # update the working directory to the unified path
            self .state .work_dir =root_dir 

            cmd =[
            *self ._module_cmd ("generation.legacy"),
            "--extern-only",
            "--source-file",str (self .state .source_file ),
            "--output-base",str (self .base_dir ),
            str (self .state .expand_file ),
            ]
            result =subprocess .run (
            cmd ,
            cwd =str (self .base_dir .parent ),
            capture_output =True ,
            text =True ,
            check =False ,
            )

            if result .returncode !=0 :
                self ._show_message ("Error",f"Failed to generate the source-call graph:\n{result.stderr}",is_error =True )
                return 

                # legacy stdout is DOT; write it to the target file
            target_dot .write_text (result .stdout ,encoding ="utf-8")
            # Reuse the filtered version directly
            import shutil 
            shutil .copy2 (target_dot ,filtered_dot )

            # render the PNG (filtered-only version)
            subprocess .run (
            ["dot","-Tpng",str (filtered_dot ),"-o",str (png_path )],
            check =True ,
            capture_output =True ,
            )

            # Read `mycalls_meta` and count `extern` calls
            internal_cnt =0 
            external_cnt =0 
            try :
                mycalls_meta_path =debug_dir /"mycalls_meta.json"
                if mycalls_meta_path .exists ():
                    import json 
                    data =json .loads (mycalls_meta_path .read_text (encoding ="utf-8"))
                    for finfo in data .values ():
                        if isinstance (finfo ,dict ):
                            for meta in finfo .values ():
                                if not isinstance (meta ,dict ):
                                    continue 
                                if meta .get ("extern")==0 :
                                    internal_cnt +=1 
                                else :
                                    external_cnt +=1 
            except Exception :
                internal_cnt =external_cnt =0 

                # update the status to the filtered DOT
            self .state .dot_file =filtered_dot 
            self ._update_status_display ()
            self ._update_call_stats (internal_cnt ,external_cnt ,visible =True )
            self ._display_image (png_path )
            # sub-features：View function mapping table（mycalls_meta）
            src_path =self .state .source_file 
            exp_path =self .state .expand_file 
            meta_path =debug_dir /"mycalls_meta.json"
            self ._set_subfunc_toolbar ([
            ("View source code",lambda p =src_path :self ._open_file_with_system (p )),
            ("View expand file",lambda p =exp_path :self ._open_file_with_system (p )),
            ("View function mapping table",lambda p =meta_path :self ._open_file_with_system (p )),
            ])
            self ._show_message ("Success",f"Source-call graph generated：{filtered_dot.name}")

        except Exception as e :
            self ._show_message ("Error",f"Failed to generate the source-call graph:\n{e}",is_error =True )

            # ===================== Button3: View conditional nodes =====================

    def view_conditions (self ):
        """Button3: View conditional nodes
        
        Workflow:
        1. Call the legacy flow to generate the full view, including conditional nodes
        2. Also generate `circle.txt` in the config_files directory
        3. Save to the config_files directory and the intermediate_results directory
        4. Generate the PNG and display it
        """
        if not self .state .expand_file :
            self ._show_message ("Error","PleaseSelect source file",is_error =True )
            return 

        try :
        # unified basename（match legacy/_ensure_output_dirs by stripping `.233r`, `.c`, `.cpp`, etc.）
            base_name =self .state .get_base_name ()or (self .state .source_file .stem if self .state .source_file else None )
            if not base_name :
                self ._show_message ("Error","Unable to parse the base name. Make sure an expand file has been selected.",is_error =True )
                return 

            root_dir =self .base_dir /"intermediate_results"/base_name 
            target_dir =root_dir /"View conditional nodes"
            target_dir .mkdir (parents =True ,exist_ok =True )
            # update the working directory to the unified path，avoid later modules accidentally using the config directory
            self .state .work_dir =root_dir 

            # config_files directory：intermediate_results/<base name>/config_files（legacy writes `<base_name>_full.dot`）
            config_dir =self ._config_dir_for_base (base_name )
            config_dir .mkdir (parents =True ,exist_ok =True )

            # Step 1: call legacy generateconditional view DOT（--conditions-only）
            print ("⚙️  callmycallyplusgenerateconditional-node view（--conditions-only）...")
            cmd =[
            *self ._module_cmd ("generation.legacy"),
            "--conditions-only",
            "--output-base",str (self .base_dir ),
            str (self .state .expand_file ),
            ]
            result =subprocess .run (
            cmd ,
            cwd =str (self .base_dir .parent ),
            capture_output =True ,
            text =True ,
            )
            if result .returncode !=0 :
                self ._show_message ("Error",f"generateconditional-node viewfailed:\n{result.stderr}",is_error =True )
                return 

            config_dot =config_dir /f"{base_name}_full.dot"
            if not config_dot .exists ():
                self ._show_message ("Error",f"generated full.dot file not found:\n{config_dot}",is_error =True )
                return 

                # Step 2: call legacy to generate `circle.txt` using `--export-txt`
            print ("⚙️  Generated `circle.txt`config_files...")

            txt_output_path =config_dir /"circle.txt"
            cmd_txt =[
            *self ._module_cmd ("generation.legacy"),
            str (self .state .expand_file ),
            "--export-txt",str (txt_output_path ),
            "--output-base",str (self .base_dir ),
            ]
            if self .state .source_file :
                cmd_txt .extend (["--source-file",str (self .state .source_file )])
                # force overwrite to avoid stale `circle.txt` leftovers
            try :
                txt_output_path .unlink (missing_ok =True )
            except Exception :
                pass 

            result_txt =subprocess .run (
            cmd_txt ,
            cwd =str (self .base_dir .parent ),
            capture_output =True ,
            text =True 
            )

            if result_txt .returncode !=0 :
                print (f"⚠️  Warning while generating `circle.txt`: {result_txt.stderr}")
            else :
                print (f"✅ Generated `circle.txt`: {txt_output_path}")

                # Step 3: copy to the intermediate_results directory
            import shutil 
            target_dot =target_dir /"conditions.dot"
            shutil .copy (config_dot ,target_dot )

            # Step 4: generatePNG
            png_path =target_dir /"conditions.png"
            subprocess .run (
            ["dot","-Tpng",str (target_dot ),"-o",str (png_path )],
            check =True ,
            capture_output =True 
            )
            print (f"✅ Generated PNG image: {png_path}")

            # Step 5: Update Status
            source_txt =config_dir /"circle.txt"
            if source_txt .exists ():
                self .state .txt_file =source_txt 
                print (f"✅ config files ready: {source_txt}")

            self .state .dot_file =target_dot 
            self ._update_status_display ()

            # Display the image
            self ._display_image (png_path )

            self ._show_message ("Success",f"Conditional-node graph and config files generated successfully\n\nDOT: {config_dot}\nTXT: {txt_output_path}")

        except Exception as e :
            self ._show_message ("Error",f"View conditional nodesfailed:\n{e}",is_error =True )
            import traceback 
            traceback .print_exc ()

            # ===================== Button4: Selectconfig_files =====================

    def select_config_folder (self ):
        """Button4: Select the config_files folder"""
        folder_path =filedialog .askdirectory (
        title ="Select the config_files folder"
        )

        if not folder_path :
            return 

        try :
            folder =Path (folder_path )

            # Search for DOT and TXT files
            dot_files =list (folder .glob ("*.dot"))
            txt_files =list (folder .glob ("*.txt"))

            if not dot_files and not txt_files :
                self ._show_message ("Error","No `.dot` or `.txt` file was found in the folder",is_error =True )
                return 

                # Update Status
            if dot_files :
                self .state .dot_file =dot_files [0 ]# Use the first DOT file

            if txt_files :
                self .state .txt_file =txt_files [0 ]# Use the first TXT file

                # If the working directory has not been initialized yet, initialize it from the config directory name
            if self .state .work_dir is None :
            # compatible with both old and new directory layouts：if the selected path is .../intermediate_results/<base>/config_files，then `base_name` is the parent directory name
                if folder .name =="config_files"and folder .parent .name :
                    base_name =folder .parent .name 
                else :
                    base_name =folder .name 
                self .state .work_dir =self .base_dir /"intermediate_results"/base_name 
                self .state .work_dir .mkdir (parents =True ,exist_ok =True )
                for sub in [
                "dag_generation",
                "View conditional nodes",
                "View Mutex Graph",
                "generatesemaphoregraph",
                "config_files",
                "debug",
                "logs",
                "temp",
                "images",
                ]:
                    (self .state .work_dir /sub ).mkdir (parents =True ,exist_ok =True )

                    # Reset the cached image
            self .cached_images ={key :None for key in self .cached_images }

            self ._update_status_display ()

            # if a DOT file exists, try generating and displaying the PNG
            if self .state .dot_file :
                try :
                    png_path =self .state .dot_file .with_suffix ('.png')
                    subprocess .run (
                    ["dot","-Tpng",str (self .state .dot_file ),"-o",str (png_path )],
                    check =True ,
                    capture_output =True 
                    )
                    self ._display_image (png_path )
                except :
                    pass 

            self ._show_message ("Success",f"config files loaded\nDOT: {len(dot_files)}\nTXT: {len(txt_files)}")

        except Exception as e :
            self ._show_message ("Error",f"failed to load the config_files folder:\n{e}",is_error =True )

            # ===================== Button5: View mutex locks =====================

    def view_mutex (self ):
        """Button5: View mutex locks
        
        features：
        1. parse mutex information from circle.txt
        2. use networkx to analyze mutex-lock coverage
        3. Provide two sub-features：View Mutex Graph、View Mutex Info
        """
        if not self .state .dot_file or not self .state .txt_file :
            self ._show_message ("Error","PleaseCompletedButton3（generateconditionalnodegraph）\nneedDOT File and circle.txt",is_error =True )
            self ._set_subfunc_toolbar (None )
            return 

        if not nx :
            self ._show_message ("Error","networkx is required:\npip install networkx",is_error =True )
            self ._set_subfunc_toolbar (None )
            return 

        try :
            print ("⚙️  start parsing mutex information...")

            self .cached_images ["mutex"]=None 
            # Step 1: read the DOT file and build the graph
            self .G =self ._read_dot_to_networkx (self .state .dot_file )
            print (f"✅ read graph structure: {len(self.G.nodes())} node, {len(self.G.edges())} edge")

            # Step 2: parsemutex lockpairing
            self .mutex_records =self ._parse_mutex_from_txt (self .state .txt_file )
            if not self .mutex_records :
                txt_content =self .state .txt_file .read_text (encoding ='utf-8',errors ='ignore').strip ()
                if not txt_content :
                    self ._show_message (
                    "Info",
                    "config files are empty\n\n"
                    "Reason: no mutex locks (pthread_mutex_lock/unlock) were detected in the source code\n\n"
                    "note：\n"
                    "• If your code uses mutex locks, make sure the expand file was generated correctly\n"
                    "• If the code truly contains no mutex locks, this is expected",
                    is_error =False ,
                    )
                else :
                    self ._show_message (
                    "Info",
                    "Not foundmutex lockpairinginformation\n\n"
                    "possible causes：\n"
                    "• circle.txt format is invalid\n"
                    "• mutex lock/unlock calls are not paired\n"
                    "• node names do not exist in the DOT file",
                    is_error =False ,
                    )
                self .mutex_records =[]# continue running even though no pairings were found
            print (f"✅ Found {len(self.mutex_records)} mutex-lock pairings")

            # Step 3: analyze coverage
            for rec in self .mutex_records :
                if rec .lock not in self .G .nodes or rec .unlock not in self .G .nodes :
                    print (f"⚠️  node does not exist: {rec.lock} or {rec.unlock}")
                    continue 
                try :
                    reach_from_lock =nx .descendants (self .G ,rec .lock )
                    reach_to_unlock =nx .ancestors (self .G ,rec .unlock )
                    between =reach_from_lock &reach_to_unlock |{rec .lock ,rec .unlock }
                    rec .covered =sorted (between ,key =lambda x :self ._suffix_num (x ))
                    print (f"✅ mutex lock {rec.idx}: cover {len(rec.covered)} nodes")
                except Exception as e :
                    print (f"⚠️  analysis failed: {e}")

                    # mark as ready
            self .mutex_prepared =True 

            # setsub-featuresButton
            self ._set_subfunc_toolbar ([
            ("View Mutex Graph",lambda :self ._display_cached_image ("mutex",fallback =self ._show_mutex_graph )),
            ("View Mutex Info",self .show_mutex_info ),
            ])

            # defaultdisplay the mutex graph
            self ._show_mutex_graph ()

        except Exception as e :
            self ._show_message ("Error",f"Failed to inspect mutex locks:\n{e}",is_error =True )
            self ._set_subfunc_toolbar (None )
            import traceback 
            traceback .print_exc ()

    def _show_mutex_graph (self ):
        """Sub-feature 1: display the mutex graph with colored subgraphs."""
        if not self .mutex_prepared :
            self ._show_message ("Warning",'Please click "View Mutex" to parse the data first.',is_error =False )
            return 

        try :
            print ("⚙️  generatemutex lockgraph...")

            # Generate DOT content
            dot_lines =['digraph Mutex {']
            dot_lines .append ('  rankdir=LR;')
            dot_lines .append ('  node [shape=box, style=filled, fillcolor=white];')

            # Add all edges
            dot_lines .append ('\n  // Edges')
            for u ,v in self .G .edges ():
                dot_lines .append (f'  "{u}" -> "{v}";')

                # Create colored mutex subgraphs
            color_map ={}
            cluster_id =0 
            for rec in self .mutex_records :
                if not rec .covered :
                    continue 

                    # assign colors
                color =self .MUTEX_COLORS [len (color_map )%len (self .MUTEX_COLORS )]
                color_map [rec .var ]=color 
                cluster_id +=1 

                # create subgraphs
                dot_lines .append (f'\n  subgraph cluster_{cluster_id} {{')
                dot_lines .append (f'    label="Mutex {rec.var} (ID={rec.idx})";')
                dot_lines .append (f'    color="{color}";')
                dot_lines .append (f'    style=filled;')
                dot_lines .append (f'    fillcolor="{color}30";')# Semi-transparent background
                dot_lines .append (f'    fontcolor=black;')
                dot_lines .append (f'    fontsize=12;')

                # Add nodes
                for node in rec .covered :
                    label =node 
                    if node ==rec .lock :
                        label =f"{node}\\n[LOCK]"
                    elif node ==rec .unlock :
                        label =f"{node}\\n[UNLOCK]"
                    dot_lines .append (f'    "{node}" [label="{label}"];')

                dot_lines .append ('  }')

            dot_lines .append ('}')
            dot_content ='\n'.join (dot_lines )

            # save and render
            target_dir =self .state .work_dir /"view_mutex"
            target_dir .mkdir (parents =True ,exist_ok =True )

            dot_path =target_dir /"mutex_graph.dot"
            dot_path .write_text (dot_content ,encoding ='utf-8')

            png_path =target_dir /"mutex_graph.png"
            subprocess .run (
            ["dot","-Gdpi=110","-Tpng",str (dot_path ),"-o",str (png_path )],
            check =True ,
            capture_output =True 
            )
            print (f"✅ generatemutex lockgraph: {png_path}")
            self .cached_images ["mutex"]=png_path if png_path .exists ()else None 

            # Display image
            self ._display_image (png_path )

        except Exception as e :
            self ._show_message ("Error",f"generatemutex lockgraphfailed:\n{e}",is_error =True )
            import traceback 
            traceback .print_exc ()

    def show_mutex_info (self ):
        """sub-features2: display mutex text information on the canvas"""
        if not self .mutex_prepared :
            self ._show_message ("Warning",'Please click "View Mutex" to parse the data first.',is_error =False )
            return 

        top =tk .Toplevel (self .root )
        top .title ("mutex lockinformation")
        top .geometry ("720x520")

        text_widget =tk .Text (top ,font =("Consolas",10 ),wrap =tk .WORD )
        scrollbar =tk .Scrollbar (top ,command =text_widget .yview )
        text_widget .configure (yscrollcommand =scrollbar .set )
        text_widget .pack (side =tk .LEFT ,fill =tk .BOTH ,expand =True )
        scrollbar .pack (side =tk .RIGHT ,fill =tk .Y )

        if not self .mutex_records :
            text_widget .insert (tk .END ,"The current configuration does not match any mutex-lock pairings。\n")
        else :
            for i ,rec in enumerate (self .mutex_records ,1 ):
                lines =[
                f"[Mutex {i}] var={rec.var}  ID={rec.idx}",
                f"  LOCK   : {rec.lock}",
                f"  UNLOCK : {rec.unlock}",
                ]
                if rec .lock_file or rec .unlock_file :
                    lines .append (f"  FILE   : {rec.lock_file or rec.unlock_file}")
                if rec .lock_line is not None or rec .unlock_line is not None :
                    a =rec .lock_line if rec .lock_line is not None else "?"
                    b =rec .unlock_line if rec .unlock_line is not None else "?"
                    lines .append (f"  LINES  : {a} -> {b}")
                covered =rec .covered or []
                lines .append (f"  COVERED ({len(covered)} nodes):")
                preview =covered [:20 ]
                for node in preview :
                    mark =""
                    if node ==rec .lock :
                        mark =" [LOCK]"
                    elif node ==rec .unlock :
                        mark =" [UNLOCK]"
                    lines .append (f"    - {node}{mark}")
                if len (covered )>len (preview ):
                    lines .append (f"    ... ... and {len(covered) - len(preview)} nodes")
                text_widget .insert (tk .END ,"\n".join (lines )+"\n\n")

        text_widget .config (state =tk .DISABLED )

        # ===================== Button6: generatesemaphoregraph =====================

    def generate_semaphore (self ):
        """Button6: generatesemaphoregraph
        
        features：
        1. parse semaphore information from circle.txt
        2. add semaphore edges to the original graph（sem_post → sem_wait）
        3. run Tarjan to analyze strongly connected components
        4. generate the thread-group visualization graph
        """
        if not self .state .dot_file or not self .state .txt_file :
            self ._show_message ("Error","PleaseCompletedButton3（generateconditionalnodegraph）\nneedDOT File and circle.txt",is_error =True )
            return 

        if not nx :
            self ._show_message ("Error","networkx is required:\npip install networkx",is_error =True )
            return 

        try :
            print ("⚙️  start generating the semaphore graph...")

            for key in ("original","tarjan","threads"):
                self .cached_images [key ]=None 
                # Step 1: readoriginalgraph
            G =self ._read_dot_to_networkx (self .state .dot_file )
            print (f"✅ readoriginalgraph: {len(G.nodes())} node, {len(G.edges())} edge")

            # Step 2: parsesemaphore pairings
            sem_records =self ._parse_semaphore_from_txt (self .state .txt_file )
            if not sem_records :
                txt_content =self .state .txt_file .read_text (encoding ='utf-8',errors ='ignore').strip ()
                if not txt_content :
                    self ._show_message (
                    "Info",
                    "config files are empty\n\n"
                    "Reason: no semaphores (sem_post/sem_wait) were detected in the source code\n\n"
                    "note：\n"
                    "• If your code uses semaphores, make sure the expand file was generated correctly\n"
                    "• If the code truly contains no semaphores, this is expected",
                    is_error =False ,
                    )
                else :
                    self ._show_message (
                    "Info",
                    "Not foundsemaphore pairingsinformation\n\n"
                    "possible causes：\n"
                    "• circle.txt format is invalid\n"
                    "• semaphore post/wait calls are not paired\n"
                    "• node names do not exist in the DOT file",
                    is_error =False ,
                    )
                sem_records =[]
            print (f"✅ Found {len(sem_records)} semaphore pairings")

            # Step 3: add semaphore edges
            self .sem_records =sem_records 
            G_sem =G .copy ()
            for rec in sem_records :
                if rec .post in G_sem .nodes and rec .wait in G_sem .nodes :
                    G_sem .add_edge (
                    rec .post ,
                    rec .wait ,
                    style ='dashed',
                    color ='#FF7043',
                    label =f'{rec.var} {rec.idx}',
                    )
                    print (f"✅ add semaphore edges: {rec.post} → {rec.wait}")

                    # Step 4: run the Tarjan algorithm
            sccs =list (nx .strongly_connected_components (G_sem ))
            self .sccs =sccs 
            print (f"✅ Tarjan analysis: found {len(sccs)}  strongly connected components")

            # Step 5: generate multiple views
            target_dir =self .state .work_dir /"generatesemaphoregraph"
            target_dir .mkdir (parents =True ,exist_ok =True )

            # thread color mapping
            thread_colors :Dict [str ,str ]={}
            for node in G_sem .nodes ():
                prefix =node .split ('/',1 )[0 ]if '/'in node else 'main'
                if prefix not in thread_colors :
                    color_idx =len (thread_colors )%len (self .THREAD_COLORS )
                    thread_colors [prefix ]=self .THREAD_COLORS [color_idx ]
            self .thread_color_map =thread_colors 

            # View 1: originalgraph+semaphoreedge
            self ._generate_semaphore_original (G_sem ,target_dir )

            # View 2: Tarjan SCC graph
            self ._generate_semaphore_tarjan (G_sem ,sccs ,target_dir )

            # View 3: thread-group graph
            self ._generate_semaphore_threads (G_sem ,sccs ,target_dir )

            # Step6: displaythread-group graph
            png_path =target_dir /"threads.png"
            if png_path .exists ():
                self ._display_image (png_path )

            info_lines =["semaphoregraphgenerateCompleted！\n"]
            info_lines .append (f"semaphore pairings: {len(sem_records)}")
            info_lines .append (f"Strongly connected components: {len(sccs)}\n")
            info_lines .append ("generateFile:")
            info_lines .append ("  • original.png - originalgraph+semaphoreedge")
            info_lines .append ("  • tarjan.png - SCC graph")
            info_lines .append ("  • threads.png - thread-group graph")

            self ._set_subfunc_toolbar ([
            ("View Original Graph",lambda :self ._display_cached_image ("original")),
            ("View Strongly Connected Components",lambda :self ._display_cached_image ("tarjan")),
            ("View Semaphore Graph",lambda :self ._display_cached_image ("threads")),
            ("displaysemaphoreinformation",self .show_semaphore_info ),
            ("Show Thread Color Legend",self .show_thread_legend ),
            ])

            self ._show_message ("Success","\n".join (info_lines ))

        except Exception as e :
            self ._show_message ("Error",f"generatesemaphoregraphfailed:\n{e}",is_error =True )
            import traceback 
            traceback .print_exc ()

            # ===================== Button7: time_analysis =====================

    def time_analysis_entry (self ):
        """Button7: time_analysis - Selectsource codeand a JSON file, then run instrumentation/compile/execute automatically."""
        self ._update_call_stats (visible =False )
        self .ta_source_file =None 
        self .ta_json_file =None 
        self ._set_subfunc_toolbar ([
        ("Select source-code file",self ._select_ta_source_file ),
        ("Select JSON file",self ._select_ta_json_file ),
        ("segment-leveltime_analysis（Level-1）",self ._ta_level1_one_click ),
        ("segment-leveltime_analysis（Level-2）",self ._ta_level2_one_click ),
        ("Task-count graph per thread",self ._plot_thread_task_frequency ),
        ("Thread execution-time graph",self ._plot_thread_total_time ),
        ("threadcallgraph",self ._plot_thread_call_gantt ),
        ])
        self ._show_message ("Info","Please select the source-code file and mycalls_meta_internal.json. Time analysis will run automatically once both are ready.")

    def _ta_level1_one_click (self ):
        """time_analysissub-features：segment-leveltime_analysis（Level-1）run end-to-end in one click。

        Pipeline:
          legacy(--source-file, --level1-stage1) -> stage1 seg DAG
          -> segment timing -> LPF thread schedule -> prio instrument compare
        Inputs come from status area (state.source_file, state.expand_file).
        """
        if not self .state .expand_file or not self .state .expand_file .exists ():
            self ._show_message ("Error","The status panel is missing the expand file. Please select it first.",is_error =True )
            return 
        if not self .state .source_file or not self .state .source_file .exists ():
            self ._show_message ("Error","The status panel is missing the source C file. Please select it first.",is_error =True )
            return 

        base_name =self .state .source_file .stem if self .state .source_file else None 
        if not base_name :
            base_name =self .state .get_base_name ()
        if not base_name :
            self ._show_message ("Error","Unable to infer base_name.",is_error =True )
            return 

        try :
        # 1) legacy generate + level1 stage1
            cmd =[
            sys .executable ,
            "-m",
            package_module_name ("generation.legacy"),
            str (self .state .expand_file ),
            "--threads-only",
            "--source-file",
            str (self .state .source_file ),
            "--output-base",
            str (self .base_dir ),
            "--force",
            "--level1-stage1",
            ]
            result =subprocess .run (cmd ,cwd =str (self .base_dir .parent ),capture_output =True ,text =True )
            if result .returncode !=0 :
                self ._show_message ("Error",f"Level-1 stage1 Generation failed:\n{result.stderr}",is_error =True )
                return 

                # 2) render segment DAG png and display (default)
            seg_dot =self .base_dir /"intermediate_results"/base_name /"level1"/"stage1"/"dag_stage1_seg.dot"
            seg_png =self .base_dir /"intermediate_results"/base_name /"level1"/"stage1"/"dag_stage1_seg.png"
            subprocess .run (["dot","-Tpng",str (seg_dot ),"-o",str (seg_png )],check =True ,capture_output =True )
            self ._display_image (seg_png )

            # 3) segment timing (one run)
            ta_cmd =[
            sys .executable ,
            "-m",
            package_module_name ("level1.time_analysis_level1"),
            "--base-dir",
            str (self .base_dir ),
            "--base-name",
            base_name ,
            "--source",
            str (self .state .source_file ),
            ]
            ta_res =subprocess .run (ta_cmd ,cwd =str (self .base_dir .parent ),capture_output =True ,text =True )
            if ta_res .returncode !=0 :
                self ._show_message ("Error",f"segment-leveltime_analysisfailed:\n{ta_res.stderr}",is_error =True )
                return 

                # 4) LPF schedule (thread)
            sched_cmd =[
            sys .executable ,
            "-m",
            package_module_name ("level1.lpf_segment"),
            "--base-dir",
            str (self .base_dir ),
            "--base-name",
            base_name ,
            "--project",
            base_name ,
            "--prio-max",
            "80",
            ]
            sched_res =subprocess .run (sched_cmd ,cwd =str (self .base_dir .parent ),capture_output =True ,text =True )
            if sched_res .returncode !=0 :
                self ._show_message ("Error",f"LPF schedulefailed:\n{sched_res.stderr}",is_error =True )
                return 

                # 5) prio instrument compare
            prio_cmd =[
            sys .executable ,
            "-m",
            package_module_name ("level1.instrument_prio_level1"),
            "--base-dir",
            str (self .base_dir ),
            "--base-name",
            base_name ,
            "--source",
            str (self .state .source_file ),
            ]
            prio_res =subprocess .run (prio_cmd ,cwd =str (self .base_dir .parent ),capture_output =True ,text =True )
            if prio_res .returncode !=0 :
                self ._show_message ("Error",f"priorityinstrumentationcomparison failed:\n{prio_res.stderr}",is_error =True )
                return 

                # Parse compare.json path from stdout (last "wrote ...")
            compare_path =None 
            for ln in prio_res .stdout .splitlines ():
                if ln .startswith ("wrote "):
                    compare_path =Path (ln [len ("wrote "):].strip ())
            if compare_path and compare_path .exists ():
                try :
                    compare =json .loads (compare_path .read_text (encoding ="utf-8"))
                    if compare .get ("prio_set_failed"):
                        messagebox .showwarning (
                        "Info",
                        "Detected thread priority setting failure (possibly missing root/CAP_SYS_NICE privileges), "
                        "The result of this prio comparison may not be significantly different from FIFO.\n"
                        f"Details: {compare_path}",
                        )
                except Exception :
                    pass 

                    # 6) run experiment script (if present) to get baseline/prio runtimes
            run_script =None 
            if compare_path :
                candidate =compare_path .parent /"run_experiments.sh"
                if candidate .exists ():
                    run_script =candidate 
            run_result_path =None 
            if run_script :
                try :
                    run_res =subprocess .run (
                    ["bash",str (run_script )],
                    cwd =str (run_script .parent ),
                    capture_output =True ,
                    text =True ,
                    check =True ,
                    )
                    for ln in run_res .stdout .splitlines ():
                        if "Results saved to"in ln :
                            run_result_path =Path (ln .split ("Results saved to",1 )[1 ].strip ())
                            break 
                except Exception as e :
                    self ._show_message ("Error",f"failed to run the comparison script:\n{e}",is_error =True )

            self ._show_message (
            "Success",
            "segment-leveltime_analysis (Level-1) Completed:\n"
            f"- segment-level DAG: {seg_png}\n"
            f"- segment-leveltiming: {self.base_dir/'intermediate_results'/base_name/'level1'/'timing'/base_name/'time_result_seg.json'}\n"
            f"- LPF schedule: {self.base_dir/'intermediate_results'/base_name/'level1'/'schedule'/'lpf_segment'/'schedule_seg.json'}\n"
            f"- Comparison result: {compare_path if compare_path else '(unknown)'}\n"
            f"- Runtime result: {run_result_path if run_result_path else 'not generated or script missing'}",
            )
        except subprocess .CalledProcessError as e :
            self ._show_message ("Error",f"command execution failed:\n{e}",is_error =True )
        except Exception as e :
            self ._show_message ("Error",f"segment-leveltime_analysis（Level-1）failed:\n{e}",is_error =True )

    def _ta_level2_one_click (self ):
        """time_analysissub-features：segment-leveltime_analysis（Level-2）generatesegmentation DAG。

        Current goal: reuse the Level-1 preprocessing (`legacy` + `functions_ranges/meta`) as the basis,
        and generate Level-2 segment-level DAG DOT/PNG according to the Level-2 segmentation rules (create/join/post/wait/mutex edge boundary containment).
        """
        if not self .state .expand_file or not self .state .expand_file .exists ():
            self ._show_message ("Error","The status panel is missing the expand file. Please select it first.",is_error =True )
            return 
        if not self .state .source_file or not self .state .source_file .exists ():
            self ._show_message ("Error","The status panel is missing the source C file. Please select it first.",is_error =True )
            return 

        base_name =self .state .source_file .stem if self .state .source_file else None 
        if not base_name :
            base_name =self .state .get_base_name ()
        if not base_name :
            self ._show_message ("Error","Unable to infer base_name.",is_error =True )
            return 

        try :
        # 1) legacy generate + export circle.txt (for validation in existing UI features)
            config_dir =self ._config_dir_for_base (base_name )
            config_dir .mkdir (parents =True ,exist_ok =True )
            circle_txt =config_dir /"circle.txt"
            cmd =[
            sys .executable ,
            "-m",
            package_module_name ("generation.legacy"),
            str (self .state .expand_file ),
            "--threads-only",
            "--source-file",
            str (self .state .source_file ),
            "--output-base",
            str (self .base_dir ),
            "--force",
            "--level1-stage1",
            "--export-txt",
            str (circle_txt ),
            ]
            result =subprocess .run (cmd ,cwd =str (self .base_dir .parent ),capture_output =True ,text =True )
            if result .returncode !=0 :
                self ._show_message ("Error",f"Level-2 preprocessing failed(legacy/export-txt):\n{result.stderr}",is_error =True )
                return 

                # 1.5) merge post->wait edges into DAG (stage: merge_post_wait)
            merge_cmd =[
            sys .executable ,
            "-m",
            package_module_name ("level2.merge_post_wait_dag"),
            "--base-dir",
            str (self .base_dir ),
            "--base-name",
            base_name ,
            ]
            merge_res =subprocess .run (merge_cmd ,cwd =str (self .base_dir .parent ),capture_output =True ,text =True )
            if merge_res .returncode !=0 :
                self ._show_message ("Error",f"Level-2 merge_post_wait failed:\n{merge_res.stderr}",is_error =True )
                return 

                # 1.6) archive inputs into level2/merge_post_wait (not a manual copy; triggered by this button)
            gen_root =self .base_dir /"intermediate_results"/base_name /"dag_generation"
            merge_dir =self .base_dir /"intermediate_results"/base_name /"level2"/"merge_post_wait"
            merge_dir .mkdir (parents =True ,exist_ok =True )
            try :
                if (gen_root /"functions_full.json").exists ():
                    shutil .copy2 (gen_root /"functions_full.json",merge_dir /"functions_full.json")
                internal_meta =gen_root /"debug"/"mycalls_meta_internal.json"
                if internal_meta .exists ():
                    shutil .copy2 (internal_meta ,merge_dir /"mycalls_meta_internal.json")
                if circle_txt .exists ():
                    shutil .copy2 (circle_txt ,merge_dir /"circle.txt")
            except Exception as e :
                self ._show_message ("Error",f"failed to archive Level-2 intermediate files:\n{e}",is_error =True )
                return 

                # 2) build Level-2 segments + dag (json + dot)
            level2_segment_dag .main # ensure import
            seg_json ,dag_json =level2_segment_dag .build_level2_segments_and_dag (
            base_dir =self .base_dir ,
            base_name =base_name ,
            source_file =self .state .source_file ,
            )
            out_dir =self .base_dir /"intermediate_results"/base_name /"level2"/"stage2"
            out_dir .mkdir (parents =True ,exist_ok =True )
            seg_path =out_dir /"segments_level2.json"
            dag_path =out_dir /"dag_level2_seg.json"
            dot_path =out_dir /"dag_level2_seg.dot"
            png_path =out_dir /"dag_level2_seg.png"
            seg_path .write_text (json .dumps (seg_json ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
            dag_path .write_text (json .dumps (dag_json ,ensure_ascii =False ,indent =2 ),encoding ="utf-8")
            dot_path .write_text (level2_segment_dag ._to_dot (seg_json ,dag_json ),encoding ="utf-8")# type: ignore[attr-defined]

            subprocess .run (["dot","-Tpng",str (dot_path ),"-o",str (png_path )],check =True ,capture_output =True )
            self ._display_image (png_path )

            self ._show_message (
            "Success",
            "segment-leveltime_analysis（Level-2）Generatedsegmentation DAG：\n"
            f"- merge_post_wait: {merge_dir}\n"
            f"- segments: {seg_path}\n"
            f"- dag: {dag_path}\n"
            f"- dag_png: {png_path}",
            )
        except Exception as e :
            self ._show_message ("Error",f"segment-leveltime_analysis（Level-2）failed:\n{e}",is_error =True )

            # ===================== modular experiment（pipeline） =====================

    def _pipeline_context (self )->Optional [Tuple [str ,Path ]]:
        if not self .state .source_file or not self .state .source_file .exists ():
            self ._show_message ("Error","Please select a source file (.c) in the status panel.",is_error =True )
            return None 
        base_name =self .state .source_file .stem or self .state .get_base_name ()
        if not base_name :
            self ._show_message ("Error","Unable to infer base_name.",is_error =True )
            return None 
        return base_name ,self .state .source_file .resolve ()

    def _pipeline_pick_option (self ,*,title :str ,options :List [Tuple ],labels :List [str ])->Optional [Tuple ]:
        if not options :
            self ._show_message ("Error",f"{title}：has no options.",is_error =True )
            return None 
        if len (options )==1 :
            return options [0 ]
        lines =[f"{i + 1}. {labels[i]}"for i in range (len (labels ))]
        idx =simpledialog .askinteger (
        title ,
        "Please enter the option number:\n"+"\n".join (lines ),
        parent =self .root ,
        minvalue =1 ,
        maxvalue =len (options ),
        )
        if idx is None :
            return None 
        return options [idx -1 ]

    def _pipeline_pick_rule (self ,level :str )->Optional [str ]:
        rules =sorted (pipeline_list_rules (level ).keys ())
        if not rules :
            self ._show_message ("Error",f"{level} has no registered rules.",is_error =True )
            return None 
        if len (rules )==1 :
            return rules [0 ]
        choice =simpledialog .askstring (
        f"Select a {level} rule",
        f"Available rules: {', '.join(rules)}\nEnter `rule_name`:",
        initialvalue =rules [0 ],
        parent =self .root ,
        )
        if not choice :
            return None 
        choice =choice .strip ()
        if choice not in rules :
            self ._show_message ("Error",f"Rule does not exist: {choice}",is_error =True )
            return None 
        return choice 

    def _pipeline_list_block_targets (self ,base_name :str )->List [Tuple [str ,str ]]:
        out :List [Tuple [str ,str ]]=[]
        root =self .base_dir /"intermediate_results"/base_name /"pipeline"/"blocks"
        for level in ("level1","level2","level3"):
            level_dir =root /level 
            if not level_dir .exists ():
                continue 
            for rule_dir in sorted (level_dir .iterdir ()):
                if not rule_dir .is_dir ():
                    continue 
                seg =rule_dir /"segments.json"
                dag =rule_dir /"dag_seg.json"
                if seg .exists ()and dag .exists ():
                    out .append ((level ,rule_dir .name ))
        return out 

    def _pipeline_list_schedule_targets (self ,base_name :str )->List [Tuple [str ,str ,str ]]:
        out :List [Tuple [str ,str ,str ]]=[]
        root =self .base_dir /"intermediate_results"/base_name /"pipeline"/"schedule"
        for level in ("level1","level2","level3"):
            level_dir =root /level 
            if not level_dir .exists ():
                continue 
            for rule_dir in sorted (level_dir .iterdir ()):
                if not rule_dir .is_dir ():
                    continue 
                for algo_dir in sorted (rule_dir .iterdir ()):
                    if not algo_dir .is_dir ():
                        continue 
                    if (algo_dir /"schedule.json").exists ():
                        out .append ((level ,rule_dir .name ,algo_dir .name ))
        return out 

    def _pipeline_list_timing_targets (self ,base_name :str )->List [Tuple [str ,str ]]:
        out :List [Tuple [str ,str ]]=[]
        root =self .base_dir /"intermediate_results"/base_name /"pipeline"
        blocks_root =root /"blocks"
        timing_root =root /"timing"
        for level in ("level1","level2","level3"):
            level_dir =timing_root /level 
            if not level_dir .exists ():
                continue 
            for rule_dir in sorted (level_dir .iterdir ()):
                if not rule_dir .is_dir ():
                    continue 
                timing_json =rule_dir /"timing.json"
                dag_json =blocks_root /level /rule_dir .name /"dag_seg.json"
                if timing_json .exists ()and dag_json .exists ():
                    out .append ((level ,rule_dir .name ))
        return out 

    def _pipeline_default_rule (self ,level :str )->Optional [str ]:
        rules =sorted (pipeline_list_rules (level ).keys ())
        return rules [0 ]if rules else None 

    def _pipeline_default_algo (self )->Optional [str ]:
        algos =sorted (pipeline_list_algos ().keys ())
        return algos [0 ]if algos else None 

    def _pipeline_collect_run (self ,*,base_name :str ,source_file :Path )->Dict :
        if self ._sudo_user :
            payload =self ._pipeline_cli (
            [
            "collect",
            "--base-name",
            base_name ,
            "--source",
            str (source_file ),
            ]
            )
        else :
            payload =pipeline_runner .run_collector (base_dir =self .base_dir ,base_name =base_name ,source_file =source_file )
        self ._pipeline_set_context (level ="-",rule ="-",view ="-",algo ="-")
        self ._pipeline_record_outputs ({"block_info":self .base_dir /"intermediate_results"/base_name /"pipeline"/"block_info.json"})
        return payload 

    def _pipeline_blocks_run (self ,*,base_name :str ,source_file :Path ,level :str ,rule_name :str )->Path :
        if self ._sudo_user :
            self ._pipeline_cli (
            [
            "blocks",
            "--base-name",
            base_name ,
            "--level",
            level ,
            "--rule",
            rule_name ,
            "--source",
            str (source_file ),
            ]
            )
        else :
            pipeline_runner .run_blocks (
            base_dir =self .base_dir ,
            base_name =base_name ,
            level =level ,
            rule_name =rule_name ,
            source_file =source_file ,
            )
        out_dir =self .base_dir /"intermediate_results"/base_name /"pipeline"/"blocks"/level /rule_name 
        png =out_dir /"dag_seg.png"
        if not png .exists ():
            png =out_dir /"sched"/"dag_seg.png"
        if png .exists ():
            self ._display_image (png )
        self ._pipeline_set_context (level =level ,rule =rule_name ,view ="single",algo ="-")
        self ._pipeline_record_outputs (
        {
        "segments":out_dir /"segments.json",
        "segments_png":png ,
        }
        )
        return out_dir 

    def _pipeline_timing_run (self ,*,base_name :str ,level :str ,rule_name :str )->Dict :
        if self ._sudo_user :
            result =self ._pipeline_cli (
            [
            "timing",
            "--base-name",
            base_name ,
            "--level",
            level ,
            "--rule",
            rule_name ,
            ]
            )
        else :
            result =pipeline_runner .run_timing_stage (
            base_dir =self .base_dir ,base_name =base_name ,level =level ,rule_name =rule_name 
            )
        self ._pipeline_set_context (level =level ,rule =rule_name ,view ="single",algo ="-")
        self ._pipeline_record_outputs (
        {"timing":self .base_dir /"intermediate_results"/base_name /"pipeline"/"timing"/level /rule_name /"timing.json"}
        )
        return result 

    def _pipeline_schedule_run (self ,*,base_name :str ,level :str ,rule_name :str ,algo_name :str )->Dict :
        if self ._sudo_user :
            result =self ._pipeline_cli (
            [
            "schedule",
            "--base-name",
            base_name ,
            "--level",
            level ,
            "--rule",
            rule_name ,
            "--algo",
            algo_name ,
            ]
            )
        else :
            result =pipeline_runner .run_schedule_stage (
            base_dir =self .base_dir ,
            base_name =base_name ,
            level =level ,
            rule_name =rule_name ,
            algo_name =algo_name ,
            )
        self ._pipeline_set_context (level =level ,rule =rule_name ,view ="single",algo =algo_name )
        self ._pipeline_record_outputs (
        {"schedule":self .base_dir /"intermediate_results"/base_name /"pipeline"/"schedule"/level /rule_name /algo_name /"schedule.json"}
        )
        return result 

    def _pipeline_instrument_run (
    self ,
    *,
    base_name :str ,
    level :str ,
    rule_name :str ,
    algo_name :str ,
    instrument_mode :str ,
    )->Dict :
        if self ._sudo_user :
            result =self ._pipeline_cli (
            [
            "instrument",
            "--base-name",
            base_name ,
            "--level",
            level ,
            "--rule",
            rule_name ,
            "--algo",
            algo_name ,
            "--mode",
            instrument_mode ,
            ]
            )
        else :
            result =pipeline_runner .run_instrument_stage (
            base_dir =self .base_dir ,
            base_name =base_name ,
            level =level ,
            rule_name =rule_name ,
            algo_name =algo_name ,
            instrument_mode =instrument_mode ,
            )
        self ._pipeline_set_context (level =level ,rule =rule_name ,view ="single",algo =algo_name )
        self ._pipeline_record_outputs (
        {
        "source_original":Path (str (result .get ("source_original"))),
        "source_instrumented":Path (str (result .get ("source_instrumented"))),
        }
        )
        return result 

    def _pipeline_validation_outputs (self ,*,base_name :str ,level :str ,rule_name :str ,algo_name :str )->Dict [str ,Path ]:
        validation_root =self .base_dir /"intermediate_results"/base_name /"pipeline"/"validation"/level /rule_name /algo_name 
        return {
        "validation_dot":validation_root /"dag_seg_annotated.dot",
        "validation_png":validation_root /"dag_seg_annotated.png",
        "validation_const":validation_root /"const_binding.json",
        }

    def pipeline_full_run (self ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,source_file =ctx 

        level ="level2"
        rule_name ="effective_line_merge"
        algo_names =sorted (pipeline_list_algos ().keys ())
        if not rule_name :
            self ._show_message ("Error",f"{level} has no available rules.",is_error =True )
            return 
        if not algo_names :
            self ._show_message ("Error","No available scheduling result exists for the current state.",is_error =True )
            return 
        instrument_mode ="generic"

        try :
            self ._pipeline_notice ("One-click full pipeline：start generating expand...")
            self ._generate_expand_from_source_impl (show_message =False )

            self ._pipeline_notice ("One-click full pipeline：start generating the DAG...")
            self ._generate_dag_impl (force_regenerate =True ,show_message =False )

            self ._pipeline_notice ("One-click full pipeline：collect...")
            self ._pipeline_collect_run (base_name =base_name ,source_file =source_file )

            self ._pipeline_notice (f"One-click full pipeline：blocks ({level}/{rule_name})...")
            self ._pipeline_blocks_run (base_name =base_name ,source_file =source_file ,level =level ,rule_name =rule_name )

            self ._pipeline_notice (f"One-click full pipeline：timing ({level}/{rule_name})...")
            timing_result =self ._pipeline_timing_run (base_name =base_name ,level =level ,rule_name =rule_name )

            last_instrument_result :Optional [Dict ]=None 
            validation_generated =0 
            last_validation_png :Optional [Path ]=None 
            for idx ,algo_name in enumerate (algo_names ,start =1 ):
                self ._pipeline_notice (
                f"One-click full pipeline：algorithm {idx}/{len(algo_names)} -> schedule ({algo_name})..."
                )
                self ._pipeline_schedule_run (base_name =base_name ,level =level ,rule_name =rule_name ,algo_name =algo_name )

                self ._pipeline_notice (
                f"One-click full pipeline：algorithm {idx}/{len(algo_names)} -> instrument + validation ({algo_name})..."
                )
                last_instrument_result =self ._pipeline_instrument_run (
                base_name =base_name ,
                level =level ,
                rule_name =rule_name ,
                algo_name =algo_name ,
                instrument_mode =instrument_mode ,
                )

                validation_outputs =self ._pipeline_validation_outputs (
                base_name =base_name ,
                level =level ,
                rule_name =rule_name ,
                algo_name =algo_name ,
                )
                validation_png =validation_outputs ["validation_png"]
                if validation_png .exists ():
                    validation_generated +=1 
                    last_validation_png =validation_png 

            if last_validation_png and last_validation_png .exists ():
                self ._display_image (last_validation_png )

            self ._pipeline_notice (
            "One-click full pipeline Completed：\n"
            f"- base: {base_name}\n"
            f"- level/rule: {level}/{rule_name}\n"
            f"- algos: {', '.join(algo_names)}\n"
            f"- timing weights: {len(timing_result.get('weights', {}))}\n"
            f"- schedule/instrument runs: {len(algo_names)}\n"
            f"- last instrumented: {last_instrument_result.get('source_instrumented') if last_instrument_result else '-'}\n"
            f"- validation generated: {validation_generated}/{len(algo_names)}",
            )
            self .pipeline_entry ()
        except Exception as e :
            self ._show_message ("Error",f"One-click full pipeline failed:\n{e}",is_error =True )

    def pipeline_entry (self ):
        base_name =self .state .source_file .stem if self .state .source_file else self .state .get_base_name ()
        self ._set_subfunc_toolbar (
        [
        ("generateblock partitioninformation",self ._pipeline_collect ,self ._pipeline_stage_enabled (base_name ,"collect")),
        ("level1 block partition",lambda :self ._pipeline_run_level ("level1"),self ._pipeline_stage_enabled (base_name ,"blocks")),
        ("level2 block partition",lambda :self ._pipeline_run_level ("level2"),self ._pipeline_stage_enabled (base_name ,"blocks")),
        ("level3 block partition",lambda :self ._pipeline_run_level ("level3"),self ._pipeline_stage_enabled (base_name ,"blocks")),
        ("block partitiontiming",self ._pipeline_timing ,self ._pipeline_stage_enabled (base_name ,"timing")),
        ("scheduling",self ._pipeline_schedule_entry ,self ._pipeline_stage_enabled (base_name ,"schedule")),
        ("priority instrumentation",self ._pipeline_instrument_entry ,self ._pipeline_stage_enabled (base_name ,"instrument")),
        ("Return to main flow",lambda :self ._set_subfunc_toolbar (None ),True ),
        ]
        )
        self ._pipeline_notice ("modular experiment：Run in collector -> blocks -> timing -> schedule -> instrument order.")

    def _pipeline_collect (self ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,source_file =ctx 
        try :
            payload =self ._pipeline_collect_run (base_name =base_name ,source_file =source_file )
            self ._pipeline_notice (
            "Generatedblock partitioninformation：\n"
            f"- block_info: {self.base_dir/'intermediate_results'/base_name/'pipeline'/'block_info.json'}\n"
            f"- has_circle_txt: {payload.get('capabilities', {}).get('has_circle_txt', False)}",
            )
            self .pipeline_entry ()
        except Exception as e :
            self ._show_message ("Error",f"generateblock partitioninformationfailed:\n{e}",is_error =True )

    def _pipeline_run_level (self ,level :str ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,source_file =ctx 
        missing =self ._pipeline_missing_paths (base_name ,"blocks")
        if missing :
            self ._show_message ("Error","Missing prefix File:\n"+"\n".join (str (p .resolve ())for p in missing ),is_error =True )
            return 
        rule_name =self ._pipeline_pick_rule (level )
        if not rule_name :
            return 
        try :
            out_dir =self ._pipeline_blocks_run (base_name =base_name ,source_file =source_file ,level =level ,rule_name =rule_name )
            self ._pipeline_notice (f"{level} block partitionCompleted：rule={rule_name}，outputdirectory={out_dir}")
            self .pipeline_entry ()
        except Exception as e :
            self ._show_message ("Error",f"{level} block partitionfailed:\n{e}",is_error =True )

    def _pipeline_timing (self ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,_ =ctx 
        missing =self ._pipeline_missing_paths (base_name ,"timing")
        if missing :
            self ._show_message ("Error","Missing prefix File:\n"+"\n".join (str (p .resolve ())for p in missing ),is_error =True )
            return 
        options =self ._pipeline_list_block_targets (base_name )
        labels =[f"{lv}/{rn}"for (lv ,rn )in options ]
        picked =self ._pipeline_pick_option (title ="Select block-partition target",options =options ,labels =labels )
        if not picked :
            return 
        level ,rule_name =picked 
        try :
            result =self ._pipeline_timing_run (base_name =base_name ,level =level ,rule_name =rule_name )
            self ._pipeline_notice (
            "block partitiontimingCompleted：\n"
            f"- target: {level}/{rule_name}\n"
            f"- weights: {len(result.get('weights', {}))}\n"
            f"- File: {self.base_dir/'intermediate_results'/base_name/'pipeline'/'timing'/level/rule_name/'timing.json'}",
            )
            self .pipeline_entry ()
        except Exception as e :
            self ._show_message ("Error",f"block partitiontimingfailed:\n{e}",is_error =True )

    def _pipeline_schedule_entry (self ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,_ =ctx 
        missing =self ._pipeline_missing_paths (base_name ,"schedule")
        if missing :
            self ._show_message ("Error","Missing prefix File:\n"+"\n".join (str (p .resolve ())for p in missing ),is_error =True )
            return 
        algos =sorted (pipeline_list_algos ().keys ())
        if not algos :
            self ._show_message ("Error","No registered scheduling result exists for the current state.",is_error =True )
            return 
        specs :List [Tuple [str ,callable ]]=[]
        for algo_name in algos :
            specs .append ((f"Algorithm: {algo_name}",lambda n =algo_name :self ._pipeline_schedule_with_algo (n )))
        specs .append (("Return to modular experiment",self .pipeline_entry ))
        self ._set_subfunc_toolbar (specs )
        self ._pipeline_notice ("Please selectscheduling。")

    def _pipeline_schedule_with_algo (self ,algo_name :str ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,_ =ctx 
        options =self ._pipeline_list_timing_targets (base_name )
        labels =[f"{lv}/{rn}"for (lv ,rn )in options ]
        picked =self ._pipeline_pick_option (title =f"Selectscheduleinput ({algo_name})",options =options ,labels =labels )
        if not picked :
            return 
        level ,rule_name =picked 
        try :
            result =self ._pipeline_schedule_run (base_name =base_name ,level =level ,rule_name =rule_name ,algo_name =algo_name )
            self ._pipeline_notice (
            "schedule calculation Completed:\n"
            f"- target: {level}/{rule_name}\n"
            f"- algo: {algo_name}\n"
            f"- priorities: {len(result.get('priorities', {}))}",
            )
            self .pipeline_entry ()
        except Exception as e :
            self ._show_message ("Error",f"Schedule computation failed:\n{e}",is_error =True )

    def _pipeline_instrument_entry (self ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,_ =ctx 
        missing =self ._pipeline_missing_paths (base_name ,"instrument")
        if missing :
            self ._show_message ("Error","Missing prefix File:\n"+"\n".join (str (p .resolve ())for p in missing ),is_error =True )
            return 
        self ._set_subfunc_toolbar (
        [
        ("Specialized instrumentation",lambda :self ._pipeline_instrument ("specialized")),
        ("Generic instrumentation",lambda :self ._pipeline_instrument ("generic")),
        ("Return to modular experiment",self .pipeline_entry ),
        ]
        )
        self ._pipeline_notice ("Please select an instrumentation mode: Specialized Instrumentation or Generic Instrumentation.")

    def _pipeline_instrument (self ,instrument_mode :str ):
        ctx =self ._pipeline_context ()
        if not ctx :
            return 
        base_name ,_ =ctx 
        missing =self ._pipeline_missing_paths (base_name ,"instrument")
        if missing :
            self ._show_message ("Error","Missing prefix File:\n"+"\n".join (str (p .resolve ())for p in missing ),is_error =True )
            return 
        options =self ._pipeline_list_schedule_targets (base_name )
        labels =[f"{lv}/{rn}/{an}"for (lv ,rn ,an )in options ]
        picked =self ._pipeline_pick_option (title ="Select instrumentation target",options =options ,labels =labels )
        if not picked :
            return 
        level ,rule_name ,algo_name =picked 
        try :
            result =self ._pipeline_instrument_run (
            base_name =base_name ,
            level =level ,
            rule_name =rule_name ,
            algo_name =algo_name ,
            instrument_mode =instrument_mode ,
            )
            self ._pipeline_notice (
            "priority instrumentationCompleted：\n"
            f"- target: {level}/{rule_name}/{algo_name}\n"
            f"- mode: {instrument_mode}\n"
            f"- source_original: {result.get('source_original')}\n"
            f"- source_instrumented: {result.get('source_instrumented')}",
            )
            self .pipeline_entry ()
        except Exception as e :
            self ._show_message ("Error",f"priority instrumentationfailed:\n{e}",is_error =True )

    def _pipeline_cli (self ,argv :List [str ])->Dict :
        """Run pipeline stages via CLI in a child process (helps under sudo-root GUI)."""
        cmd =[
        sys .executable ,
        "-m",
        package_module_name ("pipeline.cli"),
        "--base-dir",
        str (self .base_dir ),
        *argv ,
        ]
        proc =self ._run (
        cmd ,
        cwd =self .base_dir .parent ,
        capture_output =True ,
        text =True ,
        )
        if proc .returncode !=0 :
            raise RuntimeError (proc .stderr .strip ()or f"pipeline CLI failed: rc={proc.returncode}")
        try :
            return json .loads (proc .stdout or "{}")
        except Exception :
            return {}

            # ===================== Button8: scheduling =====================

    def scheduler_entry (self ):
        """Button 8: scheduling - longest path (weighted DAG)"""
        self ._set_subfunc_toolbar ([
        ("generatelongest path",self ._scheduler_longest_path ),
        ("CPC analysis",self ._scheduler_cpc ),
        ("CPCpriorityinstrumentation",self ._scheduler_cpc_instrument ),
        ("experiment-result comparison",self ._scheduler_compare_metrics ),
        ])
        self ._show_message (
        "Info",
        "Please select the DAG DOT file and time_result.json to generate the weighted DAG and compute the longest path, or run CPC analysis / priority instrumentation.",
        )

    def _scheduler_longest_path (self ):
        dot_str =filedialog .askopenfilename (
        title ="Select DAG DOT file",
        filetypes =[("DOT File","*.dot"),("All files","*.*")],
        )
        if not dot_str :
            return 
        json_str =filedialog .askopenfilename (
        title ="Select time_result.json",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not json_str :
            return 

        dot_path =Path (dot_str )
        json_path =Path (json_str )

        try :
            nodes ,edges =scheduler .parse_dot_edges (dot_path )
            weights =scheduler .load_time_result_weights (json_path )
            source =scheduler .find_single_source (nodes ,edges )
            if source is None :
            # Non-blocking: compute the longest path from any start node in the full graph, but inform the user that the source node is not unique
                pass 
            result =scheduler .longest_path_dag (nodes ,edges ,weights ,source =source )

            base_name =self ._infer_base_from_path (json_path )
            out_dir =None 
            if base_name :
                out_dir =self .base_dir /"intermediate_results"/base_name /"scheduling"
            else :
                out_dir =json_path .parent /"scheduling"
            out_dir .mkdir (parents =True ,exist_ok =True )
            highlight_dot_path =out_dir /"dag_highlight.dot"
            highlight_png_path =out_dir /"dag_highlight.png"
            longest_json_path =out_dir /"longest_path.json"
            longest_txt_path =out_dir /"longest_path.txt"

            original_dot_text =dot_path .read_text (encoding ="utf-8",errors ="replace")
            highlight_text =scheduler .highlight_dot_inplace (
            original_dot_text ,
            path_nodes =result .path ,
            path_edges =list (zip (result .path ,result .path [1 :])),
            node_weight_ns =result .node_weight_ns ,
            )
            highlight_dot_path .write_text (highlight_text ,encoding ="utf-8")
            scheduler .write_longest_path_json (
            longest_json_path ,
            dot_path =dot_path ,
            time_json_path =json_path ,
            result =result ,
            )
            # for manual inspection
            longest_txt_path .write_text (
            "The longest path (node ​​weight=total_ns, missing weights are counted as 0):\n"
            f"Total time: {result.total_weight_ns:,} ns\n"
            f"Path length: {len(result.path)}\n"
            +"\n".join (result .path )
            +"\n",
            encoding ="utf-8",
            )

            subprocess .run (
            ["dot","-Tpng",str (highlight_dot_path ),"-o",str (highlight_png_path )],
            check =True ,
            capture_output =True ,
            )
            self ._display_image (highlight_png_path )
            self ._show_message (
            "Success",
            "Generated authorized DAG and longest path:\n"
            f"DOT: {highlight_dot_path}\n"
            f"PNG: {highlight_png_path}\n"
            f"JSON: {longest_json_path}",
            )
        except Exception as e :
        # scheduler.longest_path_dag reports an error when a cycle exists
            self ._show_message ("Error",f"generatelongest pathfailed:\n{e}",is_error =True )

    def _scheduler_cpc (self ):
        dot_str =filedialog .askopenfilename (
        title ="Select DAG DOT file",
        filetypes =[("DOT File","*.dot"),("All files","*.*")],
        )
        if not dot_str :
            return 
        time_json_str =filedialog .askopenfilename (
        title ="Select time_result.json",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not time_json_str :
            return 
        longest_json_str =filedialog .askopenfilename (
        title ="Select longest_path.json",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not longest_json_str :
            return 

        dot_path =Path (dot_str )
        time_json_path =Path (time_json_str )
        longest_json_path =Path (longest_json_str )

        try :
            nodes ,edges =scheduler .parse_dot_edges (dot_path )
            weights =scheduler .load_time_result_weights (time_json_path )
            longest =json .loads (longest_json_path .read_text (encoding ="utf-8"))
            longest_path_nodes =longest .get ("path",[])

            if not longest_path_nodes :
                raise RuntimeError ("longest_path.json is missing the `path` field or it is empty.")

            result =scheduler .compute_cpc_priorities (
            nodes ,
            edges ,
            weights ,
            longest_path_nodes ,
            m =2 ,
            )

            base_name =self ._infer_base_from_path (time_json_path )
            out_dir =None 
            if base_name :
                out_dir =self .base_dir /"intermediate_results"/base_name /"scheduling"/"cpc"
            else :
                out_dir =time_json_path .parent /"scheduling"/"cpc"
            out_dir .mkdir (parents =True ,exist_ok =True )

            highlight_dot_path =out_dir /"dag_highlight.dot"
            highlight_png_path =out_dir /"dag_highlight.png"
            schedule_json_path =out_dir /"schedule.json"
            schedule_txt_path =out_dir /"schedule.txt"

            original_dot_text =dot_path .read_text (encoding ="utf-8",errors ="replace")
            highlight_text =scheduler .apply_priorities_to_dot (
            original_dot_text ,
            priorities =result .priorities ,
            node_weight_ns =result .node_weight_ns ,
            longest_path =result .longest_path ,
            )
            highlight_dot_path .write_text (highlight_text ,encoding ="utf-8")

            scheduler .write_cpc_schedule_json (
            schedule_json_path ,
            dot_path =dot_path ,
            time_json_path =time_json_path ,
            longest_json_path =longest_json_path ,
            result =result ,
            )
            schedule_txt_path .write_text (
            "CPC nodepriority (m=2, lack of rights reset 0):\n"
            f"Provider segment count: {len(result.providers)}\n"
            f"Node count: {len(result.priorities)}\n"
            +"\n".join (f"{n}: prio={p}, weight={result.node_weight_ns.get(n,0)}"
            for n ,p in sorted (result .priorities .items (),key =lambda kv :-kv [1 ])),
            encoding ="utf-8",
            )

            subprocess .run (
            ["dot","-Tpng",str (highlight_dot_path ),"-o",str (highlight_png_path )],
            check =True ,
            capture_output =True ,
            )
            self ._display_image (highlight_png_path )
            self ._show_message (
            "Success",
            "CPC analysis Completed：\n"
            f"DOT: {highlight_dot_path}\n"
            f"PNG: {highlight_png_path}\n"
            f"JSON: {schedule_json_path}",
            )
        except Exception as e :
            self ._show_message ("Error",f"CPC analysis failed:\n{e}",is_error =True )

    def _scheduler_cpc_instrument (self ):
        src_str =filedialog .askopenfilename (
        title ="Select source code file (C)",
        filetypes =[("CSource File","*.c"),("All files","*.*")],
        )
        if not src_str :
            return 
        meta_str =filedialog .askopenfilename (
        title ="Select mycalls_meta_internal.json",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not meta_str :
            return 
        schedule_str =filedialog .askopenfilename (
        title ="Select CPC schedule.json",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not schedule_str :
            return 

        src_path =Path (src_str )
        meta_path =Path (meta_str )
        schedule_path =Path (schedule_str )

        try :
            sched_data =json .loads (schedule_path .read_text (encoding ="utf-8"))
            priorities =sched_data .get ("priorities")
            if not isinstance (priorities ,dict ):
                raise RuntimeError ("schedule.json does not contain a `priorities` object.")

            result =time_analysis .run_time_analysis (
            src_path ,
            meta_path ,
            self .base_dir ,
            priorities =priorities ,
            cpc_mode =True ,
            )

            base_name =self ._infer_base_from_path (meta_path )or src_path .stem 
            out_dir =self .base_dir /"intermediate_results"/base_name /"scheduling"/"cpc_analysis_result"
            out_dir .mkdir (parents =True ,exist_ok =True )

            # copy related outputs for easier comparison
            shutil .copy2 (result .result_json ,out_dir /"time_result.json")
            if result .prio_result_json :
                shutil .copy2 (result .prio_result_json ,out_dir /"time_result_prio.json")
            if result .prio_weighted_dot :
                shutil .copy2 (result .prio_weighted_dot ,out_dir /"dag_weighted_prio.dot")
            weighted_src =result .result_json .parent /"dag_weighted.dot"
            if weighted_src .exists ():
                shutil .copy2 (weighted_src ,out_dir /"dag_weighted.dot")
            summary_src =meta_path .parent /"thread_time_summary.json"
            if summary_src .exists ():
                shutil .copy2 (summary_src ,out_dir /"thread_time_summary.json")
            if result .metrics_json and result .metrics_json .exists ():
                shutil .copy2 (result .metrics_json ,out_dir /result .metrics_json .name )

            self ._show_message (
            "Success",
            "Completed CPC priorityinstrumentationtime_analysis:\n"
            f"outputdirectory: {out_dir}\n"
            f"Base result: {out_dir / 'time_result.json'}\n"
            f"priorityresult: {out_dir / 'time_result_prio.json'}",
            )
        except Exception as e :
            self ._show_message ("Error",f"CPC instrumentationtime_analysisfailed:\n{e}",is_error =True )

    def _select_ta_source_file (self ):
        path_str =filedialog .askopenfilename (
        title ="SelectCSource File（time_analysis）",
        filetypes =[("CSource File","*.c"),("All files","*.*")]
        )
        if not path_str :
            return 
        self .ta_source_file =Path (path_str )
        self ._maybe_run_time_analysis ()

    def _select_ta_json_file (self ):
        path_str =filedialog .askopenfilename (
        title ="Select mycalls_meta_internal.json",
        filetypes =[("JSONFile","*.json"),("All files","*.*")]
        )
        if not path_str :
            return 
        self .ta_json_file =Path (path_str )
        self ._maybe_run_time_analysis ()

    def _maybe_run_time_analysis (self ):
        if not self .ta_source_file or not self .ta_json_file :
            return 
        try :
            result =time_analysis .run_time_analysis (
            self .ta_source_file ,
            self .ta_json_file ,
            self .base_dir ,
            )
            # point the working directory to the output for later inspection
            self .state .work_dir =result .instrumented_dir 
            trace_path =result .result_json .parent /"thread_trace.json"
            self ._show_message (
            "Success",
            "time_analysisCompleted：\n"
            f"instrumentationdirectory: {result.instrumented_dir}\n"
            f"result: {result.result_json}\n"
            f"Metrics: {result.metrics_json}\n"
            f"Trace: {trace_path}\n"
            f"Log: {result.log_path}",
            )
        except Exception as e :
            self ._show_message ("Error",f"time_analysisfailed:\n{e}",is_error =True )

    def _scheduler_compare_metrics (self ):
        file_a =filedialog .askopenfilename (
        title ="Select metrics file A (metrics*.json)",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not file_a :
            return 
        file_b =filedialog .askopenfilename (
        title ="Select metrics file B (metrics*.json)",
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not file_b :
            return 

        path_a =Path (file_a )
        path_b =Path (file_b )
        try :
            m_a =json .loads (path_a .read_text (encoding ="utf-8"))
            m_b =json .loads (path_b .read_text (encoding ="utf-8"))
            base_name =self ._infer_base_from_path (path_a )or self ._infer_base_from_path (path_b )or "compare"
            root_dir =self .base_dir /"intermediate_results"/base_name /"scheduling"/"compare"
            ts_dir =root_dir /datetime .now ().strftime ("%Y%m%d_%H%M%S")
            out_dir =ts_dir 
            out_dir .mkdir (parents =True ,exist_ok =True )

            lbl_a =path_a .stem 
            lbl_b =path_b .stem 

            prog_png =time_charts .render_program_compare_png (
            m_a ,
            m_b ,
            labels =(lbl_a ,lbl_b ),
            output_dir =out_dir ,
            )
            thread_png =time_charts .render_thread_compare_png (
            m_a ,
            m_b ,
            labels =(lbl_a ,lbl_b ),
            output_dir =out_dir ,
            )
            self ._display_image (thread_png )
            self ._show_message (
            "Success",
            "Generated indicator comparison graph:\n"
            f"Total-time comparison: {prog_png}\n"
            f"Thread-time comparison: {thread_png}",
            )
        except Exception as e :
            self ._show_message ("Error",f"Metric comparison failed:\n{e}",is_error =True )

    def _pick_time_analysis_json (self ,title :str )->Optional [Path ]:
        path_str =filedialog .askopenfilename (
        title =title ,
        filetypes =[("JSONFile","*.json"),("All files","*.*")],
        )
        if not path_str :
            return None 
        return Path (path_str )

    def _plot_thread_task_frequency (self ):
        """sub-features：Task-count graph per thread（count）"""
        json_path =self ._pick_time_analysis_json ("Select a statistics JSON file (thread_time_summary.json / time_result.json / meta.json)")
        if not json_path :
            return 
        try :
            metrics =time_charts .load_thread_metrics (json_path )
            out_dir =time_charts .choose_time_analysis_output_dir (
            json_path ,
            time_analysis_root =self .state .work_dir if self .state .work_dir else None ,
            )
            png_path =time_charts .render_thread_frequency_png (metrics ,output_dir =out_dir )
            self ._display_image (png_path )
            self ._show_message ("Success",f"Generatedstatisticsgraph：\n{png_path}")
        except Exception as e :
            self ._show_message ("Error",f"generatestatisticsgraphfailed:\n{e}",is_error =True )

    def _plot_thread_total_time (self ):
        """sub-features：Thread execution-time graph（total_ns）"""
        json_path =self ._pick_time_analysis_json ("Select a statistics JSON file (thread_time_summary.json / time_result.json / meta.json)")
        if not json_path :
            return 
        try :
            metrics =time_charts .load_thread_metrics (json_path )
            out_dir =time_charts .choose_time_analysis_output_dir (
            json_path ,
            time_analysis_root =self .state .work_dir if self .state .work_dir else None ,
            )
            png_path =time_charts .render_thread_total_time_png (metrics ,output_dir =out_dir )
            self ._display_image (png_path )
            self ._show_message ("Success",f"Generatedstatisticsgraph：\n{png_path}")
        except Exception as e :
            self ._show_message ("Error",f"generatestatisticsgraphfailed:\n{e}",is_error =True )

    def _plot_thread_call_gantt (self ):
        """sub-features：threadcallgraph（Gantt chart，requires `thread_trace.json`）"""
        json_path =self ._pick_time_analysis_json ("Select thread_trace.json（time_analysis trace）")
        if not json_path :
            return 
        try :
            events =time_charts .load_trace_events (json_path )
            out_dir =time_charts .choose_time_analysis_output_dir (
            json_path ,
            time_analysis_root =self .state .work_dir if self .state .work_dir else None ,
            )
            png_path =time_charts .render_thread_gantt_png (events ,output_dir =out_dir )
            self ._display_image (png_path )
            self ._show_message ("Success",f"Generatedthreadcallgraph：\n{png_path}")
        except Exception as e :
            self ._show_message ("Error",f"generatethreadcallgraphfailed:\n{e}",is_error =True )

            # ===================== Helper methods: graph analysis =====================

    def _norm (self ,text :str )->str :
        """Normalize strings"""
        return text .strip ().replace ('"','')

    def _suffix_num (self ,name :str )->int :
        """Extract trailing digits from node names for sorting"""
        import re 
        match =re .search (r'(\d+)$',name )
        return int (match .group (1 ))if match else 0 

    def _parse_optional_meta (self ,parts :List [str ])->Tuple [Optional [int ],Optional [str ]]:
        """Parse the optional source-code line number and filename
        
        Format rules:
        - Column 4（parts[3]）：line number (integer). If conversion fails, treat it as a filename.
        - Column 5（parts[4]）：filename (string, optional). If present, it overrides the filename from Column 4.
        
        Reference:dag_describe.py line 362-377
        """
        line_no :Optional [int ]=None 
        file_name :Optional [str ]=None 
        if len (parts )>=4 :
            try :
                line_no =int (parts [3 ])
            except Exception :
                file_name =parts [3 ]
        if len (parts )>=5 :
            file_name =parts [4 ]
        return line_no ,file_name 

    def _read_dot_to_networkx (self ,dot_path :Path ):
        """Read the DOT file and convert it to a networkx graph, matching mycallypro."""
        if not nx :
            raise RuntimeError ("networkx is not installed; unable to parse the DOT file")

            # Prefer networkx loading; if it is incompatible with the pydot version, use a custom conversion
        try :
            graph =nx .DiGraph (nx .nx_pydot .read_dot (str (dot_path )))
            return nx .relabel_nodes (graph ,self ._norm )
        except Exception :
            pass 

            # Fallback 1: use pydot loading plus custom conversion to avoid `get_strict()` compatibility issues in `nx.nx_pydot.from_pydot`
        if pydot :
            pd_graphs =pydot .graph_from_dot_file (str (dot_path ))
            if not pd_graphs :
                raise RuntimeError ("pydot Unable to parse the DOT file")
            pdg =pd_graphs [0 ]
            G =nx .DiGraph ()
            # edge
            for e in pdg .get_edges ():
                src =self ._norm (e .get_source ())
                dst =self ._norm (e .get_destination ())
                G .add_edge (src ,dst )
                # node + attributes (retain at least `style`)
            for n in pdg .get_nodes ():
                name =self ._norm (n .get_name ())
                if name in ("node","graph","edge"):
                    continue 
                if name not in G :
                    G .add_node (name )
                attrs =n .get_attributes ()or {}
                style =attrs .get ("style")
                if style :
                    G .nodes [name ]["style"]=style 
            return G 

            # Fallback 2: minimal regex parsing that extracts only edges and node styles
        import re 
        EDGE_RE =re .compile (r'\"([^\"]+)\"\s*->\s*\"([^\"]+)\"')
        NODE_RE =re .compile (r'\"([^\"]+)\"\s*\[(.*?)\]')
        raw =Path (dot_path ).read_text (encoding ="utf-8",errors ="ignore")
        G =nx .DiGraph ()
        for m in EDGE_RE .finditer (raw ):
            G .add_edge (self ._norm (m .group (1 )),self ._norm (m .group (2 )))
        for m in NODE_RE .finditer (raw ):
            name =self ._norm (m .group (1 ))
            if name not in G :
                G .add_node (name )
            attrs =m .group (2 )
            if "style="in attrs :
            # Read `style=xxx` or `style="xxx"`
                sm =re .search (r'style\s*=\s*"?([a-zA-Z, ]+)"?',attrs )
                if sm :
                    G .nodes [name ]["style"]=sm .group (1 )
        return G 

    def _parse_mutex_from_txt (self ,txt_path :Path )->List [MutexRecord ]:
        """parse mutex information from circle.txt
        
        Use a stack-matching algorithm to pair lock and unlock
        Reference:dag_describe.py line 379-431
        """
        # Step 1: parse all mutex-lock-related entries
        entries :List [Tuple [str ,str ,str ,str ,Optional [int ],Optional [str ]]]=[]
        block =None 

        content =txt_path .read_text (encoding ='utf-8',errors ='ignore')
        for line in content .splitlines ():
            s =self ._norm (line )
            if not s :
                continue 
            if s =="mutex":
                block ="mutex"
                continue 
            if s =="semaphore":
                block ="sem"
                continue 
            if block !="mutex":
                continue 

            parts =s .split ()
            if len (parts )<3 :
                continue 

            func ,var ,idx =parts [0 ],parts [1 ],parts [2 ]
            line_no ,file_name =self ._parse_optional_meta (parts )

            lower =func .lower ()
            if "pthread_mutex_unlock"in lower or "/unlock"in lower :
                entries .append ((self ._norm (func ),var ,idx ,"unlock",line_no ,file_name ))
            elif "pthread_mutex_lock"in lower or "/lock"in lower :
                entries .append ((self ._norm (func ),var ,idx ,"lock",line_no ,file_name ))

                # Step 2: use a stack to pair lock and unlock
        stacks :Dict [str ,List [Tuple [str ,str ,Optional [int ],Optional [str ]]]]={}
        pairs :List [MutexRecord ]=[]

        for func ,var ,idx ,typ ,line_no ,file_name in entries :
            stacks .setdefault (idx ,[])
            if typ =="lock":
                stacks [idx ].append ((func ,var ,line_no ,file_name ))
            elif typ =="unlock"and stacks [idx ]:
                lock_func ,lock_var ,lock_line ,lock_file =stacks [idx ].pop ()
                # If variables differ, use the unlock variable
                if lock_var !=var :
                    lock_var =var 
                record =MutexRecord (
                lock =self ._norm (lock_func ),
                unlock =self ._norm (func ),
                var =lock_var ,
                idx =idx ,
                lock_line =lock_line ,
                unlock_line =line_no ,
                lock_file =lock_file ,
                unlock_file =file_name ,
                covered =[],
                )
                pairs .append (record )

        if not pairs :
            print ("⚠️  No paired mutex-lock records found")
            return []

        print (f"✅ Parsed {len(pairs)} mutex-lock pairings")
        return pairs 

    def _generate_mutex_dot (self ,G ,mutex_records :List [MutexRecord ])->str :
        """Generate DOT content with mutex-lock markers"""

        MUTEX_COLORS =[
        '#FFE0B2','#FFCCBC','#D1C4E9','#C5CAE9',
        '#BBDEFB','#B2DFDB','#C8E6C9','#F0F4C3',
        '#FFF9C4','#FFECB3','#FFCCBC','#D7CCC8'
        ]

        lines =['digraph G {']
        lines .append ('  rankdir=TB;')
        lines .append ('  node [shape=box, style=filled, fillcolor=white];')

        # Create mutex-lock subgraphs
        for i ,rec in enumerate (mutex_records ):
            if not rec .covered :
                continue 

            color =MUTEX_COLORS [i %len (MUTEX_COLORS )]
            lines .append (f'\n  subgraph cluster_mutex_{i} {{')
            lines .append (f'    label="Mutex {rec.var} ({rec.idx})";')
            lines .append (f'    style=filled;')
            lines .append (f'    fillcolor="{color}";')
            lines .append (f'    fontcolor=black;')

            for node in rec .covered :
                label =node 
                if node ==rec .lock :
                    label =f"{node}\\n[LOCK]"
                elif node ==rec .unlock :
                    label =f"{node}\\n[UNLOCK]"

                lines .append (f'    "{node}" [label="{label}"];')

            lines .append ('  }')

            # Add all edges
        lines .append ('\n  // Edges')
        for src ,dst in G .edges ():
            lines .append (f'  "{src}" -> "{dst}";')

        lines .append ('}')

        return '\n'.join (lines )

    def _parse_semaphore_from_txt (self ,txt_path :Path )->List [SemRecord ]:
        """parse semaphore information from circle.txt
        
        Use a dictionary keyed by ID to collect post and wait nodes
        Reference:dag_describe.py line 549-596
        """
        by_id :Dict [str ,Dict [str ,any ]]={}
        block =None 

        content =txt_path .read_text (encoding ='utf-8',errors ='ignore')
        for line in content .splitlines ():
            s =self ._norm (line )
            if not s :
                continue 
            if s =="mutex":
                block ="mutex"
                continue 
            if s =="semaphore":
                block ="sem"
                continue 
            if block !="sem":
                continue 

            parts =s .split ()
            if len (parts )<3 :
                continue 

            func ,var ,idx =parts [0 ],parts [1 ],parts [2 ]
            line_no ,file_name =self ._parse_optional_meta (parts )

            record =by_id .setdefault (
            idx ,
            {
            "post":None ,
            "wait":None ,
            "var":var ,
            "post_line":None ,
            "wait_line":None ,
            "post_file":None ,
            "wait_file":None ,
            },
            )

            if "sem_post"in func :
                record ["post"]=self ._norm (func )
                record ["post_line"]=line_no 
                record ["post_file"]=file_name 
            elif "sem_wait"in func :
                record ["wait"]=self ._norm (func )
                record ["wait_line"]=line_no 
                record ["wait_file"]=file_name 

                # Build the pairing list
        pairs :List [SemRecord ]=[]
        for idx ,info in by_id .items ():
            if info ["post"]and info ["wait"]:
                pairs .append (
                SemRecord (
                post =str (info ["post"]),
                wait =str (info ["wait"]),
                var =str (info ["var"]),
                idx =idx ,
                post_line =info .get ("post_line"),
                wait_line =info .get ("wait_line"),
                post_file =info .get ("post_file"),
                wait_file =info .get ("wait_file"),
                )
                )

        print (f"✅ Parsed {len(pairs)} semaphore pairings")
        return pairs 

    def _generate_semaphore_original (self ,G ,target_dir :Path ):
        """generateoriginalgraph+semaphoreedge"""
        lines =['digraph G {']
        lines .append ('  rankdir=LR;')
        lines .append ('  fontname="Microsoft YaHei";')
        lines .append ('  node [shape=box];')

        # allnode
        for node in G .nodes ():
            lines .append (f'  "{node}";')

            # Edges: distinguish normal edges from semaphore edges
        for src ,dst ,data in G .edges (data =True ):
            if data .get ('style')=='dashed':
                label =data .get ('label','')
                color =data .get ('color','#FF7043')
                lines .append (f'  "{src}" -> "{dst}" [style=dashed, color="{color}", label="{label}"];')
            else :
                lines .append (f'  "{src}" -> "{dst}";')

        lines .append ('}')

        dot_path =target_dir /"original.dot"
        dot_path .write_text ('\n'.join (lines ),encoding ='utf-8')

        png_path =target_dir /"original.png"
        subprocess .run (
        ["dot","-Gdpi=110","-Tpng",str (dot_path ),"-o",str (png_path )],
        check =True ,
        capture_output =True 
        )
        print (f"✅ generateoriginalgraph: {png_path}")
        self .cached_images ["original"]=png_path if png_path .exists ()else None 

    def _generate_semaphore_tarjan (self ,G ,sccs :List [set ],target_dir :Path ):
        """generateTarjan SCC graph"""
        lines =['digraph G {']
        lines .append ('  rankdir=LR;')
        lines .append ('  fontname="Microsoft YaHei";')
        lines .append ('  node [shape=box, style=filled];')

        color_map :Dict [str ,str ]={}
        for comp in sccs :
            color ="#%06x"%random .randint (0 ,0xFFFFFF )
            for node in comp :
                color_map [node ]=color 

        for node in G .nodes ():
            col =color_map .get (node ,"#B0BEC5")
            lines .append (f'  "{node}" [fillcolor="{col}"];')

            # edge
        for src ,dst ,data in G .edges (data =True ):
            if data .get ('style')=='dashed':
                lines .append (f'  "{src}" -> "{dst}" [style=dashed, color="#FF7043"];')
            else :
                lines .append (f'  "{src}" -> "{dst}";')

        lines .append ('}')

        dot_path =target_dir /"tarjan.dot"
        dot_path .write_text ('\n'.join (lines ),encoding ='utf-8')

        png_path =target_dir /"tarjan.png"
        subprocess .run (
        ["dot","-Gdpi=110","-Tpng",str (dot_path ),"-o",str (png_path )],
        check =True ,
        capture_output =True 
        )
        print (f"✅ generateTarjangraph: {png_path}")
        self .cached_images ["tarjan"]=png_path if png_path .exists ()else None 

    def _generate_semaphore_threads (self ,G ,sccs :List [set ],target_dir :Path ):
        """generatethread-group graph"""

        cycles :Dict [str ,Dict [str ,List [str ]]]={}
        idx =0 
        for comp in self .sccs :
            if len (comp )<=1 :
                continue 
            per_thread :Dict [str ,List [str ]]={}
            for node in comp :
                prefix =node .split ('/')[0 ]if '/'in node else 'Unknown'
                per_thread .setdefault (prefix ,[]).append (node )
            if len (per_thread )<=1 :
                continue 
            for t in per_thread :
                per_thread [t ]=sorted (per_thread [t ],key =self ._suffix_num )
            idx +=1 
            cycles [f"Cycle{idx}"]=dict (sorted (per_thread .items ()))

        self .cycle_data =cycles 

        node_colors :Dict [str ,str ]={}
        for node in G .nodes ():
            prefix =node .split ('/')[0 ]if '/'in node else 'Unknown'
            node_colors [node ]=self .thread_color_map .get (prefix ,'#CFD8DC')

        lines =['digraph G {']
        lines .append ('  rankdir=LR;')
        lines .append ('  fontname="Microsoft YaHei";')
        lines .append ('  node [shape=box, style=filled];')

        for src ,dst ,data in G .edges (data =True ):
            if data .get ('style')=='dashed':
                lines .append (f'  "{src}" -> "{dst}" [style=dashed, color="#FF7043"];')
            else :
                lines .append (f'  "{src}" -> "{dst}";')

        for cname ,per_thread in cycles .items ():
            lines .append (f'  subgraph cluster_{cname} {{')
            lines .append ('    style=dashed;')
            lines .append ('    color=gray;')
            lines .append (f'    label="{cname}";')
            for _ ,nodes in per_thread .items ():
                for node in nodes :
                    col =node_colors .get (node ,'#FFFFFF')
                    lines .append (f'    "{node}" [fillcolor="{col}"];')
            lines .append ('  }')

        for node ,col in node_colors .items ():
            lines .append (f'  "{node}" [fillcolor="{col}"];')

        lines .append ('}')

        dot_path =target_dir /"threads.dot"
        dot_path .write_text ('\n'.join (lines ),encoding ='utf-8')

        png_path =target_dir /"threads.png"
        subprocess .run (
        ["dot","-Gdpi=110","-Tpng",str (dot_path ),"-o",str (png_path )],
        check =True ,
        capture_output =True 
        )
        print (f"✅ generatethreadgraph: {png_path}")
        self .cached_images ["threads"]=png_path if png_path .exists ()else None 

    def show_semaphore_info (self ):
        """Display the semaphore pairing information list."""
        pairs =self .sem_records or self ._parse_semaphore_from_txt (self .state .txt_file )
        self .canvas .delete ("all")
        y =20 
        self .canvas .create_text (
        20 ,
        y ,
        anchor ="nw",
        text ="semaphore pairings（post → wait）",
        font =("Microsoft YaHei",14 ,"bold"),
        fill ="#000",
        )
        y +=36 
        if not pairs :
            self .canvas .create_text (
            20 ,
            y ,
            anchor ="nw",
            text ="No data available. Please load circle.txt or generate the semaphore graph.",
            font =("Consolas",12 ),
            fill ="#555",
            )
            return 

        for rec in pairs :
            extra =""
            file_info =rec .post_file or rec .wait_file 
            if file_info :
                extra +=f"  FILE: {file_info}"
            if rec .post_line is not None or rec .wait_line is not None :
                a =rec .post_line if rec .post_line is not None else "?"
                b =rec .wait_line if rec .wait_line is not None else "?"
                extra +=f"  LINES: {a} -> {b}"
            self .canvas .create_text (
            20 ,
            y ,
            anchor ="nw",
            text =f"ID={rec.idx}  VAR={rec.var}  {rec.post} -> {rec.wait}{extra}",
            font =("Consolas",11 ),
            fill ="#263238",
            )
            y +=24 

        if self .cycle_data :
            y +=20 
            self .canvas .create_text (
            20 ,
            y ,
            anchor ="nw",
            text ="Semaphore cycle data structure:",
            font =("Microsoft YaHei",13 ,"bold"),
            fill ="#000",
            )
            y +=28 
            for cname ,per_thread in self .cycle_data .items ():
                self .canvas .create_text (
                20 ,
                y ,
                anchor ="nw",
                text =f"{cname}:",
                font =("Consolas",11 ),
                fill ="#263238",
                )
                y +=20 
                for thread ,nodes in per_thread .items ():
                    self .canvas .create_text (
                    40 ,
                    y ,
                    anchor ="nw",
                    text =f"{thread}: {', '.join(nodes)}",
                    font =("Consolas",10 ),
                    fill ="#455A64",
                    )
                    y +=18 
        self .canvas .config (scrollregion =self .canvas .bbox (tk .ALL ))

    def show_thread_legend (self ):
        """Show Thread Color Legend。"""
        self .canvas .delete ("all")
        y =40 
        self .canvas .create_text (
        40 ,
        10 ,
        anchor ="nw",
        text ="Thread color legend",
        font =("Microsoft YaHei",14 ,"bold"),
        fill ="#212121",
        )
        if not self .thread_color_map :
            self .canvas .create_text (
            40 ,
            y ,
            anchor ="nw",
            text ="Please generate the semaphore graph first to compute thread colors.",
            font =("Consolas",12 ),
            fill ="#555",
            )
        else :
            for thread ,color in self .thread_color_map .items ():
                self .canvas .create_rectangle (40 ,y ,100 ,y +30 ,fill =color ,outline ="black")
                self .canvas .create_text (
                120 ,
                y +15 ,
                anchor ="w",
                text =thread ,
                font =("Microsoft YaHei",12 ),
                )
                y +=40 
        self .canvas .config (scrollregion =self .canvas .bbox (tk .ALL ))

        # ===================== Helper methods =====================

        # ===================== Canvas interaction =====================

    def _start_move (self ,event ):
        """Start dragging"""
        self .canvas .scan_mark (event .x ,event .y )

    def _on_move (self ,event ):
        """Drag the canvas"""
        self .canvas .scan_dragto (event .x ,event .y ,gain =1 )

    def _on_zoom (self ,event ):
        """Zoom image
        
        Mouse wheel up: zoom in
        Mouse wheel down: zoom out
        """
        if not self .original_image :
            return 

            # Determine the scroll direction
        if event .type ==tk .EventType .MouseWheel :
        # Windows/Mac
            delta =event .delta 
        else :
        # Linux (Button-4 = up, Button-5 = down)
            delta =120 if event .num ==4 else -120 

            # Compute the zoom factor
        scale_factor =1.1 if delta >0 else 0.9 

        # Limit the zoom range (0.1x ~ 10x)
        new_scale =self .canvas_scale *scale_factor 
        if new_scale <0.1 or new_scale >10.0 :
            return 

        self .canvas_scale =new_scale 

        # Re-render the image
        self ._refresh_canvas_image ()


def main ():
    """Main function"""
    root =tk .Tk ()
    app =MycallyplusGUIv3 (root )
    root .mainloop ()


if __name__ =="__main__":
    main ()
