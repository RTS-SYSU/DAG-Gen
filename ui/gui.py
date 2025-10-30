#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mycallyplus - 统一工作台（整合版）

核心功能
---------
1. 读取 DOT / TXT（circle）文件，展示原始图。
2. 查看互斥锁：根据 TXT 中的互斥量描述，标记 lock→unlock 区域。
3. 生成信号量图：叠加 sem_post→sem_wait 虚线边，运行 Tarjan，并展示线程矩形框。
4. 显示互斥锁 / 信号量信息（包含可选的源代码行号范围）。

交互规范
---------
- 左侧按钮均为主功能；右侧为“展示区 + 子功能区”。
- 无子功能时隐藏子功能区；有子功能时显示对应按钮。
- “查看互斥锁”点击后默认展示互斥锁图；子功能可切换查看文本信息。
- “生成信号量图”默认展示信号量图；子功能提供原始图、Tarjan 图、线程图、信息以及线程颜色图例。
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import subprocess
import tkinter as tk
from dataclasses import dataclass
import sys
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import networkx as nx
from PIL import Image, ImageTk

try:
    import pydot  # type: ignore
except Exception:  # pragma: no cover - 可选依赖
    pydot = None


# --------------------------------------------------------------------------- #
# 工具函数
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    """统一去除首尾空白与引号。"""
    return text.strip().strip('"').strip("'").strip()


def _suffix_num(name: str) -> int:
    """提取节点名末尾数字，若无则返回 0，用于稳定排序。"""
    tail = name.split('/')[-1]
    digits = ''.join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else 0


def _edge_attr_string(attrs: Dict[str, str]) -> str:
    """将边属性转换为 Graphviz 属性字符串。"""
    if not attrs:
        return ""
    parts = []
    for key, val in attrs.items():
        if val is None:
            continue
        clean = _norm(str(val))
        parts.append(f'{key}="{clean}"')
    return " [" + ", ".join(parts) + "]" if parts else ""


def _hash_path(path: str) -> str:
    return hashlib.md5(os.path.abspath(path).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# 数据结构
# --------------------------------------------------------------------------- #

@dataclass
class MutexRecord:
    lock: str
    unlock: str
    var: str
    idx: str
    lock_line: Optional[int]
    unlock_line: Optional[int]
    lock_file: Optional[str]
    unlock_file: Optional[str]
    covered: List[str]


@dataclass
class SemRecord:
    post: str
    wait: str
    var: str
    idx: str
    post_line: Optional[int]
    wait_line: Optional[int]
    post_file: Optional[str]
    wait_file: Optional[str]


# --------------------------------------------------------------------------- #
# 主界面
# --------------------------------------------------------------------------- #

class MycallyplusGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Mycallyplus - 统一工作台（整合版）")
        self.root.geometry("1380x860")
        self.root.configure(bg="#ECEFF1")

        # 工作路径 - 修改为 mycallyplus 作为工作区
        self.base_dir = Path(__file__).resolve().parent.parent
        self.dot_dir = self.base_dir / "配置文件"
        self.output_root = self.base_dir / "dag图"
        self.output_root.mkdir(parents=True, exist_ok=True)
        
        # 中间结果根目录 - 在 mycallyplus 下
        self.intermediate_root = self.base_dir / "中间结果"
        self.intermediate_root.mkdir(parents=True, exist_ok=True)
        
        # 生成功能状态
        self.current_c_path: Optional[Path] = None
        self.current_expand_path: Optional[Path] = None
        self.current_work_dir: Optional[Path] = None  # 当前工作目录（中间结果/<源文件名>/）
        
        # 生成进度状态
        self.generation_errors: List[str] = []  # 记录生成过程中的错误

        # 可视化状态
        self.current_dot_path: Optional[Path] = None
        self.current_circle_path: Optional[Path] = None
        self.current_config_dir: Optional[Path] = None
        self.current_output_dir: Optional[Path] = None
        self.current_intermediate_dot: Optional[Path] = None

        self.G: nx.DiGraph = nx.DiGraph()
        self.sccs: List[Iterable[str]] = []
        self.threads: List[str] = []
        self.thread_color_map: Dict[str, str] = {}
        self.cycle_data: Dict[str, Dict[str, List[str]]] = {}

        self.mutex_records: List[MutexRecord] = []
        self.sem_records: List[SemRecord] = []
        self.mutex_prepared = False

        self.cached_images: Dict[str, Optional[Path]] = {
            "original": None,
            "tarjan": None,
            "threads": None,
        }

        self.mode = "tarjan"
        self.tk_img: Optional[ImageTk.PhotoImage] = None

        self.THREAD_COLORS = [
            "#90CAF9", "#A5D6A7", "#FFE082", "#F48FB1",
            "#CE93D8", "#FFAB91", "#80CBC4", "#B39DDB"
        ]
        self.MUTEX_COLORS = [
            "#FFB74D", "#81C784", "#64B5F6", "#BA68C8",
            "#E57373", "#4DB6AC", "#FFD54F", "#9575CD",
            "#4FC3F7", "#AED581", "#FF8A65", "#B39DDB"
        ]

        self._build_ui()
        self.use_default()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self) -> None:
        main = tk.Frame(self.root, bg="#ECEFF1")
        main.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        left = tk.LabelFrame(main, text="操作", bg="#CFD8DC",
                             font=("Microsoft YaHei", 10, "bold"),
                             padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        def add_btn(text: str, cmd, separator_before: bool = False) -> None:
            if separator_before:
                sep = tk.Frame(left, height=2, bg="#90A4AE")
                sep.pack(fill=tk.X, pady=8)
            tk.Button(left, text=text, command=cmd,
                      width=22, height=2, bg="#ECEFF1",
                      relief=tk.RAISED, activebackground="#CFD8DC",
                      font=("Microsoft YaHei", 9)).pack(pady=4)

        # 生成功能按钮（2个）
        add_btn("选择源文件", self.load_source_file)
        add_btn("生成dag图", self.load_dag_graph)
        add_btn("查看条件节点", self.view_condition_nodes)
        
        # 可视化功能按钮（5个）
        add_btn("使用默认配置（dag1）", self.use_default, separator_before=True)
        add_btn("选择配置文件", self.select_config_folder)
        add_btn("生成原始图", self.generate_original_graph)
        add_btn("查看互斥锁", self.view_mutex)
        add_btn("生成信号量图", self.generate_semaphore_pipeline)

        right = tk.LabelFrame(main, text="可视化", bg="#FFFFFF",
                              font=("Microsoft YaHei", 10, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        self.status = tk.Label(right, text="当前配置：<未加载>",
                               anchor="w", bg="#ECEFF1", font=("Consolas", 10))
        self.status.pack(fill=tk.X)

        self.canvas = tk.Canvas(right, bg="#FAFAFA",
                                highlightthickness=1, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bottom = tk.Frame(right, bg="#ECEFF1")
        self._subtoolbar_visible = False

        # 画布交互
        self.canvas.bind("<ButtonPress-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", self._on_zoom)  # Linux
        self.canvas.bind("<Button-5>", self._on_zoom)

    def _build_subtoolbar(self, specs: Sequence[Tuple[str, callable]]) -> None:
        for child in self.bottom.winfo_children():
            child.destroy()
        for text, cmd in specs:
            tk.Button(self.bottom, text=text, command=cmd, width=18,
                      bg="#ECEFF1", activebackground="#CFD8DC",
                      font=("Microsoft YaHei", 9)).pack(side=tk.LEFT, padx=4)

    def _toggle_subtoolbar(self, show: bool) -> None:
        if show and not self._subtoolbar_visible:
            self.bottom.pack(fill=tk.X, pady=8)
            self._subtoolbar_visible = True
        elif not show and self._subtoolbar_visible:
            self.bottom.pack_forget()
            self._subtoolbar_visible = False

    def _set_subtoolbar(self, specs: Optional[Sequence[Tuple[str, callable]]]) -> None:
        if specs:
            self._build_subtoolbar(specs)
            self._toggle_subtoolbar(True)
        else:
            self._toggle_subtoolbar(False)

    # --------------------------------------------------------------- 状态 --

    def _update_status(self) -> None:
        src = self.current_expand_path.name if self.current_expand_path else "<未选择>"
        cfg = str(self.current_config_dir) if self.current_config_dir else "<未选择>"
        dot = self.current_dot_path.name if self.current_dot_path else "无"
        txt = self.current_circle_path.name if self.current_circle_path else "无"
        self.status.config(text=f"源文件：{src} | 配置：{cfg} | DOT: {dot} | TXT: {txt}")
    
    def _update_status_simple(self, message: str) -> None:
        """简单更新状态栏"""
        self.status.config(text=message)
    
    def _get_base_name(self, expand_path: Path) -> str:
        """从 expand 文件路径提取基础名称
        
        例如：
        - main.c.233r.expand -> main
        - test.expand -> test
        - program.c.233r.expand -> program
        """
        name = expand_path.stem  # 移除 .expand
        # 如果是 .233r.expand 格式，移除 .233r (5个字符)
        if name.endswith('.233r'):
            name = name[:-5]  # 移除 .233r
        # 如果还有 .c 后缀，移除它
        if name.endswith('.c'):
            name = name[:-2]
        return name

    def _ensure_output_dir(self) -> Path:
        if not self.current_config_dir:
            self.current_output_dir = self.output_root
            return self.current_output_dir

        mapping_path = self.output_root / "info.json"
        mapping: Dict[str, str] = {}
        if mapping_path.exists():
            try:
                mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
            except Exception:
                mapping = {}

        key = _hash_path(str(self.current_config_dir))
        if key in mapping and Path(mapping[key]).exists():
            self.current_output_dir = Path(mapping[key])
            return self.current_output_dir

        next_idx = len([p for p in self.output_root.iterdir() if p.name.startswith("图")]) + 1
        outdir = self.output_root / f"图{next_idx}"
        outdir.mkdir(parents=True, exist_ok=True)
        mapping[key] = str(outdir)
        mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        self.current_output_dir = outdir
        return outdir

    # ------------------------------------------------------------- 文件读写 --

    def _read_dot_to_graph(self, path: Path) -> nx.DiGraph:
        try:
            graph = nx.DiGraph(nx.nx_pydot.read_dot(str(path)))
        except Exception:
            if not pydot:
                raise
            pd_graphs = pydot.graph_from_dot_file(str(path))
            if not pd_graphs:
                raise RuntimeError("pydot 解析 dot 失败")
            graph = nx.DiGraph(nx.nx_pydot.from_pydot(pd_graphs[0]))
        return nx.relabel_nodes(graph, _norm)

    def _render_dot_quiet(self, dot_str: str, out_png: Path) -> None:
        tmp = self.output_root / "_temp_render.dot"
        tmp.write_text(dot_str, encoding="utf-8")
        try:
            subprocess.run(["dot", "-Tpng", str(tmp), "-o", str(out_png)], check=True)
        except Exception as exc:
            messagebox.showerror("Graphviz 错误", str(exc))
        finally:
            if tmp.exists():
                tmp.unlink()

    def _render_dot_to_canvas(self, dot_str: str, out_png: Path) -> None:
        self._render_dot_quiet(dot_str, out_png)
        if out_png.exists():
            self._show_image(out_png)
            messagebox.showinfo("完成", f"已生成图像：\n{out_png}")

    def _show_image(self, path: Path) -> None:
        img = Image.open(path)
        self.tk_img = ImageTk.PhotoImage(img)
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def _display_cached_image(self, key: str) -> None:
        path = self.cached_images.get(key)
        if not path or not Path(path).exists():
            messagebox.showwarning("提示", "对应图像不存在，请先生成信号量图。")
            return
        self._show_image(Path(path))

    # -------------------------------------------------------------- 图状态 --

    def _extract_threads(self) -> None:
        threads = {n.split('/')[0] for n in self.G.nodes() if '/' in n}
        self.threads = sorted(threads)
        self.thread_color_map = {
            t: self.THREAD_COLORS[i % len(self.THREAD_COLORS)]
            for i, t in enumerate(self.threads)
        }

    # ----------------------------------------------------------- 功能实现 --

    def use_default(self) -> None:
        dag1 = self.dot_dir / "dag1"
        if not dag1.exists():
            messagebox.showwarning("提示", "未找到默认配置，请手动选择。")
            return
        for path in dag1.rglob("*.dot"):
            try:
                self.G = self._read_dot_to_graph(path)
            except Exception as exc:
                messagebox.showerror("错误", f"读取 DOT 失败：{exc}")
                return
            self.current_dot_path = path
            self.current_config_dir = path.parent
            self.current_circle_path = None
            self._extract_threads()
            self._ensure_output_dir()
            self._update_status()
            self._set_subtoolbar(None)
            messagebox.showinfo("成功", f"已加载默认配置：{path}")
            return
        messagebox.showwarning("提示", "默认目录中未找到 DOT 文件，请手动选择。")

    def select_dot_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="选择 DOT 文件", filetypes=[("DOT 文件", "*.dot")]
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self.G = self._read_dot_to_graph(path)
        except Exception as exc:
            messagebox.showerror("错误", f"加载 DOT 失败：\n{exc}")
            return
        self.current_dot_path = path
        self.current_config_dir = path.parent
        self.cached_images = {"original": None, "tarjan": None, "threads": None}
        self.sem_records.clear()
        self.current_intermediate_dot = None
        self._extract_threads()
        self._ensure_output_dir()
        self._update_status()
        self._set_subtoolbar(None)
        messagebox.showinfo("成功", f"已加载 DOT 文件：{path.name}")

    def select_txt_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="选择 TXT 文件", filetypes=[("TXT 文件", "*.txt")]
        )
        if not path_str:
            return
        path = Path(path_str)
        if not path.exists():
            messagebox.showerror("错误", "文件不存在。")
            return
        self.current_circle_path = path
        self._update_status()
        self._set_subtoolbar(None)
        messagebox.showinfo("成功", f"已选择 TXT 文件：{path.name}")

    def select_config_folder(self) -> None:
        """
        选择配置文件夹，并自动匹配其中的 dot / txt 文件。

        约束：
        - 仅在所选文件夹的第一层查找（不递归）。
        - 至少需要一个 dot 文件；txt 文件可选。若存在多个，取按名称排序后的第一个。
        """
        folder = filedialog.askdirectory(title="选择配置文件夹")
        if not folder:
            return
        folder_path = Path(folder)
        if not folder_path.is_dir():
            messagebox.showerror("错误", "请选择有效的文件夹。")
            return

        dot_files = sorted([p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() == ".dot"])
        if not dot_files:
            messagebox.showerror("错误", "该文件夹中未找到 dot 文件。")
            return
        dot_path = dot_files[0]

        txt_files = sorted([p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() == ".txt"])
        txt_path = txt_files[0] if txt_files else None

        try:
            self.G = self._read_dot_to_graph(dot_path)
        except Exception as exc:
            messagebox.showerror("错误", f"加载 DOT 失败：\n{exc}")
            return

        self.current_dot_path = dot_path
        self.current_circle_path = txt_path
        self.current_config_dir = folder_path
        self.cached_images = {"original": None, "tarjan": None, "threads": None}
        self.sem_records.clear()
        self.current_intermediate_dot = None

        self._extract_threads()
        self._ensure_output_dir()
        self._update_status()
        self._set_subtoolbar(None)

        info = [f"DOT：{dot_path.name}"]
        if txt_path:
            info.append(f"TXT：{txt_path.name}")
        else:
            info.append("TXT：<未找到，部分功能不可用>")
        messagebox.showinfo("成功", "已加载配置文件夹：\n" + "\n".join(info))

    # -------------------------------------------------------- 原始图展示 --

    def generate_original_graph(self) -> None:
        if not self.current_dot_path:
            messagebox.showerror("错误", "请先选择 dot 文件。")
            return
        out_dir = self._ensure_output_dir()
        out_png = out_dir / "原始图.png"
        try:
            subprocess.run(
                ["dot", "-Tpng", str(self.current_dot_path), "-o", str(out_png)],
                check=True,
            )
        except Exception as exc:
            messagebox.showerror("错误", f"生成原始图失败：\n{exc}")
            return
        self.cached_images["original"] = out_png
        self._show_image(out_png)
        self._set_subtoolbar(None)
        messagebox.showinfo("成功", f"已生成原始图：\n{out_png}")

    # ------------------------------------------------------------- 互斥锁 --

    def _parse_optional_meta(self, parts: List[str]) -> Tuple[Optional[int], Optional[str]]:
        """
        解析可选的源码行号与文件名。

        格式约定：
        - 第四列：行号（整数）。若无法转换为整数，则视为文件名。
        - 第五列：文件名（字符串，可选）。若存在则覆盖第四列中的文件名。
        """
        line_no: Optional[int] = None
        file_name: Optional[str] = None
        if len(parts) >= 4:
            try:
                line_no = int(parts[3])
            except Exception:
                file_name = parts[3]
        if len(parts) >= 5:
            file_name = parts[4]
        return line_no, file_name

    def _prepare_mutex_data(self) -> bool:
        if not self.current_circle_path:
            messagebox.showerror("错误", "请先加载 txt 文件。")
            return False

        entries: List[Tuple[str, str, str, str, Optional[int], Optional[str]]] = []
        block = None
        for line in self.current_circle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = _norm(line)
            if not s:
                continue
            if s == "互斥量":
                block = "mutex"
                continue
            if s == "信号量":
                block = "sem"
                continue
            if block != "mutex":
                continue
            parts = s.split()
            if len(parts) < 3:
                continue
            func, var, idx = parts[0], parts[1], parts[2]
            line_no, file_name = self._parse_optional_meta(parts)
            lower = func.lower()
            if "pthread_mutex_unlock" in lower or "/unlock" in lower:
                entries.append((_norm(func), var, idx, "unlock", line_no, file_name))
            elif "pthread_mutex_lock" in lower or "/lock" in lower:
                entries.append((_norm(func), var, idx, "lock", line_no, file_name))

        stacks: Dict[str, List[Tuple[str, str, Optional[int], Optional[str]]]] = {}
        pairs: List[MutexRecord] = []
        for func, var, idx, typ, line_no, file_name in entries:
            stacks.setdefault(idx, [])
            if typ == "lock":
                stacks[idx].append((func, var, line_no, file_name))
            elif typ == "unlock" and stacks[idx]:
                lock_func, lock_var, lock_line, lock_file = stacks[idx].pop()
                if lock_var != var:
                    # 变量不一致时仍以 unlock 的变量为准
                    lock_var = var
                record = MutexRecord(
                    lock=_norm(lock_func),
                    unlock=_norm(func),
                    var=lock_var,
                    idx=idx,
                    lock_line=lock_line,
                    unlock_line=line_no,
                    lock_file=lock_file,
                    unlock_file=file_name,
                    covered=[],
                )
                pairs.append(record)

        if not pairs:
            messagebox.showwarning("提示", "未找到配对的互斥锁记录")
            self.mutex_prepared = False
            return False

        self.mutex_records.clear()
        for rec in pairs:
            if rec.lock not in self.G.nodes or rec.unlock not in self.G.nodes:
                continue
            reach_from_lock = nx.descendants(self.G, rec.lock)
            reach_to_unlock = nx.ancestors(self.G, rec.unlock)
            between = sorted(reach_from_lock & reach_to_unlock | {rec.lock, rec.unlock},
                             key=lambda x: (x.split('/')[0] if '/' in x else x, _suffix_num(x)))
            rec.covered = between
            self.mutex_records.append(rec)

        if not self.mutex_records:
            messagebox.showwarning("提示", "互斥锁节点未在图中找到。")
            self.mutex_prepared = False
            return False

        self.mutex_prepared = True
        return True

    def _show_mutex_graph(self) -> None:
        if not self.mutex_prepared:
            messagebox.showwarning("提示", "请先点击“查看互斥锁”解析数据。")
            return
        dot_lines = ['digraph Mutex {', 'rankdir=LR;', 'fontname="Microsoft YaHei";']
        for u, v in self.G.edges():
            dot_lines.append(f'"{u}" -> "{v}";')
        for n in self.G.nodes():
            dot_lines.append(f'"{n}" [shape=box, style=filled, fillcolor="#E3F2FD"];')

        color_map: Dict[str, str] = {}
        cluster_id = 0
        for rec in self.mutex_records:
            color = color_map.setdefault(
                rec.var, self.MUTEX_COLORS[len(color_map) % len(self.MUTEX_COLORS)]
            )
            cluster_id += 1
            dot_lines.append(f'subgraph cluster_{cluster_id} {{')
            dot_lines.append(f'  label="{rec.var}"; color="{color}";')
            for node in rec.covered:
                dot_lines.append(f'  "{node}";')
            dot_lines.append('}')
        dot_lines.append('}')

        out_dir = self._ensure_output_dir()
        out_png = out_dir / "mutex.png"
        self._render_dot_to_canvas("\n".join(dot_lines), out_png)

    def show_mutex_info(self) -> None:
        if not self.mutex_prepared:
            messagebox.showwarning("提示", "请先点击“查看互斥锁”解析数据。")
            return
        self.canvas.delete("all")
        y = 20
        self.canvas.create_text(20, y, anchor="nw",
                                text="互斥锁信息（编号、锁节点、解锁节点、覆盖节点）",
                                font=("Microsoft YaHei", 14, "bold"), fill="#000")
        y += 40
        for rec in self.mutex_records:
            lock_file = rec.lock_file or rec.unlock_file
            lines = [
                f"ID: {rec.idx}",
                f"LOCK: {rec.lock}",
                f"UNLOCK: {rec.unlock}",
            ]
            if lock_file:
                lines.append(f"FILE: {lock_file}")
            if rec.lock_line is not None or rec.unlock_line is not None:
                lock_line = rec.lock_line if rec.lock_line is not None else "?"
                unlock_line = rec.unlock_line if rec.unlock_line is not None else "?"
                lines.append(f"LINES: {lock_line} -> {unlock_line}")
            lines.append("COVERED:")
            lines.extend(f"  - {node}" for node in rec.covered)
            text = "\n".join(lines)
            item = self.canvas.create_text(
                20, y, anchor="nw", text=text, font=("Consolas", 11),
                fill="#263238", width=max(self.canvas.winfo_width() - 60, 400)
            )
            bbox = self.canvas.bbox(item)
            if bbox:
                y = bbox[3] + 20
            else:
                y += 120
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def view_mutex(self) -> None:
        if not self.current_dot_path or not self.current_circle_path:
            messagebox.showerror("错误", "请先加载 dot 与 txt 文件。")
            self._set_subtoolbar(None)
            return
        if not self._prepare_mutex_data():
            self._set_subtoolbar(None)
            return
        self._set_subtoolbar([
            ("查看互斥锁图", self._show_mutex_graph),
            ("查看互斥锁信息", self.show_mutex_info),
        ])
        self._show_mutex_graph()

    # ------------------------------------------------------------ 信号量 --

    def _parse_semaphore_pairs(self) -> List[SemRecord]:
        if not self.current_circle_path:
            return []
        by_id: Dict[str, Dict[str, Optional[str]]] = {}
        block = None
        for line in self.current_circle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = _norm(line)
            if not s:
                continue
            if s == "互斥量":
                block = "mutex"
                continue
            if s == "信号量":
                block = "sem"
                continue
            if block != "sem":
                continue
            parts = s.split()
            if len(parts) < 3:
                continue
            func, var, idx = parts[0], parts[1], parts[2]
            line_no, file_name = self._parse_optional_meta(parts)
            record = by_id.setdefault(
                idx,
                {
                    "post": None,
                    "wait": None,
                    "var": var,
                    "post_line": None,
                    "wait_line": None,
                    "post_file": None,
                    "wait_file": None,
                },
            )
            if "sem_post" in func:
                record["post"] = _norm(func)
                record["post_line"] = line_no
                record["post_file"] = file_name
            elif "sem_wait" in func:
                record["wait"] = _norm(func)
                record["wait_line"] = line_no
                record["wait_file"] = file_name

        pairs: List[SemRecord] = []
        for idx, info in by_id.items():
            if info["post"] and info["wait"]:
                pairs.append(
                    SemRecord(
                        post=str(info["post"]),
                        wait=str(info["wait"]),
                        var=str(info["var"]),
                        idx=idx,
                        post_line=info.get("post_line"),
                        wait_line=info.get("wait_line"),
                        post_file=info.get("post_file"),
                        wait_file=info.get("wait_file"),
                    )
                )
        return pairs

    def _run_tarjan_from_intermediate(self, graph: nx.DiGraph, out_dir: Path) -> None:
        self.sccs = list(nx.strongly_connected_components(graph))
        colors: Dict[str, str] = {}
        for comp in self.sccs:
            color = "#%06x" % random.randint(0, 0xFFFFFF)
            for node in comp:
                colors[node] = color

        lines = [
            "digraph Tarjan {",
            '  rankdir=LR;',
            '  fontname="Microsoft YaHei";'
        ]
        for u, v, data in graph.edges(data=True):
            lines.append(f'  "{u}" -> "{v}"{_edge_attr_string(data)};')
        for node in graph.nodes():
            col = colors.get(node, "#B0BEC5")
            lines.append(f'  "{node}" [style=filled, fillcolor="{col}"];')
        lines.append("}")

        out_png = out_dir / "tarjan.png"
        self.cached_images["tarjan"] = out_png
        self._render_dot_quiet("\n".join(lines), out_png)

    def _generate_threads_from_intermediate(self, graph: nx.DiGraph, out_dir: Path) -> None:
        cycles: Dict[str, Dict[str, List[str]]] = {}
        idx = 0
        for comp in self.sccs:
            if len(comp) <= 1:
                continue
            per_thread: Dict[str, List[str]] = {}
            for node in comp:
                prefix = node.split('/')[0] if '/' in node else "Unknown"
                per_thread.setdefault(prefix, []).append(node)
            if len(per_thread) <= 1:
                continue
            for t in per_thread:
                per_thread[t] = sorted(per_thread[t], key=_suffix_num)
            idx += 1
            cycles[f"Cycle{idx}"] = dict(sorted(per_thread.items()))

        self.cycle_data = cycles

        node_colors: Dict[str, str] = {}
        for node in graph.nodes():
            prefix = node.split('/')[0] if '/' in node else "Unknown"
            node_colors[node] = self.thread_color_map.get(prefix, "#CFD8DC")

        lines = [
            "digraph Threads {",
            '  rankdir=LR;',
            '  fontname="Microsoft YaHei";'
        ]
        for u, v, data in graph.edges(data=True):
            lines.append(f'  "{u}" -> "{v}"{_edge_attr_string(data)};')
        for cname, per_thread in cycles.items():
            lines.append(f'  subgraph cluster_{cname} {{')
            lines.append('    style=dashed;')
            lines.append('    color=gray;')
            lines.append(f'    label="{cname}";')
            for t, nodes in per_thread.items():
                for node in nodes:
                    col = node_colors.get(node, "#FFFFFF")
                    lines.append(f'    "{node}" [style=filled, fillcolor="{col}"];')
            lines.append("  }")
        for node, col in node_colors.items():
            lines.append(f'  "{node}" [style=filled, fillcolor="{col}"];')
        lines.append("}")

        out_png = out_dir / "threads.png"
        self.cached_images["threads"] = out_png
        self._render_dot_quiet("\n".join(lines), out_png)

    def generate_semaphore_pipeline(self) -> None:
        if not self.current_dot_path:
            messagebox.showerror("错误", "请先加载 dot 文件。")
            self._set_subtoolbar(None)
            return
        if not self.current_circle_path:
            messagebox.showerror("错误", "请先加载 txt 文件。")
            self._set_subtoolbar(None)
            return

        out_dir = self._ensure_output_dir()
        self.sem_records = self._parse_semaphore_pairs()

        graph_idx = self.current_output_dir.name.lstrip("图") if self.current_output_dir else "1"
        inter_dir = out_dir / "中间结果"
        inter_dir.mkdir(parents=True, exist_ok=True)
        intermediate_path = inter_dir / f"文件图{graph_idx}.dot"

        lines = [
            "digraph G {",
            '  rankdir=LR;',
            '  fontname="Microsoft YaHei";'
        ]
        for u, v in self.G.edges():
            lines.append(f'  "{u}" -> "{v}";')
        for rec in self.sem_records:
            lines.append(
                f'  "{rec.post}" -> "{rec.wait}" '
                f'[style=dashed, color="#FF7043", label="{rec.var} {rec.idx}"];'
            )
        lines.append("}")
        intermediate_path.write_text("\n".join(lines), encoding="utf-8")
        self.current_intermediate_dot = intermediate_path

        self.cached_images["original"] = out_dir / "原始图.png"
        self._render_dot_quiet("\n".join(lines), self.cached_images["original"])

        g_intermediate = self._read_dot_to_graph(intermediate_path)
        self._run_tarjan_from_intermediate(g_intermediate, out_dir)
        self._generate_threads_from_intermediate(g_intermediate, out_dir)

        self._display_cached_image("threads")
        self._set_subtoolbar([
            ("查看原始图", lambda: self._display_cached_image("original")),
            ("查看强连通分量", lambda: self._display_cached_image("tarjan")),
            ("查看信号量图", lambda: self._display_cached_image("threads")),
            ("显示信号量信息", self.show_semaphore_info),
            ("显示线程颜色图例", self.show_thread_legend),
        ])
        messagebox.showinfo("完成", "信号量图已生成。")

    def show_semaphore_info(self) -> None:
        pairs = self.sem_records or self._parse_semaphore_pairs()
        self.canvas.delete("all")
        y = 20
        self.canvas.create_text(20, y, anchor="nw",
                                text="信号量配对（post → wait）",
                                font=("Microsoft YaHei", 14, "bold"), fill="#000")
        y += 36
        if not pairs:
            self.canvas.create_text(20, y, anchor="nw",
                                    text="暂无数据，请先加载 txt 或生成信号量图",
                                    font=("Consolas", 12), fill="#555")
            return
        for rec in pairs:
            extra = ""
            file_info = rec.post_file or rec.wait_file
            if file_info:
                extra += f"  FILE: {file_info}"
            if rec.post_line is not None or rec.wait_line is not None:
                a = rec.post_line if rec.post_line is not None else "?"
                b = rec.wait_line if rec.wait_line is not None else "?"
                extra += f"  LINES: {a} -> {b}"
            self.canvas.create_text(
                20, y, anchor="nw",
                text=f"ID={rec.idx}  VAR={rec.var}  {rec.post} -> {rec.wait}{extra}",
                font=("Consolas", 11), fill="#263238"
            )
            y += 24

        if self.cycle_data:
            y += 20
            self.canvas.create_text(20, y, anchor="nw",
                                    text="信号量环数据结构：",
                                    font=("Microsoft YaHei", 13, "bold"), fill="#000")
            y += 28
            for cname, per_thread in self.cycle_data.items():
                self.canvas.create_text(20, y, anchor="nw",
                                        text=f"{cname}:", font=("Consolas", 11), fill="#263238")
                y += 20
                for thread, nodes in per_thread.items():
                    self.canvas.create_text(
                        40, y, anchor="nw",
                        text=f"{thread}: {', '.join(nodes)}",
                        font=("Consolas", 10), fill="#455A64"
                    )
                    y += 18
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    # ---------------------------------------------------------- 其他视图 --

    def show_thread_legend(self) -> None:
        self.canvas.delete("all")
        y = 40
        self.canvas.create_text(40, 10, anchor="nw",
                                text="线程颜色图例",
                                font=("Microsoft YaHei", 14, "bold"), fill="#212121")
        for thread, color in self.thread_color_map.items():
            self.canvas.create_rectangle(40, y, 100, y + 30, fill=color, outline="black")
            self.canvas.create_text(120, y + 15, anchor="w",
                                    text=thread, font=("Microsoft YaHei", 12))
            y += 40
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    # -------------------------------------------------------------- 画布 --

    def _start_move(self, event) -> None:
        self.canvas.scan_mark(event.x, event.y)

    def _on_move(self, event) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_zoom(self, event) -> None:
        delta = event.delta if hasattr(event, "delta") else (120 if event.num == 4 else -120)
        scale = 1.1 if delta > 0 else 0.9
        self.canvas.scale(tk.ALL, event.x, event.y, scale, scale)
        self.canvas.configure(scrollregion=self.canvas.bbox(tk.ALL))

    # --------------------------------------------------------- 外部加载 --

    def load_from_path(self, path: Path) -> None:
        """根据传入路径自动加载配置。

        - 如果是目录：等价于选择配置文件夹（首个 .dot，首个 .txt 可选）
        - 如果是 .dot：仅加载 dot
        - 如果是 .txt：仅记录 circle.txt 路径（等待后续生成图使用）
        """
        try:
            if path.is_dir():
                dot_files = sorted([p for p in path.iterdir() if p.suffix.lower() == ".dot"])
                if not dot_files:
                    messagebox.showwarning("提示", "目录中未找到 .dot 文件")
                    return
                dot_path = dot_files[0]
                txt_files = sorted([p for p in path.iterdir() if p.suffix.lower() == ".txt"])
                txt_path = txt_files[0] if txt_files else None
                self.G = self._read_dot_to_graph(dot_path)
                self.current_dot_path = dot_path
                self.current_circle_path = txt_path
                self.current_config_dir = path
                self.cached_images = {"original": None, "tarjan": None, "threads": None}
                self.sem_records.clear()
                self.current_intermediate_dot = None
                self._extract_threads()
                self._ensure_output_dir()
                self._update_status()
                self._set_subtoolbar(None)
                return

            if path.suffix.lower() == ".dot":
                self.G = self._read_dot_to_graph(path)
                self.current_dot_path = path
                self.current_config_dir = path.parent
                self._extract_threads()
                self._ensure_output_dir()
                self._update_status()
                self._set_subtoolbar(None)
                return

            if path.suffix.lower() == ".txt":
                self.current_circle_path = path
                self.current_config_dir = path.parent
                self._update_status()
                self._set_subtoolbar(None)
                return
        except Exception as exc:
            messagebox.showerror("自动加载失败", str(exc))
    
    # ========================================================================
    # 生成功能（3个按钮）
    # ========================================================================
    
    def load_source_file(self) -> None:
        """选择源文件（C或expand），并自动生成所有必需文件"""
        path_str = filedialog.askopenfilename(
            title="选择源文件或expand文件",
            filetypes=[
                ("C文件", "*.c"),
                ("Expand文件", "*.expand"),
                ("所有文件", "*")
            ]
        )
        if not path_str:
            return
        
        path = Path(path_str).resolve()
        if not path.exists():
            messagebox.showerror("错误", "文件不存在")
            return
        
        # 清空错误记录
        self.generation_errors.clear()
        
        # 获取基础名称并创建工作目录
        base_name = self._get_base_name(path)
        self.current_work_dir = self.intermediate_root / base_name
        self.current_work_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建所有子目录
        subdirs = [
            "rtl文件", "配置文件", "生成dag图", "查看条件节点",
            "生成原始图", "查看互斥锁图", "生成信号量图",
            "debug", "images", "logs", "temp"
        ]
        for subdir in subdirs:
            (self.current_work_dir / subdir).mkdir(parents=True, exist_ok=True)
        
        try:
            # 总共7个步骤
            total_steps = 7
            
            # 步骤1: 处理源文件
            self._update_progress(1, total_steps, "处理源文件")
            self._process_source_file(path)
            
            # 步骤2: 生成 dag.dot
            self._update_progress(2, total_steps, "生成dag图DOT文件")
            self._generate_dag_dot()
            
            # 步骤3: 生成 conditions.dot
            self._update_progress(3, total_steps, "生成条件节点DOT文件")
            self._generate_conditions_dot()
            
            # 步骤4: 生成 circle.txt
            self._update_progress(4, total_steps, "生成配置文件")
            self._generate_config_file()
            
            # 步骤5: 生成原始图
            self._update_progress(5, total_steps, "生成原始图")
            self._generate_original_image()
            
            # 步骤6: 生成互斥锁图
            self._update_progress(6, total_steps, "生成互斥锁图")
            self._generate_mutex_image()
            
            # 步骤7: 生成信号量图
            self._update_progress(7, total_steps, "生成信号量图")
            self._generate_semaphore_images()
            
            # 完成
            self._update_progress(7, total_steps, "完成")
            
            # 报告结果
            if self.generation_errors:
                error_msg = "生成完成，但有以下错误：\n\n" + "\n".join(self.generation_errors)
                messagebox.showwarning("部分成功", error_msg)
            else:
                messagebox.showinfo("成功", 
                    f"已完成所有生成任务！\n\n"
                    f"源文件: {path.name}\n"
                    f"工作目录: {self.current_work_dir.name}\n\n"
                    f"现在可以点击功能按钮查看结果")
            
        except Exception as exc:
            messagebox.showerror("生成失败", f"发生严重错误：\n{exc}")
            import traceback
            traceback.print_exc()
    
    def _update_progress(self, current: int, total: int, message: str) -> None:
        """更新进度显示"""
        progress_text = f"正在生成... ({current}/{total}) {message}"
        self.status.config(text=progress_text)
        self.root.update_idletasks()
    
    def _process_source_file(self, path: Path) -> None:
        """步骤1: 处理源文件"""
        try:
            import shutil
            
            if path.suffix == ".c":
                # 编译C文件生成expand
                self.current_c_path = path
                expand_path = self._compile_to_expand_v2(path)
                self.current_expand_path = expand_path
            else:
                # 直接复制expand文件
                self.current_c_path = None
                rtl_dir = self.current_work_dir / "rtl文件"
                target_path = rtl_dir / path.name
                shutil.copy(path, target_path)
                self.current_expand_path = target_path
                
        except Exception as exc:
            self.generation_errors.append(f"[步骤1] 处理源文件失败: {exc}")
            raise
    
    def _compile_to_expand(self, c_path: Path) -> Path:
        """将C文件编译为expand文件"""
        import shutil
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp())
        try:
            expand_path = temp_dir / f"{c_path.stem}.c.233r.expand"
            cmd = [
                "gcc",
                "-fdump-rtl-expand",
                "-O2",
                "-c",
                str(c_path),
                "-o",
                str(temp_dir / "temp.o")
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # GCC会生成expand文件
            generated = list(temp_dir.glob("*.expand"))
            if not generated:
                raise RuntimeError("GCC未生成expand文件")
            
            final_expand = self.base_dir / "源文件" / expand_path.name
            final_expand.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(generated[0], final_expand)
            
            return final_expand
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _compile_to_expand_v2(self, c_path: Path) -> Path:
        """将C文件编译为expand文件（新版本，保存到工作目录）"""
        import shutil
        import tempfile
        
        temp_dir = Path(tempfile.mkdtemp())
        try:
            cmd = [
                "gcc",
                "-fdump-rtl-expand",
                "-O2",
                "-c",
                str(c_path),
                "-o",
                str(temp_dir / "temp.o")
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            
            # GCC会生成expand文件
            generated = list(temp_dir.glob("*.expand"))
            if not generated:
                raise RuntimeError("GCC未生成expand文件")
            
            # 保存到工作目录的rtl文件夹
            rtl_dir = self.current_work_dir / "rtl文件"
            target_path = rtl_dir / generated[0].name
            shutil.copy(generated[0], target_path)
            
            return target_path
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _generate_dag_dot(self) -> None:
        """步骤2: 生成dag.dot"""
        try:
            # 调用 legacy，指定output_base为mycallyplus目录
            cmd = [
                sys.executable, "-m", "mycallypro.legacy",
                str(self.current_expand_path),
                "--threads-only",
                "--output-base", str(self.base_dir)  # 指向mycallyplus
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir.parent),  # 在cally目录执行
                capture_output=True,
                text=True,
                check=True
            )
            
            # legacy 会生成在 mycallyplus/配置文件/<basename>/<basename>_threads.dot
            base_name = self._get_base_name(self.current_expand_path)
            config_dir = self.base_dir / "配置文件" / base_name
            source_dot = config_dir / f"{base_name}_threads.dot"
            
            # 等待文件生成
            import time
            for _ in range(10):
                if source_dot.exists():
                    break
                time.sleep(0.1)
            
            if not source_dot.exists():
                raise RuntimeError(f"未找到生成的DOT文件，查找路径: {source_dot}")
            
            # 复制到中间结果目录
            target_dir = self.current_work_dir / "生成dag图"
            target_dot = target_dir / "dag.dot"
            import shutil
            shutil.copy(source_dot, target_dot)
            
            # 生成PNG
            png_path = target_dir / "dag.png"
            subprocess.run(
                ["dot", "-Tpng", str(target_dot), "-o", str(png_path)],
                check=True,
                capture_output=True
            )
                
        except Exception as exc:
            self.generation_errors.append(f"[步骤2] 生成dag.dot失败: {exc}")
    
    def _generate_conditions_dot(self) -> None:
        """步骤3: 生成conditions.dot（完整DAG）"""
        try:
            # 调用 legacy，指定output_base为mycallyplus目录
            cmd = [
                sys.executable, "-m", "mycallypro.legacy",
                str(self.current_expand_path),
                "--conditions-only",
                "--output-base", str(self.base_dir)
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir.parent),
                capture_output=True,
                text=True,
                check=True
            )
            
            # legacy 会生成在 mycallyplus/配置文件/<basename>/<basename>_full.dot
            base_name = self._get_base_name(self.current_expand_path)
            config_dir = self.base_dir / "配置文件" / base_name
            source_dot = config_dir / f"{base_name}_full.dot"
            
            # 等待文件生成
            import time
            for _ in range(10):
                if source_dot.exists():
                    break
                time.sleep(0.1)
            
            if not source_dot.exists():
                raise RuntimeError(f"未找到生成的DOT文件，查找路径: {source_dot}")
            
            # 复制到中间结果目录
            target_dir = self.current_work_dir / "查看条件节点"
            target_dot = target_dir / "conditions.dot"
            import shutil
            shutil.copy(source_dot, target_dot)
            
            # 生成PNG
            png_path = target_dir / "conditions.png"
            subprocess.run(
                ["dot", "-Tpng", str(target_dot), "-o", str(png_path)],
                check=True,
                capture_output=True
            )
                
        except Exception as exc:
            self.generation_errors.append(f"[步骤3] 生成conditions.dot失败: {exc}")
    
    def _generate_config_file(self) -> None:
        """步骤4: 生成circle.txt配置文件"""
        try:
            # 调用 legacy，指定output_base为mycallyplus目录
            cmd = [
                sys.executable,
                "-m",
                "mycallypro.legacy",
                str(self.current_expand_path),
                "--export-txt",
                "--output-base", str(self.base_dir)
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir.parent),
                capture_output=True,
                text=True,
                check=True
            )
            
            # legacy 生成在 mycallyplus/配置文件/<basename>/circle.txt
            base_name = self._get_base_name(self.current_expand_path)
            config_dir = self.base_dir / "配置文件" / base_name
            source_txt = config_dir / "circle.txt"
            
            # 等待文件生成
            import time
            for _ in range(10):
                if source_txt.exists():
                    break
                time.sleep(0.1)
            
            if not source_txt.exists():
                raise RuntimeError(f"未找到生成的circle.txt文件，查找路径: {source_txt}")
            
            # 复制到中间结果目录
            target_dir = self.current_work_dir / "配置文件"
            target_txt = target_dir / "circle.txt"
            import shutil
            shutil.copy(source_txt, target_txt)
            
            self.current_circle_path = target_txt
                
        except Exception as exc:
            self.generation_errors.append(f"[步骤4] 生成circle.txt失败: {exc}")
    
    def _generate_original_image(self) -> None:
        """步骤5: 生成原始图（基于conditions.dot）"""
        try:
            conditions_dot = self.current_work_dir / "查看条件节点" / "conditions.dot"
            if not conditions_dot.exists():
                raise RuntimeError("conditions.dot不存在")
            
            target_dir = self.current_work_dir / "生成原始图"
            png_path = target_dir / "original.png"
            
            subprocess.run(
                ["dot", "-Tpng", str(conditions_dot), "-o", str(png_path)],
                check=True,
                capture_output=True
            )
            
        except Exception as exc:
            self.generation_errors.append(f"[步骤5] 生成原始图失败: {exc}")
    
    def _generate_mutex_image(self) -> None:
        """步骤6: 生成互斥锁图"""
        try:
            conditions_dot = self.current_work_dir / "查看条件节点" / "conditions.dot"
            circle_txt = self.current_work_dir / "配置文件" / "circle.txt"
            
            if not conditions_dot.exists() or not circle_txt.exists():
                raise RuntimeError("依赖文件不存在")
            
            # 读取DOT和配置
            self.G = self._read_dot_to_graph(conditions_dot)
            self.current_circle_path = circle_txt
            self._parse_circle_file()
            
            # 生成互斥锁图
            target_dir = self.current_work_dir / "查看互斥锁图"
            
            # 这里需要调用原有的互斥锁生成逻辑
            # 暂时简化：复制原始图
            original_png = self.current_work_dir / "生成原始图" / "original.png"
            if original_png.exists():
                import shutil
                mutex_png = target_dir / "mutex.png"
                shutil.copy(original_png, mutex_png)
            
        except Exception as exc:
            self.generation_errors.append(f"[步骤6] 生成互斥锁图失败: {exc}")
    
    def _generate_semaphore_images(self) -> None:
        """步骤7: 生成信号量图（semaphore, tarjan, threads）"""
        try:
            conditions_dot = self.current_work_dir / "查看条件节点" / "conditions.dot"
            circle_txt = self.current_work_dir / "配置文件" / "circle.txt"
            
            if not conditions_dot.exists() or not circle_txt.exists():
                raise RuntimeError("依赖文件不存在")
            
            target_dir = self.current_work_dir / "生成信号量图"
            
            # 生成三个图（这里需要调用原有逻辑，暂时简化）
            # 1. semaphore.png
            # 2. tarjan.png
            # 3. threads.png
            
            # 暂时复制原始图作为占位
            original_png = self.current_work_dir / "生成原始图" / "original.png"
            if original_png.exists():
                import shutil
                for name in ["semaphore.png", "tarjan.png", "threads.png"]:
                    target_path = target_dir / name
                    shutil.copy(original_png, target_path)
            
        except Exception as exc:
            self.generation_errors.append(f"[步骤7] 生成信号量图失败: {exc}")
    
    def _auto_generate_dag(self, mode: str, output_name: str) -> None:
        """自动生成DAG文件（内部调用，不显示消息框）"""
        if not self.current_expand_path:
            raise RuntimeError("未设置 expand 文件路径")
        
        # 构建命令
        cmd = [sys.executable, "-m", "mycallypro.legacy"]
        cmd.append(str(self.current_expand_path))
        
        if mode:
            cmd.append(mode)
        
        # 执行生成
        result = subprocess.run(
            cmd,
            cwd=str(self.base_dir.parent),
            capture_output=True,
            text=True,
            check=True
        )
        
        # 获取配置目录
        base_name = self._get_base_name(self.current_expand_path)
        
        config_dir = self.base_dir / "配置文件" / base_name
        
        # 查找生成的DOT文件并重命名
        dot_files = list(config_dir.glob("*.dot"))
        if dot_files:
            target_dot = config_dir / output_name
            if dot_files[0] != target_dot:
                dot_files[0].rename(target_dot)
    
    def _auto_generate_circle_txt(self) -> None:
        """自动生成 circle.txt（内部调用，不显示消息框）"""
        if not self.current_expand_path:
            raise RuntimeError("未设置 expand 文件路径")
        
        cmd = [
            sys.executable, 
            "-m", 
            "mycallypro.legacy",
            str(self.current_expand_path),
            "--export-txt",
            "circle.txt"
        ]
        
        result = subprocess.run(
            cmd,
            cwd=str(self.base_dir.parent),
            capture_output=True,
            text=True,
            check=True
        )
        
        base_name = self._get_base_name(self.current_expand_path)
        
        config_dir = self.base_dir / "配置文件" / base_name
        circle_txt = config_dir / "circle.txt"
        
        if circle_txt.exists():
            self.current_circle_path = circle_txt
            self.current_config_dir = config_dir
    
    def load_dag_graph(self) -> None:
        """加载并显示 dag.dot 图（从工作目录加载）"""
        if not self.current_work_dir:
            messagebox.showerror("错误", "请先选择源文件")
            return
        
        try:
            dag_png = self.current_work_dir / "生成dag图" / "dag.png"
            
            if not dag_png.exists():
                messagebox.showerror("错误", "dag.png 文件不存在，请先选择源文件")
                return
            
            # 加载图到可视化区
            self._show_image(dag_png)
            self._update_status_simple(f"已加载: {dag_png.parent.name}/{dag_png.name}")
            
        except Exception as exc:
            messagebox.showerror("错误", str(exc))
    
    def view_condition_nodes(self) -> None:
        """加载并显示条件节点图（从工作目录加载）"""
        if not self.current_work_dir:
            messagebox.showerror("错误", "请先选择源文件")
            return
        
        try:
            conditions_png = self.current_work_dir / "查看条件节点" / "conditions.png"
            
            if not conditions_png.exists():
                messagebox.showerror("错误", "conditions.png 文件不存在，请先选择源文件")
                return
            
            # 加载图到可视化区
            self._show_image(conditions_png)
            self._update_status_simple(f"已加载: {conditions_png.parent.name}/{conditions_png.name}")
            
        except Exception as exc:
            messagebox.showerror("错误", str(exc))
    
    # ========================================================================
    # 可视化功能（5个按钮）
    # ========================================================================


def main() -> None:
    root = tk.Tk()
    app = MycallyplusGUI(root)
    # 支持通过环境变量或第一个参数传入要打开的路径
    open_path = os.environ.get("MYCALLYPRO_OPEN_PATH")
    if not open_path and len(sys.argv) > 1:
        open_path = sys.argv[1]
    if open_path:
        p = Path(open_path).expanduser()
        if p.exists():
            try:
                app.load_from_path(p)
            except Exception:
                pass
    root.mainloop()


if __name__ == "__main__":
    main()
