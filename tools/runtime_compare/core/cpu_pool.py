"""CPU 池管理"""

import threading
from typing import List, Optional


class CpuPool:
    """CPU 核心池，管理 CPU 核心的分配和释放"""
    
    def __init__(self, cpus: List[int]) -> None:
        """初始化 CPU 池
        
        Args:
            cpus: 可用的 CPU 核心列表
        """
        self._cpus = cpus[:]
        self._lock = threading.Lock()
        self._leased: List[List[int]] = []
    
    def try_acquire_group(self, k: int, preferred: Optional[List[int]] = None) -> Optional[List[int]]:
        """尝试获取 k 个 CPU 核心
        
        Args:
            k: 需要的核心数量
            preferred: 优先使用的核心列表（如果指定了 cpu_list）
            
        Returns:
            如果成功，返回分配的核心列表；否则返回 None
        """
        with self._lock:
            free = [c for c in self._cpus if all(c not in g for g in self._leased)]
            
            # 如果指定了优先列表，优先使用其中的核心
            if preferred:
                preferred_available = [c for c in preferred if c in free]
                if len(preferred_available) >= k:
                    group = preferred_available[:k]
                    self._leased.append(group)
                    return group
            
            # 否则从空闲核心中选择
            if len(free) < k:
                return None
            group = free[:k]
            self._leased.append(group)
            return group
    
    def release_group(self, group: List[int]) -> None:
        """释放 CPU 核心组
        
        Args:
            group: 要释放的核心列表
        """
        with self._lock:
            self._leased = [g for g in self._leased if g != group]
    
    def free_count(self) -> int:
        """获取当前空闲的核心数量"""
        with self._lock:
            used = {c for g in self._leased for c in g}
            return len([c for c in self._cpus if c not in used])
    
    def total_count(self) -> int:
        """获取总的核心数量"""
        return len(self._cpus)
