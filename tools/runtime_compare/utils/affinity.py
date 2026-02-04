"""CPU 亲和性相关工具函数"""

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Tuple


def rewrite_sched_setaffinity_cpu_set(source: str, cpu_set: List[int]) -> Tuple[str, bool]:
    """重写源码中的 sched_setaffinity CPU_SET 调用
    
    将源码中写死的 CPU_SET 替换为指定的 CPU 集合，防止程序覆盖工具分配的 CPU 隔离。
    
    Args:
        source: C 源码内容
        cpu_set: 要设置的 CPU 编号列表
        
    Returns:
        (修改后的源码, 是否发生了修改)
    """
    if "sched_setaffinity" not in source or "CPU_ZERO(&set)" not in source:
        return source, False

    lines = source.splitlines(keepends=True)
    out: List[str] = []
    in_block = False
    inserted = False
    changed = False

    cpu_set_lines = [f"    CPU_SET({c}, &set);\n" for c in cpu_set]

    for ln in lines:
        if "CPU_ZERO(&set)" in ln:
            in_block = True
            inserted = False
            out.append(ln)
            continue

        if in_block:
            if re.match(r"^\s*CPU_SET\(\s*\d+\s*,\s*&set\s*\)\s*;\s*$", ln):
                # Drop original CPU_SET lines; we'll insert our own once.
                changed = True
                continue

            if (not inserted) and ("sched_setaffinity" in ln):
                out.extend(cpu_set_lines)
                inserted = True
                if cpu_set_lines:
                    changed = True
                # Continue to keep the sched_setaffinity line
                out.append(ln)
                in_block = False
                continue

            out.append(ln)
            continue

        out.append(ln)

    return "".join(out), changed


def run_with_affinity(
    cmd: List[str],
    *,
    cwd: Path,
    env: Dict[str, str],
    cpu_set: List[int],
    use_sudo: bool,
) -> Tuple[int, str, str, int]:
    """在指定的 CPU 核心集合上运行命令
    
    Args:
        cmd: 要执行的命令
        cwd: 工作目录
        env: 环境变量
        cpu_set: CPU 核心集合
        use_sudo: 是否使用 sudo 运行
        
    Returns:
        (返回码, stdout, stderr, wall_time_ns)
    """
    full_cmd = cmd[:]
    if use_sudo and os.geteuid() != 0:
        # Non-interactive: require passwordless sudo.
        full_cmd = ["sudo", "-n"] + full_cmd

    def preexec() -> None:
        # Ensure the child (and thus its threads) stay within the CPU set.
        os.sched_setaffinity(0, set(cpu_set))

    t0 = time.monotonic_ns()
    proc = subprocess.run(
        full_cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        preexec_fn=preexec,
    )
    t1 = time.monotonic_ns()
    return proc.returncode, proc.stdout or "", proc.stderr or "", (t1 - t0)
