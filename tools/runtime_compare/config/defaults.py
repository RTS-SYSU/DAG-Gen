"""default configuration"""

# compile option
GCC_FLAGS =["-O0","-g","-std=c11","-pthread","-Wl,--wrap=main","-lm"]

# default number of working threads
DEFAULT_MAX_WORKERS =4 

# default parameter
DEFAULT_WORK_SCALE =25000 
DEFAULT_REPEATS =1 
DEFAULT_CORES_PER_TASK =1 

# Web server configuration
WEB_HOST ="0.0.0.0"# Listen on all interface
WEB_PORT =5000 
WEB_DEBUG =False 
