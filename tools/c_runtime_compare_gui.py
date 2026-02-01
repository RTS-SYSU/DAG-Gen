#!/usr/bin/env python3
"""
GUI tool: compare runtime of two C programs (baseline vs prio) with CPU core isolation.

Key features (per user requirements):
- Inputs: two C files; compile via gcc: -O2 -g -std=c11 -pthread -lm
- UI supports setting WORK_SCALE and run count (repeat)
- Runs tasks in background; user can enqueue more tasks while others run
- Each task gets an exclusive CPU core set (size configurable); tasks do not share cores
- Optional "sudo" execution support:
  - If enabled, the tool requires either running as root or passwordless sudo (sudo -n)
- Results stored under mycallyplus_v1/experiment/<baseline_stem>/... with baseline/prio subfolders
- UI shows queue/progress, assigned cores, elapsed time, and buttons to open result folder

Limitations (current by design):
- Assumes each C file can be built as a standalone program (single translation unit).
  If it depends on extra .c files, extend compile step accordingly.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from queue import Queue
from typing import Dict, List, Optional, Tuple

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


GCC_FLAGS = ["-O0", "-g", "-std=c11", "-pthread", "-Wl,--wrap=main", "-lm"]
DEFAULT_MAX_WORKERS = 4


def _now_ts_safe() -> str:
    # Similar style to existing run_results naming (date -Iseconds with ':' replaced)
    ts = datetime.now().astimezone().isoformat(timespec="seconds")
    return ts.replace(":", "-")


def _read_cpu_online() -> List[int]:
    # Best-effort parse Linux CPU online list like "0-3,8-11".
    # Fallback to 0..os.cpu_count()-1.
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


def _format_cpu_set(cpus: List[int]) -> str:
    return ",".join(str(x) for x in cpus)


def _ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)


def _open_in_file_manager(path: Path) -> None:
    # Linux default; ignore errors.
    try:
        subprocess.Popen(["xdg-open", str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _has_passwordless_sudo() -> bool:
    if os.geteuid() == 0:
        return True
    try:
        subprocess.run(["sudo", "-n", "true"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def _ensure_writable_dir(path: Path, *, use_sudo: bool) -> None:
    """Ensure `path` exists and is writable by current user.

    If `use_sudo` is enabled and passwordless sudo/root is available, attempts to fix ownership.
    """
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

    if use_sudo and _has_passwordless_sudo():
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


def _parse_internal_time_seconds(stdout: str) -> Optional[float]:
    # Prefer PROGRAM_TOTAL_NS=... ; fallback to lines containing "total time".
    ns_candidates: List[int] = []
    time_candidates: List[float] = []
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


def _rewrite_sched_setaffinity_cpu_set(source: str, cpu_set: List[int]) -> Tuple[str, bool]:
    """Best-effort rewrite for common pattern:

      cpu_set_t set;
      CPU_ZERO(&set);
      CPU_SET(..., &set);
      ...
      sched_setaffinity(0, sizeof(set), &set)

    We replace the CPU_SET lines to match `cpu_set`, to prevent the program from
    overriding the tool-assigned CPU isolation.
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


def _run_with_affinity(
    cmd: List[str],
    *,
    cwd: Path,
    env: Dict[str, str],
    cpu_set: List[int],
    use_sudo: bool,
) -> Tuple[int, str, str, int]:
    # Returns (returncode, stdout, stderr, wall_ns)
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


@dataclass
class Task:
    task_id: str
    baseline_c: Path
    prio_c: Path
    work_scale: int
    repeats: int
    cores_per_task: int
    use_sudo: bool

    status: str = "queued"  # queued|running|done|error
    message: str = ""
    cpu_set: List[int] = field(default_factory=list)
    start_ns: Optional[int] = None
    end_ns: Optional[int] = None

    out_dir: Optional[Path] = None

    # Progress detail: (phase, i, n)
    phase: str = "queued"
    progress_i: int = 0
    progress_n: int = 0


class CpuPool:
    def __init__(self, cpus: List[int]) -> None:
        self._cpus = cpus[:]
        self._lock = threading.Lock()
        self._leased: List[List[int]] = []

    def try_acquire_group(self, k: int) -> Optional[List[int]]:
        with self._lock:
            free = [c for c in self._cpus if all(c not in g for g in self._leased)]
            if len(free) < k:
                return None
            group = free[:k]
            self._leased.append(group)
            return group

    def release_group(self, group: List[int]) -> None:
        with self._lock:
            self._leased = [g for g in self._leased if g != group]

    def free_count(self) -> int:
        with self._lock:
            used = {c for g in self._leased for c in g}
            return len([c for c in self._cpus if c not in used])

    def total_count(self) -> int:
        return len(self._cpus)


class TaskRunner(threading.Thread):
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
        super().__init__(daemon=True)
        self._base_dir = base_dir
        self._cpu_pool = cpu_pool
        self._task_q = task_q
        self._on_update = on_update
        self._stop_evt = threading.Event()
        self._serial_sem = serial_sem
        self._queue_mode_fn = queue_mode_fn

    def stop(self) -> None:
        self._stop_evt.set()

    def run(self) -> None:
        while not self._stop_evt.is_set():
            try:
                task = self._task_q.get(timeout=0.2)
            except Exception:
                continue
            self._run_one(task)
            self._task_q.task_done()

    def _run_one(self, task: Task) -> None:
        acquired_serial = False
        try:
            if self._queue_mode_fn():
                self._serial_sem.acquire()
                acquired_serial = True
            # Acquire CPU group
            group = self._cpu_pool.try_acquire_group(task.cores_per_task)
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

            if task.use_sudo and not _has_passwordless_sudo():
                task.status = "error"
                task.message = "启用 sudo 运行但当前不可用（请用 sudo 启动本工具，或配置 sudo NOPASSWD）。"
                self._on_update(task)
                return

            # Prepare output directories
            exp_root = self._base_dir / "experiment"
            _ensure_writable_dir(exp_root, use_sudo=task.use_sudo)

            base_stem = task.baseline_c.stem
            prio_stem = task.prio_c.stem
            ts = _now_ts_safe()
            root_bucket = exp_root / base_stem
            _ensure_writable_dir(root_bucket, use_sudo=task.use_sudo)
            out_dir = root_bucket / f"compare_{base_stem}_vs_{prio_stem}" / f"{ts}_ws{task.work_scale}_r{task.repeats}_c{task.cores_per_task}"
            _ensure_writable_dir(out_dir, use_sudo=task.use_sudo)
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
            # This is done only in the copied sources (never touches originals).
            patched_affinity = {"baseline": False, "prio": False}
            patch_error: Optional[str] = None
            try:
                b_src = baseline_dir / task.baseline_c.name
                if b_src.exists():
                    txt = b_src.read_text(encoding="utf-8", errors="replace")
                    new_txt, changed = _rewrite_sched_setaffinity_cpu_set(txt, task.cpu_set)
                    if changed:
                        b_src.write_text(new_txt, encoding="utf-8")
                        patched_affinity["baseline"] = True
                p_src = prio_dir / task.prio_c.name
                if p_src.exists():
                    txt = p_src.read_text(encoding="utf-8", errors="replace")
                    new_txt, changed = _rewrite_sched_setaffinity_cpu_set(txt, task.cpu_set)
                    if changed:
                        p_src.write_text(new_txt, encoding="utf-8")
                        patched_affinity["prio"] = True
            except Exception as e:
                patch_error = str(e)

            # Compile both (single file build)
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
            env["WORK_SCALE"] = str(task.work_scale)  # in case program reads env (optional)

            baseline_times: List[float] = []
            prio_times: List[float] = []
            runs: List[Dict] = []

            run_log = []

            def run_prog(label: str, bin_path: Path, iter_idx: int) -> float:
                rc, out, err, wall_ns = _run_with_affinity(
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
                t = _parse_internal_time_seconds(out)
                if t is None:
                    # Fallback: record wall time and mark parsing failure.
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
            # Convenience: per-run time table
            try:
                csv_lines = ["program,iter,time_s,wall_s,parsed_from_stdout,cpu_set\n"]
                for r in runs:
                    csv_lines.append(
                        f"{r['program']},{r['iter']},{r['time_s']:.9f},{r['wall_s']:.9f},{int(r['parsed_from_stdout'])},\"{_format_cpu_set(r['cpu_set'])}\"\n"
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


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("C 程序对照测时工具（baseline vs prio）")
        self.geometry("1100x650")

        self.base_dir = Path(__file__).resolve().parents[1]  # mycallyplus_v1/

        self.cpu_list = _read_cpu_online()
        self.cpu_pool = CpuPool(self.cpu_list)

        self.task_q: Queue[Task] = Queue()
        self.tasks: List[Task] = []
        self.var_queue_mode = tk.BooleanVar(value=False)
        self._serial_sem = threading.Semaphore(1)

        self._build_ui()

        # Start a small worker pool so tasks can run concurrently on disjoint CPU sets.
        max_workers = min(DEFAULT_MAX_WORKERS, max(1, len(self.cpu_list)))
        self.runners: List[TaskRunner] = []
        for _ in range(max_workers):
            r = TaskRunner(
                base_dir=self.base_dir,
                cpu_pool=self.cpu_pool,
                task_q=self.task_q,
                on_update=self._on_task_update,
                serial_sem=self._serial_sem,
                queue_mode_fn=lambda: bool(self.var_queue_mode.get()),
            )
            r.start()
            self.runners.append(r)

        self.after(200, self._tick_elapsed)

    def _build_ui(self) -> None:
        frm = ttk.Frame(self)
        frm.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Top controls
        top = ttk.LabelFrame(frm, text="新建实验任务")
        top.pack(fill=tk.X)

        self.var_baseline = tk.StringVar()
        self.var_prio = tk.StringVar()
        self.var_work_scale = tk.StringVar(value="25000")
        self.var_repeats = tk.StringVar(value="1")
        self.var_cores = tk.StringVar(value="1")
        self.var_use_sudo = tk.BooleanVar(value=False)

        def pick(var: tk.StringVar) -> None:
            p = filedialog.askopenfilename(title="选择 C 文件", filetypes=[("C file", "*.c"), ("All", "*.*")])
            if p:
                var.set(p)

        row0 = ttk.Frame(top)
        row0.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(row0, text="baseline C:").pack(side=tk.LEFT)
        ttk.Entry(row0, textvariable=self.var_baseline, width=80).pack(side=tk.LEFT, padx=6)
        ttk.Button(row0, text="选择", command=lambda: pick(self.var_baseline)).pack(side=tk.LEFT)

        row1 = ttk.Frame(top)
        row1.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(row1, text="prio C:").pack(side=tk.LEFT)
        ttk.Entry(row1, textvariable=self.var_prio, width=80).pack(side=tk.LEFT, padx=6)
        ttk.Button(row1, text="选择", command=lambda: pick(self.var_prio)).pack(side=tk.LEFT)

        row2 = ttk.Frame(top)
        row2.pack(fill=tk.X, padx=8, pady=6)
        ttk.Label(row2, text="WORK_SCALE:").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.var_work_scale, width=10).pack(side=tk.LEFT, padx=6)
        ttk.Label(row2, text="重复次数:").pack(side=tk.LEFT, padx=(12, 0))
        ttk.Entry(row2, textvariable=self.var_repeats, width=6).pack(side=tk.LEFT, padx=6)
        ttk.Label(row2, text="每任务核数:").pack(side=tk.LEFT, padx=(12, 0))
        ttk.Entry(row2, textvariable=self.var_cores, width=6).pack(side=tk.LEFT, padx=6)
        ttk.Checkbutton(row2, text="sudo 运行(需 root 或 sudo -n)", variable=self.var_use_sudo).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Checkbutton(row2, text="单并发排队模式", variable=self.var_queue_mode).pack(side=tk.LEFT, padx=(12, 0))

        row3 = ttk.Frame(top)
        row3.pack(fill=tk.X, padx=8, pady=6)

        ttk.Label(row3, text=f"在线 CPU: {len(self.cpu_list)} (online={_format_cpu_set(self.cpu_list)})").pack(side=tk.LEFT)
        self.lbl_cpu_free = ttk.Label(row3, text="")
        self.lbl_cpu_free.pack(side=tk.LEFT, padx=12)

        ttk.Button(row3, text="打开 experiment 目录", command=lambda: _open_in_file_manager(self.base_dir / "experiment")).pack(side=tk.RIGHT)

        ttk.Button(row3, text="加入队列", command=self._enqueue_task).pack(side=tk.RIGHT, padx=8)

        # Task list
        mid = ttk.LabelFrame(frm, text="后台任务")
        mid.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        cols = ("id", "status", "phase", "progress", "cpu", "elapsed", "message", "out")
        self.tree = ttk.Treeview(mid, columns=cols, show="headings", height=16)
        for c, w in [
            ("id", 120),
            ("status", 80),
            ("phase", 90),
            ("progress", 90),
            ("cpu", 120),
            ("elapsed", 90),
            ("message", 320),
            ("out", 260),
        ]:
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        btns = ttk.Frame(mid)
        btns.pack(fill=tk.X, padx=8, pady=(0, 8))
        ttk.Button(btns, text="打开选中任务结果目录", command=self._open_selected_out_dir).pack(side=tk.LEFT)
        ttk.Button(btns, text="复制选中任务结果路径", command=self._copy_selected_out_dir).pack(side=tk.LEFT, padx=8)

        # Footer
        self.status_bar = ttk.Label(frm, text="", anchor=tk.W)
        self.status_bar.pack(fill=tk.X, pady=(8, 0))

        self._refresh_cpu_label()

    def _refresh_cpu_label(self) -> None:
        self.lbl_cpu_free.configure(text=f"空闲核数: {self.cpu_pool.free_count()} / {self.cpu_pool.total_count()}")

    def _enqueue_task(self) -> None:
        try:
            baseline = Path(self.var_baseline.get()).expanduser().resolve()
            prio = Path(self.var_prio.get()).expanduser().resolve()
            if not baseline.exists() or baseline.suffix.lower() != ".c":
                raise ValueError("baseline C 文件无效")
            if not prio.exists() or prio.suffix.lower() != ".c":
                raise ValueError("prio C 文件无效")
            work_scale = int(self.var_work_scale.get().strip())
            repeats = int(self.var_repeats.get().strip())
            cores = int(self.var_cores.get().strip())
            use_sudo = bool(self.var_use_sudo.get())
            if repeats < 1:
                raise ValueError("重复次数必须 >= 1")
            if cores < 1:
                raise ValueError("每任务核数必须 >= 1")
        except Exception as e:
            messagebox.showerror("参数错误", str(e))
            return

        # Warn if CPU cores not enough to even run one task.
        if cores > len(self.cpu_list):
            messagebox.showwarning("CPU 不足", f"需要 {cores} 核，但在线 CPU 只有 {len(self.cpu_list)}。")
            return

        task_id = f"{baseline.stem}_vs_{prio.stem}_{_now_ts_safe()}"
        task = Task(
            task_id=task_id,
            baseline_c=baseline,
            prio_c=prio,
            work_scale=work_scale,
            repeats=repeats,
            cores_per_task=cores,
            use_sudo=use_sudo,
        )
        self.tasks.append(task)
        self.task_q.put(task)
        self._insert_or_update_row(task)
        self.status_bar.configure(text=f"已加入队列：{task_id}")
        self._refresh_cpu_label()

    def _insert_or_update_row(self, task: Task) -> None:
        vals = (
            task.task_id,
            task.status,
            task.phase,
            f"{task.progress_i}/{task.progress_n}" if task.progress_n else "",
            _format_cpu_set(task.cpu_set) if task.cpu_set else "",
            self._elapsed_str(task),
            task.message,
            str(task.out_dir) if task.out_dir else "",
        )
        if self.tree.exists(task.task_id):
            for i, v in enumerate(vals):
                self.tree.set(task.task_id, self.tree["columns"][i], v)
        else:
            self.tree.insert("", tk.END, iid=task.task_id, values=vals)

    def _elapsed_str(self, task: Task) -> str:
        if task.start_ns is None:
            return ""
        end = task.end_ns if task.end_ns is not None else time.monotonic_ns()
        sec = (end - task.start_ns) / 1e9
        return f"{sec:.1f}s"

    def _on_task_update(self, task: Task) -> None:
        # Called from background thread; marshal to UI thread.
        def cb() -> None:
            self._insert_or_update_row(task)
            self._refresh_cpu_label()
            if task.status in ("done", "error"):
                self.status_bar.configure(text=f"{task.task_id}: {task.status} - {task.message}")
        self.after(0, cb)

    def _tick_elapsed(self) -> None:
        for t in self.tasks:
            if t.status in ("running", "queued"):
                self._insert_or_update_row(t)
        self._refresh_cpu_label()
        self.after(500, self._tick_elapsed)

    def _selected_task(self) -> Optional[Task]:
        sel = self.tree.selection()
        if not sel:
            return None
        task_id = sel[0]
        for t in self.tasks:
            if t.task_id == task_id:
                return t
        return None

    def _open_selected_out_dir(self) -> None:
        t = self._selected_task()
        if not t or not t.out_dir:
            return
        _open_in_file_manager(t.out_dir)

    def _copy_selected_out_dir(self) -> None:
        t = self._selected_task()
        if not t or not t.out_dir:
            return
        self.clipboard_clear()
        self.clipboard_append(str(t.out_dir))
        self.status_bar.configure(text=f"已复制路径：{t.out_dir}")


def main() -> int:
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
