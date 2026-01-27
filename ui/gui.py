# -*- coding: utf-8 -*-
"""
Mycallyplus GUI v3.0 - 状态区驱动设计
重新设计的GUI，采用状态区机制，手动逐步点击流程
"""

import sys
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass
import subprocess
import shutil
import random
import re
import json
from PIL import Image, ImageTk

# 使用包内模块，避免与非 v1 版本混淆
from mycallyplus_v1 import filter_dot, time_analysis, time_charts, scheduler
from mycallyplus_v1.level1 import time_analysis_level1 as level1_time_analysis
from mycallyplus_v1.level1 import lpf_thread as level1_lpf_thread
from mycallyplus_v1.level1 import instrument_prio_level1 as level1_prio_instrument

try:
    import networkx as nx
except ImportError:
    nx = None

try:  # Graphviz 解析可选依赖
    import pydot  # type: ignore
except Exception:  # pragma: no cover - 可选依赖
    pydot = None


@dataclass
class MutexRecord:
    """互斥锁记录"""
    lock: str
    unlock: str
    var: str
    idx: str
    lock_line: Optional[int] = None
    unlock_line: Optional[int] = None
    lock_file: Optional[str] = None
    unlock_file: Optional[str] = None
    covered: List[str] = None
    
    def __post_init__(self):
        if self.covered is None:
            self.covered = []


@dataclass
class SemRecord:
    """信号量记录"""
    post: str
    wait: str
    var: str
    idx: str
    post_line: Optional[int] = None
    wait_line: Optional[int] = None
    post_file: Optional[str] = None
    wait_file: Optional[str] = None


class FileState:
    """文件状态管理"""
    def __init__(self):
        self.source_file: Optional[Path] = None      # .c 文件
        self.expand_file: Optional[Path] = None      # .233r.expand 文件
        self.dot_file: Optional[Path] = None         # .dot 文件（最新的）
        self.txt_file: Optional[Path] = None         # circle.txt 文件
        self.work_dir: Optional[Path] = None         # 工作目录
        
    def get_base_name(self) -> Optional[str]:
        """从expand文件提取基础名"""
        if not self.expand_file:
            return None
        name = self.expand_file.stem  # 移除 .expand
        if name.endswith('.233r'):
            name = name[:-5]  # 移除 .233r
        # 去掉末尾的语言扩展（.c / .cpp / 其他）
        if '.' in name:
            name = name.split('.')[0]
        return name
    
    def clear(self):
        """清空所有状态"""
        self.source_file = None
        self.expand_file = None
        self.dot_file = None
        self.txt_file = None
        self.work_dir = None


class MycallyplusGUIv3:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Mycallyplus v3.0 - 状态区驱动")
        self.root.geometry("1400x900")
        self.root.configure(bg="#ECEFF1")
        
        # 工作路径 - 修改为 mycallyplus 目录
        self.base_dir = Path(__file__).resolve().parent.parent
        self.base_dir.mkdir(parents=True, exist_ok=True)
        
        # 文件状态
        self.state = FileState()
        self.filtered_dot_dir = self.base_dir / "中间结果" / "过滤dot"
        self.filtered_dot_dir.mkdir(parents=True, exist_ok=True)
        
        # 当前显示的图片
        self.current_image: Optional[Path] = None
        self.tk_img: Optional[ImageTk.PhotoImage] = None
        self.original_image: Optional[Image.Image] = None  # 保存原始PIL图像用于缩放
        self.canvas_scale = 1.0  # 当前缩放比例
        
        # 互斥锁分析状态
        self.mutex_prepared = False
        self.mutex_records: List[MutexRecord] = []
        self.G = None  # networkx图对象
        self.sem_records: List[SemRecord] = []
        self.thread_color_map: Dict[str, str] = {}
        self.cycle_data: Dict[str, Dict[str, List[str]]] = {}
        self.sccs: List[set] = []
        self.cached_images: Dict[str, Optional[Path]] = {
            "original": None,
            "tarjan": None,
            "threads": None,
            "mutex": None,
        }
        # 时间分析选择状态
        self.ta_source_file: Optional[Path] = None
        self.ta_json_file: Optional[Path] = None

        # 互斥锁颜色配置
        self.MUTEX_COLORS = [
            "#FFB74D", "#81C784", "#64B5F6", "#BA68C8",
            "#E57373", "#4DB6AC", "#FFD54F", "#9575CD",
            "#4FC3F7", "#AED581", "#FF8A65", "#B39DDB"
        ]

        self.THREAD_COLORS = [
            "#90CAF9", "#A5D6A7", "#FFE082", "#F48FB1",
            "#CE93D8", "#FFAB91", "#80CBC4", "#B39DDB"
        ]
        
        # 构建UI
        self._build_ui()
        self._update_status_display()

    # 路径辅助：统一配置目录（新位置）
    def _config_dir_for_base(self, base_name: str) -> Path:
        return self.base_dir / "中间结果" / base_name / "配置文件"

    # 路径辅助：兼容旧配置目录（仅读取时使用）
    def _iter_config_dirs(self, base_name: str):
        # 新目录优先
        yield self._config_dir_for_base(base_name)
        # 旧目录兼容
        yield self.base_dir / "配置文件" / base_name

    def _infer_base_from_path(self, path: Path) -> Optional[str]:
        """从任意路径推导 base（优先匹配 '中间结果/<base>/' 段）。"""
        try:
            parts = path.resolve().parts
            if "中间结果" in parts:
                i = parts.index("中间结果")
                if i + 1 < len(parts):
                    return parts[i + 1]
        except Exception:
            pass
        # 回退：使用当前状态或文件名推断
        return self.state.get_base_name() or (self.state.source_file.stem if self.state.source_file else None)
    
    def _build_ui(self):
        """构建UI界面"""
        # 主容器
        main_frame = tk.Frame(self.root, bg="#ECEFF1")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左侧按钮区
        left_frame = tk.LabelFrame(
            main_frame, 
            text="操作", 
            bg="#CFD8DC",
            font=("Microsoft YaHei", 10, "bold"),
            padx=10, 
            pady=10
        )
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=8, pady=8)
        
        # 功能按钮（仅改名与顺序，不改变回调逻辑）
        buttons = [
            ("选择源文件", self.select_source_file),
            ("选择expand文件", self.select_expand_file),
            ("选择dot文件", self.select_dot_file),
            ("选择配置文件", self.select_config_folder),
            ("过滤dot文件", self.filter_dot_file),
            ("生成expand文件", self.generate_expand_from_source),
            ("生成dag图", self.generate_dag),
            ("查看条件节点", self.view_conditions),
            ("生成源码调用图", self.generate_source_only_dag),
            ("查看互斥锁", self.view_mutex),
            ("生成信号量图", self.generate_semaphore),
            ("时间分析", self.time_analysis_entry),
            ("调度算法", self.scheduler_entry),
        ]
        
        for text, cmd in buttons:
            tk.Button(
                left_frame,
                text=text,
                command=cmd,
                width=22,
                height=2,
                bg="#ECEFF1",
                relief=tk.RAISED,
                activebackground="#CFD8DC",
                font=("Microsoft YaHei", 9)
            ).pack(pady=5)
        
        # 右侧显示区
        right_frame = tk.LabelFrame(
            main_frame,
            text="可视化",
            bg="#FFFFFF",
            font=("Microsoft YaHei", 10, "bold")
        )
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        
        # 状态区（显示当前加载的文件）
        status_frame = tk.LabelFrame(
            right_frame,
            text="状态区 - 当前已加载文件",
            bg="#E3F2FD",
            font=("Microsoft YaHei", 9, "bold"),
            padx=10,
            pady=5
        )
        status_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 状态显示标签
        self.status_labels = {}
        status_items = [
            ("source", "源文件: "),
            ("expand", "Expand文件: "),
            ("dot", "DOT文件: "),
            ("txt", "配置文件: "),
        ]
        
        for key, label_text in status_items:
            frame = tk.Frame(status_frame, bg="#E3F2FD")
            frame.pack(fill=tk.X, pady=2)
            
            tk.Label(
                frame,
                text=label_text,
                bg="#E3F2FD",
                font=("Microsoft YaHei", 9, "bold"),
                anchor="w",
                width=12
            ).pack(side=tk.LEFT)
            
            label = tk.Label(
                frame,
                text="<未加载>",
                bg="#E3F2FD",
                font=("Consolas", 9),
                anchor="w",
                fg="#666666"
            )
            label.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.status_labels[key] = label

        # 源码调用图统计栏（显示 extern 统计）
        self.call_stats_label = tk.Label(
            right_frame,
            text="",
            bg="#FFF3E0",
            font=("Microsoft YaHei", 9, "bold"),
            anchor="w",
            padx=8,
            pady=4
        )
        self.call_stats_label.pack(fill=tk.X, padx=5, pady=4)
        
        # 图片显示区（Canvas）
        self.canvas = tk.Canvas(
            right_frame,
            bg="#FAFAFA",
            highlightthickness=1,
            relief=tk.SUNKEN
        )
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 子功能区（动态显示）
        self.subfunc_frame = tk.Frame(right_frame, bg="#ECEFF1")
        self._subfunc_visible = False
        
        # 画布交互 - 拖动和缩放
        self.canvas.bind("<ButtonPress-1>", self._start_move)
        self.canvas.bind("<B1-Motion>", self._on_move)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", self._on_zoom)  # Linux 向上滚动
        self.canvas.bind("<Button-5>", self._on_zoom)  # Linux 向下滚动
    
    # ===================== 状态更新 =====================
    
    def _build_subfunc_toolbar(self, specs: List[Tuple[str, callable]]) -> None:
        """构建子功能工具栏
        
        Args:
            specs: [(按钮文本, 回调函数), ...]
        """
        # 清除现有按钮
        for child in self.subfunc_frame.winfo_children():
            child.destroy()
        
        # 创建新按钮
        for text, cmd in specs:
            tk.Button(
                self.subfunc_frame,
                text=text,
                command=cmd,
                width=18,
                bg="#ECEFF1",
                activebackground="#CFD8DC",
                font=("Microsoft YaHei", 9)
            ).pack(side=tk.LEFT, padx=4)
    
    def _toggle_subfunc_toolbar(self, show: bool) -> None:
        """显示或隐藏子功能工具栏"""
        if show and not self._subfunc_visible:
            self.subfunc_frame.pack(fill=tk.X, pady=8, before=self.canvas)
            self._subfunc_visible = True
        elif not show and self._subfunc_visible:
            self.subfunc_frame.pack_forget()
            self._subfunc_visible = False
    
    def _set_subfunc_toolbar(self, specs: Optional[List[Tuple[str, callable]]]) -> None:
        """设置子功能工具栏
        
        Args:
            specs: None表示隐藏，否则显示指定按钮
        """
        if specs:
            self._build_subfunc_toolbar(specs)
            self._toggle_subfunc_toolbar(True)
        else:
            self._toggle_subfunc_toolbar(False)
    
    def _update_status_display(self):
        """更新状态区显示"""
        self.status_labels["source"].config(
            text=self.state.source_file.name if self.state.source_file else "<未加载>",
            fg="#000000" if self.state.source_file else "#666666"
        )
        self.status_labels["expand"].config(
            text=self.state.expand_file.name if self.state.expand_file else "<未加载>",
            fg="#000000" if self.state.expand_file else "#666666"
        )
        self.status_labels["dot"].config(
            text=self.state.dot_file.name if self.state.dot_file else "<未加载>",
            fg="#000000" if self.state.dot_file else "#666666"
        )
        self.status_labels["txt"].config(
            text=self.state.txt_file.name if self.state.txt_file else "<未加载>",
            fg="#000000" if self.state.txt_file else "#666666"
        )

    def _update_call_stats(self, internal: int = 0, external: int = 0, visible: bool = False):
        """更新源码调用统计栏"""
        if visible:
            self.call_stats_label.config(
                text=f"源代码函数调用：{internal}  |  外部函数调用：{external}"
            )
        else:
            self.call_stats_label.config(text="")
    
    def _show_message(self, title: str, message: str, is_error: bool = False):
        """显示消息"""
        if is_error:
            messagebox.showerror(title, message)
        else:
            messagebox.showinfo(title, message)

    def _open_file_with_system(self, path: Path):
        """使用系统默认程序打开文件"""
        if not path.exists():
            self._show_message("错误", f"文件不存在：{path}", is_error=True)
            return
        try:
            if sys.platform.startswith("darwin"):
                subprocess.run(["open", str(path)], check=False)
            elif os.name == "nt":
                os.startfile(str(path))  # type: ignore
            else:
                subprocess.run(["xdg-open", str(path)], check=False)
        except Exception as e:
            self._show_message("错误", f"无法打开文件：{e}", is_error=True)
    
    def _display_image(self, image_path: Path):
        """在canvas上显示图片（支持缩放和拖动）"""
        try:
            if not image_path.exists():
                return

            # 加载原始图像
            self.original_image = Image.open(image_path)
            self.current_image = image_path
            self.canvas_scale = self._compute_initial_scale(
                self.original_image.width,
                self.original_image.height,
            )

            # 显示图像
            self._refresh_canvas_image()

        except Exception as e:
            print(f"显示图片失败: {e}")

    def _refresh_canvas_image(self):
        """刷新canvas上的图像（应用当前缩放）"""
        if not self.original_image:
            return

        try:
            # 计算缩放后的尺寸
            width = max(1, int(self.original_image.width * self.canvas_scale))
            height = max(1, int(self.original_image.height * self.canvas_scale))

            # 缩放图像
            if self.canvas_scale != 1.0:
                resized = self.original_image.resize(
                    (width, height),
                    Image.Resampling.LANCZOS
                )
            else:
                resized = self.original_image

            # 转换为Tkinter可用的格式
            self.tk_img = ImageTk.PhotoImage(resized)

            # 清空画布并显示
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img, tags="image")

            # 设置滚动区域
            self.canvas.config(scrollregion=(0, 0, width, height))

        except Exception as e:
            print(f"刷新图像失败: {e}")

    def _display_cached_image(self, key: str, *, fallback=None):
        """显示缓存中的图像。若不存在且提供了 fallback，则先执行 fallback。"""
        path = self.cached_images.get(key)
        if path and Path(path).exists():
            self._display_image(Path(path))
            return True
        if callable(fallback):
            fallback()
            path = self.cached_images.get(key)
            if path and Path(path).exists():
                self._display_image(Path(path))
                return True
        if path is None:
            self._show_message("提示", "尚未生成对应图像，请先执行生成操作。", is_error=False)
        else:
            self._show_message("提示", f"未找到图像文件：{path}", is_error=False)
        return False

    def _compute_initial_scale(self, width: int, height: int) -> float:
        """根据画布尺寸和安全上限计算初始缩放因子。"""
        if width <= 0 or height <= 0:
            return 1.0

        # 读取当前画布尺寸；必要时刷新以确保布局完成
        self.canvas.update_idletasks()
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            # 组件尚未布局，采用保守的虚拟画布尺寸
            canvas_width = 1600
            canvas_height = 1200

        # 给图像留边框空间
        max_width = max(canvas_width - 40, 200)
        max_height = max(canvas_height - 40, 200)

        scale = min(max_width / width, max_height / height, 1.0)

        if scale <= 0:
            # 当原图极大或上述计算异常时，退化到固定阈值
            safe_scale = min(1600 / max(width, 1), 1200 / max(height, 1))
            scale = max(safe_scale, 0.1)

        return scale
    
    # ===================== 按钮1: 选择源文件 =====================
    
    def select_source_file(self):
        """按钮1: 选择源文件（仅更新状态）"""
        file_path = filedialog.askopenfilename(
            title="选择C/C++源文件",
            filetypes=[("C/C++源文件", "*.c *.cpp"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return

        source_path = Path(file_path)
        # 仅更新状态，不触发编译或目录创建
        self.state.source_file = source_path
        self.state.work_dir = source_path.parent
        self._update_status_display()
    
    # ===================== 按钮1.5: 选择expand文件 =====================
    
    def select_expand_file(self):
        """按钮1.5: 选择expand文件（仅更新状态）"""
        file_path = filedialog.askopenfilename(
            title="选择Expand文件",
            filetypes=[("Expand文件", "*.expand"), ("所有文件", "*.*")]
        )
        
        if not file_path:
            return
        expand_src = Path(file_path)
        self.state.expand_file = expand_src
        self.state.work_dir = expand_src.parent
        self._update_status_display()

    def generate_expand_from_source(self):
        """按钮1.6: 根据当前源文件生成expand文件并存入配置文件目录。"""
        if not self.state.source_file:
            self._show_message("错误", "请先选择源文件", is_error=True)
            return
        source_file = self.state.source_file
        src_dir = source_file.parent
        base_name = source_file.stem
        config_dir = self.base_dir / "配置文件" / base_name
        config_dir.mkdir(parents=True, exist_ok=True)

        # 智能检测 include 目录
        include_dirs = []
        seen_paths = set()
        potential_include_paths = [
            src_dir / "include",
            src_dir / "includes",
            src_dir / "../include",
            src_dir / "../includes",
            src_dir / "inc",
        ]
        for inc_path in potential_include_paths:
            if inc_path.exists() and inc_path.is_dir():
                resolved_path = str(inc_path.resolve())
                if resolved_path not in seen_paths:
                    seen_paths.add(resolved_path)
                    include_dirs.extend(["-I", resolved_path])

        try:
            # 临时 .o
            import tempfile
            with tempfile.NamedTemporaryFile(dir=src_dir, suffix=".o", delete=False) as tmp:
                obj_name = Path(tmp.name).name

            cmd = ["gcc", "-fdump-rtl-expand", *include_dirs, "-c", source_file.name, "-o", obj_name]
            result = subprocess.run(
                cmd,
                cwd=str(src_dir),
                capture_output=True,
                text=True,
            )

            # 清理临时 .o
            try:
                obj_path = src_dir / obj_name
                if obj_path.exists():
                    obj_path.unlink()
            except Exception:
                pass

            if result.returncode != 0:
                self._show_message("错误", f"生成expand失败:\n{result.stderr}", is_error=True)
                return

            # 找到最新 expand
            expand_files = sorted(
                src_dir.glob(f"{source_file.name}.*.expand"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            if not expand_files:
                self._show_message("错误", "未找到生成的expand文件", is_error=True)
                return

            expand_src = expand_files[0]
            dst = config_dir / expand_src.name
            if dst.exists():
                dst.unlink()
            shutil.move(str(expand_src), str(dst))

            # 更新状态
            self.state.expand_file = dst
            self.state.work_dir = config_dir
            self._update_status_display()
            self._show_message("成功", f"已生成expand文件：\n{dst}")
        except Exception as e:
            self._show_message("错误", f"生成expand失败:\n{e}", is_error=True)
            import traceback
            traceback.print_exc()

    # ===================== 按钮1.6: 选择dot文件 =====================

    def select_dot_file(self):
        """按钮1.6: 选择dot文件（仅更新状态）"""
        file_path = filedialog.askopenfilename(
            title="选择DOT文件",
            filetypes=[("DOT文件", "*.dot"), ("所有文件", "*.*")]
        )

        if not file_path:
            return

        dot_src = Path(file_path)
        self.state.dot_file = dot_src
        self.state.work_dir = dot_src.parent
        self._update_status_display()
    
    # ===================== 按钮1.7: 过滤DOT文件 =====================
    
    def filter_dot_file(self):
        """选择任意DOT，过滤后写入统一目录，并更新状态区为新DOT。"""
        path_str = filedialog.askopenfilename(
            title="选择需要过滤的DOT文件",
            filetypes=[("DOT文件", "*.dot"), ("所有文件", "*.*")]
        )
        if not path_str:
            return
        src = Path(path_str)
        if not src.exists():
            self._show_message("错误", "文件不存在", is_error=True)
            return

        try:
            dst = self.filtered_dot_dir / f"{src.stem}_filt{src.suffix}"
            filter_dot.filter_file(src, dst)

            # 更新状态为新的DOT
            self.state.dot_file = dst
            self._update_status_display()
            self._show_message("成功", f"已生成过滤后的DOT:\n{dst}")
        except Exception as e:
            self._show_message("错误", f"过滤DOT失败:\n{e}", is_error=True)
    
    def _compile_to_expand(self, source_file: Path) -> Optional[Path]:
        """编译C文件生成expand文件
        
        策略：
        1. 首先检查源文件目录下是否已有expand文件
        2. 如果有，直接复制到rtl目录
        3. 如果没有，尝试使用gcc编译生成（自动检测include目录）
        """
        try:
            rtl_dir = self.state.work_dir / "rtl文件"
            
            # 策略1：检查是否已有expand文件
            # 查找 main.c.233r.expand 格式的文件
            existing_expand = list(source_file.parent.glob(f"{source_file.name}.*.expand"))
            
            if existing_expand:
                print(f"✅ 找到已有expand文件: {existing_expand[0].name}")
                expand_src = existing_expand[0]
                expand_dest = rtl_dir / expand_src.name
                
                import shutil
                shutil.copy2(str(expand_src), str(expand_dest))
                return expand_dest
            
            # 策略2：使用gcc编译生成
            print("⚙️  未找到已有expand文件，尝试使用gcc编译...")
            
            # 智能检测include目录（支持多种常见布局）
            include_dirs = []
            seen_paths = set()
            potential_include_paths = [
                source_file.parent / "include",      # 同级 include/
                source_file.parent / "includes",     # 同级 includes/
                source_file.parent / "../include",   # 上级 include/
                source_file.parent / "../includes",  # 上级 includes/
                source_file.parent / "inc",          # 同级 inc/
            ]
            
            for inc_path in potential_include_paths:
                if inc_path.exists() and inc_path.is_dir():
                    resolved_path = str(inc_path.resolve())
                    if resolved_path not in seen_paths:
                        seen_paths.add(resolved_path)
                        include_dirs.extend(["-I", resolved_path])
                        try:
                            rel_path = inc_path.relative_to(source_file.parent.parent)
                            print(f"   📁 检测到include目录: {rel_path}")
                        except ValueError:
                            print(f"   📁 检测到include目录: {inc_path.name}")
            
            # 构建gcc命令 - 使用相对路径和临时.o文件
            import tempfile
            
            # 在源文件目录创建临时.o文件
            with tempfile.NamedTemporaryFile(dir=source_file.parent, suffix=".o", delete=False) as tmp:
                obj_name = Path(tmp.name).name
            
            cmd = [
                "gcc",
                "-fdump-rtl-expand",
                *include_dirs,  # 添加include路径
                "-c",
                source_file.name,  # 使用相对路径（只有文件名）
                "-o", obj_name
            ]
            
            print(f"   🔨 GCC命令: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                cwd=str(source_file.parent),  # 在源文件目录执行
                capture_output=True,
                text=True
            )
            
            # 清理临时.o文件
            obj_file = source_file.parent / obj_name
            try:
                if obj_file.exists():
                    obj_file.unlink()
            except:
                pass
            
            if result.returncode != 0:
                print(f"❌ GCC编译失败: {result.stderr}")
                print("\n💡 提示: 如果源文件需要特殊的编译选项，")
                print("       建议先手动编译生成expand文件，")
                print(f"       然后将其放在: {source_file.parent}")
                return None
            
            # 查找生成的expand文件（按修改时间排序，取最新的）
            expand_files = sorted(
                source_file.parent.glob(f"{source_file.name}.*.expand"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            if not expand_files:
                print("❌ 未找到生成的expand文件")
                return None
            
            # 移动expand文件到rtl目录
            expand_src = expand_files[0]
            expand_dest = rtl_dir / expand_src.name
            
            import shutil
            shutil.move(str(expand_src), str(expand_dest))
            
            return expand_dest
            
        except Exception as e:
            print(f"编译expand失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    # ===================== 按钮2: 生成dag图 =====================
    
    def generate_dag(self):
        """按钮2: 生成dag图
        
        工作流程：
        - 若状态区已有 dot 文件：直接渲染并展示
        - 否则调用 legacy 生成 threads-only dot，再复制到工作目录并渲染
        """
        self._update_call_stats(visible=False)
        self._set_subfunc_toolbar(None)
        try:
            # 优先使用已有 dot
            if self.state.dot_file and self.state.dot_file.exists():
                dot_path = self.state.dot_file
                target_dir = (
                    self.state.work_dir / "生成dag图"
                    if self.state.work_dir else dot_path.parent
                )
                target_dir.mkdir(parents=True, exist_ok=True)
                png_path = target_dir / "dag.png"
                subprocess.run(
                    ["dot", "-Tpng", str(dot_path), "-o", str(png_path)],
                    check=True,
                    capture_output=True
                )
                self._display_image(png_path)
                self._show_message("成功", f"已直接渲染当前 DOT：{dot_path.name}")
                return

            if not self.state.expand_file:
                self._show_message("错误", "请先选择源文件或加载 DOT", is_error=True)
                return
            
            # 调用legacy生成dag图到配置文件目录
            cmd = [
                sys.executable,
                "-m", "mycallyplus_v1.generation.legacy",
                str(self.state.expand_file),
                "--threads-only",
                "--output-base", str(self.base_dir)
            ]
            
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir.parent),
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                self._show_message("错误", f"生成dag图失败:\n{result.stderr}", is_error=True)
                return
            
            # 从配置文件目录查找生成的文件
            source_name = (
                self.state.source_file.stem
                if self.state.source_file
                else self.state.get_base_name()
            )
            config_dir = None
            for cand in self._iter_config_dirs(source_name):
                if cand.exists():
                    config_dir = cand
                    break
            if config_dir is None:
                self._show_message("错误", f"未找到配置目录\n路径: {self._config_dir_for_base(source_name)}", is_error=True)
                return
            
            dot_files = list(config_dir.glob("*_threads.dot"))
            
            if not dot_files:
                self._show_message("错误", f"未找到threads.dot文件\n目录: {config_dir}", is_error=True)
                return
            
            source_dot = dot_files[0]

            # 统一存储路径：中间结果/<基名>/生成dag图/
            base_name = self.state.get_base_name() or source_name
            root_dir = self.base_dir / "中间结果" / base_name
            target_dir = root_dir / "生成dag图"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_dot = target_dir / "dag.dot"
            
            import shutil
            shutil.copy(source_dot, target_dot)

            # 更新工作目录到统一路径，避免后续模块误用配置目录
            self.state.work_dir = root_dir
            self.state.dot_file = target_dot
            # 生成并展示 PNG（需要本机安装 graphviz 的 dot 命令）
            png_path = target_dir / "dag.png"
            subprocess.run(
                ["dot", "-Tpng", str(target_dot), "-o", str(png_path)],
                check=True,
                capture_output=True,
            )
            self._display_image(png_path)
            self._update_status_display()
            self._show_message("成功", f"dag图生成成功：\n{png_path}")
            
        except Exception as e:
            self._show_message("错误", f"生成dag图失败:\n{e}", is_error=True)

    def generate_source_only_dag(self):
        """按钮2.1: 生成源码调用图（仅保留来自当前源文件的调用）"""
        if not self.state.expand_file or not self.state.source_file:
            self._show_message("错误", "请先选择源文件和 expand 文件", is_error=True)
            return

        try:
            # 统一存储路径：中间结果/<基名>/生成dag图/
            base_name = self.state.get_base_name() or self.state.source_file.stem
            root_dir = self.base_dir / "中间结果" / base_name
            target_dir = root_dir / "生成dag图"
            target_dir.mkdir(parents=True, exist_ok=True)
            target_dot = target_dir / "dag_source_only.dot"
            filtered_dot = target_dir / "dag_source_only_filt.dot"
            png_path = target_dir / "dag_source_only_filt.png"
            debug_dir = target_dir / "debug"
            # 更新工作目录为统一路径
            self.state.work_dir = root_dir

            cmd = [
                sys.executable,
                "-m", "mycallyplus_v1.generation.legacy",
                "--extern-only",
                "--source-file", str(self.state.source_file),
                "--output-base", str(self.base_dir),
                str(self.state.expand_file),
            ]
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir.parent),
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                self._show_message("错误", f"生成源码调用图失败:\n{result.stderr}", is_error=True)
                return

            # legacy stdout 是 dot，写入目标文件
            target_dot.write_text(result.stdout, encoding="utf-8")
            # 过滤版直接沿用
            import shutil
            shutil.copy2(target_dot, filtered_dot)

            # 渲染 PNG（仅过滤版）
            subprocess.run(
                ["dot", "-Tpng", str(filtered_dot), "-o", str(png_path)],
                check=True,
                capture_output=True,
            )

            # 读取 mycalls_meta 统计 extern
            internal_cnt = 0
            external_cnt = 0
            try:
                mycalls_meta_path = debug_dir / "mycalls_meta.json"
                if mycalls_meta_path.exists():
                    import json
                    data = json.loads(mycalls_meta_path.read_text(encoding="utf-8"))
                    for finfo in data.values():
                        if isinstance(finfo, dict):
                            for meta in finfo.values():
                                if not isinstance(meta, dict):
                                    continue
                                if meta.get("extern") == 0:
                                    internal_cnt += 1
                                else:
                                    external_cnt += 1
            except Exception:
                internal_cnt = external_cnt = 0

            # 更新状态为过滤后的 dot
            self.state.dot_file = filtered_dot
            self._update_status_display()
            self._update_call_stats(internal_cnt, external_cnt, visible=True)
            self._display_image(png_path)
            # 子功能：查看函数对应表（mycalls_meta）
            src_path = self.state.source_file
            exp_path = self.state.expand_file
            meta_path = debug_dir / "mycalls_meta.json"
            self._set_subfunc_toolbar([
                ("查看源代码", lambda p=src_path: self._open_file_with_system(p)),
                ("查看expand文件", lambda p=exp_path: self._open_file_with_system(p)),
                ("查看函数对应表", lambda p=meta_path: self._open_file_with_system(p)),
            ])
            self._show_message("成功", f"源码调用图已生成：{filtered_dot.name}")

        except Exception as e:
            self._show_message("错误", f"生成源码调用图失败:\n{e}", is_error=True)
    
    # ===================== 按钮3: 查看条件节点 =====================
    
    def view_conditions(self):
        """按钮3: 查看条件节点
        
        工作流程：
        1. 调用legacy生成完整视图（包含条件节点）
        2. 同时生成circle.txt配置文件
        3. 保存到配置文件目录和中间结果目录
        4. 生成PNG并显示
        """
        if not self.state.expand_file:
            self._show_message("错误", "请先选择源文件", is_error=True)
            return
        
        try:
            # 统一 basename（与 legacy/_ensure_output_dirs 一致：去掉 .233r 与 .c/.cpp 等）
            base_name = self.state.get_base_name() or (self.state.source_file.stem if self.state.source_file else None)
            if not base_name:
                self._show_message("错误", "无法解析基名（请确认已选择 expand 文件）", is_error=True)
                return

            root_dir = self.base_dir / "中间结果" / base_name
            target_dir = root_dir / "查看条件节点"
            target_dir.mkdir(parents=True, exist_ok=True)
            # 更新工作目录为统一路径，避免后续模块误用配置目录
            self.state.work_dir = root_dir

            # 配置文件目录：中间结果/<基名>/配置文件（legacy 会写入 <基名>_full.dot）
            config_dir = self._config_dir_for_base(base_name)
            config_dir.mkdir(parents=True, exist_ok=True)

            # 步骤1: 调用 legacy 生成条件视图 DOT（--conditions-only）
            print("⚙️  调用mycallyplus生成条件节点视图（--conditions-only）...")
            cmd = [
                sys.executable,
                "-m", "mycallyplus_v1.generation.legacy",
                "--conditions-only",
                "--output-base", str(self.base_dir),
                str(self.state.expand_file),
            ]
            result = subprocess.run(
                cmd,
                cwd=str(self.base_dir.parent),
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                self._show_message("错误", f"生成条件节点视图失败:\n{result.stderr}", is_error=True)
                return

            config_dot = config_dir / f"{base_name}_full.dot"
            if not config_dot.exists():
                self._show_message("错误", f"未找到生成的 full.dot 文件:\n{config_dot}", is_error=True)
                return
            
            # 步骤2: 调用legacy生成circle.txt（使用--export-txt参数）
            print("⚙️  生成circle.txt配置文件...")
            
            txt_output_path = config_dir / "circle.txt"
            cmd_txt = [
                sys.executable,
                "-m", "mycallyplus_v1.generation.legacy",
                str(self.state.expand_file),
                "--export-txt", str(txt_output_path),
                "--output-base", str(self.base_dir)
            ]
            
            result_txt = subprocess.run(
                cmd_txt,
                cwd=str(self.base_dir.parent),
                capture_output=True,
                text=True
            )
            
            if result_txt.returncode != 0:
                print(f"⚠️  生成circle.txt警告: {result_txt.stderr}")
            else:
                print(f"✅ 生成circle.txt: {txt_output_path}")
            
            # 步骤3: 复制到中间结果目录
            import shutil
            target_dot = target_dir / "conditions.dot"
            shutil.copy(config_dot, target_dot)
            
            # 步骤4: 生成PNG
            png_path = target_dir / "conditions.png"
            subprocess.run(
                ["dot", "-Tpng", str(target_dot), "-o", str(png_path)],
                check=True,
                capture_output=True
            )
            print(f"✅ 生成PNG图像: {png_path}")
            
            # 步骤5: 更新状态
            source_txt = config_dir / "circle.txt"
            if source_txt.exists():
                self.state.txt_file = source_txt
                print(f"✅ 配置文件就绪: {source_txt}")
            
            self.state.dot_file = target_dot
            self._update_status_display()
            
            # 显示图片
            self._display_image(png_path)
            
            self._show_message("成功", f"条件节点图和配置文件生成成功\n\nDOT: {config_dot}\nTXT: {txt_output_path}")
            
        except Exception as e:
            self._show_message("错误", f"查看条件节点失败:\n{e}", is_error=True)
            import traceback
            traceback.print_exc()
    
    # ===================== 按钮4: 选择配置文件 =====================
    
    def select_config_folder(self):
        """按钮4: 选择配置文件夹"""
        folder_path = filedialog.askdirectory(
            title="选择配置文件夹"
        )
        
        if not folder_path:
            return
        
        try:
            folder = Path(folder_path)
            
            # 查找dot和txt文件
            dot_files = list(folder.glob("*.dot"))
            txt_files = list(folder.glob("*.txt"))
            
            if not dot_files and not txt_files:
                self._show_message("错误", "文件夹中没有找到.dot或.txt文件", is_error=True)
                return
            
            # 更新状态
            if dot_files:
                self.state.dot_file = dot_files[0]  # 取第一个dot文件
            
            if txt_files:
                self.state.txt_file = txt_files[0]  # 取第一个txt文件

            # 若尚未建立工作目录，则根据配置目录名初始化
            if self.state.work_dir is None:
                # 兼容新旧目录：如果选择的是 .../中间结果/<base>/配置文件，则 base_name = 上级目录名
                if folder.name == "配置文件" and folder.parent.name:
                    base_name = folder.parent.name
                else:
                    base_name = folder.name
                self.state.work_dir = self.base_dir / "中间结果" / base_name
                self.state.work_dir.mkdir(parents=True, exist_ok=True)
                for sub in [
                    "生成dag图",
                    "查看条件节点",
                    "查看互斥锁图",
                    "生成信号量图",
                    "配置文件",
                    "debug",
                    "logs",
                    "temp",
                    "images",
                ]:
                    (self.state.work_dir / sub).mkdir(parents=True, exist_ok=True)

            # 重置缓存图像
            self.cached_images = {key: None for key in self.cached_images}

            self._update_status_display()
            
            # 如果有dot文件，尝试生成并显示PNG
            if self.state.dot_file:
                try:
                    png_path = self.state.dot_file.with_suffix('.png')
                    subprocess.run(
                        ["dot", "-Tpng", str(self.state.dot_file), "-o", str(png_path)],
                        check=True,
                        capture_output=True
                    )
                    self._display_image(png_path)
                except:
                    pass
            
            self._show_message("成功", f"配置文件已加载\nDOT: {len(dot_files)}个\nTXT: {len(txt_files)}个")

        except Exception as e:
            self._show_message("错误", f"加载配置文件夹失败:\n{e}", is_error=True)
    
    # ===================== 按钮5: 查看互斥锁 =====================
    
    def view_mutex(self):
        """按钮5: 查看互斥锁
        
        功能：
        1. 解析circle.txt中的互斥量信息
        2. 使用networkx分析互斥锁覆盖区域
        3. 提供两个子功能：查看互斥锁图、查看互斥锁信息
        """
        if not self.state.dot_file or not self.state.txt_file:
            self._show_message("错误", "请先完成按钮3（生成条件节点图）\n需要DOT文件和circle.txt", is_error=True)
            self._set_subfunc_toolbar(None)
            return
        
        if not nx:
            self._show_message("错误", "需要安装networkx库:\npip install networkx", is_error=True)
            self._set_subfunc_toolbar(None)
            return
        
        try:
            print("⚙️  开始解析互斥锁信息...")

            self.cached_images["mutex"] = None
            # 步骤1: 读取DOT文件并构建图
            self.G = self._read_dot_to_networkx(self.state.dot_file)
            print(f"✅ 读取图结构: {len(self.G.nodes())} 节点, {len(self.G.edges())} 边")
            
            # 步骤2: 解析互斥锁配对
            self.mutex_records = self._parse_mutex_from_txt(self.state.txt_file)
            if not self.mutex_records:
                txt_content = self.state.txt_file.read_text(encoding='utf-8', errors='ignore').strip()
                if not txt_content:
                    self._show_message(
                        "提示",
                        "配置文件为空\n\n"
                        "原因：源代码中未检测到互斥锁（pthread_mutex_lock/unlock）\n\n"
                        "说明：\n"
                        "• 如果您的代码使用了互斥锁，请确保已正确编译生成expand文件\n"
                        "• 如果代码确实不包含互斥锁，这是正常的",
                        is_error=False,
                    )
                else:
                    self._show_message(
                        "提示",
                        "未找到互斥锁配对信息\n\n"
                        "可能原因：\n"
                        "• circle.txt格式不正确\n"
                        "• 互斥锁lock/unlock未成对出现\n"
                        "• 节点名称在DOT文件中不存在",
                        is_error=False,
                    )
                self.mutex_records = []  # 继续执行但配对为空
            print(f"✅ 找到 {len(self.mutex_records)} 个互斥锁配对")
            
            # 步骤3: 分析覆盖区域
            for rec in self.mutex_records:
                if rec.lock not in self.G.nodes or rec.unlock not in self.G.nodes:
                    print(f"⚠️  节点不存在: {rec.lock} 或 {rec.unlock}")
                    continue
                try:
                    reach_from_lock = nx.descendants(self.G, rec.lock)
                    reach_to_unlock = nx.ancestors(self.G, rec.unlock)
                    between = reach_from_lock & reach_to_unlock | {rec.lock, rec.unlock}
                    rec.covered = sorted(between, key=lambda x: self._suffix_num(x))
                    print(f"✅ 互斥锁 {rec.idx}: 覆盖 {len(rec.covered)} 个节点")
                except Exception as e:
                    print(f"⚠️  分析失败: {e}")
            
            # 标记为已准备
            self.mutex_prepared = True
            
            # 设置子功能按钮
            self._set_subfunc_toolbar([
                ("查看互斥锁图", lambda: self._display_cached_image("mutex", fallback=self._show_mutex_graph)),
                ("查看互斥锁信息", self.show_mutex_info),
            ])

            # 默认显示互斥锁图
            self._show_mutex_graph()
            
        except Exception as e:
            self._show_message("错误", f"查看互斥锁失败:\n{e}", is_error=True)
            self._set_subfunc_toolbar(None)
            import traceback
            traceback.print_exc()
    
    def _show_mutex_graph(self):
        """子功能1: 显示互斥锁图（带彩色子图）"""
        if not self.mutex_prepared:
            self._show_message("警告", "请先点击'查看互斥锁'解析数据", is_error=False)
            return
        
        try:
            print("⚙️  生成互斥锁图...")
            
            # 生成DOT内容
            dot_lines = ['digraph Mutex {']
            dot_lines.append('  rankdir=LR;')
            dot_lines.append('  node [shape=box, style=filled, fillcolor=white];')
            
            # 添加所有边
            dot_lines.append('\n  // Edges')
            for u, v in self.G.edges():
                dot_lines.append(f'  "{u}" -> "{v}";')
            
            # 创建互斥锁子图（彩色）
            color_map = {}
            cluster_id = 0
            for rec in self.mutex_records:
                if not rec.covered:
                    continue
                
                # 分配颜色
                color = self.MUTEX_COLORS[len(color_map) % len(self.MUTEX_COLORS)]
                color_map[rec.var] = color
                cluster_id += 1
                
                # 创建子图
                dot_lines.append(f'\n  subgraph cluster_{cluster_id} {{')
                dot_lines.append(f'    label="Mutex {rec.var} (ID={rec.idx})";')
                dot_lines.append(f'    color="{color}";')
                dot_lines.append(f'    style=filled;')
                dot_lines.append(f'    fillcolor="{color}30";')  # 半透明背景
                dot_lines.append(f'    fontcolor=black;')
                dot_lines.append(f'    fontsize=12;')
                
                # 添加节点
                for node in rec.covered:
                    label = node
                    if node == rec.lock:
                        label = f"{node}\\n[LOCK]"
                    elif node == rec.unlock:
                        label = f"{node}\\n[UNLOCK]"
                    dot_lines.append(f'    "{node}" [label="{label}"];')
                
                dot_lines.append('  }')
            
            dot_lines.append('}')
            dot_content = '\n'.join(dot_lines)
            
            # 保存并渲染
            target_dir = self.state.work_dir / "查看互斥锁"
            target_dir.mkdir(parents=True, exist_ok=True)
            
            dot_path = target_dir / "mutex_graph.dot"
            dot_path.write_text(dot_content, encoding='utf-8')

            png_path = target_dir / "mutex_graph.png"
            subprocess.run(
                ["dot", "-Gdpi=110", "-Tpng", str(dot_path), "-o", str(png_path)],
                check=True,
                capture_output=True
            )
            print(f"✅ 生成互斥锁图: {png_path}")
            self.cached_images["mutex"] = png_path if png_path.exists() else None

            # 显示图像
            self._display_image(png_path)
            
        except Exception as e:
            self._show_message("错误", f"生成互斥锁图失败:\n{e}", is_error=True)
            import traceback
            traceback.print_exc()
    
    def show_mutex_info(self):
        """子功能2: 在画布上显示互斥锁文本信息"""
        if not self.mutex_prepared:
            self._show_message("警告", "请先点击'查看互斥锁'解析数据", is_error=False)
            return

        top = tk.Toplevel(self.root)
        top.title("互斥锁信息")
        top.geometry("720x520")

        text_widget = tk.Text(top, font=("Consolas", 10), wrap=tk.WORD)
        scrollbar = tk.Scrollbar(top, command=text_widget.yview)
        text_widget.configure(yscrollcommand=scrollbar.set)
        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        if not self.mutex_records:
            text_widget.insert(tk.END, "当前配置未匹配到任何互斥锁配对。\n")
        else:
            for i, rec in enumerate(self.mutex_records, 1):
                lines = [
                    f"[Mutex {i}] var={rec.var}  ID={rec.idx}",
                    f"  LOCK   : {rec.lock}",
                    f"  UNLOCK : {rec.unlock}",
                ]
                if rec.lock_file or rec.unlock_file:
                    lines.append(f"  FILE   : {rec.lock_file or rec.unlock_file}")
                if rec.lock_line is not None or rec.unlock_line is not None:
                    a = rec.lock_line if rec.lock_line is not None else "?"
                    b = rec.unlock_line if rec.unlock_line is not None else "?"
                    lines.append(f"  LINES  : {a} -> {b}")
                covered = rec.covered or []
                lines.append(f"  COVERED ({len(covered)} nodes):")
                preview = covered[:20]
                for node in preview:
                    mark = ""
                    if node == rec.lock:
                        mark = " [LOCK]"
                    elif node == rec.unlock:
                        mark = " [UNLOCK]"
                    lines.append(f"    - {node}{mark}")
                if len(covered) > len(preview):
                    lines.append(f"    ... 还有 {len(covered) - len(preview)} 个节点")
                text_widget.insert(tk.END, "\n".join(lines) + "\n\n")

        text_widget.config(state=tk.DISABLED)
    
    # ===================== 按钮6: 生成信号量图 =====================
    
    def generate_semaphore(self):
        """按钮6: 生成信号量图
        
        功能：
        1. 解析circle.txt中的信号量信息
        2. 在原始图上添加信号量边（sem_post → sem_wait）
        3. 运行Tarjan算法分析强连通分量
        4. 生成线程分组的可视化图
        """
        if not self.state.dot_file or not self.state.txt_file:
            self._show_message("错误", "请先完成按钮3（生成条件节点图）\n需要DOT文件和circle.txt", is_error=True)
            return
        
        if not nx:
            self._show_message("错误", "需要安装networkx库:\npip install networkx", is_error=True)
            return
        
        try:
            print("⚙️  开始生成信号量图...")

            for key in ("original", "tarjan", "threads"):
                self.cached_images[key] = None
            # 步骤1: 读取原始图
            G = self._read_dot_to_networkx(self.state.dot_file)
            print(f"✅ 读取原始图: {len(G.nodes())} 节点, {len(G.edges())} 边")
            
            # 步骤2: 解析信号量配对
            sem_records = self._parse_semaphore_from_txt(self.state.txt_file)
            if not sem_records:
                txt_content = self.state.txt_file.read_text(encoding='utf-8', errors='ignore').strip()
                if not txt_content:
                    self._show_message(
                        "提示",
                        "配置文件为空\n\n"
                        "原因：源代码中未检测到信号量（sem_post/sem_wait）\n\n"
                        "说明：\n"
                        "• 如果您的代码使用了信号量，请确保已正确编译生成expand文件\n"
                        "• 如果代码确实不包含信号量，这是正常的",
                        is_error=False,
                    )
                else:
                    self._show_message(
                        "提示",
                        "未找到信号量配对信息\n\n"
                        "可能原因：\n"
                        "• circle.txt格式不正确\n"
                        "• 信号量post/wait未成对出现\n"
                        "• 节点名称在DOT文件中不存在",
                        is_error=False,
                    )
                sem_records = []
            print(f"✅ 找到 {len(sem_records)} 个信号量配对")
            
            # 步骤3: 添加信号量边
            self.sem_records = sem_records
            G_sem = G.copy()
            for rec in sem_records:
                if rec.post in G_sem.nodes and rec.wait in G_sem.nodes:
                    G_sem.add_edge(
                        rec.post,
                        rec.wait,
                        style='dashed',
                        color='#FF7043',
                        label=f'{rec.var} {rec.idx}',
                    )
                    print(f"✅ 添加信号量边: {rec.post} → {rec.wait}")

            # 步骤4: 运行Tarjan算法
            sccs = list(nx.strongly_connected_components(G_sem))
            self.sccs = sccs
            print(f"✅ Tarjan分析: 找到 {len(sccs)} 个强连通分量")

            # 步骤5: 生成多个视图
            target_dir = self.state.work_dir / "生成信号量图"
            target_dir.mkdir(parents=True, exist_ok=True)

            # 线程颜色映射
            thread_colors: Dict[str, str] = {}
            for node in G_sem.nodes():
                prefix = node.split('/', 1)[0] if '/' in node else 'main'
                if prefix not in thread_colors:
                    color_idx = len(thread_colors) % len(self.THREAD_COLORS)
                    thread_colors[prefix] = self.THREAD_COLORS[color_idx]
            self.thread_color_map = thread_colors

            # 视图1: 原始图+信号量边
            self._generate_semaphore_original(G_sem, target_dir)
            
            # 视图2: Tarjan强连通分量图
            self._generate_semaphore_tarjan(G_sem, sccs, target_dir)
            
            # 视图3: 线程分组图
            self._generate_semaphore_threads(G_sem, sccs, target_dir)
            
            # 步骤6: 显示线程分组图
            png_path = target_dir / "threads.png"
            if png_path.exists():
                self._display_image(png_path)

            info_lines = ["信号量图生成完成！\n"]
            info_lines.append(f"信号量配对: {len(sem_records)} 个")
            info_lines.append(f"强连通分量: {len(sccs)} 个\n")
            info_lines.append("生成文件:")
            info_lines.append("  • original.png - 原始图+信号量边")
            info_lines.append("  • tarjan.png - 强连通分量图")
            info_lines.append("  • threads.png - 线程分组图")

            self._set_subfunc_toolbar([
                ("查看原始图", lambda: self._display_cached_image("original")),
                ("查看强连通分量", lambda: self._display_cached_image("tarjan")),
                ("查看信号量图", lambda: self._display_cached_image("threads")),
                ("显示信号量信息", self.show_semaphore_info),
                ("显示线程颜色图例", self.show_thread_legend),
            ])

            self._show_message("成功", "\n".join(info_lines))
            
        except Exception as e:
            self._show_message("错误", f"生成信号量图失败:\n{e}", is_error=True)
            import traceback
            traceback.print_exc()

    # ===================== 按钮7: 时间分析 =====================

    def time_analysis_entry(self):
        """按钮7: 时间分析 - 选择源代码与 JSON 后自动插桩编译运行。"""
        self._update_call_stats(visible=False)
        self.ta_source_file = None
        self.ta_json_file = None
        self._set_subfunc_toolbar([
            ("选中源代码文件", self._select_ta_source_file),
            ("选中JSON文件", self._select_ta_json_file),
            ("段级时间分析（Level-1）", self._ta_level1_one_click),
            ("线程中任务执行次数图", self._plot_thread_task_frequency),
            ("线程执行时间图", self._plot_thread_total_time),
            ("线程调用图", self._plot_thread_call_gantt),
        ])
        self._show_message("提示", "请选择源代码文件和 mycalls_meta_internal.json，完成后自动执行时间分析。")

    def _ta_level1_one_click(self):
        """时间分析子功能：段级时间分析（Level-1）一键跑到底。

        Pipeline:
          legacy(--source-file, --level1-stage1) -> stage1 seg DAG
          -> segment timing -> LPF thread schedule -> prio instrument compare
        Inputs come from status area (state.source_file, state.expand_file).
        """
        if not self.state.expand_file or not self.state.expand_file.exists():
            self._show_message("错误", "状态区缺少 expand 文件，请先选择 expand 文件。", is_error=True)
            return
        if not self.state.source_file or not self.state.source_file.exists():
            self._show_message("错误", "状态区缺少源 C 文件，请先选择源文件。", is_error=True)
            return

        base_name = self.state.source_file.stem if self.state.source_file else None
        if not base_name:
            base_name = self.state.get_base_name()
        if not base_name:
            self._show_message("错误", "无法推导 base_name。", is_error=True)
            return

        try:
            # 1) legacy generate + level1 stage1
            cmd = [
                sys.executable,
                "-m",
                "mycallyplus_v1.generation.legacy",
                str(self.state.expand_file),
                "--threads-only",
                "--source-file",
                str(self.state.source_file),
                "--output-base",
                str(self.base_dir),
                "--force",
                "--level1-stage1",
            ]
            result = subprocess.run(cmd, cwd=str(self.base_dir.parent), capture_output=True, text=True)
            if result.returncode != 0:
                self._show_message("错误", f"Level-1 stage1 生成失败:\n{result.stderr}", is_error=True)
                return

            # 2) render segment DAG png and display (default)
            seg_dot = self.base_dir / "中间结果" / base_name / "level1" / "stage1" / "dag_stage1_seg.dot"
            seg_png = self.base_dir / "中间结果" / base_name / "level1" / "stage1" / "dag_stage1_seg.png"
            subprocess.run(["dot", "-Tpng", str(seg_dot), "-o", str(seg_png)], check=True, capture_output=True)
            self._display_image(seg_png)

            # 3) segment timing (one run)
            ta_cmd = [
                sys.executable,
                "-m",
                "mycallyplus_v1.level1.time_analysis_level1",
                "--base-dir",
                str(self.base_dir),
                "--base-name",
                base_name,
                "--source",
                str(self.state.source_file),
            ]
            ta_res = subprocess.run(ta_cmd, cwd=str(self.base_dir.parent), capture_output=True, text=True)
            if ta_res.returncode != 0:
                self._show_message("错误", f"段级时间分析失败:\n{ta_res.stderr}", is_error=True)
                return

            # 4) LPF schedule (thread)
            sched_cmd = [
                sys.executable,
                "-m",
                "mycallyplus_v1.level1.lpf_segment",
                "--base-dir",
                str(self.base_dir),
                "--base-name",
                base_name,
                "--project",
                base_name,
                "--prio-max",
                "80",
            ]
            sched_res = subprocess.run(sched_cmd, cwd=str(self.base_dir.parent), capture_output=True, text=True)
            if sched_res.returncode != 0:
                self._show_message("错误", f"LPF 调度失败:\n{sched_res.stderr}", is_error=True)
                return

            # 5) prio instrument compare
            prio_cmd = [
                sys.executable,
                "-m",
                "mycallyplus_v1.level1.instrument_prio_level1",
                "--base-dir",
                str(self.base_dir),
                "--base-name",
                base_name,
                "--source",
                str(self.state.source_file),
            ]
            prio_res = subprocess.run(prio_cmd, cwd=str(self.base_dir.parent), capture_output=True, text=True)
            if prio_res.returncode != 0:
                self._show_message("错误", f"优先级插桩对比失败:\n{prio_res.stderr}", is_error=True)
                return

            # Parse compare.json path from stdout (last "wrote ...")
            compare_path = None
            for ln in prio_res.stdout.splitlines():
                if ln.startswith("wrote "):
                    compare_path = Path(ln[len("wrote ") :].strip())
            if compare_path and compare_path.exists():
                try:
                    compare = json.loads(compare_path.read_text(encoding="utf-8"))
                    if compare.get("prio_set_failed"):
                        messagebox.showwarning(
                            "提示",
                            "检测到线程优先级设置失败（可能缺少 root/CAP_SYS_NICE 权限），"
                            "本次 prio 对比结果可能与 FIFO 无显著差异。\n"
                            f"详情见: {compare_path}",
                        )
                except Exception:
                    pass

            # 6) run experiment script (if present) to get baseline/prio runtimes
            run_script = None
            if compare_path:
                candidate = compare_path.parent / "run_experiments.sh"
                if candidate.exists():
                    run_script = candidate
            run_result_path = None
            if run_script:
                try:
                    run_res = subprocess.run(
                        ["bash", str(run_script)],
                        cwd=str(run_script.parent),
                        capture_output=True,
                        text=True,
                        check=True,
                    )
                    for ln in run_res.stdout.splitlines():
                        if "Results saved to" in ln:
                            run_result_path = Path(ln.split("Results saved to", 1)[1].strip())
                            break
                except Exception as e:
                    self._show_message("错误", f"运行对照脚本失败:\n{e}", is_error=True)

            self._show_message(
                "成功",
                "段级时间分析（Level-1）已完成：\n"
                f"- 段级 DAG: {seg_png}\n"
                f"- 段级测时: {self.base_dir/'中间结果'/base_name/'level1'/'timing'/base_name/'time_result_seg.json'}\n"
                f"- LPF schedule: {self.base_dir/'中间结果'/base_name/'level1'/'schedule'/'lpf_segment'/'schedule_seg.json'}\n"
                f"- 对比结果: {compare_path if compare_path else '(unknown)'}\n"
                f"- 运行时间结果: {run_result_path if run_result_path else '未生成或脚本缺失'}",
            )
        except subprocess.CalledProcessError as e:
            self._show_message("错误", f"命令执行失败:\n{e}", is_error=True)
        except Exception as e:
            self._show_message("错误", f"段级时间分析（Level-1）失败:\n{e}", is_error=True)

    # ===================== 按钮8: 调度算法 =====================

    def scheduler_entry(self):
        """按钮8: 调度算法 - 最长路径（带权 DAG）"""
        self._set_subfunc_toolbar([
            ("生成最长路径", self._scheduler_longest_path),
            ("CPC分析", self._scheduler_cpc),
            ("CPC优先级插桩", self._scheduler_cpc_instrument),
            ("实验结果对比", self._scheduler_compare_metrics),
        ])
        self._show_message(
            "提示",
            "请选择 DAG 的 DOT 文件与 time_result.json，生成带权 DAG 并计算最长路径；或执行 CPC 分析/优先级插桩。",
        )

    def _scheduler_longest_path(self):
        dot_str = filedialog.askopenfilename(
            title="选择 DAG DOT 文件",
            filetypes=[("DOT文件", "*.dot"), ("所有文件", "*.*")],
        )
        if not dot_str:
            return
        json_str = filedialog.askopenfilename(
            title="选择 time_result.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not json_str:
            return

        dot_path = Path(dot_str)
        json_path = Path(json_str)

        try:
            nodes, edges = scheduler.parse_dot_edges(dot_path)
            weights = scheduler.load_time_result_weights(json_path)
            source = scheduler.find_single_source(nodes, edges)
            if source is None:
                # 不阻塞：按“全图任意起点”求最长路径，但提示用户源点不唯一
                pass
            result = scheduler.longest_path_dag(nodes, edges, weights, source=source)

            base_name = self._infer_base_from_path(json_path)
            out_dir = None
            if base_name:
                out_dir = self.base_dir / "中间结果" / base_name / "调度算法"
            else:
                out_dir = json_path.parent / "调度算法"
            out_dir.mkdir(parents=True, exist_ok=True)
            highlight_dot_path = out_dir / "dag_highlight.dot"
            highlight_png_path = out_dir / "dag_highlight.png"
            longest_json_path = out_dir / "longest_path.json"
            longest_txt_path = out_dir / "longest_path.txt"

            original_dot_text = dot_path.read_text(encoding="utf-8", errors="replace")
            highlight_text = scheduler.highlight_dot_inplace(
                original_dot_text,
                path_nodes=result.path,
                path_edges=list(zip(result.path, result.path[1:])),
                node_weight_ns=result.node_weight_ns,
            )
            highlight_dot_path.write_text(highlight_text, encoding="utf-8")
            scheduler.write_longest_path_json(
                longest_json_path,
                dot_path=dot_path,
                time_json_path=json_path,
                result=result,
            )
            # 便于人工查看
            longest_txt_path.write_text(
                "最长路径（节点权重=total_ns，缺失权重按 0 计）：\n"
                f"总耗时: {result.total_weight_ns:,} ns\n"
                f"路径长度: {len(result.path)}\n"
                + "\n".join(result.path)
                + "\n",
                encoding="utf-8",
            )

            subprocess.run(
                ["dot", "-Tpng", str(highlight_dot_path), "-o", str(highlight_png_path)],
                check=True,
                capture_output=True,
            )
            self._display_image(highlight_png_path)
            self._show_message(
                "成功",
                "已生成带权 DAG 与最长路径：\n"
                f"DOT: {highlight_dot_path}\n"
                f"PNG: {highlight_png_path}\n"
                f"JSON: {longest_json_path}",
            )
        except Exception as e:
            # scheduler.longest_path_dag 会在有环时给出中文报错
            self._show_message("错误", f"生成最长路径失败:\n{e}", is_error=True)

    def _scheduler_cpc(self):
        dot_str = filedialog.askopenfilename(
            title="选择 DAG DOT 文件",
            filetypes=[("DOT文件", "*.dot"), ("所有文件", "*.*")],
        )
        if not dot_str:
            return
        time_json_str = filedialog.askopenfilename(
            title="选择 time_result.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not time_json_str:
            return
        longest_json_str = filedialog.askopenfilename(
            title="选择 longest_path.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not longest_json_str:
            return

        dot_path = Path(dot_str)
        time_json_path = Path(time_json_str)
        longest_json_path = Path(longest_json_str)

        try:
            nodes, edges = scheduler.parse_dot_edges(dot_path)
            weights = scheduler.load_time_result_weights(time_json_path)
            longest = json.loads(longest_json_path.read_text(encoding="utf-8"))
            longest_path_nodes = longest.get("path", [])

            if not longest_path_nodes:
                raise RuntimeError("longest_path.json 中缺少 path 字段或为空。")

            result = scheduler.compute_cpc_priorities(
                nodes,
                edges,
                weights,
                longest_path_nodes,
                m=2,
            )

            base_name = self._infer_base_from_path(time_json_path)
            out_dir = None
            if base_name:
                out_dir = self.base_dir / "中间结果" / base_name / "调度算法" / "cpc"
            else:
                out_dir = time_json_path.parent / "调度算法" / "cpc"
            out_dir.mkdir(parents=True, exist_ok=True)

            highlight_dot_path = out_dir / "dag_highlight.dot"
            highlight_png_path = out_dir / "dag_highlight.png"
            schedule_json_path = out_dir / "schedule.json"
            schedule_txt_path = out_dir / "schedule.txt"

            original_dot_text = dot_path.read_text(encoding="utf-8", errors="replace")
            highlight_text = scheduler.apply_priorities_to_dot(
                original_dot_text,
                priorities=result.priorities,
                node_weight_ns=result.node_weight_ns,
                longest_path=result.longest_path,
            )
            highlight_dot_path.write_text(highlight_text, encoding="utf-8")

            scheduler.write_cpc_schedule_json(
                schedule_json_path,
                dot_path=dot_path,
                time_json_path=time_json_path,
                longest_json_path=longest_json_path,
                result=result,
            )
            schedule_txt_path.write_text(
                "CPC 节点优先级（m=2，缺权重置 0）：\n"
                f"provider 段数: {len(result.providers)}\n"
                f"节点数: {len(result.priorities)}\n"
                + "\n".join(f"{n}: prio={p}, weight={result.node_weight_ns.get(n,0)}"
                            for n, p in sorted(result.priorities.items(), key=lambda kv: -kv[1])),
                encoding="utf-8",
            )

            subprocess.run(
                ["dot", "-Tpng", str(highlight_dot_path), "-o", str(highlight_png_path)],
                check=True,
                capture_output=True,
            )
            self._display_image(highlight_png_path)
            self._show_message(
                "成功",
                "CPC 分析完成：\n"
                f"DOT: {highlight_dot_path}\n"
                f"PNG: {highlight_png_path}\n"
                f"JSON: {schedule_json_path}",
            )
        except Exception as e:
            self._show_message("错误", f"CPC 分析失败:\n{e}", is_error=True)

    def _scheduler_cpc_instrument(self):
        src_str = filedialog.askopenfilename(
            title="选择源代码文件（C）",
            filetypes=[("C源文件", "*.c"), ("所有文件", "*.*")],
        )
        if not src_str:
            return
        meta_str = filedialog.askopenfilename(
            title="选择 mycalls_meta_internal.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not meta_str:
            return
        schedule_str = filedialog.askopenfilename(
            title="选择 CPC schedule.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not schedule_str:
            return

        src_path = Path(src_str)
        meta_path = Path(meta_str)
        schedule_path = Path(schedule_str)

        try:
            sched_data = json.loads(schedule_path.read_text(encoding="utf-8"))
            priorities = sched_data.get("priorities")
            if not isinstance(priorities, dict):
                raise RuntimeError("schedule.json 中未找到 priorities 对象。")

            result = time_analysis.run_time_analysis(
                src_path,
                meta_path,
                self.base_dir,
                priorities=priorities,
                cpc_mode=True,
            )

            base_name = self._infer_base_from_path(meta_path) or src_path.stem
            out_dir = self.base_dir / "中间结果" / base_name / "调度算法" / "cpc分析结果"
            out_dir.mkdir(parents=True, exist_ok=True)

            # 复制相关输出便于对比
            shutil.copy2(result.result_json, out_dir / "time_result.json")
            if result.prio_result_json:
                shutil.copy2(result.prio_result_json, out_dir / "time_result_prio.json")
            if result.prio_weighted_dot:
                shutil.copy2(result.prio_weighted_dot, out_dir / "dag_weighted_prio.dot")
            weighted_src = result.result_json.parent / "dag_weighted.dot"
            if weighted_src.exists():
                shutil.copy2(weighted_src, out_dir / "dag_weighted.dot")
            summary_src = meta_path.parent / "thread_time_summary.json"
            if summary_src.exists():
                shutil.copy2(summary_src, out_dir / "thread_time_summary.json")
            if result.metrics_json and result.metrics_json.exists():
                shutil.copy2(result.metrics_json, out_dir / result.metrics_json.name)

            self._show_message(
                "成功",
                "已完成 CPC 优先级插桩时间分析：\n"
                f"输出目录: {out_dir}\n"
                f"基础结果: {out_dir / 'time_result.json'}\n"
                f"优先级结果: {out_dir / 'time_result_prio.json'}",
            )
        except Exception as e:
            self._show_message("错误", f"CPC 插桩时间分析失败:\n{e}", is_error=True)

    def _select_ta_source_file(self):
        path_str = filedialog.askopenfilename(
            title="选择C源文件（时间分析）",
            filetypes=[("C源文件", "*.c"), ("所有文件", "*.*")]
        )
        if not path_str:
            return
        self.ta_source_file = Path(path_str)
        self._maybe_run_time_analysis()

    def _select_ta_json_file(self):
        path_str = filedialog.askopenfilename(
            title="选择 mycalls_meta_internal.json",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if not path_str:
            return
        self.ta_json_file = Path(path_str)
        self._maybe_run_time_analysis()

    def _maybe_run_time_analysis(self):
        if not self.ta_source_file or not self.ta_json_file:
            return
        try:
            result = time_analysis.run_time_analysis(
                self.ta_source_file,
                self.ta_json_file,
                self.base_dir,
            )
            # 将工作目录指向输出，便于后续查看
            self.state.work_dir = result.instrumented_dir
            trace_path = result.result_json.parent / "thread_trace.json"
            self._show_message(
                "成功",
                "时间分析完成：\n"
                f"插桩目录: {result.instrumented_dir}\n"
                f"结果: {result.result_json}\n"
                f"指标: {result.metrics_json}\n"
                f"Trace: {trace_path}\n"
                f"日志: {result.log_path}",
            )
        except Exception as e:
            self._show_message("错误", f"时间分析失败:\n{e}", is_error=True)

    def _scheduler_compare_metrics(self):
        file_a = filedialog.askopenfilename(
            title="选择指标文件 A (metrics*.json)",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_a:
            return
        file_b = filedialog.askopenfilename(
            title="选择指标文件 B (metrics*.json)",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not file_b:
            return

        path_a = Path(file_a)
        path_b = Path(file_b)
        try:
            m_a = json.loads(path_a.read_text(encoding="utf-8"))
            m_b = json.loads(path_b.read_text(encoding="utf-8"))
            base_name = self._infer_base_from_path(path_a) or self._infer_base_from_path(path_b) or "compare"
            root_dir = self.base_dir / "中间结果" / base_name / "调度算法" / "compare"
            ts_dir = root_dir / datetime.now().strftime("%Y%m%d_%H%M%S")
            out_dir = ts_dir
            out_dir.mkdir(parents=True, exist_ok=True)

            lbl_a = path_a.stem
            lbl_b = path_b.stem

            prog_png = time_charts.render_program_compare_png(
                m_a,
                m_b,
                labels=(lbl_a, lbl_b),
                output_dir=out_dir,
            )
            thread_png = time_charts.render_thread_compare_png(
                m_a,
                m_b,
                labels=(lbl_a, lbl_b),
                output_dir=out_dir,
            )
            self._display_image(thread_png)
            self._show_message(
                "成功",
                "已生成指标对比图：\n"
                f"总耗时对比: {prog_png}\n"
                f"线程耗时对比: {thread_png}",
            )
        except Exception as e:
            self._show_message("错误", f"指标对比失败:\n{e}", is_error=True)

    def _pick_time_analysis_json(self, title: str) -> Optional[Path]:
        path_str = filedialog.askopenfilename(
            title=title,
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")],
        )
        if not path_str:
            return None
        return Path(path_str)

    def _plot_thread_task_frequency(self):
        """子功能：线程中任务执行次数图（count）"""
        json_path = self._pick_time_analysis_json("选择统计 JSON（thread_time_summary.json / time_result.json / meta.json）")
        if not json_path:
            return
        try:
            metrics = time_charts.load_thread_metrics(json_path)
            out_dir = time_charts.choose_time_analysis_output_dir(
                json_path,
                time_analysis_root=self.state.work_dir if self.state.work_dir else None,
            )
            png_path = time_charts.render_thread_frequency_png(metrics, output_dir=out_dir)
            self._display_image(png_path)
            self._show_message("成功", f"已生成统计图：\n{png_path}")
        except Exception as e:
            self._show_message("错误", f"生成统计图失败:\n{e}", is_error=True)

    def _plot_thread_total_time(self):
        """子功能：线程执行时间图（total_ns）"""
        json_path = self._pick_time_analysis_json("选择统计 JSON（thread_time_summary.json / time_result.json / meta.json）")
        if not json_path:
            return
        try:
            metrics = time_charts.load_thread_metrics(json_path)
            out_dir = time_charts.choose_time_analysis_output_dir(
                json_path,
                time_analysis_root=self.state.work_dir if self.state.work_dir else None,
            )
            png_path = time_charts.render_thread_total_time_png(metrics, output_dir=out_dir)
            self._display_image(png_path)
            self._show_message("成功", f"已生成统计图：\n{png_path}")
        except Exception as e:
            self._show_message("错误", f"生成统计图失败:\n{e}", is_error=True)

    def _plot_thread_call_gantt(self):
        """子功能：线程调用图（甘特图，需要 thread_trace.json）"""
        json_path = self._pick_time_analysis_json("选择 thread_trace.json（时间分析 trace）")
        if not json_path:
            return
        try:
            events = time_charts.load_trace_events(json_path)
            out_dir = time_charts.choose_time_analysis_output_dir(
                json_path,
                time_analysis_root=self.state.work_dir if self.state.work_dir else None,
            )
            png_path = time_charts.render_thread_gantt_png(events, output_dir=out_dir)
            self._display_image(png_path)
            self._show_message("成功", f"已生成线程调用图：\n{png_path}")
        except Exception as e:
            self._show_message("错误", f"生成线程调用图失败:\n{e}", is_error=True)
    
    # ===================== 辅助方法：图分析 =====================
    
    def _norm(self, text: str) -> str:
        """标准化字符串"""
        return text.strip().replace('"', '')
    
    def _suffix_num(self, name: str) -> int:
        """提取节点名称后缀数字用于排序"""
        import re
        match = re.search(r'(\d+)$', name)
        return int(match.group(1)) if match else 0
    
    def _parse_optional_meta(self, parts: List[str]) -> Tuple[Optional[int], Optional[str]]:
        """解析可选的源码行号与文件名
        
        格式约定：
        - 第四列（parts[3]）：行号（整数）。若无法转换为整数，则视为文件名。
        - 第五列（parts[4]）：文件名（字符串，可选）。若存在则覆盖第四列中的文件名。
        
        参考：dag_describe.py line 362-377
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
    
    def _read_dot_to_networkx(self, dot_path: Path):
        """读取 DOT 文件并转换为 networkx 图（与 mycallypro 对齐）。"""
        if not nx:
            raise RuntimeError("networkx 未安装，无法解析 DOT 文件")

        # 优先使用 networkx 的读入；若与 pydot 版本不兼容，则采用自定义转换
        try:
            graph = nx.DiGraph(nx.nx_pydot.read_dot(str(dot_path)))
            return nx.relabel_nodes(graph, self._norm)
        except Exception:
            pass

        # 退化1：使用 pydot 读取 + 自定义转换，避免 nx.nx_pydot.from_pydot 的 get_strict() 兼容问题
        if pydot:
            pd_graphs = pydot.graph_from_dot_file(str(dot_path))
            if not pd_graphs:
                raise RuntimeError("pydot 无法解析 DOT 文件")
            pdg = pd_graphs[0]
            G = nx.DiGraph()
            # 边
            for e in pdg.get_edges():
                src = self._norm(e.get_source())
                dst = self._norm(e.get_destination())
                G.add_edge(src, dst)
            # 节点 + 属性（至少保留 style）
            for n in pdg.get_nodes():
                name = self._norm(n.get_name())
                if name in ("node", "graph", "edge"):
                    continue
                if name not in G:
                    G.add_node(name)
                attrs = n.get_attributes() or {}
                style = attrs.get("style")
                if style:
                    G.nodes[name]["style"] = style
            return G

        # 退化2：极简正则解析（仅提取边与节点 style）
        import re
        EDGE_RE = re.compile(r'\"([^\"]+)\"\s*->\s*\"([^\"]+)\"')
        NODE_RE = re.compile(r'\"([^\"]+)\"\s*\[(.*?)\]')
        raw = Path(dot_path).read_text(encoding="utf-8", errors="ignore")
        G = nx.DiGraph()
        for m in EDGE_RE.finditer(raw):
            G.add_edge(self._norm(m.group(1)), self._norm(m.group(2)))
        for m in NODE_RE.finditer(raw):
            name = self._norm(m.group(1))
            if name not in G:
                G.add_node(name)
            attrs = m.group(2)
            if "style=" in attrs:
                # 取 style=xxx 或 style="xxx"
                sm = re.search(r'style\s*=\s*"?([a-zA-Z, ]+)"?', attrs)
                if sm:
                    G.nodes[name]["style"] = sm.group(1)
        return G
    
    def _parse_mutex_from_txt(self, txt_path: Path) -> List[MutexRecord]:
        """解析circle.txt中的互斥量信息
        
        使用栈匹配算法配对lock和unlock
        参考：dag_describe.py line 379-431
        """
        # 第一步：解析所有互斥锁相关的条目
        entries: List[Tuple[str, str, str, str, Optional[int], Optional[str]]] = []
        block = None
        
        content = txt_path.read_text(encoding='utf-8', errors='ignore')
        for line in content.splitlines():
            s = self._norm(line)
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
                entries.append((self._norm(func), var, idx, "unlock", line_no, file_name))
            elif "pthread_mutex_lock" in lower or "/lock" in lower:
                entries.append((self._norm(func), var, idx, "lock", line_no, file_name))
        
        # 第二步：使用栈匹配lock和unlock
        stacks: Dict[str, List[Tuple[str, str, Optional[int], Optional[str]]]] = {}
        pairs: List[MutexRecord] = []
        
        for func, var, idx, typ, line_no, file_name in entries:
            stacks.setdefault(idx, [])
            if typ == "lock":
                stacks[idx].append((func, var, line_no, file_name))
            elif typ == "unlock" and stacks[idx]:
                lock_func, lock_var, lock_line, lock_file = stacks[idx].pop()
                # 变量不一致时以unlock的变量为准
                if lock_var != var:
                    lock_var = var
                record = MutexRecord(
                    lock=self._norm(lock_func),
                    unlock=self._norm(func),
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
            print("⚠️  未找到配对的互斥锁记录")
            return []
        
        print(f"✅ 解析到 {len(pairs)} 个互斥锁配对")
        return pairs
    
    def _generate_mutex_dot(self, G, mutex_records: List[MutexRecord]) -> str:
        """生成带有互斥锁标记的DOT内容"""
        
        MUTEX_COLORS = [
            '#FFE0B2', '#FFCCBC', '#D1C4E9', '#C5CAE9', 
            '#BBDEFB', '#B2DFDB', '#C8E6C9', '#F0F4C3',
            '#FFF9C4', '#FFECB3', '#FFCCBC', '#D7CCC8'
        ]
        
        lines = ['digraph G {']
        lines.append('  rankdir=TB;')
        lines.append('  node [shape=box, style=filled, fillcolor=white];')
        
        # 创建互斥锁子图
        for i, rec in enumerate(mutex_records):
            if not rec.covered:
                continue
            
            color = MUTEX_COLORS[i % len(MUTEX_COLORS)]
            lines.append(f'\n  subgraph cluster_mutex_{i} {{')
            lines.append(f'    label="Mutex {rec.var} ({rec.idx})";')
            lines.append(f'    style=filled;')
            lines.append(f'    fillcolor="{color}";')
            lines.append(f'    fontcolor=black;')
            
            for node in rec.covered:
                label = node
                if node == rec.lock:
                    label = f"{node}\\n[LOCK]"
                elif node == rec.unlock:
                    label = f"{node}\\n[UNLOCK]"
                
                lines.append(f'    "{node}" [label="{label}"];')
            
            lines.append('  }')
        
        # 添加所有边
        lines.append('\n  // Edges')
        for src, dst in G.edges():
            lines.append(f'  "{src}" -> "{dst}";')
        
        lines.append('}')
        
        return '\n'.join(lines)
    
    def _parse_semaphore_from_txt(self, txt_path: Path) -> List[SemRecord]:
        """解析circle.txt中的信号量信息
        
        使用字典按ID收集post和wait节点
        参考：dag_describe.py line 549-596
        """
        by_id: Dict[str, Dict[str, any]] = {}
        block = None
        
        content = txt_path.read_text(encoding='utf-8', errors='ignore')
        for line in content.splitlines():
            s = self._norm(line)
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
                record["post"] = self._norm(func)
                record["post_line"] = line_no
                record["post_file"] = file_name
            elif "sem_wait" in func:
                record["wait"] = self._norm(func)
                record["wait_line"] = line_no
                record["wait_file"] = file_name
        
        # 构建配对列表
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
        
        print(f"✅ 解析到 {len(pairs)} 个信号量配对")
        return pairs
    
    def _generate_semaphore_original(self, G, target_dir: Path):
        """生成原始图+信号量边"""
        lines = ['digraph G {']
        lines.append('  rankdir=LR;')
        lines.append('  fontname="Microsoft YaHei";')
        lines.append('  node [shape=box];')
        
        # 所有节点
        for node in G.nodes():
            lines.append(f'  "{node}";')
        
        # 边：区分普通边和信号量边
        for src, dst, data in G.edges(data=True):
            if data.get('style') == 'dashed':
                label = data.get('label', '')
                color = data.get('color', '#FF7043')
                lines.append(f'  "{src}" -> "{dst}" [style=dashed, color="{color}", label="{label}"];')
            else:
                lines.append(f'  "{src}" -> "{dst}";')
        
        lines.append('}')
        
        dot_path = target_dir / "original.dot"
        dot_path.write_text('\n'.join(lines), encoding='utf-8')
        
        png_path = target_dir / "original.png"
        subprocess.run(
            ["dot", "-Gdpi=110", "-Tpng", str(dot_path), "-o", str(png_path)],
            check=True,
            capture_output=True
        )
        print(f"✅ 生成原始图: {png_path}")
        self.cached_images["original"] = png_path if png_path.exists() else None
    
    def _generate_semaphore_tarjan(self, G, sccs: List[set], target_dir: Path):
        """生成Tarjan强连通分量图"""
        lines = ['digraph G {']
        lines.append('  rankdir=LR;')
        lines.append('  fontname="Microsoft YaHei";')
        lines.append('  node [shape=box, style=filled];')

        color_map: Dict[str, str] = {}
        for comp in sccs:
            color = "#%06x" % random.randint(0, 0xFFFFFF)
            for node in comp:
                color_map[node] = color

        for node in G.nodes():
            col = color_map.get(node, "#B0BEC5")
            lines.append(f'  "{node}" [fillcolor="{col}"];')
        
        # 边
        for src, dst, data in G.edges(data=True):
            if data.get('style') == 'dashed':
                lines.append(f'  "{src}" -> "{dst}" [style=dashed, color="#FF7043"];')
            else:
                lines.append(f'  "{src}" -> "{dst}";')
        
        lines.append('}')
        
        dot_path = target_dir / "tarjan.dot"
        dot_path.write_text('\n'.join(lines), encoding='utf-8')
        
        png_path = target_dir / "tarjan.png"
        subprocess.run(
            ["dot", "-Gdpi=110", "-Tpng", str(dot_path), "-o", str(png_path)],
            check=True,
            capture_output=True
        )
        print(f"✅ 生成Tarjan图: {png_path}")
        self.cached_images["tarjan"] = png_path if png_path.exists() else None
    
    def _generate_semaphore_threads(self, G, sccs: List[set], target_dir: Path):
        """生成线程分组图"""
        
        cycles: Dict[str, Dict[str, List[str]]] = {}
        idx = 0
        for comp in self.sccs:
            if len(comp) <= 1:
                continue
            per_thread: Dict[str, List[str]] = {}
            for node in comp:
                prefix = node.split('/')[0] if '/' in node else 'Unknown'
                per_thread.setdefault(prefix, []).append(node)
            if len(per_thread) <= 1:
                continue
            for t in per_thread:
                per_thread[t] = sorted(per_thread[t], key=self._suffix_num)
            idx += 1
            cycles[f"Cycle{idx}"] = dict(sorted(per_thread.items()))

        self.cycle_data = cycles

        node_colors: Dict[str, str] = {}
        for node in G.nodes():
            prefix = node.split('/')[0] if '/' in node else 'Unknown'
            node_colors[node] = self.thread_color_map.get(prefix, '#CFD8DC')

        lines = ['digraph G {']
        lines.append('  rankdir=LR;')
        lines.append('  fontname="Microsoft YaHei";')
        lines.append('  node [shape=box, style=filled];')

        for src, dst, data in G.edges(data=True):
            if data.get('style') == 'dashed':
                lines.append(f'  "{src}" -> "{dst}" [style=dashed, color="#FF7043"];')
            else:
                lines.append(f'  "{src}" -> "{dst}";')

        for cname, per_thread in cycles.items():
            lines.append(f'  subgraph cluster_{cname} {{')
            lines.append('    style=dashed;')
            lines.append('    color=gray;')
            lines.append(f'    label="{cname}";')
            for _, nodes in per_thread.items():
                for node in nodes:
                    col = node_colors.get(node, '#FFFFFF')
                    lines.append(f'    "{node}" [fillcolor="{col}"];')
            lines.append('  }')

        for node, col in node_colors.items():
            lines.append(f'  "{node}" [fillcolor="{col}"];')

        lines.append('}')

        dot_path = target_dir / "threads.dot"
        dot_path.write_text('\n'.join(lines), encoding='utf-8')

        png_path = target_dir / "threads.png"
        subprocess.run(
            ["dot", "-Gdpi=110", "-Tpng", str(dot_path), "-o", str(png_path)],
            check=True,
            capture_output=True
        )
        print(f"✅ 生成线程图: {png_path}")
        self.cached_images["threads"] = png_path if png_path.exists() else None

    def show_semaphore_info(self):
        """显示信号量配对信息列表。"""
        pairs = self.sem_records or self._parse_semaphore_from_txt(self.state.txt_file)
        self.canvas.delete("all")
        y = 20
        self.canvas.create_text(
            20,
            y,
            anchor="nw",
            text="信号量配对（post → wait）",
            font=("Microsoft YaHei", 14, "bold"),
            fill="#000",
        )
        y += 36
        if not pairs:
            self.canvas.create_text(
                20,
                y,
                anchor="nw",
                text="暂无数据，请先加载 circle.txt 或生成信号量图",
                font=("Consolas", 12),
                fill="#555",
            )
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
                20,
                y,
                anchor="nw",
                text=f"ID={rec.idx}  VAR={rec.var}  {rec.post} -> {rec.wait}{extra}",
                font=("Consolas", 11),
                fill="#263238",
            )
            y += 24

        if self.cycle_data:
            y += 20
            self.canvas.create_text(
                20,
                y,
                anchor="nw",
                text="信号量环数据结构：",
                font=("Microsoft YaHei", 13, "bold"),
                fill="#000",
            )
            y += 28
            for cname, per_thread in self.cycle_data.items():
                self.canvas.create_text(
                    20,
                    y,
                    anchor="nw",
                    text=f"{cname}:",
                    font=("Consolas", 11),
                    fill="#263238",
                )
                y += 20
                for thread, nodes in per_thread.items():
                    self.canvas.create_text(
                        40,
                        y,
                        anchor="nw",
                        text=f"{thread}: {', '.join(nodes)}",
                        font=("Consolas", 10),
                        fill="#455A64",
                    )
                    y += 18
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def show_thread_legend(self):
        """显示线程颜色图例。"""
        self.canvas.delete("all")
        y = 40
        self.canvas.create_text(
            40,
            10,
            anchor="nw",
            text="线程颜色图例",
            font=("Microsoft YaHei", 14, "bold"),
            fill="#212121",
        )
        if not self.thread_color_map:
            self.canvas.create_text(
                40,
                y,
                anchor="nw",
                text="请先生成信号量图以计算线程颜色。",
                font=("Consolas", 12),
                fill="#555",
            )
        else:
            for thread, color in self.thread_color_map.items():
                self.canvas.create_rectangle(40, y, 100, y + 30, fill=color, outline="black")
                self.canvas.create_text(
                    120,
                    y + 15,
                    anchor="w",
                    text=thread,
                    font=("Microsoft YaHei", 12),
                )
                y += 40
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    # ===================== 辅助方法 =====================
    
    # ===================== 画布交互 =====================
    
    def _start_move(self, event):
        """开始拖动"""
        self.canvas.scan_mark(event.x, event.y)
    
    def _on_move(self, event):
        """拖动画布"""
        self.canvas.scan_dragto(event.x, event.y, gain=1)
    
    def _on_zoom(self, event):
        """缩放图像
        
        鼠标滚轮向上：放大
        鼠标滚轮向下：缩小
        """
        if not self.original_image:
            return
        
        # 确定滚动方向
        if event.type == tk.EventType.MouseWheel:
            # Windows/Mac
            delta = event.delta
        else:
            # Linux (Button-4 = 向上, Button-5 = 向下)
            delta = 120 if event.num == 4 else -120
        
        # 计算缩放因子
        scale_factor = 1.1 if delta > 0 else 0.9
        
        # 限制缩放范围 (0.1x ~ 10x)
        new_scale = self.canvas_scale * scale_factor
        if new_scale < 0.1 or new_scale > 10.0:
            return
        
        self.canvas_scale = new_scale
        
        # 重新渲染图像
        self._refresh_canvas_image()


def main():
    """主函数"""
    root = tk.Tk()
    app = MycallyplusGUIv3(root)
    root.mainloop()


if __name__ == "__main__":
    main()
