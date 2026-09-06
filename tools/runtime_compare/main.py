#!/usr/bin/env python3
"""
Runtime Compare Tool - main entry

Supports three modes:
- GUI mode：python3 main.py --gui
- Web mode：python3 main.py --web [--host 0.0.0.0] [--port 5000]
- CLI mode：python3 main.py --cli [--config tasks.json] [--list] [--status] ...
"""

import argparse 
import sys 
from pathlib import Path 

# Ensure project modules can be imported (two levels up from tools/runtime_compare to the project root)
# `resolve()` must be called first here; otherwise running `main.py` with a relative path may compute the wrong project-root directory.
project_root =Path (__file__ ).resolve ().parent .parent .parent 
sys .path .insert (0 ,str (project_root ))

from tools .runtime_compare .config .defaults import WEB_HOST ,WEB_PORT 
from tools .runtime_compare .cli import main_cli ,create_cli_parser 
# Web Delay related imports until needed (import flask in avoid CLI mode)

def _prompt_results_root (default_root :Path )->Path :
    """Interactively select/create the experiment-results directory (CLI scenario)."""
    if not sys .stdin .isatty ():
        return default_root 

    print ("\nexperimentresultsavedirectory：")
    print (f"  1) usedefaultdirectory: {default_root}")
    print ("  2) Enter an existing directory path (or a new path, which will be created automatically)")
    print ("  3) Create a subdirectory under the default directory and use it")
    choice =(input ("Please select [1/2/3] (default 1): ").strip ()or "1")

    if choice =="2":
        p =input ("Enter the directory path: ").strip ()
        if not p :
            return default_root 
        path =Path (p ).expanduser ()
        if not path .is_absolute ():
        # Resolve relative paths from the parent of the default directory to avoid unexpected locations
            path =(default_root .parent /path ).resolve ()
        else :
            path =path .resolve ()
        path .mkdir (parents =True ,exist_ok =True )
        return path 

    if choice =="3":
        name =input ("Please enter the new subdirectory name:").strip ()
        if not name :
            return default_root 
            # Simple safeguard: forbid path separators
        if any (sep in name for sep in ("/","\\"))or name in (".","..")or ".."in name :
            print ("Invalid directory name; falling back to the default directory.")
            return default_root 
        path =(default_root /name ).resolve ()
        path .mkdir (parents =True ,exist_ok =True )
        return path 

    return default_root 


def main ():
    parser =argparse .ArgumentParser (description ='Runtime Compare Tool')

    # Mode selection (mutually exclusive)
    mode_group =parser .add_mutually_exclusive_group (required =True )
    mode_group .add_argument ('--gui',action ='store_true',help ='Start GUI mode（not implemented yet）')
    mode_group .add_argument ('--web',action ='store_true',help ='Start Web mode')
    mode_group .add_argument ('--cli',action ='store_true',help ='Start CLI mode')

    # Common parameters
    parser .add_argument ('--base-dir',type =Path ,default =None ,help ='project root directory (default: auto-detect)')
    parser .add_argument ('--queue-mode',action ='store_true',help ='Enable single-concurrency queue mode')
    parser .add_argument ('--results-root',type =Path ,default =None ,help ='experimentresultroot directory（default: tools/runtime_compare/experimentresult）')
    parser .add_argument ('--pick-results-root',action ='store_true',help ='Interactive Select/createexperimentresultdirectory at Start (mainly used for CLI)')

    # Web mode parameters
    parser .add_argument ('--host',default =WEB_HOST ,help =f'Web server listen address（default: {WEB_HOST}）')
    parser .add_argument ('--port',type =int ,default =WEB_PORT ,help =f'Web server port（default: {WEB_PORT}）')

    # If --cli is specified, Use `parse_known_args` to avoid parsing CLI-specific arguments
    if '--cli'in sys .argv :
        args ,unknown =parser .parse_known_args ()
    else :
        args =parser .parse_args ()
        unknown =[]

        # Determine the project root directory
    if args .base_dir :
        base_dir =Path (args .base_dir ).resolve ()
    else :
    # Automatically detect by walking two levels up from tools/runtime_compare to project root
        base_dir =Path (__file__ ).parent .parent .parent .resolve ()

    tool_dir =Path (__file__ ).parent .resolve ()# tools/runtime_compare
    default_results_root =(tool_dir /"experimentresult").resolve ()
    results_root =args .results_root .expanduser ()if args .results_root else default_results_root 
    if not results_root .is_absolute ():
        results_root =(tool_dir /results_root ).resolve ()
    else :
        results_root =results_root .resolve ()
    if args .pick_results_root :
        results_root =_prompt_results_root (results_root )

    if args .cli :
    # CLI mode: use independent parameter parser
        cli_parser =create_cli_parser ()
        cli_args =cli_parser .parse_args (unknown )# parse the remaining arguments
        cli_args .base_dir =args .base_dir or base_dir 
        cli_args .queue_mode =args .queue_mode or cli_args .queue_mode 
        cli_args .results_root =results_root 
        sys .exit (main_cli (cli_args ))

    elif args .web :
    # Delayed import of web-related modules (need flask)
        from tools .runtime_compare .ui .web .server import run_server 
        from tools .runtime_compare .ui .web .api import init_task_manager 

        print (f"Starting the web server...")
        print (f"  projectdirectory: {base_dir}")
        print (f"  Listen address: http://{args.host}:{args.port}")
        print (f"  Queue mode: {'enabled' if args.queue_mode else 'disabled'}")
        print (f"  experimentresultdirectory: {results_root}")

        # initialize the task manager
        init_task_manager (base_dir ,queue_mode =args .queue_mode ,results_root =results_root )

        # Start the server
        run_server (base_dir ,host =args .host ,port =args .port )

    elif args .gui :
        print ("GUI modenot implemented yet...")
        # TODO: Implement GUI mode
        sys .exit (1 )

    else :
        parser .print_help ()
        sys .exit (1 )


if __name__ =='__main__':
    main ()
