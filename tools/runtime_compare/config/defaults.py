"""默认配置"""

# 编译选项
GCC_FLAGS = ["-O0", "-g", "-std=c11", "-pthread", "-Wl,--wrap=main", "-lm"]

# 默认工作线程数
DEFAULT_MAX_WORKERS = 4

# 默认参数
DEFAULT_WORK_SCALE = 25000
DEFAULT_REPEATS = 1
DEFAULT_CORES_PER_TASK = 1

# Web 服务器配置
WEB_HOST = "0.0.0.0"  # 监听所有接口
WEB_PORT = 5000
WEB_DEBUG = False
