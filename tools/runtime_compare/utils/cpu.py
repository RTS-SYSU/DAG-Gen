"""CPU 相关工具函数"""

import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def read_cpu_online() -> List[int]:
    """读取系统在线 CPU 列表
    
    Returns:
        在线 CPU 编号列表，例如 [0, 1, 2, 3]
    """
    p = Path("/sys/devices/system/cpu/online")
    if p.exists():
        s = p.read_text(encoding="utf-8", errors="replace").strip()
        cpus: List[int] = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                try:
                    lo = int(a)
                    hi = int(b)
                except Exception:
                    continue
                cpus.extend(list(range(lo, hi + 1)))
            else:
                try:
                    cpus.append(int(part))
                except Exception:
                    continue
        cpus = sorted(set(cpus))
        if cpus:
            return cpus
    n = os.cpu_count() or 1
    return list(range(n))


def format_cpu_set(cpus: List[int]) -> str:
    """格式化 CPU 集合为字符串
    
    Args:
        cpus: CPU 编号列表
        
    Returns:
        格式化的字符串，例如 "0,1,2,3"
    """
    return ",".join(str(x) for x in cpus)


def get_cpu_freq(cpu_id: int) -> Optional[int]:
    """获取 CPU 的最大频率（Hz）
    
    Args:
        cpu_id: CPU 编号
        
    Returns:
        CPU 最大频率（Hz），如果无法获取则返回 None
    """
    freq_file = Path(f"/sys/devices/system/cpu/cpu{cpu_id}/cpufreq/cpuinfo_max_freq")
    if freq_file.exists():
        try:
            freq_khz = int(freq_file.read_text(encoding="utf-8", errors="replace").strip())
            return freq_khz * 1000  # 转换为 Hz
        except Exception:
            pass
    return None


def detect_cpu_clusters() -> Dict[str, Dict]:
    """检测 CPU 集群（大核/小核）
    
    Returns:
        包含 big 和 little 核心信息的字典，格式：
        {
            'big': {'cpus': [4, 5, 6, 7], 'freq_hz': 2400000000},
            'little': {'cpus': [0, 1, 2, 3], 'freq_hz': 1800000000}
        }
        如果无法区分，则返回 None
    """
    cpu_list = read_cpu_online()
    if not cpu_list:
        return None
    
    # 获取每个 CPU 的频率
    cpu_freqs: Dict[int, int] = {}
    for cpu_id in cpu_list:
        freq = get_cpu_freq(cpu_id)
        if freq:
            cpu_freqs[cpu_id] = freq
    
    if not cpu_freqs:
        return None
    
    # 按频率分组
    freq_groups: Dict[int, List[int]] = {}
    for cpu_id, freq in cpu_freqs.items():
        if freq not in freq_groups:
            freq_groups[freq] = []
        freq_groups[freq].append(cpu_id)
    
    # 如果只有一组，无法区分大小核
    if len(freq_groups) <= 1:
        return None
    
    # 按频率排序，频率高的为大核
    sorted_freqs = sorted(freq_groups.keys(), reverse=True)
    
    # 取频率最高的作为大核
    big_freq = sorted_freqs[0]
    big_cpus = sorted(freq_groups[big_freq])
    
    # 其他作为小核（如果有多个频率组，合并除最高外的所有）
    little_cpus = []
    little_freq = None
    if len(sorted_freqs) > 1:
        # 取频率最低的作为小核的代表频率
        little_freq = sorted_freqs[-1]
        for freq in sorted_freqs[1:]:
            little_cpus.extend(freq_groups[freq])
        little_cpus = sorted(little_cpus)
    
    result = {
        'big': {
            'cpus': big_cpus,
            'freq_hz': big_freq,
            'freq_ghz': round(big_freq / 1e9, 2)
        }
    }
    
    if little_cpus:
        result['little'] = {
            'cpus': little_cpus,
            'freq_hz': little_freq,
            'freq_ghz': round(little_freq / 1e9, 2)
        }
    
    return result


def get_cpu_info() -> Dict:
    """获取完整的 CPU 信息
    
    Returns:
        包含 CPU 列表、集群信息等的字典
    """
    cpu_list = read_cpu_online()
    clusters = detect_cpu_clusters()
    
    # 获取每个 CPU 的频率
    cpu_freqs: Dict[int, float] = {}
    for cpu_id in cpu_list:
        freq = get_cpu_freq(cpu_id)
        if freq:
            cpu_freqs[cpu_id] = round(freq / 1e9, 2)  # 转换为 GHz
    
    result = {
        'cpu_list': cpu_list,
        'cpu_total': len(cpu_list),
        'cpu_freqs': cpu_freqs,
        'clusters': clusters,
        'has_big_little': clusters is not None
    }
    
    return result


def _bench_loop(iterations: int = 1_000_000) -> int:
    """简单双循环用于基准测试，返回迭代次数"""
    s = 0
    for i in range(iterations):
        s += (i ^ (s << 1)) & 0xFFFFFFFF
    return iterations


def benchmark_core_speed(sample_cpus: List[int], duration_ms: int = 80) -> Dict[int, float]:
    """在指定 CPU 上做轻量基准，估算 MOPS
    
    Args:
        sample_cpus: 要测试的 CPU 列表
        duration_ms: 每个 CPU 至少运行的时间（毫秒）
    
    Returns:
        字典: {cpu_id: mops值}
    """
    import time

    results: Dict[int, float] = {}
    original_affinity: Optional[set] = None

    for cpu in sample_cpus:
        try:
            if hasattr(os, "sched_getaffinity"):
                original_affinity = os.sched_getaffinity(0)
                os.sched_setaffinity(0, {cpu})
        except Exception:
            original_affinity = None

        start = time.perf_counter()
        iters = 0
        # 运行直到超过目标时间
        while True:
            iters += _bench_loop(200_000)
            if (time.perf_counter() - start) * 1000 >= duration_ms:
                break
        elapsed = time.perf_counter() - start
        if elapsed > 0:
            mops = (iters / elapsed) / 1e6
            results[cpu] = round(mops, 2)
        try:
            if original_affinity is not None and hasattr(os, "sched_setaffinity"):
                os.sched_setaffinity(0, original_affinity)
        except Exception:
            pass
    return results
