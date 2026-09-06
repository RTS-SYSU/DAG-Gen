"""sudo related tool functions"""

import os 
import subprocess 


def has_passwordless_sudo ()->bool :
    """Check whether you have password-free sudo permissions\n    \n    Returns:\nIf you have root permissions or password-free sudo, return True\n    """
    if os .geteuid ()==0 :
        return True 
    try :
        subprocess .run (["sudo","-n","true"],check =True ,stdout =subprocess .DEVNULL ,stderr =subprocess .DEVNULL )
        return True 
    except Exception :
        return False 
