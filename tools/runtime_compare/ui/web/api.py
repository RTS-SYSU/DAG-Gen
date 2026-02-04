"""API 路由"""

from flask import jsonify, request, render_template, send_file
from pathlib import Path
from typing import Dict, List
import os
import json
import platform

from ...core.task import Task
from ...core.cpu_pool import CpuPool
from ...core.task_runner import TaskRunner
from ...config.defaults import DEFAULT_MAX_WORKERS
from ...utils.cpu import read_cpu_online, get_cpu_info, benchmark_core_speed
from ...utils.datetime_utils import now_ts_safe
from ...utils.config_manager import save_config, load_config, tasks_from_config


# 全局状态（在实际应用中应该使用更好的状态管理）
_task_manager: Dict = {
    'tasks': [],
    'task_q': None,
    'cpu_pool': None,
    'runners': [],
    'queue_mode': False,
    'serial_sem': None,
}


def register_routes(app):
    """注册所有路由"""
    
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
        })

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
    
    @app.route('/api/tasks/<task_id>', methods=['DELETE'])
    def cancel_task(task_id):
        """取消任务（仅限 queued 状态）"""
        tasks = _task_manager.get('tasks', [])
        for task in tasks:
            if task.task_id == task_id:
                if task.status == 'queued':
                    task.status = 'cancelled'
                    return jsonify({'status': 'cancelled'}), 200
                else:
                    return jsonify({'error': '只能取消等待中的任务'}), 400
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
                
                # 保存临时文件
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                    file.save(tmp.name)
                    config_path = Path(tmp.name)
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
            
            # 创建任务对象
            new_tasks = tasks_from_config(config, config_name=config_name)
            
            # 去重检查：检查是否已存在相同参数的任务
            existing_tasks = _task_manager.get('tasks', [])
            existing_keys = {
                (t.baseline_c, t.prio_c, t.work_scale, t.repeats, t.cores_per_task)
                for t in existing_tasks
            }
            
            added_count = 0
            for task in new_tasks:
                task_key = (task.baseline_c, task.prio_c, task.work_scale, task.repeats, task.cores_per_task)
                if task_key not in existing_keys:
                    _task_manager['tasks'].append(task)
                    _task_manager['task_q'].put(task)
                    existing_keys.add(task_key)
                    added_count += 1
            
            # 清理临时文件
            if 'file' in request.files:
                try:
                    config_path.unlink()
                except:
                    pass
            
            return jsonify({
                'imported': added_count,
                'total': len(new_tasks),
                'message': f'成功导入 {added_count}/{len(new_tasks)} 个任务'
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


def init_task_manager(base_dir: Path, queue_mode: bool = False):
    """初始化任务管理器
    
    Args:
        base_dir: 项目根目录
        queue_mode: 是否启用排队模式
    """
    import threading
    from queue import Queue
    
    cpu_list = read_cpu_online()
    cpu_pool = CpuPool(cpu_list)
    task_q: Queue[Task] = Queue()
    tasks: List[Task] = []
    serial_sem = threading.Semaphore(1)
    
    # 先创建 _task_manager，这样 queue_mode_fn 可以访问它
    _task_manager.update({
        'tasks': tasks,
        'task_q': task_q,
        'cpu_pool': cpu_pool,
        'runners': [],
        'queue_mode': queue_mode,
        'serial_sem': serial_sem,
    })
    
    def queue_mode_fn():
        # 动态读取当前排队模式设置
        return _task_manager.get('queue_mode', False)
    
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
        )
        r.start()
        runners.append(r)
    
    # 更新 runners 列表
    _task_manager['runners'] = runners
