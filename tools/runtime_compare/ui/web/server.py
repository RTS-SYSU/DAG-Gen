"""Flask Web 服务器"""

from flask import Flask
from pathlib import Path

from ...config.defaults import WEB_HOST, WEB_PORT, WEB_DEBUG


def create_app(base_dir: Path) -> Flask:
    """创建 Flask 应用
    
    Args:
        base_dir: 项目根目录
        
    Returns:
        Flask 应用实例
    """
    app = Flask(__name__, 
                template_folder=str(Path(__file__).parent / "templates"),
                static_folder=str(Path(__file__).parent / "static"))
    
    # 存储应用状态
    app.config['BASE_DIR'] = base_dir
    
    # 注册路由
    from .api import register_routes
    register_routes(app)
    
    return app


def run_server(base_dir: Path, host: str = WEB_HOST, port: int = WEB_PORT, debug: bool = WEB_DEBUG):
    """运行 Web 服务器
    
    Args:
        base_dir: 项目根目录
        host: 监听地址
        port: 监听端口
        debug: 是否启用调试模式
    """
    app = create_app(base_dir)
    app.run(host=host, port=port, debug=debug, threaded=True)
