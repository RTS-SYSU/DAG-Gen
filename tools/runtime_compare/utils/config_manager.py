"""配置文件管理模块"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from ..core.task import Task
from ..utils.datetime_utils import now_ts_safe


def save_config(
    tasks: List[Task],
    config_path: Optional[Path] = None,
    queue_mode: bool = False,
    mode: str = "append"
) -> Path:
    """保存任务配置到 JSON 文件
    
    Args:
        tasks: 任务列表
        config_path: 配置文件路径（如果为 None，自动生成）
        queue_mode: 是否启用排队模式
        mode: 保存模式，"append"（追加）或 "overwrite"（覆盖）
        
    Returns:
        配置文件路径
    """
    if config_path is None:
        # 自动生成路径：tools/runtime_compare/配置文件/tasks_<timestamp>.json
        tool_dir = Path(__file__).parent.parent  # utils -> runtime_compare
        config_dir = tool_dir / "配置文件"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / f"tasks_{now_ts_safe()}.json"
    
    config_path = Path(config_path).expanduser().resolve()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 转换为字典格式
    tasks_data = []
    for task in tasks:
        task_dict = {
            "baseline_c": str(task.baseline_c),
            "prio_c": str(task.prio_c),
            "work_scale": task.work_scale,
            "repeats": task.repeats,
            "cores_per_task": task.cores_per_task,
            "use_sudo": task.use_sudo,
        }
        if task.cpu_list:
            task_dict["cpu_list"] = task.cpu_list
        tasks_data.append(task_dict)
    
    config = {
        "tasks": tasks_data,
        "queue_mode": queue_mode,
        "created_at": datetime.now().isoformat(),
    }
    
    # 追加模式：读取现有配置，合并任务
    if mode == "append" and config_path.exists():
        try:
            existing = load_config(config_path)
            # 合并任务列表（去重）
            existing_task_ids = {
                (t["baseline_c"], t["prio_c"], t["work_scale"], t["repeats"], t["cores_per_task"])
                for t in existing.get("tasks", [])
            }
            new_tasks = [
                t for t in tasks_data
                if (t["baseline_c"], t["prio_c"], t["work_scale"], t["repeats"], t["cores_per_task"])
                not in existing_task_ids
            ]
            config["tasks"] = existing.get("tasks", []) + new_tasks
        except Exception:
            # 如果读取失败，使用覆盖模式
            pass
    
    # 写入文件
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    
    return config_path


def load_config(config_path: Path) -> Dict[str, Any]:
    """从 JSON 文件加载任务配置
    
    Args:
        config_path: 配置文件路径
        
    Returns:
        配置字典
    """
    config_path = Path(config_path).expanduser().resolve()
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    
    validate_config(config)
    return config


def validate_config(config: Dict[str, Any]) -> None:
    """验证配置文件格式
    
    Args:
        config: 配置字典
        
    Raises:
        ValueError: 如果配置格式无效
    """
    if not isinstance(config, dict):
        raise ValueError("配置文件必须是 JSON 对象")
    
    if "tasks" not in config:
        raise ValueError("配置文件缺少 'tasks' 字段")
    
    if not isinstance(config["tasks"], list):
        raise ValueError("'tasks' 必须是数组")
    
    required_fields = ["baseline_c", "prio_c", "work_scale", "repeats", "cores_per_task"]
    for i, task in enumerate(config["tasks"]):
        if not isinstance(task, dict):
            raise ValueError(f"任务 {i} 必须是对象")
        for field in required_fields:
            if field not in task:
                raise ValueError(f"任务 {i} 缺少必需字段: {field}")
        
        # 验证文件路径
        baseline = Path(task["baseline_c"]).expanduser()
        prio = Path(task["prio_c"]).expanduser()
        if not baseline.exists():
            raise ValueError(f"任务 {i} baseline_c 文件不存在: {baseline}")
        if not prio.exists():
            raise ValueError(f"任务 {i} prio_c 文件不存在: {prio}")


def tasks_from_config(config: Dict[str, Any], config_name: Optional[str] = None) -> List[Task]:
    """从配置字典创建 Task 对象列表
    
    Args:
        config: 配置字典
        config_name: 配置文件名（不含扩展名），用于结果目录命名
        
    Returns:
        Task 对象列表
    """
    from ..utils.datetime_utils import now_ts_safe
    
    tasks = []
    for task_data in config["tasks"]:
        baseline_c = Path(task_data["baseline_c"]).expanduser().resolve()
        prio_c = Path(task_data["prio_c"]).expanduser().resolve()
        
        task_id = f"{baseline_c.stem}_vs_{prio_c.stem}_{now_ts_safe()}"
        
        task = Task(
            task_id=task_id,
            baseline_c=baseline_c,
            prio_c=prio_c,
            work_scale=int(task_data["work_scale"]),
            repeats=int(task_data["repeats"]),
            cores_per_task=int(task_data["cores_per_task"]),
            use_sudo=bool(task_data.get("use_sudo", False)),
            cpu_list=task_data.get("cpu_list"),  # 可选
            config_name=config_name,  # 设置配置文件名
        )
        tasks.append(task)
    
    return tasks
