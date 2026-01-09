from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Tuple


@dataclass(frozen=True)
class ThreadMetric:
    total_ns: int = 0
    count: int = 0


@dataclass(frozen=True)
class TraceEvent:
    key: str
    start_ns: int
    dur_ns: int

    @property
    def thread(self) -> str:
        return self.key.split("/", 1)[0] if "/" in self.key else self.key

    @property
    def task(self) -> str:
        return self.key.split("/", 1)[1] if "/" in self.key else self.key


def load_thread_metrics(json_path: Path) -> Dict[str, ThreadMetric]:
    """从多种 JSON 结构提取“按线程汇总”的 count/total_ns。

    支持：
    1) thread_time_summary.json: {thread: {total_ns, count}}
    2) time_result.json: {callsite: {total_ns, count, ...}} -> 按 callsite 前缀 thread 聚合
    3) mycalls_meta(_internal).json: {thread: {node: {total_ns, count, ...}}} -> 按顶层 thread 聚合
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("JSON 顶层必须是对象(dict)")

    # case 3: meta json style: {thread: {node: {file,line,total_ns,count,...}}}
    if _looks_like_meta_json(data):
        out: Dict[str, ThreadMetric] = {}
        for thread_name, node_map in data.items():
            if not isinstance(node_map, dict):
                continue
            total_ns = 0
            count = 0
            for meta in node_map.values():
                if not isinstance(meta, dict):
                    continue
                total_ns += int(meta.get("total_ns", 0) or 0)
                count += int(meta.get("count", 0) or 0)
            out[str(thread_name)] = ThreadMetric(total_ns=total_ns, count=count)
        return out

    # case 1 or 2: {k: {total_ns,count,...}}
    if all(isinstance(v, dict) for v in data.values()):
        # treat as callsite map when many keys contain '/'
        if any("/" in str(k) for k in data.keys()):
            return _aggregate_by_prefix(data)
        # treat as already thread summary
        out = {}
        for k, v in data.items():
            out[str(k)] = ThreadMetric(
                total_ns=int(v.get("total_ns", 0) or 0),
                count=int(v.get("count", 0) or 0),
            )
        return out

    raise ValueError("无法识别的 JSON 结构（未找到可解析的线程统计字段）")


def load_trace_events(json_path: Path) -> List[TraceEvent]:
    """读取线程调用 trace（thread_trace.json）。

    期望结构：[{key,start_ns,dur_ns}, ...]
    """
    data = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("trace JSON 顶层必须是数组(list)")
    out: List[TraceEvent] = []
    for i, row in enumerate(data):
        if not isinstance(row, dict):
            continue
        key = row.get("key")
        start_ns = row.get("start_ns")
        dur_ns = row.get("dur_ns")
        if not isinstance(key, str) or start_ns is None or dur_ns is None:
            continue
        try:
            out.append(TraceEvent(key=key, start_ns=int(start_ns), dur_ns=int(dur_ns)))
        except Exception:
            raise ValueError(f"trace JSON 第 {i+1} 项字段类型非法") from None
    if not out:
        raise ValueError("trace JSON 为空或无有效事件")
    return out


def choose_time_analysis_output_dir(
    json_path: Path,
    *,
    time_analysis_root: Optional[Path] = None,
) -> Path:
    """选择统计图保存目录（优先落到 中间结果/<base>/时间分析/<project>/）。"""
    json_path = json_path.expanduser().resolve()

    # If selected JSON is already inside .../中间结果/<base>/时间分析/<project>/..., use that project dir.
    parts = list(json_path.parts)
    if "中间结果" in parts:
        idx = parts.index("中间结果")
        if idx + 2 < len(parts) and "时间分析" in parts[idx + 2 :]:
            j = parts.index("时间分析", idx + 2)
            if j + 1 < len(parts):
                return Path(*parts[: j + 2])
            return Path(*parts[: j + 1])

    # If GUI provided time_analysis_root (中间结果/<base>/时间分析), choose newest project dir.
    if time_analysis_root:
        root = time_analysis_root.expanduser().resolve()
        if root.name == "时间分析":
            candidates = [p for p in root.iterdir() if p.is_dir()]
            if candidates:
                return max(candidates, key=lambda p: p.stat().st_mtime)
        if root.parent.name == "时间分析":
            return root

    # Fallback: same dir as selected JSON
    return json_path.parent


def render_thread_frequency_png(
    metrics: Mapping[str, ThreadMetric],
    *,
    title: str = "Figure 2. Task Execution Frequency (count)",
    output_dir: Path,
    filename: str = "thread_task_frequency.png",
) -> Path:
    labels, values = _sorted_items(metrics, key="count")
    return _render_bar_png(
        labels,
        values,
        title=title,
        ylabel="Frequency (count)",
        xlabel="Thread Name",
        output_dir=output_dir,
        filename=filename,
        cmap="viridis",
        fmt="{:,d}",
    )


def render_thread_total_time_png(
    metrics: Mapping[str, ThreadMetric],
    *,
    title: str = "Figure 1. Aggregate Execution Time by Thread (ns)",
    output_dir: Path,
    filename: str = "thread_total_time.png",
) -> Path:
    labels, values = _sorted_items(metrics, key="total_ns")
    return _render_bar_png(
        labels,
        values,
        title=title,
        ylabel="Time Spent (total_ns)",
        xlabel="Thread Name",
        output_dir=output_dir,
        filename=filename,
        cmap="magma",
        fmt="{:,d}",
    )


# ===================== Compare charts =====================


def render_program_compare_png(
    metrics_a: Mapping,
    metrics_b: Mapping,
    *,
    labels: Tuple[str, str],
    output_dir: Path,
    filename: str = "metrics_compare_program.png",
) -> Path:
    total_a = int(metrics_a.get("program_total_ns", 0) or 0)
    total_b = int(metrics_b.get("program_total_ns", 0) or 0)
    return _render_grouped_bar_png(
        categories=["program_total_ns"],
        values_a=[total_a],
        values_b=[total_b],
        labels=labels,
        title="Program Total Execution Time (ns)",
        ylabel="Time (ns)",
        output_dir=output_dir,
        filename=filename,
    )


def render_thread_compare_png(
    metrics_a: Mapping,
    metrics_b: Mapping,
    *,
    labels: Tuple[str, str],
    output_dir: Path,
    filename: str = "metrics_compare_threads.png",
) -> Path:
    threads_a = metrics_a.get("thread_time_ns", {}) or {}
    threads_b = metrics_b.get("thread_time_ns", {}) or {}
    all_threads = sorted(set(threads_a.keys()) | set(threads_b.keys()))
    vals_a = [int((threads_a.get(t) or {}).get("total_ns", 0) or 0) for t in all_threads]
    vals_b = [int((threads_b.get(t) or {}).get("total_ns", 0) or 0) for t in all_threads]
    return _render_grouped_bar_png(
        categories=all_threads,
        values_a=vals_a,
        values_b=vals_b,
        labels=labels,
        title="Thread Total Execution Time (ns)",
        ylabel="Time (ns)",
        output_dir=output_dir,
        filename=filename,
    )


def render_thread_gantt_png(
    events: List[TraceEvent],
    *,
    title: str = "Thread Task Scheduling",
    output_dir: Path,
    filename: str = "thread_call_gantt.png",
) -> Path:
    """渲染线程调用甘特图（按 key 前缀分线程，跨线程共享时间轴）。"""
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / filename
    if out_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"{out_path.stem}_{stamp}{out_path.suffix}"

    # headless backend
    import matplotlib

    matplotlib.use("Agg")
    import numpy as np
    import matplotlib.pyplot as plt

    # group by thread
    by_thread: Dict[str, List[TraceEvent]] = {}
    for ev in events:
        by_thread.setdefault(ev.thread, []).append(ev)
    for evs in by_thread.values():
        evs.sort(key=lambda e: e.start_ns)

    threads = sorted(by_thread.keys())
    min_start = min(ev.start_ns for ev in events)
    max_end = max(ev.start_ns + max(0, ev.dur_ns) for ev in events)
    total_span_ns = max(1, max_end - min_start)

    # convert to ms
    def to_ms(ns: int) -> float:
        return ns / 1e6

    total_span_ms = to_ms(total_span_ns)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except Exception:
        pass

    height = max(5.6, 0.7 * len(threads) + 1.8)
    width = max(11.5, min(20.0, 11.5 + 0.1 * len(events) ** 0.5))
    fig, ax = plt.subplots(figsize=(width, height), dpi=160)

    cmap = plt.get_cmap("tab10")
    thread_color = {t: cmap(i % 10) for i, t in enumerate(threads)}

    row_h = 8
    row_gap = 4
    y_ticks = []
    y_labels = []

    # label threshold: only label if segment wide enough
    label_min_ms = max(0.0, total_span_ms * 0.04)

    for i, t in enumerate(threads):
        y0 = i * (row_h + row_gap)
        y_ticks.append(y0 + row_h / 2)
        y_labels.append(t)

        color = thread_color[t]
        for ev in by_thread[t]:
            start_ms = to_ms(ev.start_ns - min_start)
            dur_ms = max(0.0, to_ms(ev.dur_ns))
            if dur_ms <= 0:
                continue
            ax.broken_barh([(start_ms, dur_ms)], (y0, row_h), facecolors=color, edgecolors="#1f1f1f", linewidth=0.35, alpha=0.92)

            if dur_ms >= label_min_ms:
                label = ev.task
                # too long labels hurt readability
                if len(label) > 28:
                    label = label[:25] + "..."
                ax.text(
                    start_ms + dur_ms / 2,
                    y0 + row_h / 2,
                    label,
                    ha="center",
                    va="center",
                    fontsize=9,
                    color="white",
                    fontweight="bold",
                    clip_on=True,
                )

    ax.set_title(title, fontsize=16, fontweight="bold", pad=12)
    ax.set_xlabel("Time (ms)", fontsize=12)
    ax.set_ylabel("Thread Name", fontsize=12)
    ax.set_yticks(y_ticks)
    ax.set_yticklabels(y_labels, fontsize=11)
    ax.set_xlim(0, max(1.0, total_span_ms * 1.02))
    ax.grid(axis="x", linestyle="-", alpha=0.35)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def _looks_like_meta_json(data: Mapping) -> bool:
    for v in data.values():
        if not isinstance(v, dict):
            continue
        # nested dict of meta entries
        for vv in v.values():
            if isinstance(vv, dict) and ("file" in vv or "line" in vv):
                return True
        return False
    return False


def _aggregate_by_prefix(data: Mapping) -> Dict[str, ThreadMetric]:
    out: Dict[str, ThreadMetric] = {}
    for k, v in data.items():
        if not isinstance(v, dict):
            continue
        name = str(k)
        thread = name.split("/", 1)[0] if "/" in name else name
        cur = out.get(thread, ThreadMetric())
        out[thread] = ThreadMetric(
            total_ns=cur.total_ns + int(v.get("total_ns", 0) or 0),
            count=cur.count + int(v.get("count", 0) or 0),
        )
    return out


def _sorted_items(metrics: Mapping[str, ThreadMetric], *, key: str) -> Tuple[Iterable[str], Iterable[int]]:
    rows = []
    for thread, m in metrics.items():
        if not isinstance(m, ThreadMetric):
            m = ThreadMetric(total_ns=int(getattr(m, "total_ns", 0)), count=int(getattr(m, "count", 0)))
        rows.append((thread, m))

    if key == "total_ns":
        rows.sort(key=lambda x: x[1].total_ns, reverse=True)
        return [r[0] for r in rows], [r[1].total_ns for r in rows]
    rows.sort(key=lambda x: x[1].count, reverse=True)
    return [r[0] for r in rows], [r[1].count for r in rows]


def _render_bar_png(
    labels: Iterable[str],
    values: Iterable[int],
    *,
    title: str,
    ylabel: str,
    xlabel: str,
    output_dir: Path,
    filename: str,
    cmap: str,
    fmt: str,
) -> Path:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / filename
    if out_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"{out_path.stem}_{stamp}{out_path.suffix}"

    # headless backend
    import matplotlib

    matplotlib.use("Agg")
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    labels_list = list(labels)
    values_list = [int(v) for v in values]

    width = max(9.5, 1.55 * max(1, len(labels_list)))
    fig, ax = plt.subplots(figsize=(width, 5.6), dpi=160)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except Exception:
        pass

    xs = np.arange(len(labels_list))
    colors = plt.get_cmap(cmap)(np.linspace(0.25, 0.9, len(labels_list)))
    bars = ax.bar(xs, values_list, width=0.62, color=colors, edgecolor="#2f2f2f", linewidth=0.6)

    ax.set_title(title, fontsize=16, fontweight="bold", pad=14)
    ax.set_xlabel(xlabel, fontsize=12)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xticks(xs)
    ax.set_xticklabels(labels_list, fontsize=11)
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", linestyle="-", alpha=0.28)
    ax.set_axisbelow(True)

    if len(labels_list) > 6:
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")

    max_v = max(values_list) if values_list else 0
    pad = max(1, int(max_v * 0.02))
    ax.set_ylim(0, max_v + pad * 8)

    for bar, val in zip(bars, values_list):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + pad,
            fmt.format(val),
            ha="center",
            va="bottom",
            fontsize=11,
            fontweight="bold",
            color="#111111",
        )

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path


def _render_grouped_bar_png(
    categories: List[str],
    values_a: List[int],
    values_b: List[int],
    *,
    labels: Tuple[str, str],
    title: str,
    ylabel: str,
    output_dir: Path,
    filename: str,
) -> Path:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    out_path = output_dir / filename
    if out_path.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = output_dir / f"{out_path.stem}_{stamp}{out_path.suffix}"

    import matplotlib

    matplotlib.use("Agg")
    import numpy as np
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter

    cats = list(categories)
    a = [int(v) for v in values_a]
    b = [int(v) for v in values_b]

    width = max(9.0, 1.2 * max(1, len(cats)))
    height = max(5.0, 0.6 * len(cats) + 2.4)
    fig, ax = plt.subplots(figsize=(width, height), dpi=160)

    try:
        plt.style.use("seaborn-v0_8-whitegrid")
    except Exception:
        pass

    xs = np.arange(len(cats))
    bar_w = 0.35
    bars1 = ax.bar(xs - bar_w / 2, a, bar_w, label=labels[0], color="#64B5F6", edgecolor="#2f2f2f", linewidth=0.6)
    bars2 = ax.bar(xs + bar_w / 2, b, bar_w, label=labels[1], color="#E57373", edgecolor="#2f2f2f", linewidth=0.6)

    ax.set_title(title, fontsize=16, fontweight="bold", pad=14)
    ax.set_ylabel(ylabel, fontsize=12)
    ax.set_xticks(xs)
    ax.set_xticklabels(cats, fontsize=11)
    ax.yaxis.set_major_formatter(StrMethodFormatter("{x:,.0f}"))
    ax.grid(axis="y", linestyle="-", alpha=0.28)
    ax.set_axisbelow(True)
    ax.legend()

    if len(cats) > 6:
        plt.setp(ax.get_xticklabels(), rotation=20, ha="right")

    max_v = max(a + b) if (a or b) else 0
    pad = max(1, int(max_v * 0.02))
    ax.set_ylim(0, max_v + pad * 10)

    for bars, vals in ((bars1, a), (bars2, b)):
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + pad,
                f"{val:,}",
                ha="center",
                va="bottom",
                fontsize=10,
                color="#111111",
            )

    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    return out_path
