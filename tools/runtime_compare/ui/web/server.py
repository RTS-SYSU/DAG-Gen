"""Flask Web server"""

from flask import Flask 
from pathlib import Path 

from ...config .defaults import WEB_HOST ,WEB_PORT ,WEB_DEBUG 


def create_app (base_dir :Path )->Flask :
    """create Flask application\n    \n    Args:\n        base_dir: projectroot directory\n        \n    Returns:\nFlask application example\n    """
    app =Flask (__name__ ,
    template_folder =str (Path (__file__ ).parent /"templates"),
    static_folder =str (Path (__file__ ).parent /"static"))

    # Storage application status
    app .config ['BASE_DIR']=base_dir 

    # Register route
    from .api import register_routes 
    register_routes (app )

    return app 


def run_server (base_dir :Path ,host :str =WEB_HOST ,port :int =WEB_PORT ,debug :bool =WEB_DEBUG ):
    """Run the web server\n    \n    Args:\n        base_dir: projectroot directory\nhost: listening address\nport: listening port\ndebug: whether to enable debug mode\n    """
    app =create_app (base_dir )
    app .run (host =host ,port =port ,debug =debug ,threaded =True )
