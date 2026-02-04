"""CLI 命令行模式"""

import argparse
import logging
import sys
import time
from pathlib import Path
from queue import Queue
from typing import List, Optional

from .core.task import Task
from .core.cpu_pool import CpuPool
from .core.task_runner import TaskRunner
from .config.defaults import DEFAULT_MAX_WORKERS
from .utils.cpu import read_cpu_online
from .utils.config_manager import load_config, tasks_from_config, save_config
from .utils.file_ops import ensure_dir


class CLIManager:
    """CLI 模式管理器"""
    
    def __init__(self, base_dir: Path, queue_mode: bool = False):
        """初始化 CLI 管理器
        
        Args:
            base_dir: 项目根目录
            queue_mode: 是否启用排队模式
        """
        self.base_dir = base_dir
        self.queue_mode = queue_mode
        
        # 计算工具目录路径（tools/runtime_compare/）
        self.tool_dir = Path(__file__).parent.resolve()
        
        # 初始化 CPU 池和任务队列
        self.cpu_list = read_cpu_online()
        self.cpu_pool = CpuPool(self.cpu_list)
        self.task_q: Queue[Task] = Queue()
        self.tasks: List[Task] = []
        
        # 串行信号量
        import threading
        self.serial_sem = threading.Semaphore(1)
        
        # 日志目录（在工具目录下）
        self.log_dir = self.tool_dir / "实验结果" / "logs"
        ensure_dir(self.log_dir)
        
        # 设置日志
        self._setup_logging()
        
        # 启动工作线程
        self.runners: List[TaskRunner] = []
        max_workers = min(DEFAULT_MAX_WORKERS, max(1, len(self.cpu_list)))
        for i in range(max_workers):
            r = TaskRunner(
                base_dir=self.base_dir,
                cpu_pool=self.cpu_pool,
                task_q=self.task_q,
                on_update=self._on_task_update,
                serial_sem=self.serial_sem,
                queue_mode_fn=lambda: self.queue_mode,
            )
            r.start()
            self.runners.append(r)
    
    def _setup_logging(self):
        """设置日志"""
        log_file = self.log_dir / "cli.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler(sys.stdout),
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def _on_task_update(self, task: Task):
        """任务更新回调"""
        self.logger.info(
            f"任务 {task.task_id}: {task.status} - {task.phase} - {task.message}"
        )
        if task.status in ("done", "error"):
            self.logger.info(f"任务 {task.task_id} 完成: {task.message}")
            if task.out_dir:
                self.logger.info(f"结果目录: {task.out_dir}")
    
    def load_from_config(self, config_path: Path) -> int:
        """从配置文件加载任务
        
        Args:
            config_path: 配置文件路径（可以是绝对路径、相对路径或文件名）
            
        Returns:
            加载的任务数量
        """
        # 处理配置文件路径：如果只是文件名或相对路径，尝试在配置文件目录查找
        config_path = Path(config_path).expanduser()
        if not config_path.is_absolute():
            # 尝试在配置文件目录查找
            config_dir = self.tool_dir / "配置文件"
            potential_path = config_dir / config_path
            if potential_path.exists():
                config_path = potential_path
            else:
                # 如果配置文件目录中不存在，尝试相对于当前工作目录
                config_path = config_path.resolve()
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        self.logger.info(f"加载配置文件: {config_path}")
        config = load_config(config_path)
        
        # 提取配置文件名（不含扩展名）
        config_name = config_path.stem
        
        # 设置排队模式
        if "queue_mode" in config:
            self.queue_mode = bool(config["queue_mode"])
            self.logger.info(f"排队模式: {'启用' if self.queue_mode else '禁用'}")
        
        # 创建任务（传递配置文件名）
        tasks = tasks_from_config(config, config_name=config_name)
        self.logger.info(f"从配置文件加载了 {len(tasks)} 个任务")
        
        # 添加到队列（串行执行）
        for task in tasks:
            self.tasks.append(task)
            self.task_q.put(task)
            self.logger.info(f"已添加任务: {task.task_id}")
        
        return len(tasks)
    
    def add_task(
        self,
        baseline_c: Path,
        prio_c: Path,
        work_scale: int,
        repeats: int,
        cores_per_task: int,
        cpu_list: Optional[List[int]] = None,
        use_sudo: bool = False,
    ) -> Task:
        """添加单个任务
        
        Args:
            baseline_c: baseline C 文件路径
            prio_c: prio C 文件路径
            work_scale: 工作负载规模
            repeats: 重复次数
            cores_per_task: 每任务核数
            cpu_list: 可选的手动指定 CPU 核心列表
            use_sudo: 是否使用 sudo
            
        Returns:
            创建的 Task 对象
        """
        from .utils.datetime_utils import now_ts_safe
        
        baseline_c = Path(baseline_c).expanduser().resolve()
        prio_c = Path(prio_c).expanduser().resolve()
        
        task_id = f"{baseline_c.stem}_vs_{prio_c.stem}_{now_ts_safe()}"
        task = Task(
            task_id=task_id,
            baseline_c=baseline_c,
            prio_c=prio_c,
            work_scale=work_scale,
            repeats=repeats,
            cores_per_task=cores_per_task,
            use_sudo=use_sudo,
            cpu_list=cpu_list,
        )
        
        self.tasks.append(task)
        self.task_q.put(task)
        self.logger.info(f"已添加任务: {task_id}")
        
        return task
    
    def list_tasks(self):
        """列出所有任务"""
        if not self.tasks:
            print("暂无任务")
            return
        
        print(f"\n任务列表（共 {len(self.tasks)} 个）:")
        print("-" * 100)
        print(f"{'任务ID':<40} {'状态':<10} {'阶段':<15} {'CPU':<15} {'消息':<30}")
        print("-" * 100)
        
        for task in self.tasks:
            cpu_str = ",".join(map(str, task.cpu_set)) if task.cpu_set else "-"
            print(
                f"{task.task_id:<40} {task.status:<10} {task.phase:<15} {cpu_str:<15} {task.message[:30]:<30}"
            )
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务（仅限 queued 状态）
        
        Args:
            task_id: 任务 ID
            
        Returns:
            是否成功取消
        """
        for task in self.tasks:
            if task.task_id == task_id:
                if task.status == "queued":
                    task.status = "cancelled"
                    self.logger.info(f"已取消任务: {task_id}")
                    return True
                else:
                    self.logger.warning(f"只能取消等待中的任务，当前状态: {task.status}")
                    return False
        self.logger.error(f"任务不存在: {task_id}")
        return False
    
    def status(self):
        """显示系统状态"""
        running = sum(1 for t in self.tasks if t.status == "running")
        queued = sum(1 for t in self.tasks if t.status == "queued")
        done = sum(1 for t in self.tasks if t.status == "done")
        error = sum(1 for t in self.tasks if t.status == "error")
        
        print(f"\n系统状态:")
        print(f"  在线 CPU: {len(self.cpu_list)} ({', '.join(map(str, self.cpu_list))})")
        print(f"  空闲 CPU: {self.cpu_pool.free_count()} / {self.cpu_pool.total_count()}")
        print(f"  排队模式: {'启用' if self.queue_mode else '禁用'}")
        print(f"\n任务统计:")
        print(f"  运行中: {running}")
        print(f"  等待中: {queued}")
        print(f"  已完成: {done}")
        print(f"  失败: {error}")
        print(f"  总计: {len(self.tasks)}")
    
    def wait_all(self):
        """等待所有任务完成"""
        self.logger.info("等待所有任务完成...")
        while True:
            running = [t for t in self.tasks if t.status in ("running", "queued")]
            if not running:
                break
            time.sleep(1)
        self.logger.info("所有任务已完成")
    
    def shutdown(self):
        """关闭管理器"""
        self.logger.info("关闭 CLI 管理器...")
        for runner in self.runners:
            runner.stop()
        for runner in self.runners:
            runner.join(timeout=2)


def main_cli(args):
    """CLI 主函数"""
    # 确定项目根目录
    if args.base_dir:
        base_dir = Path(args.base_dir).resolve()
    else:
        # 自动检测：从 tools/runtime_compare 向上两级
        base_dir = Path(__file__).parent.parent.parent.resolve()
    
    manager = CLIManager(base_dir, queue_mode=args.queue_mode)
    
    try:
        if args.config:
            # 从配置文件加载（load_from_config 会处理路径查找）
            config_path = Path(args.config)
            count = manager.load_from_config(config_path)
            print(f"已加载 {count} 个任务")
            
            # 等待所有任务完成（串行执行）
            if args.wait:
                manager.wait_all()
                manager.shutdown()
            else:
                print("任务已在后台运行")
                print("提示: 使用 --wait 选项等待任务完成，或使用 --status 查看状态")
                # 等待一小段时间让任务启动
                import time
                time.sleep(2)
                manager.shutdown()
        
        elif args.add_task:
            # 添加单个任务（从 JSON 文件）
            task_config = Path(args.add_task).expanduser().resolve()
            config = load_config(task_config)
            if len(config["tasks"]) != 1:
                print(f"错误: 任务配置文件应包含恰好 1 个任务，实际有 {len(config['tasks'])} 个")
                return 1
            task_data = config["tasks"][0]
            manager.add_task(
                baseline_c=task_data["baseline_c"],
                prio_c=task_data["prio_c"],
                work_scale=task_data["work_scale"],
                repeats=task_data["repeats"],
                cores_per_task=task_data["cores_per_task"],
                cpu_list=task_data.get("cpu_list"),
                use_sudo=task_data.get("use_sudo", False),
            )
            if args.wait:
                manager.wait_all()
                manager.shutdown()
            else:
                import time
                time.sleep(2)
                manager.shutdown()
        
        elif args.list:
            manager.list_tasks()
            manager.shutdown()
        
        elif args.cancel:
            result = manager.cancel_task(args.cancel)
            manager.shutdown()
            return 0 if result else 1
        
        elif args.status:
            manager.status()
            manager.shutdown()
        
        else:
            print("请指定操作（--config, --add-task, --list, --cancel, --status）")
            manager.shutdown()
            return 1
        
        return 0
    
    except KeyboardInterrupt:
        print("\n用户中断")
        manager.shutdown()
        return 1
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        manager.shutdown()
        return 1


def create_cli_parser():
    """创建 CLI 参数解析器"""
    parser = argparse.ArgumentParser(
        description="Runtime Compare Tool - CLI 模式",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 从配置文件加载任务
  python3 main.py --cli --config tasks.json --wait
  
  # 添加单个任务
  python3 main.py --cli --add-task task.json
  
  # 查看任务列表
  python3 main.py --cli --list
  
  # 查看系统状态
  python3 main.py --cli --status
  
  # 取消任务
  python3 main.py --cli --cancel <task_id>
        """
    )
    
    parser.add_argument("--base-dir", type=Path, help="项目根目录（默认: 自动检测）")
    parser.add_argument("--queue-mode", action="store_true", help="启用单并发排队模式")
    parser.add_argument("--wait", action="store_true", help="等待所有任务完成")
    
    # 操作选项（互斥）
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--config", type=Path, help="从配置文件加载任务")
    group.add_argument("--add-task", type=Path, help="添加单个任务（从 JSON 文件）")
    group.add_argument("--list", action="store_true", help="列出所有任务")
    group.add_argument("--cancel", type=str, help="取消任务（任务ID）")
    group.add_argument("--status", action="store_true", help="显示系统状态")
    
    return parser
