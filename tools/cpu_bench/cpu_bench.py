#!/usr/bin/env python3
"""\nCore-by-core lightweight performance benchmark\n\n- Bound to each Online CPUs, running operation loop, estimating MOPS (million operations/seconds)\n- The result is printed to the console and saved to txt and json File under the current script directory.\n\nusage:\n  python3 cpu_bench.py\n"""

import json 
import os 
import time 
from pathlib import Path 


def read_cpu_online ():
    """Return the list of online CPUs."""
    p =Path ("/sys/devices/system/cpu/online")
    if p .exists ():
        s =p .read_text (encoding ="utf-8",errors ="replace").strip ()
        cpus =[]
        for part in s .split (","):
            part =part .strip ()
            if not part :
                continue 
            if "-"in part :
                a ,b =part .split ("-",1 )
                cpus .extend (range (int (a ),int (b )+1 ))
            else :
                cpus .append (int (part ))
        cpus =sorted (set (cpus ))
        if cpus :
            return cpus 
    n =os .cpu_count ()or 1 
    return list (range (n ))


def _bench_loop (iterations :int =200_000 )->int :
    """A simple bitwise operation loop that returns the number of iterations."""
    s =0 
    for i in range (iterations ):
        s +=(i ^(s <<1 ))&0xFFFFFFFF 
    return iterations 


def bench_cpu (cpu_id :int ,min_ms :int =200 )->float :
    """Run the benchmark on the specified CPU and return MOPS."""
    original =None 
    try :
        if hasattr (os ,"sched_getaffinity"):
            original =os .sched_getaffinity (0 )
            os .sched_setaffinity (0 ,{cpu_id })
    except Exception :
        original =None 

    start =time .perf_counter ()
    iters =0 
    while True :
        iters +=_bench_loop ()
        if (time .perf_counter ()-start )*1000 >=min_ms :
            break 
    elapsed =time .perf_counter ()-start 

    try :
        if original is not None and hasattr (os ,"sched_setaffinity"):
            os .sched_setaffinity (0 ,original )
    except Exception :
        pass 

    if elapsed ==0 :
        return 0.0 
    return round ((iters /elapsed )/1e6 ,2 )# MOPS


def main ():
    cpus =read_cpu_online ()
    print (f"Online CPUs: {cpus} (Total {len(cpus)} cores)")
    results ={}
    for cpu in cpus :
        mops =bench_cpu (cpu )
        results [cpu ]=mops 
        print (f"CPU {cpu}: {mops:.2f} MOPS")

        # Sort output summary by performance
    sorted_items =sorted (results .items (),key =lambda x :x [1 ],reverse =True )
    print ("\nSort by performance (MOPS):")
    for cpu ,mops in sorted_items :
        print (f"  CPU {cpu}: {mops:.2f}")

        # saveresult
    out_dir =Path (__file__ ).resolve ().parent 
    ts =time .strftime ("%Y%m%d_%H%M%S")
    txt_path =out_dir /f"cpu_bench_{ts}.txt"
    json_path =out_dir /f"cpu_bench_{ts}.json"

    txt_lines =[
    f"timestamp: {ts}",
    f"online_cpus: {cpus}",
    "results (MOPS):",
    ]
    txt_lines +=[f"CPU {cpu}: {results[cpu]:.2f}"for cpu in cpus ]
    txt_lines .append ("")
    txt_lines .append ("sorted:")
    txt_lines +=[f"CPU {cpu}: {mops:.2f}"for cpu ,mops in sorted_items ]
    txt_path .write_text ("\n".join (txt_lines ),encoding ="utf-8")

    json_path .write_text (
    json .dumps (
    {
    "timestamp":ts ,
    "online_cpus":cpus ,
    "results_mops":results ,
    "sorted":sorted_items ,
    },
    ensure_ascii =False ,
    indent =2 ,
    ),
    encoding ="utf-8",
    )

    print (f"\nSaversult: {txt_path.name}, {json_path.name}")


if __name__ =="__main__":
    main ()
