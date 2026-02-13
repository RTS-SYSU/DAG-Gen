from __future__ import annotations

ALLOWED_LEVELS = {"level1", "level2", "level3"}
ALLOWED_VIEWS = {"single"}
STANDARD_KINDS = {"compute", "mutex_cs", "create", "join", "sem_wait", "sem_post"}

SCHEMA_VERSION = "1.0"

META_RUNNING = "running"
META_SUCCESS = "success"
META_FAILED = "failed"

RESULTS_ROOT_NAME = "中间结果"
GEN_DIR_NAME = "生成dag图"
CONFIG_DIR_NAME = "配置文件"
PIPELINE_DIR_NAME = "pipeline"
