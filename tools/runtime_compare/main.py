#!/usr/bin/env python3
"""
Runtime Compare Tool - 主入口

支持三种模式：
- GUI 模式：python3 main.py --gui
- Web 模式：python3 main.py --web [--host 0.0.0.0] [--port 5000]
- CLI 模式：python3 main.py --cli [--config tasks.json] [--list] [--status] ...
"""

import argparse
import sys
from pathlib import Path

# 确保可以导入项目模块（从 tools/runtime_compare 向上两级到项目根）
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from tools.runtime_compare.config.defaults import WEB_HOST, WEB_PORT
from tools.runtime_compare.cli import main_cli, create_cli_parser
# Web 相关导入延迟到需要时再导入（避免 CLI 模式时导入 flask）


def main():
    parser = argparse.ArgumentParser(description='Runtime Compare Tool')
    
    # 模式选择（互斥）
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--gui', action='store_true', help='启动 GUI 模式（待实现）')
    mode_group.add_argument('--web', action='store_true', help='启动 Web 模式')
    mode_group.add_argument('--cli', action='store_true', help='启动 CLI 模式')
    
    # 通用参数
    parser.add_argument('--base-dir', type=Path, default=None, help='项目根目录（默认: 自动检测）')
    parser.add_argument('--queue-mode', action='store_true', help='启用单并发排队模式')
    
    # Web 模式参数
    parser.add_argument('--host', default=WEB_HOST, help=f'Web 服务器监听地址（默认: {WEB_HOST}）')
    parser.add_argument('--port', type=int, default=WEB_PORT, help=f'Web 服务器端口（默认: {WEB_PORT}）')
    
    # 如果指定了 --cli，使用 parse_known_args 避免解析 CLI 特有参数
    if '--cli' in sys.argv:
        args, unknown = parser.parse_known_args()
    else:
        args = parser.parse_args()
        unknown = []
    
    # 确定项目根目录
    if args.base_dir:
        base_dir = Path(args.base_dir).resolve()
    else:
        # 自动检测：从 tools/runtime_compare 向上两级到项目根
        base_dir = Path(__file__).parent.parent.parent.resolve()
    
    if args.cli:
        # CLI 模式：使用独立的参数解析器
        cli_parser = create_cli_parser()
        cli_args = cli_parser.parse_args(unknown)  # 解析剩余的参数
        cli_args.base_dir = args.base_dir or base_dir
        cli_args.queue_mode = args.queue_mode or cli_args.queue_mode
        sys.exit(main_cli(cli_args))
    
    elif args.web:
        # 延迟导入 Web 相关模块（需要 flask）
        from tools.runtime_compare.ui.web.server import run_server
        from tools.runtime_compare.ui.web.api import init_task_manager
        
        print(f"启动 Web 服务器...")
        print(f"  项目目录: {base_dir}")
        print(f"  监听地址: http://{args.host}:{args.port}")
        print(f"  排队模式: {'启用' if args.queue_mode else '禁用'}")
        
        # 初始化任务管理器
        init_task_manager(base_dir, queue_mode=args.queue_mode)
        
        # 启动服务器
        run_server(base_dir, host=args.host, port=args.port)
    
    elif args.gui:
        print("GUI 模式待实现...")
        # TODO: 实现 GUI 模式
        sys.exit(1)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == '__main__':
    main()
