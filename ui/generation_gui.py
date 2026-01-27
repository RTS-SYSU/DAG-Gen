from __future__ import annotations

"""Tk GUI（调用 legacy 流水线生成带编号的线程调用图）。

按钮：
- 读入 C：用 gcc 生成 expand 并复制到 test/<basename>/
- 读入 expand：仅更新 expand 路径
- 生成 dag 图：调用 `python -m mycallypro <expand>` 产出 DOT，再用 dot 渲染 PNG

注意：为兼容在包目录直接执行，本模块内带有导入与工作目录的兜底逻辑。
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

import tkinter as tk
from tkinter import filedialog, messagebox

# 配置文件目录：mycallyplus/中间结果/<base>/配置文件/
PROJECT_ROOT = Path(__file__).resolve().parent

# 允许包外直接运行（python3 gui.py）时的导入回退
try:  # 推荐：python3 -m mycallyplus.ui.generation_gui
    from ..generation.builder import build_callee_info
    from ..generation.model import CallGraph, RenderOptions
    from ..generation.parser import Parser
    from ..generation.renderer import DotRenderer
    from ..generation.threads import infer_thread_edges
except Exception:  # 绝对导入回退（在项目根目录执行 python3 gui.py）
    import sys
    from pathlib import Path

    pkg_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(pkg_root))
    try:
        from mycallyplus.generation.builder import build_callee_info
        from mycallyplus.generation.model import CallGraph, RenderOptions
        from mycallyplus.generation.parser import Parser
        from mycallyplus.generation.renderer import DotRenderer
        from mycallyplus.generation.threads import infer_thread_edges
    except Exception:
        sys.path.insert(0, str(pkg_root / "generation"))
        from builder import build_callee_info  # type: ignore
        from model import CallGraph, RenderOptions  # type: ignore
        from parser import Parser  # type: ignore
        from renderer import DotRenderer  # type: ignore
        from threads import infer_thread_edges  # type: ignore


class MyCallyGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("MyCally 助手")
        self.root.geometry("1200x800")

        self.current_c_path: Optional[Path] = None
        self.current_expand_path: Optional[Path] = None
        self.current_image: Optional[tk.PhotoImage] = None

        self._build_ui()

    # ------------------------------------------------------------------ UI --

    def _build_ui(self) -> None:
        main = tk.Frame(self.root, bg="#ECEFF1")
        main.pack(fill=tk.BOTH, expand=True)

        # 左侧按钮区
        sidebar = tk.Frame(main, width=220, bg="#CFD8DC")
        sidebar.pack(side=tk.LEFT, fill=tk.Y)

        def add_button(text: str, command) -> None:
            btn = tk.Button(
                sidebar,
                text=text,
                command=command,
                width=20,
                height=2,
                bg="#ECEFF1",
                activebackground="#B0BEC5",
                relief=tk.RAISED,
                font=("Microsoft YaHei", 10),
            )
            btn.pack(pady=12, padx=12)

        add_button("读入 C 文件", self.load_c_file)
        add_button("读入 expand 文件", self.load_expand_file)
        add_button("生成 dag 图", self.generate_dag)
        add_button("查看条件节点", self.generate_conditions_dag)
        add_button("生成配置文件", self.generate_config_files)
        
        # 冗余处理模式选项
        mode_frame = tk.LabelFrame(
            sidebar,
            text="冗余处理模式",
            bg="#CFD8DC",
            font=("Microsoft YaHei", 9, "bold"),
            padx=8,
            pady=8
        )
        mode_frame.pack(pady=12, padx=12, fill=tk.X)
        
        self.smart_mode = tk.BooleanVar(value=False)
        self.clean_mode = tk.BooleanVar(value=False)
        
        smart_check = tk.Checkbutton(
            mode_frame,
            text="智能检测 (--smart)",
            variable=self.smart_mode,
            bg="#CFD8DC",
            font=("Microsoft YaHei", 9),
            command=self._on_mode_change
        )
        smart_check.pack(anchor=tk.W, pady=2)
        
        clean_check = tk.Checkbutton(
            mode_frame,
            text="清理重建 (--clean)",
            variable=self.clean_mode,
            bg="#CFD8DC",
            font=("Microsoft YaHei", 9),
            command=self._on_mode_change
        )
        clean_check.pack(anchor=tk.W, pady=2)
        
        mode_help = tk.Label(
            mode_frame,
            text="默认：覆盖已有文件\n智能：跳过未修改文件\n清理：删除后重新生成",
            bg="#CFD8DC",
            font=("Consolas", 8),
            fg="#546E7A",
            justify=tk.LEFT
        )
        mode_help.pack(anchor=tk.W, pady=(6, 0))

        # 右侧展示区
        content = tk.Frame(main, bg="#FFFFFF")
        content.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        info_frame = tk.Frame(content, bg="#FFFFFF")
        info_frame.pack(fill=tk.X, padx=12, pady=12)

        self.c_label = tk.Label(info_frame, text="C 文件：<未选择>", anchor="w", bg="#FFFFFF", font=("Consolas", 11))
        self.c_label.pack(fill=tk.X)

        self.expand_label = tk.Label(info_frame, text="expand 文件：<未选择>", anchor="w", bg="#FFFFFF", font=("Consolas", 11))
        self.expand_label.pack(fill=tk.X, pady=(6, 0))

        canvas_frame = tk.Frame(content, bg="#ECEFF1")
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.canvas = tk.Canvas(canvas_frame, bg="#FAFAFA", relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_text(
            0,
            0,
            text="生成后的 DAG 图将在此显示",
            anchor=tk.NW,
            font=("Microsoft YaHei", 12),
            fill="#607D8B",
            tags="placeholder",
        )

        self.canvas.bind("<ButtonPress-1>", self._start_pan)
        self.canvas.bind("<B1-Motion>", self._do_pan)
        self.canvas.bind("<MouseWheel>", self._on_zoom)
        self.canvas.bind("<Button-4>", self._on_zoom)  # Linux scroll up
        self.canvas.bind("<Button-5>", self._on_zoom)  # Linux scroll down
        self.canvas_scale = 1.0

    # -------------------------------------------------------------- Helpers --

    def _on_mode_change(self) -> None:
        """当模式复选框改变时，确保smart和clean不能同时选中"""
        if self.smart_mode.get() and self.clean_mode.get():
            # 如果两个都选中了，取消之前选中的那个
            # 这里简单处理：clean优先
            self.smart_mode.set(False)

    def load_c_file(self) -> None:
        path = filedialog.askopenfilename(title="选择 C 源文件", filetypes=[("C 文件", "*.c"), ("所有文件", "*")])
        if not path:
            return

        c_path = Path(path).resolve()
        if not c_path.exists():
            messagebox.showerror("错误", "所选 C 文件不存在。")
            return

        try:
            expand_path = self._compile_to_expand(c_path)
        except Exception as exc:
            messagebox.showerror("编译失败", str(exc))
            return

        base_name = c_path.stem
        target_dir = (Path(__file__).parent / "test" / base_name).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        dest_expand = (target_dir / expand_path.name).resolve()
        try:
            shutil.copy2(expand_path, dest_expand)
        except Exception as exc:
            messagebox.showerror("复制失败", f"无法将 expand 文件复制到 {dest_expand}。\n{exc}")
            return

        self.current_c_path = c_path
        self.current_expand_path = dest_expand

        self._update_labels()
        self._clear_canvas()

        messagebox.showinfo("完成", f"已生成 expand 文件：\n{dest_expand}")

    def load_expand_file(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 expand 文件", filetypes=[("expand 文件", "*.expand"), ("所有文件", "*")]
        )
        if not path:
            return

        expand_path = Path(path).resolve()
        if not expand_path.exists():
            messagebox.showerror("错误", "所选 expand 文件不存在。")
            return

        self.current_c_path = None
        self.current_expand_path = expand_path.resolve()

        self._update_labels()
        self._clear_canvas()

    def generate_dag(self) -> None:
        if not self.current_expand_path or not self.current_expand_path.exists():
            messagebox.showwarning("提示", "请先选择 expand 文件。")
            return

        try:
            dot_str, png_path = self._build_dag(self.current_expand_path, threads_only=True)
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))
            return

        try:
            self._show_image(png_path)
        except Exception as exc:
            messagebox.showerror("显示失败", f"已生成图像，但加载时出错：\n{exc}")
            return

        messagebox.showinfo("完成", f"已生成线程视图 DAG 图：\n{png_path}")

    def generate_conditions_dag(self) -> None:
        if not self.current_expand_path or not self.current_expand_path.exists():
            messagebox.showwarning("提示", "请先选择 expand 文件。")
            return

        try:
            dot_str, png_path = self._build_conditions_dag(self.current_expand_path)
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))
            return

        try:
            self._show_image(png_path)
        except Exception as exc:
            messagebox.showerror("显示失败", f"已生成图像，但加载时出错：\n{exc}")
            return

        messagebox.showinfo("完成", f"已生成完整视图 DAG 图：\n{png_path}")

    def generate_config_files(self) -> None:
        """一键生成所有配置文件：dag图、条件节点图、circle.txt"""
        if not self.current_expand_path or not self.current_expand_path.exists():
            messagebox.showwarning("提示", "请先选择 expand 文件。")
            return

        try:
            # 确定输出目录（三阶段划分 + 扁平化结构）
            base_name = self._derive_base_name(self.current_expand_path)
            
            # 阶段3 - 配置文件目录（新位置：中间结果/<base>/配置文件）
            config_base = PROJECT_ROOT / "中间结果" / base_name / "配置文件"
            config_base.mkdir(parents=True, exist_ok=True)
            
            # 阶段2 - 中间结果目录（处理过程中的临时文件）
            intermediate_base = PROJECT_ROOT / "中间结果" / base_name
            intermediate_base.mkdir(parents=True, exist_ok=True)
            
            # 创建中间结果子目录
            (intermediate_base / "debug").mkdir(exist_ok=True)
            (intermediate_base / "temp").mkdir(exist_ok=True)
            (intermediate_base / "images").mkdir(exist_ok=True)
            (intermediate_base / "logs").mkdir(exist_ok=True)

            generated_files = []
            
            # 0. 复制源文件和expand文件到配置文件根目录（扁平结构）
            messagebox.showinfo("进度", "正在复制源文件...")
            import shutil
            
            # 复制expand文件到根目录
            expand_dest = config_base / self.current_expand_path.name
            shutil.copy2(self.current_expand_path, expand_dest)
            generated_files.append(f"✓ {self.current_expand_path.name}")
            
            # 复制源文件到根目录（如果存在）
            if self.current_c_path and self.current_c_path.exists():
                source_dest = config_base / self.current_c_path.name
                shutil.copy2(self.current_c_path, source_dest)
                generated_files.append(f"✓ {self.current_c_path.name}")
            
            # 1. 生成dag图（threads-only）
            messagebox.showinfo("进度", "正在生成 dag 图（线程视图）...")
            dot_str_threads, png_threads = self._build_dag_to_config(
                self.current_expand_path, 
                config_base,
                intermediate_base,
                threads_only=True
            )
            generated_files.append(f"✓ {base_name}.dot")
            
            # 2. 生成条件节点图（完整版）
            messagebox.showinfo("进度", "正在生成条件节点图（完整视图）...")
            dot_str_full, png_full = self._build_dag_to_config(
                self.current_expand_path,
                config_base,
                intermediate_base,
                threads_only=False
            )
            generated_files.append(f"✓ {base_name}_full.dot")
            
            # 3. 生成circle.txt
            messagebox.showinfo("进度", "正在生成 circle.txt 配置文件...")
            txt_path = self._generate_circle_txt(self.current_expand_path, config_base)
            if txt_path.exists():
                generated_files.append(f"✓ circle.txt")
            
            # PNG图片生成在中间结果目录
            generated_files.append(f"✓ 图片已生成到中间结果目录")
            
            # 显示最后生成的图片（完整视图）
            try:
                self._show_image(png_full)
            except Exception:
                pass
            
            # 显示成功消息
            files_list = "\n".join(generated_files)
            messagebox.showinfo(
                "生成完成", 
                f"所有配置文件已生成！\n\n配置文件目录：\n{config_base}\n\n生成的文件：\n{files_list}"
            )
            
        except Exception as exc:
            messagebox.showerror("生成失败", f"生成配置文件时出错：\n{exc}")
            import traceback
            traceback.print_exc()

    # ------------------------------------------------------------- Internal --

    def _compile_to_expand(self, c_path: Path) -> Path:
        """调用 gcc 生成 expand 文件并返回其路径。"""
        work_dir = c_path.parent
        base_name = c_path.name

        with tempfile.NamedTemporaryFile(dir=work_dir, suffix=".o", delete=False) as tmp:
            obj_name = Path(tmp.name).name
        try:
            subprocess.run(
                ["gcc", "-fdump-rtl-expand", "-c", base_name, "-o", obj_name],
                cwd=work_dir,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.decode("utf-8", errors="ignore") or str(exc))
        finally:
            obj_file = work_dir / obj_name
            if obj_file.exists():
                obj_file.unlink()

        candidates = sorted(work_dir.glob(f"{base_name}.*.expand"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not candidates:
            raise RuntimeError("未找到由 gcc 生成的 expand 文件。")
        return candidates[0]

    def _build_dag(self, expand_path: Path, threads_only: bool = False) -> tuple[str, Path]:
        """解析 expand 文件并生成 DAG PNG（使用 legacy 流水线以获得编号与线程语义）。"""
        # 通过运行包模块，直接复用 legacy 的编号与线程补边逻辑
        try:
            import sys
            import subprocess
            cmd = [sys.executable, "-m", "mycallyplus_v1.generation.legacy"]
            if threads_only:
                cmd.append("--threads-only")
            cmd.append(str(expand_path.resolve()))
            # 工作目录应该是项目根目录（mycallyplus的父目录）
            work_dir = PROJECT_ROOT.parent
            proc = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(work_dir),
            )
            dot_str = proc.stdout.decode("utf-8", errors="ignore")
        except subprocess.CalledProcessError as exc:
            # 捕获命令执行失败的详细错误
            error_msg = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            raise RuntimeError(f"生成 DOT 失败：\n{error_msg}")
        except Exception as exc:
            raise RuntimeError(f"生成 DOT 失败：{exc}")

        base_name = self._derive_base_name(expand_path)
        target_dir = (Path(__file__).parent / "test" / base_name).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        dot_path = (target_dir / "dag.dot").resolve()
        png_path = (target_dir / "dag.png").resolve()
        dot_path.write_text(dot_str, encoding="utf-8")

        try:
            subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True)
        except FileNotFoundError as exc:
            raise RuntimeError("未找到 dot 命令，请安装 Graphviz。") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.decode("utf-8", errors="ignore") or "dot 命令执行失败。") from exc

        return dot_str, png_path

    def _build_conditions_dag(self, expand_path: Path) -> tuple[str, Path]:
        """解析 expand 文件并生成完整视图 DAG PNG（包含线程补边和条件节点）。"""
        try:
            import sys
            import subprocess
            cmd = [sys.executable, "-m", "mycallyplus_v1.generation.legacy", str(expand_path.resolve())]
            work_dir = PROJECT_ROOT.parent
            proc = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(work_dir),
            )
            dot_str = proc.stdout.decode("utf-8", errors="ignore")
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            raise RuntimeError(f"生成完整视图 DOT 失败：\n{error_msg}")
        except Exception as exc:
            raise RuntimeError(f"生成完整视图 DOT 失败：{exc}")

        base_name = self._derive_base_name(expand_path)
        target_dir = (Path(__file__).parent / "test" / base_name).resolve()
        target_dir.mkdir(parents=True, exist_ok=True)

        dot_path = (target_dir / "dag_full.dot").resolve()
        png_path = (target_dir / "dag_full.png").resolve()
        dot_path.write_text(dot_str, encoding="utf-8")

        try:
            subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True)
        except FileNotFoundError as exc:
            raise RuntimeError("未找到 dot 命令，请安装 Graphviz。") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.decode("utf-8", errors="ignore") or "dot 命令执行失败。") from exc

        return dot_str, png_path

    def _build_dag_to_config(self, expand_path: Path, config_dir: Path, intermediate_dir: Path, threads_only: bool = False) -> tuple[str, Path]:
        """生成DAG并保存到配置文件目录（扁平结构）和中间结果目录"""
        try:
            import sys
            import subprocess
            cmd = [sys.executable, "-m", "mycallyplus_v1.generation.legacy"]
            if threads_only:
                cmd.append("--threads-only")
            cmd.append(str(expand_path.resolve()))
            work_dir = PROJECT_ROOT.parent
            proc = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(work_dir),
            )
            dot_str = proc.stdout.decode("utf-8", errors="ignore")
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            raise RuntimeError(f"生成 DOT 失败：\n{error_msg}")
        except Exception as exc:
            raise RuntimeError(f"生成 DOT 失败：{exc}")

        # 获取基础文件名
        base_name = expand_path.stem
        if base_name.endswith('.233r'):
            base_name = base_name[:-5]
        elif '.' in base_name:
            base_name = base_name.split('.')[0]
        
        # DOT文件保存到配置文件根目录（扁平结构，参考test/配置文件/）
        if threads_only:
            dot_path = config_dir / f"{base_name}.dot"
        else:
            dot_path = config_dir / f"{base_name}_full.dot"
        
        dot_path.write_text(dot_str, encoding="utf-8")
        
        # PNG图片保存到中间结果目录（不属于dag_describe的配置文件）
        images_dir = intermediate_dir / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        
        if threads_only:
            png_path = images_dir / f"{base_name}.png"
        else:
            png_path = images_dir / f"{base_name}_full.png"

        try:
            subprocess.run(["dot", "-Tpng", str(dot_path), "-o", str(png_path)], check=True)
        except FileNotFoundError as exc:
            raise RuntimeError("未找到 dot 命令，请安装 Graphviz。") from exc
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(exc.stderr.decode("utf-8", errors="ignore") or "dot 命令执行失败。") from exc

        return dot_str, png_path

    def _generate_circle_txt(self, expand_path: Path, config_dir: Path) -> Path:
        """生成circle.txt配置文件"""
        try:
            import sys
            import subprocess
            
            txt_path = config_dir / "circle.txt"
            
            cmd = [
                sys.executable, "-m", "mycallyplus_v1.generation.legacy",
                str(expand_path.resolve()),
                "--export-txt", str(txt_path),
                "--output-base", str(PROJECT_ROOT)
            ]
            
            # 添加冗余处理模式参数
            if self.smart_mode.get():
                cmd.append("--smart")
            if self.clean_mode.get():
                cmd.append("--clean")
            
            work_dir = PROJECT_ROOT.parent
            proc = subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(work_dir),
            )
            
            return txt_path
            
        except subprocess.CalledProcessError as exc:
            error_msg = exc.stderr.decode("utf-8", errors="ignore") if exc.stderr else str(exc)
            raise RuntimeError(f"生成 circle.txt 失败：\n{error_msg}")
        except Exception as exc:
            raise RuntimeError(f"生成 circle.txt 失败：{exc}")

    def _derive_base_name(self, expand_path: Path) -> str:
        name = expand_path.name
        if ".c" in name:
            return name.split(".c", 1)[0]
        return expand_path.stem

    def _update_labels(self) -> None:
        c_text = f"C 文件：{self.current_c_path}" if self.current_c_path else "C 文件：<未选择>"
        expand_text = f"expand 文件：{self.current_expand_path}" if self.current_expand_path else "expand 文件：<未选择>"
        self.c_label.config(text=c_text)
        self.expand_label.config(text=expand_text)

    def _clear_canvas(self) -> None:
        self.canvas.delete("all")
        self.current_image = None
        self.canvas_scale = 1.0
        self.canvas.create_text(
            0,
            0,
            text="生成后的 DAG 图将在此显示",
            anchor=tk.NW,
            font=("Microsoft YaHei", 12),
            fill="#607D8B",
            tags="placeholder",
        )

    def _show_image(self, image_path: Path) -> None:
        self.canvas.delete("all")
        try:
            self.current_image = tk.PhotoImage(file=str(image_path))
        except Exception:
            # Pillow 回退，兼容部分环境 PhotoImage 不支持 PNG
            try:
                from PIL import Image, ImageTk  # type: ignore

                img = Image.open(str(image_path))
                self.current_image = ImageTk.PhotoImage(img)
            except Exception as exc:  # 最终失败
                raise RuntimeError(f"无法加载图片：{exc}")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.current_image, tags="image")
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))

    def _start_pan(self, event) -> None:
        self.canvas.scan_mark(event.x, event.y)

    def _do_pan(self, event) -> None:
        self.canvas.scan_dragto(event.x, event.y, gain=1)

    def _on_zoom(self, event) -> None:
        if self.current_image is None:
            return
        if event.type == tk.EventType.ButtonPress and event.num not in (4, 5):
            return

        if event.type == tk.EventType.MouseWheel:
            delta = event.delta
        else:  # Linux scroll (Button-4/5)
            delta = 120 if event.num == 4 else -120

        scale_factor = 1.1 if delta > 0 else 0.9
        self.canvas_scale *= scale_factor
        self.canvas.scale("all", event.x, event.y, scale_factor, scale_factor)
        self.canvas.config(scrollregion=self.canvas.bbox(tk.ALL))


def main() -> None:
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        raise RuntimeError(
            "无法启动图形界面：未检测到可用的显示服务器。"
            "\n请在支持 GUI 的环境中运行，或设置 DISPLAY 变量。"
        ) from exc
    app = MyCallyGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
