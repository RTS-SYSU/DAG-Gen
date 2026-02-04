Web UI 完整功能实现计划
目标
实现完整的 Web UI 功能，使其成为在 RK3588 板子上方便的任务配置和管理工具，支持：

便捷的任务添加和设置
自动和手动配置文件导出
配置文件导入
实时任务状态更新
更好的用户界面体验
架构概览
Web UI (Flask)
├── 前端 (HTML/JavaScript)
│   ├── 任务添加表单
│   ├── 任务列表（实时更新）
│   ├── 系统信息显示
│   ├── 配置文件管理（导入/导出）
│   └── 任务详情查看
└── 后端 API (Flask Routes)
    ├── 任务管理 API
    ├── 配置文件 API
    └── 系统信息 API
实现任务
1. 配置文件自动导出功能
文件: tools/runtime_compare/ui/web/api.py

在 add_task() 函数中，添加任务成功后自动调用 save_config() 保存当前所有任务到配置文件
配置文件保存到 tools/runtime_compare/配置文件/ 目录
命名规则：web_tasks_{timestamp}.json 或用户指定的名称
使用 mode="append" 模式，支持追加任务到现有配置
实现细节:

# 在 add_task() 成功后
from ...utils.config_manager import save_config
config_dir = Path(__file__).parent.parent.parent / "配置文件"
config_path = config_dir / f"web_tasks_{now_ts_safe()}.json"
save_config(_task_manager['tasks'], config_path, 
            queue_mode=_task_manager['queue_mode'], mode="append")
2. 配置文件手动导出 API
文件: tools/runtime_compare/ui/web/api.py

新增 /api/config/export POST 端点
支持指定配置文件名（可选）
返回导出文件的路径和下载链接
支持导出当前所有任务或指定任务列表
实现细节:

@app.route('/api/config/export', methods=['POST'])
def export_config():
    data = request.get_json() or {}
    config_name = data.get('config_name')  # 可选
    # ... 导出逻辑
    return jsonify({'config_path': str(config_path), 'download_url': f'/api/config/download/{filename}'})
3. 配置文件导入功能
文件: tools/runtime_compare/ui/web/api.py

新增 /api/config/import POST 端点
支持上传 JSON 配置文件
解析配置文件并验证格式
将配置中的任务添加到任务队列（不重复添加）
返回导入的任务数量
实现细节:

@app.route('/api/config/import', methods=['POST'])
def import_config():
    # 支持文件上传或 JSON 数据
    # 使用 load_config() 和 tasks_from_config()
    # 去重检查后添加到队列
4. 配置文件列表和下载 API
文件: tools/runtime_compare/ui/web/api.py

新增 /api/config/list GET 端点：列出所有配置文件
新增 /api/config/download/<filename> GET 端点：下载指定配置文件
新增 /api/config/delete/<filename> DELETE 端点：删除配置文件
5. 前端界面增强
文件: tools/runtime_compare/ui/web/templates/index.html

5.1 配置文件管理区域
添加新的 section，包含：

配置文件列表显示
"导入配置" 按钮（文件选择）
"导出配置" 按钮（手动导出）
"刷新配置列表" 按钮
配置文件下载链接
5.2 任务表单优化
添加 "配置名称" 输入框（用于命名导出的配置文件）
改进文件路径输入（支持相对路径提示）
添加表单验证和错误提示
显示自动导出状态提示
5.3 任务列表增强
添加任务详情展开/收起功能
显示任务配置信息（work_scale, repeats 等）
添加 "查看结果目录" 链接
改进进度显示（进度条）
添加任务筛选功能（按状态筛选）
5.4 实时更新优化
保持现有的 2 秒轮询机制
添加连接状态指示器
优化更新逻辑，减少不必要的 DOM 操作
6. 配置文件存储路径修正
文件: tools/runtime_compare/utils/config_manager.py

修正 save_config() 中的自动路径生成逻辑
确保配置文件保存到 tools/runtime_compare/配置文件/ 目录
如果 config_path 为 None，使用工具目录下的配置文件目录
当前问题: 第31行的路径生成使用了 experiment/ 目录，需要改为 tools/runtime_compare/配置文件/

7. 任务管理器状态持久化
文件: tools/runtime_compare/ui/web/api.py

在 init_task_manager() 中，支持从配置文件恢复任务队列
可选：启动时自动加载最新的配置文件
8. 错误处理和用户反馈
文件: tools/runtime_compare/ui/web/api.py, tools/runtime_compare/ui/web/templates/index.html

添加统一的错误处理机制
前端显示友好的错误消息
API 返回详细的错误信息
添加操作成功提示
文件修改清单
需要修改的文件
tools/runtime_compare/ui/web/api.py
添加配置文件导出/导入 API
修改 add_task() 添加自动导出逻辑
添加配置文件管理 API
tools/runtime_compare/ui/web/templates/index.html
添加配置文件管理 UI
优化任务表单
增强任务列表显示
添加错误提示区域
tools/runtime_compare/utils/config_manager.py
修正 save_config() 的自动路径生成逻辑
新增文件（可选）
tools/runtime_compare/ui/web/static/style.css（可选）
将内联样式提取到独立 CSS 文件
tools/runtime_compare/ui/web/static/app.js（可选）
将 JavaScript 代码提取到独立 JS 文件
实现顺序
第一阶段：修正配置文件路径逻辑 + 自动导出功能
第二阶段：手动导出和导入 API
第三阶段：前端界面增强（配置文件管理区域）
第四阶段：任务列表和表单优化
第五阶段：错误处理和用户体验优化
测试要点
添加任务后自动导出配置文件
手动导出配置文件功能
导入配置文件并加载任务
配置文件列表和下载
任务状态实时更新
错误处理（无效文件、网络错误等）
注意事项
配置文件路径使用绝对路径，确保 CLI 可以正确加载
任务去重逻辑：相同参数的任务不重复添加
配置文件命名避免冲突（使用时间戳）
确保文件权限正确（Web 服务器用户可写）
保持与 CLI 模式的兼容性（配置文件格式一致）