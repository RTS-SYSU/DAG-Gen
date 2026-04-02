"""任务数据类"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional
import threading


@dataclass
class Task:
    """实验任务
    
    v3.0: 支持单文件模式（source_c + algo_name）
    兼容旧模式（baseline_c + prio_c），过渡期两种模式共存。
    """
    
    task_id: str
    # v3.0 新字段：单文件模式
    source_c: Optional[Path] = None       # 单文件模式的源文件路径
    algo_name: Optional[str] = None       # 算法名（CFS/FIFO/cpf/heft/...）
    # 旧字段：保留兼容性（过渡期）
    baseline_c: Optional[Path] = None
    prio_c: Optional[Path] = None
    
    work_scale: int = 100
    repeats: int = 10
    cores_per_task: int = 2
    use_sudo: bool = False
    cpu_list: Optional[List[int]] = None  # 可选：手动指定 CPU 核心列表
    config_name: Optional[str] = None  # 可选：配置文件名（不含扩展名），用于结果目录命名
    batch_name: Optional[str] = None   # 批量提交时的分组名（如 zhang1），用于结果子目录
    batch_ts: Optional[str] = None     # 批量提交时的统一时间戳，同一批次所有算法共用
    # 断点续跑：稳定 key + resume 状态文件
    task_key: Optional[str] = None
    resume_file: Optional[Path] = None
    
    status: str = "queued"  # queued|running|cancelling|cancelled|done|error
    message: str = ""
    cpu_set: List[int] = field(default_factory=list)
    start_ns: Optional[int] = None
    end_ns: Optional[int] = None
    
    out_dir: Optional[Path] = None
    
    # Progress detail: (phase, i, n)
    phase: str = "queued"
    progress_i: int = 0
    progress_n: int = 0

    # Cancellation (shared across threads)
    cancel_requested: bool = False
    cancel_reason: str = ""
    cancel_evt: threading.Event = field(default_factory=threading.Event, repr=False)

    @property
    def is_single_mode(self) -> bool:
        """是否为 v3.0 单文件模式"""
        return self.source_c is not None
