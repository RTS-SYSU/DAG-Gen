"""CPU 亲和性相关工具函数"""

import os
import re
import subprocess
import time
import signal
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple


def rewrite_sched_setaffinity_cpu_set(source: str, cpu_set: List[int]) -> Tuple[str, bool]:
    """重写源码中的 sched_setaffinity CPU_SET 调用
    
    将源码中写死的 CPU_SET 替换为指定的 CPU 集合，防止程序覆盖工具分配的 CPU 隔离。
    
    Args:
        source: C 源码内容
        cpu_set: 要设置的 CPU 编号列表
        
    Returns:
        (修改后的源码, 是否发生了修改)
    """
    if "sched_setaffinity" not in source:
        return source, False

    # Detect the variable name used with CPU_ZERO (e.g. &set, &cpu_set, &cpuset)
    m_zero = re.search(r"CPU_ZERO\s*\(\s*&(\w+)\s*\)", source)
    if not m_zero:
        return source, False
    var_name = m_zero.group(1)

    lines = source.splitlines(keepends=True)
    out: List[str] = []
    in_block = False
    inserted = False
    changed = False

    cpu_set_lines = [f"    CPU_SET({c}, &{var_name});\n" for c in cpu_set]
    zero_pattern = f"CPU_ZERO(&{var_name})"
    set_pattern = re.compile(
        r"^\s*CPU_SET\(\s*\d+\s*,\s*&" + re.escape(var_name) + r"\s*\)\s*;\s*$"
    )

    for ln in lines:
        if zero_pattern in ln:
            in_block = True
            inserted = False
            out.append(ln)
            continue

        if in_block:
            if set_pattern.match(ln):
                changed = True
                continue

            if (not inserted) and ("sched_setaffinity" in ln):
                out.extend(cpu_set_lines)
                inserted = True
                if cpu_set_lines:
                    changed = True
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
    cancel_check: Optional[Callable[[], bool]] = None,
    kill_grace_s: float = 1.0,
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
        # New session so we can kill the whole process group on cancel.
        os.setsid()

    t0 = time.monotonic_ns()
    proc = subprocess.Popen(
        full_cmd,
        cwd=str(cwd),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=preexec,
    )

    def terminate_group() -> None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except Exception:
            try:
                proc.terminate()
            except Exception:
                pass

    def kill_group() -> None:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    out = ""
    err = ""
    try:
        while True:
            if cancel_check and cancel_check():
                terminate_group()
                try:
                    out, err = proc.communicate(timeout=max(0.1, kill_grace_s))
                except subprocess.TimeoutExpired:
                    kill_group()
                    out, err = proc.communicate()
                break
            try:
                out, err = proc.communicate(timeout=0.2)
                break
            except subprocess.TimeoutExpired:
                continue
    finally:
        t1 = time.monotonic_ns()

    rc = proc.returncode if proc.returncode is not None else -9
    return int(rc), out or "", err or "", (t1 - t0)
