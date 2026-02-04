"""文件操作工具函数"""

import os
import subprocess
from pathlib import Path


def ensure_dir(p: Path) -> None:
    """确保目录存在"""
    p.mkdir(parents=True, exist_ok=True)


def ensure_writable_dir(path: Path, *, use_sudo: bool) -> None:
    """确保目录存在且可写
    
    如果目录不可写且启用了 sudo，会尝试修复权限。
    
    Args:
        path: 目录路径
        use_sudo: 是否使用 sudo 修复权限
        
    Raises:
        PermissionError: 如果目录不可写且无法修复
    """
    from .sudo import has_passwordless_sudo
    
    try:
        path.mkdir(parents=True, exist_ok=True)
    except PermissionError:
        pass

    if path.exists() and os.access(str(path), os.W_OK | os.X_OK):
        return

    # Try to fix with root
    if os.geteuid() == 0:
        try:
            path.mkdir(parents=True, exist_ok=True)
            path.chmod(0o775)
            return
        except Exception:
            pass

    if use_sudo and has_passwordless_sudo():
        uid = os.getuid()
        gid = os.getgid()
        subprocess.run(["sudo", "-n", "mkdir", "-p", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["sudo", "-n", "chown", "-R", f"{uid}:{gid}", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if path.exists() and os.access(str(path), os.W_OK | os.X_OK):
            return

    owner_hint = ""
    try:
        st = path.stat()
        owner_hint = f" (uid={st.st_uid}, gid={st.st_gid}, mode={oct(st.st_mode & 0o777)})"
    except Exception:
        pass
    raise PermissionError(
        f"结果目录不可写：{path}{owner_hint}。"
        f"请删除该目录或执行：sudo chown -R {os.getuid()}:{os.getgid()} '{path}'，"
        f"或以 sudo 启动本工具/启用 sudo(需 sudo -n 免密)。"
    )
