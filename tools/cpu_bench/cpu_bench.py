#!/usr/bin/env python3
"""
逐核轻量性能基准

- 绑定到每个在线 CPU，跑位运算循环，估算 MOPS（百万次操作/秒）
- 结果打印到控制台，并保存到当前脚本目录下的 txt 与 json 文件

用法：
  python3 cpu_bench.py
"""

import json
import os
import time
from pathlib import Path


def read_cpu_online():
    """获取在线 CPU 列表。"""
    p = Path("/sys/devices/system/cpu/online")
    if p.exists():
        s = p.read_text(encoding="utf-8", errors="replace").strip()
        cpus = []
        for part in s.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                cpus.extend(range(int(a), int(b) + 1))
            else:
                cpus.append(int(part))
        cpus = sorted(set(cpus))
        if cpus:
            return cpus
    n = os.cpu_count() or 1
    return list(range(n))


def _bench_loop(iterations: int = 200_000) -> int:
    """简单位运算循环，返回迭代次数。"""
    s = 0
    for i in range(iterations):
        s += (i ^ (s << 1)) & 0xFFFFFFFF
    return iterations


def bench_cpu(cpu_id: int, min_ms: int = 200) -> float:
    """在指定 CPU 上跑基准，返回 MOPS。"""
    original = None
    try:
        if hasattr(os, "sched_getaffinity"):
            original = os.sched_getaffinity(0)
            os.sched_setaffinity(0, {cpu_id})
    except Exception:
        original = None

    start = time.perf_counter()
    iters = 0
    while True:
        iters += _bench_loop()
        if (time.perf_counter() - start) * 1000 >= min_ms:
            break
    elapsed = time.perf_counter() - start

    try:
        if original is not None and hasattr(os, "sched_setaffinity"):
            os.sched_setaffinity(0, original)
    except Exception:
        pass

    if elapsed == 0:
        return 0.0
    return round((iters / elapsed) / 1e6, 2)  # MOPS


def main():
    cpus = read_cpu_online()
    print(f"在线 CPU: {cpus} (共 {len(cpus)} 核)")
    results = {}
    for cpu in cpus:
        mops = bench_cpu(cpu)
        results[cpu] = mops
        print(f"CPU {cpu}: {mops:.2f} MOPS")

    # 按性能排序输出摘要
    sorted_items = sorted(results.items(), key=lambda x: x[1], reverse=True)
    print("\n按性能排序 (MOPS):")
    for cpu, mops in sorted_items:
        print(f"  CPU {cpu}: {mops:.2f}")

    # 保存结果
    out_dir = Path(__file__).resolve().parent
    ts = time.strftime("%Y%m%d_%H%M%S")
    txt_path = out_dir / f"cpu_bench_{ts}.txt"
    json_path = out_dir / f"cpu_bench_{ts}.json"

    txt_lines = [
        f"timestamp: {ts}",
        f"online_cpus: {cpus}",
        "results (MOPS):",
    ]
    txt_lines += [f"CPU {cpu}: {results[cpu]:.2f}" for cpu in cpus]
    txt_lines.append("")
    txt_lines.append("sorted:")
    txt_lines += [f"CPU {cpu}: {mops:.2f}" for cpu, mops in sorted_items]
    txt_path.write_text("\n".join(txt_lines), encoding="utf-8")

    json_path.write_text(
        json.dumps(
            {
                "timestamp": ts,
                "online_cpus": cpus,
                "results_mops": results,
                "sorted": sorted_items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"\n已保存结果：{txt_path.name}, {json_path.name}")


if __name__ == "__main__":
    main()

