"""任务数据类"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class Task:
    """实验任务"""
    
    task_id: str
    baseline_c: Path
    prio_c: Path
    work_scale: int
    repeats: int
    cores_per_task: int
    use_sudo: bool
    cpu_list: Optional[List[int]] = None  # 可选：手动指定 CPU 核心列表
    config_name: Optional[str] = None  # 可选：配置文件名（不含扩展名），用于结果目录命名
    
    status: str = "queued"  # queued|running|done|error
    message: str = ""
    cpu_set: List[int] = field(default_factory=list)
    start_ns: Optional[int] = None
    end_ns: Optional[int] = None
    
    out_dir: Optional[Path] = None
    
    # Progress detail: (phase, i, n)
    phase: str = "queued"
    progress_i: int = 0
    progress_n: int = 0
