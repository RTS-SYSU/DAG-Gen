from __future__ import annotations

"""时间解析工具函数"""

import re
from typing import Optional


def parse_internal_time_seconds(stdout: str, stderr: str = "") -> Optional[float]:
    """从程序输出中解析内部计时时间（秒）
    
    支持三种格式：
    - MAIN_ELAPSED_S=... （pipeline 新测时版本）
    - PROGRAM_TOTAL_NS=... （ns转秒）
    - "total time" 行
    
    优先使用 pipeline 新格式，兼容旧运行时工具输出。同时扫描 stdout/stderr。
    
    Args:
        stdout: 程序的标准输出
        stderr: 程序的标准错误输出
        
    Returns:
        解析到的时间（秒），如果解析失败返回 None
    """
    ns_candidates: list[int] = []
    time_candidates: list[float] = []
    for stream_text in (stdout or "", stderr or ""):
        for ln in stream_text.splitlines():
            # 支持 pipeline 新格式 MAIN_ELAPSED_S=...
            m = re.search(r"MAIN_ELAPSED_S=([\d.]+)", ln)
            if m:
                try:
                    time_candidates.append(float(m.group(1)))
                except Exception:
                    pass
                continue
            m = re.search(r"PROGRAM_TOTAL_NS=(\d+)", ln)
            if m:
                try:
                    ns_candidates.append(int(m.group(1)))
                except Exception:
                    pass
                continue
            low = ln.lower()
            if "total time" not in low:
                continue
            m = re.search(r"([0-9]+(?:\.[0-9]+)?)", ln)
            if not m:
                continue
            try:
                time_candidates.append(float(m.group(1)))
            except Exception:
                continue
    if ns_candidates:
        return ns_candidates[-1] / 1e9
    if time_candidates:
        return time_candidates[-1]
    return None
