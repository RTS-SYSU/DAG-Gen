#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tarjan Strongly Connected Components Visualization (Integrated Edition)

Core Features
---------
1. Read DOT / TXT (circle) files and display the original graph.
2. View mutex locks: mark lock->unlock regions based on mutex descriptions in TXT.
3. Generate semaphore graph: overlay sem_post->sem_wait dashed edges, run Tarjan, and display thread rectangles.
4. Display mutex lock / semaphore information (including optional source code line number ranges).

Interaction Guidelines
---------
- Buttons on the left are main functions; right side is "display area + sub-function area".
- Hide sub-function area when there are no sub-functions; show corresponding buttons when there are sub-functions.
- Clicking "View Mutex Locks" displays the mutex lock graph by default; sub-functions can switch to view text information.
- "Generate Semaphore Graph" displays the semaphore graph by default; sub-functions provide original graph, Tarjan graph, thread graph, information, and thread color legend.
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
try:
    from PIL import Image, ImageTk  # type: ignore

    _PIL_READY = True
except Exception:  # pragma: no cover - optional dependency
    Image = None  # type: ignore
    ImageTk = None  # type: ignore
    _PIL_READY = False

try:
    import pydot  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    pydot = None


# --------------------------------------------------------------------------- #
# Utility Functions
# --------------------------------------------------------------------------- #

def _norm(text: str) -> str:
    """Strip leading/trailing whitespace and quotes."""
    return text.strip().strip('"').strip("'").strip()


def _suffix_num(name: str) -> int:
    """Extract trailing digits from node name, return 0 if none, used for stable sorting."""
    tail = name.split('/')[-1]
    digits = ''.join(ch for ch in tail if ch.isdigit())
    return int(digits) if digits else 0


def _edge_attr_string(attrs: Dict[str, str]) -> str:
    """Convert edge attributes to a Graphviz attribute string."""
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
# Data Structures
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
# Main Interface
# --------------------------------------------------------------------------- #

class TarjanGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Tarjan Strongly Connected Components Visualization (Integrated)")
        self.root.geometry("1380x860")
        self.root.configure(bg="#ECEFF1")

        # Working path
        self.base_dir = Path.cwd()
        # Default config directory switches to intermediate_results/<base>/config_files, compatible with old directory read-only
        self.dot_dir = self.base_dir / "intermediate_results"
        self.output_root = self.base_dir / "dag_output"
        self.output_root.mkdir(parents=True, exist_ok=True)

        # status
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
        # When Pillow is unavailable, we fall back to tk.PhotoImage (may not support PNG on all Tk builds).
        self.tk_img: Optional[object] = None

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

        left = tk.LabelFrame(main, text="Operations", bg="#CFD8DC",
                             font=("Microsoft YaHei", 10, "bold"),
                             padx=10, pady=10)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)

        def add_btn(text: str, cmd) -> None:
            tk.Button(left, text=text, command=cmd,
                      width=22, height=2, bg="#ECEFF1",
                      relief=tk.RAISED, activebackground="#CFD8DC",
                      font=("Microsoft YaHei", 9)).pack(pady=6)

        add_btn("Use Default Config (dag1)", self.use_default)
        add_btn("Select config_files", self.select_config_folder)
        add_btn("Generate Original Graph", self.generate_original_graph)
        add_btn("View Mutex Locks", self.view_mutex)
        add_btn("Generate Semaphore Graph", self.generate_semaphore_pipeline)

        right = tk.LabelFrame(main, text="Visualization", bg="#FFFFFF",
                              font=("Microsoft YaHei", 10, "bold"))
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)

        self.status = tk.Label(right, text="Current Config: <not loaded>",
                               anchor="w", bg="#ECEFF1", font=("Consolas", 10))
        self.status.pack(fill=tk.X)

        self.canvas = tk.Canvas(right, bg="#FAFAFA",
                                highlightthickness=1, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.bottom = tk.Frame(right, bg="#ECEFF1")
        self._subtoolbar_visible = False

        # Canvas interaction
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

    # --------------------------------------------------------------- Status --

    def _update_status(self) -> None:
        cfg = str(self.current_config_dir) if self.current_config_dir else "<not selected>"
        dot = self.current_dot_path.name if self.current_dot_path else "none"
        txt = self.current_circle_path.name if self.current_circle_path else "none"
        self.status.config(text=f"Current Config: {cfg} | DOT: {dot} | TXT: {txt}")

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

        next_idx = len([p for p in self.output_root.iterdir() if p.name.startswith("graph")]) + 1
        outdir = self.output_root / f"graph{next_idx}"
        outdir.mkdir(parents=True, exist_ok=True)
        mapping[key] = str(outdir)
        mapping_path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
        self.current_output_dir = outdir
        return outdir

    # ------------------------------------------------------------- File I/O --

    def _read_dot_to_graph(self, path: Path) -> nx.DiGraph:
        # Prefer networkx + nx_pydot
        try:
            graph = nx.DiGraph(nx.nx_pydot.read_dot(str(path)))
            return nx.relabel_nodes(graph, _norm)
        except Exception:
            pass

        # Fallback 1: pydot read + custom conversion, avoid get_strict() compatibility issue in from_pydot
        if pydot:
            pd_graphs = pydot.graph_from_dot_file(str(path))
            if not pd_graphs:
                raise RuntimeError("pydot failed to parse dot file")
            pdg = pd_graphs[0]
            G = nx.DiGraph()
            for e in pdg.get_edges():
                src = _norm(e.get_source())
                dst = _norm(e.get_destination())
                G.add_edge(src, dst)
            for n in pdg.get_nodes():
                name = _norm(n.get_name())
                if name in ("node", "graph", "edge"):
                    continue
                if name not in G:
                    G.add_node(name)
                attrs = n.get_attributes() or {}
                style = attrs.get("style")
                if style:
                    G.nodes[name]["style"] = style
            return G

        # Fallback 2: minimal regex parsing
        import re
        EDGE_RE = re.compile(r'\"([^\"]+)\"\s*->\s*\"([^\"]+)\"')
        NODE_RE = re.compile(r'\"([^\"]+)\"\s*\[(.*?)\]')
        raw = Path(path).read_text(encoding="utf-8", errors="ignore")
        G = nx.DiGraph()
        for m in EDGE_RE.finditer(raw):
            G.add_edge(_norm(m.group(1)), _norm(m.group(2)))
        for m in NODE_RE.finditer(raw):
            name = _norm(m.group(1))
            if name not in G:
                G.add_node(name)
            attrs = m.group(2)
            if "style=" in attrs:
                sm = re.search(r'style\s*=\s*"?([a-zA-Z, ]+)"?', attrs)
                if sm:
                    G.nodes[name]["style"] = sm.group(1)
        return G

    def _render_dot_quiet(self, dot_str: str, out_png: Path) -> None:
        tmp = self.output_root / "_temp_render.dot"
        tmp.write_text(dot_str, encoding="utf-8")
        try:
            subprocess.run(["dot", "-Tpng", str(tmp), "-o", str(out_png)], check=True)
        except Exception as exc:
            messagebox.showerror("Graphviz Error", str(exc))
        finally:
            if tmp.exists():
                tmp.unlink()

    def _render_dot_to_canvas(self, dot_str: str, out_png: Path) -> None:
        self._render_dot_quiet(dot_str, out_png)
        if out_png.exists():
            self._show_image(out_png)
            messagebox.showinfo("Done", f"Image generated:\n{out_png}")

    def _show_image(self, path: Path) -> None:
        # Prefer Tk native loader; fall back to Pillow if available.
        try:
            self.tk_img = tk.PhotoImage(file=str(path))
        except Exception:
            if not _PIL_READY:
                messagebox.showwarning(
                    "Warning",
                    "PIL.ImageTk is missing in the current environment, and Tk does not support loading this image format.\n"
                    "Please install: python3 -m pip install pillow",
                )
                return
            img = Image.open(path)  # type: ignore[union-attr]
            self.tk_img = ImageTk.PhotoImage(img)  # type: ignore[union-attr]
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def _display_cached_image(self, key: str) -> None:
        path = self.cached_images.get(key)
        if not path or not Path(path).exists():
            messagebox.showwarning("Warning", "The corresponding image does not exist. Please generate the semaphore graph first.")
            return
        self._show_image(Path(path))

    # -------------------------------------------------------------- Graph State --

    def _extract_threads(self) -> None:
        threads = {n.split('/')[0] for n in self.G.nodes() if '/' in n}
        self.threads = sorted(threads)
        self.thread_color_map = {
            t: self.THREAD_COLORS[i % len(self.THREAD_COLORS)]
            for i, t in enumerate(self.threads)
        }

    # ----------------------------------------------------------- Feature Implementation --

    def use_default(self) -> None:
        dag1 = self.dot_dir / "dag1"
        if not dag1.exists():
            messagebox.showwarning("Warning", "Default config not found. Please select manually.")
            return
        for path in dag1.rglob("*.dot"):
            try:
                self.G = self._read_dot_to_graph(path)
            except Exception as exc:
                messagebox.showerror("Error", f"Failed to read DOT: {exc}")
                return
            self.current_dot_path = path
            self.current_config_dir = path.parent
            self.current_circle_path = None
            self._extract_threads()
            self._ensure_output_dir()
            self._update_status()
            self._set_subtoolbar(None)
            messagebox.showinfo("Success", f"Default config loaded: {path}")
            return
        messagebox.showwarning("Warning", "No DOT file found in default directory. Please select manually.")

    def select_dot_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Select DOT File", filetypes=[("DOT Files", "*.dot")]
        )
        if not path_str:
            return
        path = Path(path_str)
        try:
            self.G = self._read_dot_to_graph(path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load DOT:\n{exc}")
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
        messagebox.showinfo("Success", f"DOT file loaded: {path.name}")

    def select_txt_file(self) -> None:
        path_str = filedialog.askopenfilename(
            title="Select TXT File", filetypes=[("TXT Files", "*.txt")]
        )
        if not path_str:
            return
        path = Path(path_str)
        if not path.exists():
            messagebox.showerror("Error", "File does not exist.")
            return
        self.current_circle_path = path
        self._update_status()
        self._set_subtoolbar(None)
        messagebox.showinfo("Success", f"TXT file selected: {path.name}")

    def select_config_folder(self) -> None:
        """
        Select config_files folder and automatically match dot / txt files within it.

        Constraints:
        - Only search in the first level of the selected folder (no recursion).
        - At least one dot file is required; txt files are optional. If multiple exist, take the first one sorted by name.
        """
        folder = filedialog.askdirectory(title="Select config_files folder")
        if not folder:
            return
        folder_path = Path(folder)
        # If intermediate_results/<base>/ is selected, automatically enter the config_files subdirectory
        if folder_path.name != "config_files" and (folder_path / "config_files").exists():
            folder_path = folder_path / "config_files"
        if not folder_path.is_dir():
            messagebox.showerror("Error", "Please select a valid folder.")
            return

        dot_files = sorted([p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() == ".dot"])
        if not dot_files:
            messagebox.showerror("Error", "No dot file found in this folder.")
            return
        dot_path = dot_files[0]

        txt_files = sorted([p for p in folder_path.iterdir() if p.is_file() and p.suffix.lower() == ".txt"])
        txt_path = txt_files[0] if txt_files else None

        try:
            self.G = self._read_dot_to_graph(dot_path)
        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load DOT:\n{exc}")
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

        info = [f"DOT: {dot_path.name}"]
        if txt_path:
            info.append(f"TXT: {txt_path.name}")
        else:
            info.append("TXT: <not found, some features unavailable>")
        messagebox.showinfo("Success", "config_files folder loaded:\n" + "\n".join(info))

    # -------------------------------------------------------- original graph display --

    def generate_original_graph(self) -> None:
        if not self.current_dot_path:
            messagebox.showerror("Error", "PleaseSelect dot File。")
            return
        out_dir = self._ensure_output_dir()
        out_png = out_dir / "originalgraph.png"
        try:
            subprocess.run(
                ["dot", "-Tpng", str(self.current_dot_path), "-o", str(out_png)],
                check=True,
            )
        except Exception as exc:
            messagebox.showerror("Error", f"generateoriginalgraphfailed：\n{exc}")
            return
        self.cached_images["original"] = out_png
        self._show_image(out_png)
        self._set_subtoolbar(None)
        messagebox.showinfo("Success", f"Generatedoriginalgraph：\n{out_png}")

    # ------------------------------------------------------------- mutex lock --

    def _parse_optional_meta(self, parts: List[str]) -> Tuple[Optional[int], Optional[str]]:
        """
        Parse the optional source-code line number and filename.

        Format rules:
        - Column 4: line number (integer). If conversion fails, treat it as a filename.
        - Column 5: filename (optional string). If present, it overrides the filename inferred from column 4.
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
            messagebox.showerror("Error", "Pleaseload txt File。")
            return False

        entries: List[Tuple[str, str, str, str, Optional[int], Optional[str]]] = []
        block = None
        for line in self.current_circle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = _norm(line)
            if not s:
                continue
            if s == "mutex":
                block = "mutex"
                continue
            if s == "semaphore":
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
                    # If the variables differ, still use the unlock variable as the source of truth.
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
            messagebox.showwarning("Info", "No paired mutex-lock records were found.")
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
            messagebox.showwarning("Info", "The mutex-lock node was not found in the graph.")
            self.mutex_prepared = False
            return False

        self.mutex_prepared = True
        return True

    def _show_mutex_graph(self) -> None:
        if not self.mutex_prepared:
            messagebox.showwarning("Info", 'Please click "View Mutex Graph" to parse the data first.')
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
            messagebox.showwarning("Info", 'Please click "View Mutex Graph" to parse the data first.')
            return
        self.canvas.delete("all")
        y = 20
        self.canvas.create_text(20, y, anchor="nw",
                                text="Mutex lock information (ID, lock node, unlock node, covered nodes)",
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
            messagebox.showerror("Error", "Please load both the DOT and TXT files.")
            self._set_subtoolbar(None)
            return
        if not self._prepare_mutex_data():
            self._set_subtoolbar(None)
            return
        self._set_subtoolbar([
            ("View Mutex Graph", self._show_mutex_graph),
            ("View Mutex Info", self.show_mutex_info),
        ])
        self._show_mutex_graph()

    # ------------------------------------------------------------ semaphore --

    def _parse_semaphore_pairs(self) -> List[SemRecord]:
        if not self.current_circle_path:
            return []
        by_id: Dict[str, Dict[str, Optional[str]]] = {}
        block = None
        for line in self.current_circle_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            s = _norm(line)
            if not s:
                continue
            if s == "mutex":
                block = "mutex"
                continue
            if s == "semaphore":
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
            messagebox.showerror("Error", "Pleaseload dot File。")
            self._set_subtoolbar(None)
            return
        if not self.current_circle_path:
            messagebox.showerror("Error", "Pleaseload txt File。")
            self._set_subtoolbar(None)
            return

        out_dir = self._ensure_output_dir()
        self.sem_records = self._parse_semaphore_pairs()

        graph_idx = self.current_output_dir.name.lstrip("graph") if self.current_output_dir else "1"
        inter_dir = out_dir / "intermediate_results"
        inter_dir.mkdir(parents=True, exist_ok=True)
        intermediate_path = inter_dir / f"Filegraph{graph_idx}.dot"

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

        self.cached_images["original"] = out_dir / "originalgraph.png"
        self._render_dot_quiet("\n".join(lines), self.cached_images["original"])

        g_intermediate = self._read_dot_to_graph(intermediate_path)
        self._run_tarjan_from_intermediate(g_intermediate, out_dir)
        self._generate_threads_from_intermediate(g_intermediate, out_dir)

        self._display_cached_image("threads")
        self._set_subtoolbar([
            ("View Original Graph", lambda: self._display_cached_image("original")),
            ("View SCC Graph", lambda: self._display_cached_image("tarjan")),
            ("View Semaphore Graph", lambda: self._display_cached_image("threads")),
            ("Show Semaphore Info", self.show_semaphore_info),
            ("Show Thread Color Legend", self.show_thread_legend),
        ])
        messagebox.showinfo("Completed", "semaphoregraphGenerated。")

    def show_semaphore_info(self) -> None:
        pairs = self.sem_records or self._parse_semaphore_pairs()
        self.canvas.delete("all")
        y = 20
        self.canvas.create_text(20, y, anchor="nw",
                                text="semaphore pairings（post → wait）",
                                font=("Microsoft YaHei", 14, "bold"), fill="#000")
        y += 36
        if not pairs:
            self.canvas.create_text(20, y, anchor="nw",
                                    text="No data available. Please load a TXT file or generate the semaphore graph.",
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
                                    text="Semaphore cycle data structure:",
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

    # ---------------------------------------------------------- Other graph views --

    def show_thread_legend(self) -> None:
        self.canvas.delete("all")
        y = 40
        self.canvas.create_text(40, 10, anchor="nw",
                                text="Thread color legend",
                                font=("Microsoft YaHei", 14, "bold"), fill="#212121")
        for thread, color in self.thread_color_map.items():
            self.canvas.create_rectangle(40, y, 100, y + 30, fill=color, outline="black")
            self.canvas.create_text(120, y + 15, anchor="w",
                                    text=thread, font=("Microsoft YaHei", 12))
            y += 40
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    # -------------------------------------------------------------- Canvas --

    def _start_move(self, event) -> None:
        self.canvas.scan_mark(event.x, event.y)

    def _on_move(self, event) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_zoom(self, event) -> None:
        delta = event.delta if hasattr(event, "delta") else (120 if event.num == 4 else -120)
        scale = 1.1 if delta > 0 else 0.9
        self.canvas.scale(tk.ALL, event.x, event.y, scale, scale)
        self.canvas.configure(scrollregion=self.canvas.bbox(tk.ALL))

    # --------------------------------------------------------- External loading --

    def load_from_path(self, path: Path) -> None:
        """Automatically load configuration from the input path.

        - If it is a directory: same as selecting the config_files folder (first `.dot`, optional first `.txt`)
        - If it is a `.dot`: load only the DOT file
        - If it is a `.txt`: record only the `circle.txt` path and wait for later graph generation
        """
        try:
            if path.is_dir():
                dot_files = sorted([p for p in path.iterdir() if p.suffix.lower() == ".dot"])
                if not dot_files:
                    messagebox.showwarning("Info", "No `.dot` file was found in the directory.")
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
            messagebox.showerror("automaticloadfailed", str(exc))


def main() -> None:
    root = tk.Tk()
    app = TarjanGUI(root)
    # Support passing the path to open through an environment variable or the first argument.
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
