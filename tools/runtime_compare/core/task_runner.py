"""任务执行器"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import threading
import time
from pathlib import Path
from queue import Queue
from typing import Dict, List, Optional, Tuple

from ..config.defaults import GCC_FLAGS
from ..core.task import Task
from ..core.cpu_pool import CpuPool
from ..utils.affinity import rewrite_sched_setaffinity_cpu_set, run_with_affinity
from ..utils.cpu import format_cpu_set
from ..utils.file_ops import ensure_writable_dir
from ..utils.sudo import has_passwordless_sudo
from ..utils.time_parse import parse_internal_time_seconds
from ..utils.datetime_utils import now_ts_safe


class TaskRunner(threading.Thread):
    """任务执行器线程"""
    
    def __init__(
        self,
        *,
        base_dir: Path,
        cpu_pool: CpuPool,
        task_q: Queue[Task],
        on_update: callable,
        serial_sem: threading.Semaphore,
        queue_mode_fn: callable,
    ) -> None:
        """初始化任务执行器
        
        Args:
            base_dir: 项目根目录
            cpu_pool: CPU 池
            task_q: 任务队列
            on_update: 任务更新回调函数
            serial_sem: 串行模式信号量
            queue_mode_fn: 获取是否启用排队模式的函数
        """
        super().__init__(daemon=True)
        self._base_dir = base_dir
        # 计算工具目录路径（tools/runtime_compare/）
        self._tool_dir = Path(__file__).parent.parent.resolve()
        self._cpu_pool = cpu_pool
        self._task_q = task_q
        self._on_update = on_update
        self._stop_evt = threading.Event()
        self._serial_sem = serial_sem
        self._queue_mode_fn = queue_mode_fn

    def stop(self) -> None:
        """停止任务执行器"""
        self._stop_evt.set()

    def run(self) -> None:
        """主循环：从队列中获取任务并执行"""
        while not self._stop_evt.is_set():
            try:
                task = self._task_q.get(timeout=0.2)
            except Exception:
                continue
            self._run_one(task)
            self._task_q.task_done()

    def _run_one(self, task: Task) -> None:
        """执行单个任务"""
        acquired_serial = False
        try:
            if self._queue_mode_fn():
                self._serial_sem.acquire()
                acquired_serial = True
            
            # Acquire CPU group (优先使用 task.cpu_list 如果指定)
            group = self._cpu_pool.try_acquire_group(
                task.cores_per_task,
                preferred=task.cpu_list
            )
            if group is None:
                # Temporary shortage: keep it queued and try again later.
                task.status = "queued"
                task.phase = "wait_cpu"
                task.message = f"等待 CPU：需要 {task.cores_per_task} 核，当前空闲 {self._cpu_pool.free_count()}"
                self._on_update(task)
                time.sleep(0.5)
                self._task_q.put(task)
                return
            
            task.cpu_set = group
            task.status = "running"
            task.phase = "setup"
            task.start_ns = time.monotonic_ns()
            self._on_update(task)

            if task.use_sudo and not has_passwordless_sudo():
                task.status = "error"
                task.message = "启用 sudo 运行但当前不可用（请用 sudo 启动本工具，或配置 sudo NOPASSWD）。"
                self._on_update(task)
                return

            # Prepare output directories
            # 新的目录结构：实验结果/{config_name}/{timestamp}_ws{work_scale}_r{repeats}/
            exp_root = self._tool_dir / "实验结果"
            ensure_writable_dir(exp_root, use_sudo=task.use_sudo)

            # 使用配置文件名作为主目录，如果没有则使用默认名称
            config_name = task.config_name if task.config_name else "experiment"
            ts = now_ts_safe()
            
            # 创建配置名称目录
            config_dir = exp_root / config_name
            ensure_writable_dir(config_dir, use_sudo=task.use_sudo)
            
            # 创建结果目录：{timestamp}_ws{work_scale}_r{repeats}
            out_dir = config_dir / f"{ts}_ws{task.work_scale}_r{task.repeats}"
            ensure_writable_dir(out_dir, use_sudo=task.use_sudo)
            task.out_dir = out_dir

            # Copy source directories to keep local headers.
            task.phase = "copy"
            task.progress_i = 0
            task.progress_n = 0
            self._on_update(task)

            baseline_src_root = task.baseline_c.parent
            prio_src_root = task.prio_c.parent

            baseline_dir = out_dir / "baseline" / baseline_src_root.name
            prio_dir = out_dir / "prio" / prio_src_root.name
            if baseline_dir.exists():
                shutil.rmtree(baseline_dir)
            if prio_dir.exists():
                shutil.rmtree(prio_dir)
            shutil.copytree(baseline_src_root, baseline_dir)
            shutil.copytree(prio_src_root, prio_dir)

            # Enforce CPU isolation inside the program too, if it sets affinity on its own.
            patched_affinity = {"baseline": False, "prio": False}
            patch_error: Optional[str] = None
            try:
                b_src = baseline_dir / task.baseline_c.name
                if b_src.exists():
                    txt = b_src.read_text(encoding="utf-8", errors="replace")
                    new_txt, changed = rewrite_sched_setaffinity_cpu_set(txt, task.cpu_set)
                    if changed:
                        b_src.write_text(new_txt, encoding="utf-8")
                        patched_affinity["baseline"] = True
                p_src = prio_dir / task.prio_c.name
                if p_src.exists():
                    txt = p_src.read_text(encoding="utf-8", errors="replace")
                    new_txt, changed = rewrite_sched_setaffinity_cpu_set(txt, task.cpu_set)
                    if changed:
                        p_src.write_text(new_txt, encoding="utf-8")
                        patched_affinity["prio"] = True
            except Exception as e:
                patch_error = str(e)

            # Compile both
            task.phase = "compile"
            task.progress_i = 0
            task.progress_n = 2
            self._on_update(task)

            baseline_bin = out_dir / "baseline" / "app_baseline"
            prio_bin = out_dir / "prio" / "app_prio"

            def compile_one(src_dir: Path, out_bin: Path) -> Tuple[int, str, str, str]:
                c_files = sorted([p.name for p in src_dir.glob("*.c")])
                cmd_parts = ["gcc", *GCC_FLAGS, f"-DWORK_SCALE={task.work_scale}", *c_files, "-o", str(out_bin)]
                cmd = cmd_parts
                proc = subprocess.run(cmd, cwd=str(src_dir), capture_output=True, text=True)
                return proc.returncode, proc.stdout or "", proc.stderr or "", " ".join(cmd_parts)

            rc, so, se, bcmd = compile_one(baseline_dir, baseline_bin)
            task.progress_i = 1
            self._on_update(task)
            (out_dir / "baseline" / "compile.log").write_text("CMD: " + bcmd + "\n" + so + se, encoding="utf-8")
            if rc != 0:
                raise RuntimeError(f"baseline 编译失败：{se[-500:]}")

            rc, so, se, pcmd = compile_one(prio_dir, prio_bin)
            task.progress_i = 2
            self._on_update(task)
            (out_dir / "prio" / "compile.log").write_text("CMD: " + pcmd + "\n" + so + se, encoding="utf-8")
            if rc != 0:
                raise RuntimeError(f"prio 编译失败：{se[-500:]}")

            # Run repeats
            task.phase = "run"
            task.progress_i = 0
            task.progress_n = task.repeats * 2
            self._on_update(task)

            env = dict(os.environ)
            env["WORK_SCALE"] = str(task.work_scale)

            baseline_times: List[float] = []
            prio_times: List[float] = []
            runs: List[Dict] = []

            run_log = []

            def run_prog(label: str, bin_path: Path, iter_idx: int) -> float:
                rc, out, err, wall_ns = run_with_affinity(
                    [str(bin_path)],
                    cwd=bin_path.parent,
                    env=env,
                    cpu_set=task.cpu_set,
                    use_sudo=task.use_sudo,
                )
                run_log.append(f"=== {label} run (rc={rc}) ===\n")
                run_log.append(out)
                if err:
                    run_log.append("\n[stderr]\n")
                    run_log.append(err)
                run_log.append("\n")
                block_lines = [f"----- [{label}] run #{iter_idx+1} (rc={rc}) -----\n", out]
                if err:
                    block_lines.append("\n[stderr]\n")
                    block_lines.append(err)
                block = "".join(block_lines)
                parsed = True
                t = parse_internal_time_seconds(out)
                if t is None:
                    parsed = False
                    t = wall_ns / 1e9
                    run_log.append(f"[warn] failed to parse internal time; fallback wall_s={t:.6f}\n\n")
                    block += f"\n[warn] failed to parse internal time; fallback wall_s={t:.6f}\n"
                if rc != 0:
                    raise RuntimeError(f"{label} 运行失败：rc={rc}, stderr_tail={err[-400:]}")
                runs.append(
                    {
                        "program": label,
                        "iter": int(iter_idx),
                        "time_s": float(t),
                        "wall_s": float(wall_ns / 1e9),
                        "parsed_from_stdout": bool(parsed),
                        "cpu_set": task.cpu_set,
                        "returncode": int(rc),
                        "log_text": block,
                    }
                )
                return float(t)

            for i in range(task.repeats):
                t = run_prog("baseline", baseline_bin, i)
                baseline_times.append(t)
                task.progress_i += 1
                self._on_update(task)

                t = run_prog("prio", prio_bin, i)
                prio_times.append(t)
                task.progress_i += 1
                self._on_update(task)

            # Summarize
            def stats(xs: List[float]) -> Dict[str, float]:
                xs2 = xs[:]
                xs2.sort()
                n = len(xs2)
                mean = sum(xs2) / max(1, n)
                med = xs2[n // 2] if n else 0.0
                return {
                    "n": float(n),
                    "min_s": float(xs2[0]) if n else 0.0,
                    "max_s": float(xs2[-1]) if n else 0.0,
                    "mean_s": float(mean),
                    "median_s": float(med),
                }

            baseline_stat = stats(baseline_times)
            prio_stat = stats(prio_times)

            delta_mean = prio_stat["mean_s"] - baseline_stat["mean_s"]
            improve = None
            if baseline_stat["mean_s"] > 1e-12:
                improve = (baseline_stat["mean_s"] - prio_stat["mean_s"]) / baseline_stat["mean_s"]

            summary = {
                "task_id": task.task_id,
                "created_at": ts,
                "cpu_set": task.cpu_set,
                "cores_per_task": task.cores_per_task,
                "work_scale": task.work_scale,
                "repeats": task.repeats,
                "affinity_rewritten_in_source": patched_affinity,
                "baseline": {
                    "c_file": str(task.baseline_c),
                    "compile_cmd": bcmd.strip(),
                    "stats": baseline_stat,
                    "times_s": baseline_times,
                },
                "prio": {
                    "c_file": str(task.prio_c),
                    "compile_cmd": pcmd.strip(),
                    "stats": prio_stat,
                    "times_s": prio_times,
                },
                "runs": runs,
                "delta_mean_s": float(delta_mean),
                "improvement_ratio": float(improve) if improve is not None else None,
            }
            if patch_error:
                summary["affinity_patch_error"] = patch_error
            (out_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
            (out_dir / "run.log").write_text("".join(run_log), encoding="utf-8")
            
            # CSV output
            try:
                csv_lines = ["program,iter,time_s,wall_s,parsed_from_stdout,cpu_set\n"]
                for r in runs:
                    csv_lines.append(
                        f"{r['program']},{r['iter']},{r['time_s']:.9f},{r['wall_s']:.9f},{int(r['parsed_from_stdout'])},\"{format_cpu_set(r['cpu_set'])}\"\n"
                    )
                (out_dir / "runs.csv").write_text("".join(csv_lines), encoding="utf-8")
            except Exception:
                pass

            # txt summary (run.sh style)
            try:
                txt_name = f"run_results_{ts}_ws{task.work_scale}_r{task.repeats}.txt"
                txt_path = out_dir / txt_name
                lines: List[str] = []
                lines.append(f"=== RUN at {ts} (WORK_SCALE={task.work_scale}, REPEATS={task.repeats}) ===\n")
                lines.append(f"baseline_bin={baseline_bin}\n")
                lines.append(f"prio_bin={prio_bin}\n\n")
                lines.append("=== PAIRED RESULTS (program-reported time, seconds) ===\n")
                lines.append("run\tbaseline\tprio\tdelta(prio-baseline)\n")
                for i in range(task.repeats):
                    b = baseline_times[i]
                    p = prio_times[i]
                    lines.append(f"{i+1}\t{b:.6f}\t{p:.6f}\t{(p-b):+.6f}\n")
                lines.append("\n=== BASELINE STATS (program time) ===\n")
                lines.append(f"times_s={[round(x,6) for x in baseline_times]}\n")
                lines.append(f"mean={baseline_stat['mean_s']:.6f}s min={baseline_stat['min_s']:.6f}s max={baseline_stat['max_s']:.6f}s rcs={[r['returncode'] for r in runs if r['program']=='baseline']}\n")
                lines.append("\n=== PRIO STATS (program time) ===\n")
                lines.append(f"times_s={[round(x,6) for x in prio_times]}\n")
                lines.append(f"mean={prio_stat['mean_s']:.6f}s min={prio_stat['min_s']:.6f}s max={prio_stat['max_s']:.6f}s rcs={[r['returncode'] for r in runs if r['program']=='prio']}\n")
                if patch_error:
                    lines.append(f"\n[warn] affinity rewrite failed: {patch_error}\n")
                elif not any(patched_affinity.values()):
                    lines.append("\n[warn] affinity rewrite not applied (no sched_setaffinity pattern found)\n")
                lines.append("\n=== LOGS (raw program output) ===\n")
                for r in runs:
                    prog_s = r["time_s"]
                    lines.append(f"\n----- [{r['program']}] run #{r['iter']+1} (program={prog_s:.6f}s, rc={r['returncode']}) -----\n")
                    lines.append(r.get("log_text",""))
                    if not r.get("log_text"):
                        lines.append("(log missing)\n")
                txt_path.write_text("".join(lines), encoding="utf-8")
            except Exception:
                pass

            task.status = "done"
            task.phase = "done"
            task.message = f"完成：baseline mean={baseline_stat['mean_s']:.3f}s, prio mean={prio_stat['mean_s']:.3f}s"
            task.end_ns = time.monotonic_ns()
            self._on_update(task)
        except Exception as e:
            task.status = "error"
            task.phase = "error"
            task.message = str(e)
            task.end_ns = time.monotonic_ns()
            self._on_update(task)
        finally:
            if task.cpu_set:
                self._cpu_pool.release_group(task.cpu_set)
            if acquired_serial:
                self._serial_sem.release()
