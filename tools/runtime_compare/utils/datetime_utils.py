"""日期时间工具函数"""

from datetime import datetime


def now_ts_safe() -> str:
    """生成安全的时间戳字符串（用于文件名）"""
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    return ts.replace(":", "-")
