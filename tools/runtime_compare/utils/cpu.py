"""CPU-related utility functions"""

import os 
from pathlib import Path 
from typing import List ,Dict ,Optional ,Tuple 


def read_cpu_online ()->List [int ]:
    """Read the system online-CPU list
    
    Returns:
        Online CPUs ID list, e.g. `[0, 1, 2, 3]`
    """
    p =Path ("/sys/devices/system/cpu/online")
    if p .exists ():
        s =p .read_text (encoding ="utf-8",errors ="replace").strip ()
        cpus :List [int ]=[]
        for part in s .split (","):
            part =part .strip ()
            if not part :
                continue 
            if "-"in part :
                a ,b =part .split ("-",1 )
                try :
                    lo =int (a )
                    hi =int (b )
                except Exception :
                    continue 
                cpus .extend (list (range (lo ,hi +1 )))
            else :
                try :
                    cpus .append (int (part ))
                except Exception :
                    continue 
        cpus =sorted (set (cpus ))
        if cpus :
            return cpus 
    n =os .cpu_count ()or 1 
    return list (range (n ))


def format_cpu_set (cpus :List [int ])->str :
    """Format the CPU set as a string
    
    Args:
        cpus: CPU ID list
        
    Returns:
        Formatted string, e.g. `"0,1,2,3"`
    """
    return ",".join (str (x )for x in cpus )


def get_cpu_freq (cpu_id :int )->Optional [int ]:
    """Get the maximum CPU frequency (Hz)
    
    Args:
        cpu_id: CPU ID
        
    Returns:
        CPU Maximum frequency (Hz), or `None` if unavailable
    """
    freq_file =Path (f"/sys/devices/system/cpu/cpu{cpu_id}/cpufreq/cpuinfo_max_freq")
    if freq_file .exists ():
        try :
            freq_khz =int (freq_file .read_text (encoding ="utf-8",errors ="replace").strip ())
            return freq_khz *1000 # Convert to Hz
        except Exception :
            pass 
    return None 


def detect_cpu_clusters ()->Dict [str ,Dict ]:
    """Detect CPU clusters (big/little cores)
    
    Returns:
        Dictionary containing big/little core information, format:
        {
            'big': {'cpus': [4, 5, 6, 7], 'freq_hz': 2400000000},
            'little': {'cpus': [0, 1, 2, 3], 'freq_hz': 1800000000}
        }
        Return `None` if the distinction cannot be made
    """
    cpu_list =read_cpu_online ()
    if not cpu_list :
        return None 

        # Get the frequency of each CPU
    cpu_freqs :Dict [int ,int ]={}
    for cpu_id in cpu_list :
        freq =get_cpu_freq (cpu_id )
        if freq :
            cpu_freqs [cpu_id ]=freq 

    if not cpu_freqs :
        return None 

        # Group by frequency
    freq_groups :Dict [int ,List [int ]]={}
    for cpu_id ,freq in cpu_freqs .items ():
        if freq not in freq_groups :
            freq_groups [freq ]=[]
        freq_groups [freq ].append (cpu_id )

        # If there is only one group, big and little cores cannot be distinguished
    if len (freq_groups )<=1 :
        return None 

        # Sort by frequency; higher frequency means big cores
    sorted_freqs =sorted (freq_groups .keys (),reverse =True )

    # Use the highest-frequency group as big cores
    big_freq =sorted_freqs [0 ]
    big_cpus =sorted (freq_groups [big_freq ])

    # Treat the others as little cores (if multiple groups exist, merge all except the highest)
    little_cpus =[]
    little_freq =None 
    if len (sorted_freqs )>1 :
    # Use the lowest frequency as the representative frequency for little cores
        little_freq =sorted_freqs [-1 ]
        for freq in sorted_freqs [1 :]:
            little_cpus .extend (freq_groups [freq ])
        little_cpus =sorted (little_cpus )

    result ={
    'big':{
    'cpus':big_cpus ,
    'freq_hz':big_freq ,
    'freq_ghz':round (big_freq /1e9 ,2 )
    }
    }

    if little_cpus :
        result ['little']={
        'cpus':little_cpus ,
        'freq_hz':little_freq ,
        'freq_ghz':round (little_freq /1e9 ,2 )
        }

    return result 


def get_cpu_info ()->Dict :
    """Get full CPU information
    
    Returns:
        Dictionary containing the CPU list, cluster information, etc.
    """
    cpu_list =read_cpu_online ()
    clusters =detect_cpu_clusters ()

    # Get the frequency of each CPU
    cpu_freqs :Dict [int ,float ]={}
    for cpu_id in cpu_list :
        freq =get_cpu_freq (cpu_id )
        if freq :
            cpu_freqs [cpu_id ]=round (freq /1e9 ,2 )# Convert to GHz

    result ={
    'cpu_list':cpu_list ,
    'cpu_total':len (cpu_list ),
    'cpu_freqs':cpu_freqs ,
    'clusters':clusters ,
    'has_big_little':clusters is not None 
    }

    return result 


def recommend_test_params (cpu_info :Dict )->Dict :
    """Automatically recommend test parameters based on hardware

    Returns:
        {
            'platform': 'rk3588' | 'vm',
            'platform_label': str,
            'cores_per_task': int,
            'cpu_list': List[int],
            'reason': str,
        }
    """
    clusters =cpu_info .get ('clusters')
    cpu_list_all =cpu_info .get ('cpu_list',[])
    total =len (cpu_list_all )

    if clusters and cpu_info .get ('has_big_little'):
        little =clusters .get ('little',{})
        big =clusters .get ('big',{})
        little_cpus =little .get ('cpus',[])
        big_cpus =big .get ('cpus',[])

        if len (little_cpus )>=2 :
            pick =little_cpus [:2 ]
            label =f"big.LITTLE (LITTLE cores x{len(little_cpus)} + big cores x{len(big_cpus)})"
            reason =f"Detected heterogeneous CPUs; select LITTLE cores {pick} to create contention (thread count > core count)"
        elif len (big_cpus )>=2 :
            pick =big_cpus [:2 ]
            label =f"big.LITTLE (big cores x{len(big_cpus)} + LITTLE cores x{len(little_cpus)})"
            reason =f"Detected heterogeneous CPUs; select big cores {pick} manufacturing competition"
        else :
            pick =cpu_list_all [:2 ]if total >=2 else cpu_list_all [:1 ]
            label ="big.LITTLE (insufficient core count, degraded)"
            reason ="Each heterogeneous group has fewer than 2 cores; use the first 2 cores"

        return {
        'platform':'rk3588',
        'platform_label':label ,
        'cores_per_task':len (pick ),
        'cpu_list':pick ,
        'reason':reason ,
        }

        # Homogeneous (VM / desktop)
    if total >=4 :
        pick_n =total //2 
        pick =cpu_list_all [:pick_n ]
    elif total >=2 :
        pick =cpu_list_all [:2 ]
    else :
        pick =cpu_list_all [:1 ]

    return {
    'platform':'vm',
    'platform_label':f"Homogeneous CPU ({total} core)",
    'cores_per_task':len (pick ),
    'cpu_list':pick ,
    'reason':f"Homogeneous architecture, use {len(pick)}/{total}  cores to create thread contention",
    }


def _bench_loop (iterations :int =1_000_000 )->int :
    """Simple nested loops for benchmarking; return the iteration count"""
    s =0 
    for i in range (iterations ):
        s +=(i ^(s <<1 ))&0xFFFFFFFF 
    return iterations 


def benchmark_core_speed (sample_cpus :List [int ],duration_ms :int =80 )->Dict [int ,float ]:
    """Run a lightweight benchmark on the specified CPU and estimate MOPS
    
    Args:
        sample_cpus: CPU list to test
        duration_ms: Minimum runtime per CPU (milliseconds)
    
    Returns:
        Dictionary: `{cpu_id: mops_value}`
    """
    import time 

    results :Dict [int ,float ]={}
    original_affinity :Optional [set ]=None 

    for cpu in sample_cpus :
        try :
            if hasattr (os ,"sched_getaffinity"):
                original_affinity =os .sched_getaffinity (0 )
                os .sched_setaffinity (0 ,{cpu })
        except Exception :
            original_affinity =None 

        start =time .perf_counter ()
        iters =0 
        # Run until the target time is exceeded
        while True :
            iters +=_bench_loop (200_000 )
            if (time .perf_counter ()-start )*1000 >=duration_ms :
                break 
        elapsed =time .perf_counter ()-start 
        if elapsed >0 :
            mops =(iters /elapsed )/1e6 
            results [cpu ]=round (mops ,2 )
        try :
            if original_affinity is not None and hasattr (os ,"sched_setaffinity"):
                os .sched_setaffinity (0 ,original_affinity )
        except Exception :
            pass 
    return results 
