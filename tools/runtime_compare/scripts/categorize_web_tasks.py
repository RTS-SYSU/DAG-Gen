#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations 

import argparse 
import os 
import shutil 
from dataclasses import dataclass 
from pathlib import Path 


@dataclass (frozen =True )
class Experiment :
    path :Path 
    name :str 
    algo :str 


def _list_subdirs (dir_path :Path )->list [str ]:
    if not dir_path .is_dir ():
        return []
    return sorted ([p .name for p in dir_path .iterdir ()if p .is_dir ()and not p .name .startswith (".")])


def infer_algo (exp_dir :Path )->str :
    baseline_dir =exp_dir /"baseline"
    prio_dir =exp_dir /"prio"

    baseline_subdirs =_list_subdirs (baseline_dir )
    if len (baseline_subdirs )==1 :
        return baseline_subdirs [0 ]

    if len (baseline_subdirs )>1 :
        prio_subdirs =set (_list_subdirs (prio_dir ))
        intersection =[x for x in baseline_subdirs if x in prio_subdirs ]
        if len (intersection )==1 :
            return intersection [0 ]
        return baseline_subdirs [0 ]

    prio_subdirs =_list_subdirs (prio_dir )
    if len (prio_subdirs )==1 :
        return prio_subdirs [0 ]

    raise ValueError (f"cannot infer algo (no subdir under baseline/prio): {exp_dir}")


def collect_experiments (web_tasks_dir :Path )->list [Experiment ]:
    experiments :list [Experiment ]=[]
    for exp_dir in sorted (web_tasks_dir .iterdir ()):
        if not exp_dir .is_dir ():
            continue 
        if not (exp_dir /"summary.json").is_file ():
            continue 
        algo =infer_algo (exp_dir )
        experiments .append (Experiment (path =exp_dir ,name =exp_dir .name ,algo =algo ))
    return experiments 


def copy_experiment (exp :Experiment ,dest_root :Path ,overwrite :bool )->tuple [bool ,Path ]:
    dest_dir =dest_root /exp .algo /exp .name 
    dest_dir .parent .mkdir (parents =True ,exist_ok =True )

    if dest_dir .exists ():
        if not overwrite :
            return False ,dest_dir 
        shutil .rmtree (dest_dir )

    shutil .copytree (exp .path ,dest_dir ,symlinks =True )

    for dirpath ,dirnames ,filenames in os .walk (dest_dir ):
        for name in dirnames +filenames :
            p =Path (dirpath )/name 
            try :
                os .chown (p ,os .getuid (),os .getgid ())
            except PermissionError :
                pass 
            try :
                os .chmod (p ,p .stat ().st_mode |0o200 )
            except PermissionError :
                pass 

    return True ,dest_dir 


def main ()->int :
    parser =argparse .ArgumentParser (
    description ="Copy and categorize runtime_compare web_tasks experiments by algo type."
    )
    parser .add_argument (
    "--src",
    default ="tools/runtime_compare/experimentresult/web_tasks",
    help ="Source web_tasks directory (default: tools/runtime_compare/experimentresult/web_tasks)",
    )
    parser .add_argument (
    "--dest",
    default ="experiment/zhang1experimentresult summary",
    help ="Destination root directory (default: experiment/zhang1experimentresult summary)",
    )
    parser .add_argument ("--overwrite",action ="store_true",help ="Overwrite existing destination folders")
    parser .add_argument ("--dry-run",action ="store_true",help ="Print actions without copying")
    args =parser .parse_args ()

    src_dir =Path (args .src ).expanduser ().resolve ()
    dest_root =Path (args .dest ).expanduser ().resolve ()

    experiments =collect_experiments (src_dir )
    if not experiments :
        print (f"No experiments found under: {src_dir}")
        return 1 

    copied =0 
    skipped =0 
    for exp in experiments :
        dest_dir =dest_root /exp .algo /exp .name 
        if args .dry_run :
            action ="COPY"if (args .overwrite or not dest_dir .exists ())else "SKIP"
            print (f"{action} {exp.path} -> {dest_dir}")
            continue 

        did_copy ,out_dir =copy_experiment (exp ,dest_root ,overwrite =args .overwrite )
        if did_copy :
            copied +=1 
            print (f"COPIED {exp.name} -> {out_dir}")
        else :
            skipped +=1 
            print (f"SKIPPED {exp.name} (exists) -> {out_dir}")

    print (f"Done. copied={copied} skipped={skipped} total={len(experiments)}")
    return 0 


if __name__ =="__main__":
    raise SystemExit (main ())

