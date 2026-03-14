from __future__ import annotations

"""API 路由"""

from flask import jsonify, request, render_template, send_file
from pathlib import Path
from typing import Dict, List
import os
import json
import platform
import subprocess
import shutil

from ...core.task import Task
from ...core.cpu_pool import CpuPool
from ...core.task_runner import TaskRunner
from ...config.defaults import DEFAULT_MAX_WORKERS
from ...utils.cpu import read_cpu_online, get_cpu_info, benchmark_core_speed
from ...utils.datetime_utils import now_ts_safe
from ...utils.config_manager import save_config, load_config, tasks_from_config
from ...utils.resume_state import apply_resume_to_task, default_resume_file


# 全局状态（在实际应用中应该使用更好的状态管理）
_task_manager: Dict = {
    'tasks': [],
    'task_q': None,
    'cpu_pool': None,
    'runners': [],
    'queue_mode': False,
    'serial_sem': None,
    'results_root': None,
}


def register_routes(app):
    """注册所有路由"""

    def _default_results_root() -> Path:
        tool_dir = Path(__file__).parent.parent.parent  # web -> ui -> runtime_compare
        return (tool_dir / "实验结果").resolve()

    def _get_results_root() -> Path:
        rr = _task_manager.get('results_root')
        if rr:
            try:
                return Path(rr).expanduser().resolve()
            except Exception:
                pass
        return _default_results_root()

    def _set_results_root(path: Path) -> Path:
        path = Path(path).expanduser()
        if not path.is_absolute():
            # 相对路径按工具目录解析，便于输入如：实验结果/xxx
            tool_dir = Path(__file__).parent.parent.parent
            path = (tool_dir / path).resolve()
        else:
            path = path.resolve()
        path.mkdir(parents=True, exist_ok=True)
        if not (path.exists() and path.is_dir()):
            raise ValueError(f"不是有效目录: {path}")
        if not os.access(str(path), os.W_OK | os.X_OK):
            raise PermissionError(f"目录不可写: {path}")
        _task_manager['results_root'] = path
        return path
    
    @app.route('/')
    def index():
        """主页"""
        return render_template('index.html')
    
    @app.route('/api/system', methods=['GET'])
    def get_system_info():
        """获取系统信息"""
        cpu_info = get_cpu_info()
        cpu_list = cpu_info['cpu_list']
        cpu_pool = _task_manager.get('cpu_pool')
        if cpu_pool:
            free_count = cpu_pool.free_count()
            total_count = cpu_pool.total_count()
        else:
            free_count = len(cpu_list)
            total_count = len(cpu_list)
        
        return jsonify({
            'cpu_online': cpu_list,
            'cpu_total': total_count,
            'cpu_free': free_count,
            'queue_mode': _task_manager.get('queue_mode', False),
            'cpu_info': cpu_info,
            'core_bench': benchmark_core_speed(cpu_list[:min(4, len(cpu_list))]) if cpu_list else {},
            'hostname': platform.node(),
            'results_root': str(_get_results_root()),
        })

    @app.route('/api/results-root', methods=['GET'])
    def get_results_root():
        """获取当前实验结果目录（后续任务生效）"""
        cur = _get_results_root()
        return jsonify({
            'results_root': str(cur),
            'default_root': str(_default_results_root()),
        }), 200

    @app.route('/api/results-root', methods=['POST'])
    def set_results_root():
        """设置实验结果目录（后续任务生效）"""
        try:
            data = request.get_json() or {}
            p = (data.get('path') or '').strip()
            if not p:
                return jsonify({'error': '缺少 path'}), 400
            new_rr = _set_results_root(Path(p))
            return jsonify({'results_root': str(new_rr)}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/results-root/new', methods=['POST'])
    def create_results_root():
        """在指定父目录下新建子目录并设为结果目录（后续任务生效）"""
        try:
            data = request.get_json() or {}
            parent = (data.get('parent') or '').strip()
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'error': '缺少 name'}), 400
            if any(sep in name for sep in ('/', '\\')) or name in ('.', '..') or '..' in name:
                return jsonify({'error': '目录名不合法'}), 400

            parent_path = Path(parent).expanduser() if parent else _get_results_root()
            if not parent_path.is_absolute():
                tool_dir = Path(__file__).parent.parent.parent
                parent_path = (tool_dir / parent_path).resolve()
            else:
                parent_path = parent_path.resolve()
            if not parent_path.exists() or not parent_path.is_dir():
                return jsonify({'error': f'父目录不存在: {parent_path}'}), 400

            new_dir = parent_path / name
            new_rr = _set_results_root(new_dir)
            return jsonify({'results_root': str(new_rr)}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 400

    @app.route('/api/system/save', methods=['POST'])
    def save_system_info():
        """保存系统信息到文件"""
        cpu_info = get_cpu_info()
        cpu_list = cpu_info.get('cpu_list', [])
        bench = benchmark_core_speed(cpu_list[:min(4, len(cpu_list))]) if cpu_list else {}

        payload = {
            'timestamp': now_ts_safe(),
            'hostname': platform.node(),
            'cpu_info': cpu_info,
            'core_bench': bench,
            'queue_mode': _task_manager.get('queue_mode', False),
        }

        tool_dir = Path(__file__).parent.parent.parent
        out_dir = tool_dir / "系统信息"
        out_dir.mkdir(parents=True, exist_ok=True)

        fname = f"{payload['timestamp']}_{payload['hostname'] or 'system'}.json"
        out_path = out_dir / fname
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')

        return jsonify({'status': 'saved', 'file': str(out_path)}), 201
    
    @app.route('/api/system/queue-mode', methods=['POST'])
    def set_queue_mode():
        """设置排队模式"""
        data = request.get_json() or {}
        queue_mode = bool(data.get('queue_mode', False))
        _task_manager['queue_mode'] = queue_mode
        return jsonify({
            'queue_mode': queue_mode,
            'status': 'updated'
        }), 200
    
    @app.route('/api/tasks', methods=['GET'])
    def get_tasks():
        """获取所有任务状态"""
        tasks = _task_manager.get('tasks', [])
        return jsonify({
            'tasks': [_task_to_dict(t) for t in tasks]
        })
    
    @app.route('/api/tasks', methods=['POST'])
    def add_task():
        """添加新任务"""
        data = request.get_json()
        
        # 验证必需字段
        required = ['baseline_c', 'prio_c', 'work_scale', 'repeats', 'cores_per_task']
        for field in required:
            if field not in data:
                return jsonify({'error': f'缺少必需字段: {field}'}), 400
        
        # 创建任务
        baseline_c = Path(data['baseline_c']).expanduser().resolve()
        prio_c = Path(data['prio_c']).expanduser().resolve()
        
        if not baseline_c.exists() or baseline_c.suffix.lower() != '.c':
            return jsonify({'error': 'baseline C 文件无效'}), 400
        if not prio_c.exists() or prio_c.suffix.lower() != '.c':
            return jsonify({'error': 'prio C 文件无效'}), 400
        
        task_id = f"{baseline_c.stem}_vs_{prio_c.stem}_{now_ts_safe()}"
        cpu_list = data.get('cpu_list')  # 可选：手动指定 CPU 核心
        
        task = Task(
            task_id=task_id,
            baseline_c=baseline_c,
            prio_c=prio_c,
            work_scale=int(data['work_scale']),
            repeats=int(data['repeats']),
            cores_per_task=int(data['cores_per_task']),
            use_sudo=bool(data.get('use_sudo', False)),
            cpu_list=cpu_list,
        )
        
        _task_manager['tasks'].append(task)
        _task_manager['task_q'].put(task)
        
        # 自动导出配置文件
        try:
            tool_dir = Path(__file__).parent.parent.parent  # web -> ui -> runtime_compare
            config_dir = tool_dir / "配置文件"
            config_dir.mkdir(parents=True, exist_ok=True)
            config_name = data.get('config_name')  # 可选：用户指定的配置名称
            if config_name:
                config_path = config_dir / f"{config_name}.json"
            else:
                config_path = config_dir / f"web_tasks_{now_ts_safe()}.json"
            
            save_config(
                _task_manager['tasks'],
                config_path,
                queue_mode=_task_manager['queue_mode'],
                mode="append"
            )
        except Exception as e:
            # 自动导出失败不影响任务添加，但记录错误
            import logging
            logging.warning(f"自动导出配置文件失败: {e}")
        
        return jsonify({'task_id': task_id, 'status': 'queued'}), 201

    @app.route('/api/fs/list', methods=['GET'])
    def list_filesystem():
        """列出目录内容（仅允许 BASE_DIR 范围）"""
        try:
            base_dir = Path(app.config['BASE_DIR']).resolve()
            req_path = (request.args.get('path') or "").strip()
            suffix = (request.args.get('suffix') or ".c").strip()

            if req_path:
                req = Path(req_path).expanduser()
                if req.is_absolute():
                    current = req.resolve()
                else:
                    current = (base_dir / req).resolve()
            else:
                current = base_dir

            try:
                current.relative_to(base_dir)
            except ValueError:
                return jsonify({'error': '路径超出允许范围'}), 400

            if not current.exists():
                return jsonify({'error': f'路径不存在: {current}'}), 404
            if not current.is_dir():
                if current.is_file():
                    current = current.parent
                else:
                    return jsonify({'error': f'不是目录: {current}'}), 400

            dirs = []
            files = []
            for child in sorted(current.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
                if child.is_dir():
                    dirs.append({'name': child.name, 'path': str(child)})
                elif child.is_file():
                    if not suffix or child.suffix.lower() == suffix.lower():
                        files.append({'name': child.name, 'path': str(child)})

            parent = None
            if current != base_dir:
                parent = str(current.parent)

            return jsonify({
                'base_dir': str(base_dir),
                'current': str(current),
                'parent': parent,
                'suffix': suffix,
                'dirs': dirs,
                'files': files,
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fs/pick-file', methods=['POST'])
    def pick_file_with_system_dialog():
        """调用系统文件管理器/文件选择器，返回选择的文件路径。"""
        try:
            base_dir = Path(app.config['BASE_DIR']).resolve()
            data = request.get_json() or {}
            suffix = (data.get('suffix') or '.c').strip()
            title = (data.get('title') or '选择文件').strip()

            # 优先使用系统文件选择器（Linux 常见桌面对话框）
            candidates = [
                ["zenity", "--file-selection", "--title", title],
                ["yad", "--file-selection", "--title", title],
                ["qarma", "--file-selection", "--title", title],
            ]
            if suffix:
                f = f"*{suffix}"
                candidates[0].extend(["--file-filter", f])
                candidates[1].extend(["--file-filter", f])
                candidates[2].extend(["--file-filter", f])

            picked = None
            for cmd in candidates:
                if not shutil.which(cmd[0]):  # type: ignore[name-defined]
                    continue
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode == 0 and proc.stdout.strip():
                    picked = proc.stdout.strip()
                    break

            # 回退：tk 文件对话框（仅在有桌面会话时尝试）
            if not picked and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                try:
                    import tkinter as tk  # 延迟导入，避免无 GUI 环境报错
                    from tkinter import filedialog

                    root = tk.Tk()
                    root.withdraw()
                    patterns = [(f"*{suffix} 文件", f"*{suffix}")] if suffix else [("所有文件", "*.*")]
                    picked_tmp = filedialog.askopenfilename(
                        title=title,
                        initialdir=str(base_dir),
                        filetypes=patterns,
                    )
                    root.destroy()
                    if picked_tmp:
                        picked = picked_tmp
                except Exception:
                    picked = None

            if not picked:
                return jsonify({'error': '未选择文件或系统文件选择器不可用'}), 400

            p = Path(picked).expanduser().resolve()
            if suffix and p.suffix.lower() != suffix.lower():
                return jsonify({'error': f'请选择 {suffix} 文件'}), 400
            return jsonify({'path': str(p)}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/api/fs/pick-dir', methods=['POST'])
    def pick_dir_with_system_dialog():
        """调用系统目录选择器，返回选择的目录路径。"""
        try:
            base_dir = Path(app.config['BASE_DIR']).resolve()
            data = request.get_json() or {}
            title = (data.get('title') or '选择目录').strip()

            candidates = [
                ["zenity", "--file-selection", "--directory", "--title", title],
                ["yad", "--file-selection", "--directory", "--title", title],
                ["qarma", "--file-selection", "--directory", "--title", title],
            ]

            picked = None
            for cmd in candidates:
                if not shutil.which(cmd[0]):
                    continue
                proc = subprocess.run(cmd, capture_output=True, text=True)
                if proc.returncode == 0 and proc.stdout.strip():
                    picked = proc.stdout.strip()
                    break

            if not picked and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
                try:
                    import tkinter as tk
                    from tkinter import filedialog

                    root = tk.Tk()
                    root.withdraw()
                    picked_tmp = filedialog.askdirectory(
                        title=title,
                        initialdir=str(base_dir),
                    )
                    root.destroy()
                    if picked_tmp:
                        picked = picked_tmp
                except Exception:
                    picked = None

            if not picked:
                return jsonify({'error': '未选择目录或系统目录选择器不可用'}), 400

            p = Path(picked).expanduser().resolve()
            if not p.exists() or not p.is_dir():
                return jsonify({'error': f'不是有效目录: {p}'}), 400
            return jsonify({'path': str(p)}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/tasks/<task_id>', methods=['DELETE'])
    def cancel_task(task_id):
        """取消任务（queued 或 running）"""
        tasks = _task_manager.get('tasks', [])
        for task in tasks:
            if task.task_id == task_id:
                if task.status in ('done', 'error', 'cancelled'):
                    return jsonify({'error': f'任务已结束，无法取消: {task.status}'}), 400
                if task.status == 'queued':
                    task.status = 'cancelled'
                    task.phase = 'cancelled'
                    task.cancel_requested = True
                    task.cancel_evt.set()
                    task.cancel_reason = '用户取消'
                    task.message = '用户取消'
                    return jsonify({'status': 'cancelled'}), 200
                if task.status in ('running', 'cancelling'):
                    task.status = 'cancelling'
                    task.cancel_requested = True
                    task.cancel_evt.set()
                    task.cancel_reason = '用户取消'
                    task.message = '用户取消，正在停止...'
                    return jsonify({'status': 'cancelling'}), 200
                task.status = 'cancelled'
                task.phase = 'cancelled'
                task.cancel_requested = True
                task.cancel_evt.set()
                task.cancel_reason = '用户取消'
                task.message = '用户取消'
                return jsonify({'status': 'cancelled'}), 200
        return jsonify({'error': '任务不存在'}), 404
    
    @app.route('/api/tasks/<task_id>/log', methods=['GET'])
    def get_task_log(task_id):
        """获取任务日志"""
        tasks = _task_manager.get('tasks', [])
        for task in tasks:
            if task.task_id == task_id and task.out_dir:
                log_file = task.out_dir / 'run.log'
                if log_file.exists():
                    return log_file.read_text(encoding='utf-8'), 200, {'Content-Type': 'text/plain'}
        return jsonify({'error': '日志不存在'}), 404
    
    # ========== 配置文件管理 API ==========
    
    def _get_config_dir() -> Path:
        """获取配置文件目录"""
        tool_dir = Path(__file__).parent.parent.parent  # web -> ui -> runtime_compare
        config_dir = tool_dir / "配置文件"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir
    
    @app.route('/api/config/list', methods=['GET'])
    def list_configs():
        """列出所有配置文件"""
        try:
            config_dir = _get_config_dir()
            configs = []
            for f in sorted(config_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                stat = f.stat()
                configs.append({
                    'filename': f.name,
                    'size': stat.st_size,
                    'modified': stat.st_mtime,
                    'path': str(f),
                })
            return jsonify({'configs': configs})
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config/download/<filename>', methods=['GET'])
    def download_config(filename):
        """下载配置文件"""
        try:
            config_dir = _get_config_dir()
            config_path = config_dir / filename
            if not config_path.exists() or not config_path.is_file():
                return jsonify({'error': '配置文件不存在'}), 404
            return send_file(str(config_path), as_attachment=True, download_name=filename)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config/delete/<filename>', methods=['DELETE'])
    def delete_config(filename):
        """删除配置文件"""
        try:
            config_dir = _get_config_dir()
            config_path = config_dir / filename
            if not config_path.exists():
                return jsonify({'error': '配置文件不存在'}), 404
            config_path.unlink()
            return jsonify({'status': 'deleted'}), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config/export', methods=['POST'])
    def export_config():
        """手动导出配置文件"""
        try:
            data = request.get_json() or {}
            config_name = data.get('config_name')  # 可选：用户指定的配置名称
            
            config_dir = _get_config_dir()
            if config_name:
                config_path = config_dir / f"{config_name}.json"
            else:
                config_path = config_dir / f"web_tasks_{now_ts_safe()}.json"
            
            tasks = _task_manager.get('tasks', [])
            save_config(
                tasks,
                config_path,
                queue_mode=_task_manager.get('queue_mode', False),
                mode="overwrite"  # 手动导出使用覆盖模式
            )
            
            return jsonify({
                'config_path': str(config_path),
                'filename': config_path.name,
                'download_url': f'/api/config/download/{config_path.name}'
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/config/import', methods=['POST'])
    def import_config():
        """导入配置文件"""
        try:
            # 支持文件上传或 JSON 数据
            if 'file' in request.files:
                file = request.files['file']
                if file.filename == '':
                    return jsonify({'error': '未选择文件'}), 400
                if not file.filename.endswith('.json'):
                    return jsonify({'error': '文件必须是 JSON 格式'}), 400

                # 保存到工具配置目录，保证断点续跑状态可持续
                config_dir = _get_config_dir()
                config_dir.mkdir(parents=True, exist_ok=True)
                safe_name = Path(file.filename).name
                config_path = (config_dir / safe_name).resolve()
                # 如同名存在，自动加时间戳避免覆盖用户文件
                if config_path.exists():
                    config_path = (config_dir / f"{Path(safe_name).stem}_{now_ts_safe()}.json").resolve()
                file.save(str(config_path))
            elif request.is_json:
                data = request.get_json()
                if 'config_path' in data:
                    config_path = Path(data['config_path']).expanduser().resolve()
                else:
                    return jsonify({'error': '需要提供文件或配置路径'}), 400
            else:
                return jsonify({'error': '需要提供文件或 JSON 数据'}), 400
            
            if not config_path.exists():
                return jsonify({'error': '配置文件不存在'}), 404
            
            # 加载配置
            config = load_config(config_path)
            config_name = config_path.stem  # 不含扩展名的文件名
            resume_file = default_resume_file(config_path)
            
            # 创建任务对象
            new_tasks = tasks_from_config(config, config_name=config_name, config_path=config_path)
            resumed = 0
            for t in new_tasks:
                ok, _ = apply_resume_to_task(t)
                if ok:
                    resumed += 1
            
            # 去重检查：检查是否已存在相同参数的任务
            existing_tasks = _task_manager.get('tasks', [])
            existing_keys = {
                (t.baseline_c, t.prio_c, t.work_scale, t.repeats, t.cores_per_task)
                for t in existing_tasks
            }
            
            added_count = 0
            queued_count = 0
            for task in new_tasks:
                task_key = (task.baseline_c, task.prio_c, task.work_scale, task.repeats, task.cores_per_task)
                if task_key not in existing_keys:
                    _task_manager['tasks'].append(task)
                    if task.status != "done":
                        _task_manager['task_q'].put(task)
                        queued_count += 1
                    existing_keys.add(task_key)
                    added_count += 1
            
            return jsonify({
                'imported': added_count,
                'total': len(new_tasks),
                'queued': queued_count,
                'resumed_done': resumed,
                'resume_file': str(resume_file),
                'message': f'成功导入 {added_count}/{len(new_tasks)} 个任务（已完成跳过 {resumed}，加入队列 {queued_count}）'
            }), 200
        except Exception as e:
            return jsonify({'error': str(e)}), 500


def _task_to_dict(task: Task) -> Dict:
    """将 Task 对象转换为字典"""
    elapsed = ""
    if task.start_ns:
        end = task.end_ns if task.end_ns else None
        if end:
            elapsed = f"{(end - task.start_ns) / 1e9:.1f}s"
    
    return {
        'task_id': task.task_id,
        'status': task.status,
        'phase': task.phase,
        'progress': f"{task.progress_i}/{task.progress_n}" if task.progress_n else "",
        'cpu_set': task.cpu_set,
        'elapsed': elapsed,
        'message': task.message,
        'out_dir': str(task.out_dir) if task.out_dir else "",
        'baseline_c': str(task.baseline_c),
        'prio_c': str(task.prio_c),
        'work_scale': task.work_scale,
        'repeats': task.repeats,
        'cores_per_task': task.cores_per_task,
    }


def init_task_manager(base_dir: Path, queue_mode: bool = False, results_root: Path | None = None):
    """初始化任务管理器
    
    Args:
        base_dir: 项目根目录
        queue_mode: 是否启用排队模式
        results_root: 实验结果根目录（可选）
    """
    import threading
    from queue import Queue
    
    cpu_list = read_cpu_online()
    cpu_pool = CpuPool(cpu_list)
    task_q: Queue[Task] = Queue()
    tasks: List[Task] = []
    serial_sem = threading.Semaphore(1)
    
    # 先创建 _task_manager，这样 queue_mode_fn 可以访问它
    tool_dir = Path(__file__).parent.parent.parent  # web -> ui -> runtime_compare
    rr = Path(results_root).expanduser() if results_root else (tool_dir / "实验结果")
    if not rr.is_absolute():
        rr = (tool_dir / rr).resolve()
    else:
        rr = rr.resolve()
    rr.mkdir(parents=True, exist_ok=True)

    _task_manager.update({
        'tasks': tasks,
        'task_q': task_q,
        'cpu_pool': cpu_pool,
        'runners': [],
        'queue_mode': queue_mode,
        'serial_sem': serial_sem,
        'results_root': rr,
    })
    
    def queue_mode_fn():
        # 动态读取当前排队模式设置
        return _task_manager.get('queue_mode', False)

    def results_root_fn():
        return _task_manager.get('results_root') or rr
    
    def on_update(task: Task):
        # Web 模式下，更新通过 API 查询，这里可以留空或记录日志
        pass
    
    # 启动工作线程
    max_workers = min(DEFAULT_MAX_WORKERS, max(1, len(cpu_list)))
    runners: List[TaskRunner] = []
    for _ in range(max_workers):
        r = TaskRunner(
            base_dir=base_dir,
            cpu_pool=cpu_pool,
            task_q=task_q,
            on_update=on_update,
            serial_sem=serial_sem,
            queue_mode_fn=queue_mode_fn,
            results_root_fn=results_root_fn,
        )
        r.start()
        runners.append(r)
    
    # 更新 runners 列表
    _task_manager['runners'] = runners
