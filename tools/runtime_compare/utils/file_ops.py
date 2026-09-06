"""File operation tool function"""

import os 
import subprocess 
from pathlib import Path 


def ensure_dir (p :Path )->None :
    """ensuredirectory exists"""
    p .mkdir (parents =True ,exist_ok =True )


def ensure_writable_dir (path :Path ,*,use_sudo :bool )->None :
    """ensuredirectory exists and is writable\n    \nIf directory is not writable and sudo is enabled, try to repair permissions.\n    \n    Args:\n        path: directorypath\nuse_sudo: whether to use sudo to repair permissions\n        \n    Raises:\nPermissionError: ifdirectory is not writable and cannot be repaired\n    """
    from .sudo import has_passwordless_sudo 

    try :
        path .mkdir (parents =True ,exist_ok =True )
    except PermissionError :
        pass 

    if path .exists ()and os .access (str (path ),os .W_OK |os .X_OK ):
        return 

        # Try to fix with root
    if os .geteuid ()==0 :
        try :
            path .mkdir (parents =True ,exist_ok =True )
            path .chmod (0o775 )
            return 
        except Exception :
            pass 

    if use_sudo and has_passwordless_sudo ():
        uid =os .getuid ()
        gid =os .getgid ()
        subprocess .run (["sudo","-n","mkdir","-p",str (path )],check =False ,stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
        subprocess .run (["sudo","-n","chown","-R",f"{uid}:{gid}",str (path )],check =False ,stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
        if path .exists ()and os .access (str (path ),os .W_OK |os .X_OK ):
            return 

    owner_hint =""
    try :
        st =path .stat ()
        owner_hint =f" (uid={st.st_uid}, gid={st.st_gid}, mode={oct(st.st_mode & 0o777)})"
    except Exception :
        pass 
    raise PermissionError (
    f"resultdirectory is not writable：{path}{owner_hint}。"
    f"Please delete the directory or execute: sudo chown -R {os.getuid()}:{os.getgid()} '{path}',"
    f"Or start this tool with sudo/enabled sudo (requires sudo -n without password)."
    )
