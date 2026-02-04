"""sudo 相关工具函数"""

import os
import subprocess


def has_passwordless_sudo() -> bool:
    """检查是否有免密 sudo 权限
    
    Returns:
        如果有 root 权限或免密 sudo，返回 True
    """
    if os.geteuid() == 0:
        return True
    try:
        subprocess.run(["sudo", "-n", "true"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False
