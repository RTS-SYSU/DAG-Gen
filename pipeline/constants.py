from __future__ import annotations

ALLOWED_LEVELS = {"level1", "level2", "level3"}
ALLOWED_VIEWS = {"single"}
STANDARD_KINDS = {"compute", "mutex_cs", "create", "join", "sem_wait", "sem_post"}

SCHEMA_VERSION = "1.0"

META_RUNNING = "running"
META_SUCCESS = "success"
META_FAILED = "failed"

RESULTS_ROOT_NAME = "intermediate_results"
FINAL_RESULTS_DIR_NAME = "results"
GEN_DIR_NAME = "dag_generation"
CONFIG_DIR_NAME = "config_files"
PIPELINE_DIR_NAME = "pipeline"
