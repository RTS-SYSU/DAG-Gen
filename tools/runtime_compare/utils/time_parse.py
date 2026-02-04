"""时间解析工具函数"""

import re
from typing import Optional


def parse_internal_time_seconds(stdout: str) -> Optional[float]:
    """从程序输出中解析内部计时时间（秒）
    
    优先解析 PROGRAM_TOTAL_NS=...，如果失败则尝试解析 "total time" 行。
    
    Args:
        stdout: 程序的标准输出
        
    Returns:
        解析到的时间（秒），如果解析失败返回 None
    """
    ns_candidates: list[int] = []
    time_candidates: list[float] = []
    for ln in stdout.splitlines():
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
