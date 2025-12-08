#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple GUI to test legacy.py function-source extraction.

Pick a source file and an .expand file, then run legacy.py with --source-file
to populate mycalls_meta.extern based on the selected source.
"""
import subprocess
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import json


def run_legacy(src_path: str, expand_path: str, output_widget: scrolledtext.ScrolledText) -> None:
    """Invoke legacy.py with the provided paths and stream output to the UI."""
    output_widget.delete("1.0", tk.END)
    if not src_path or not expand_path:
        messagebox.showerror("缺少参数", "请选择源文件和 expand 文件")
        return

    root_dir = Path(__file__).resolve().parents[2]  # repository root
    legacy_script = root_dir / "mycallyplus" / "generation" / "legacy.py"
    if not legacy_script.exists():
        messagebox.showerror("错误", f"未找到 legacy.py: {legacy_script}")
        return

    cmd = [
        sys.executable,
        str(legacy_script),
        "--source-file",
        src_path,
        expand_path,
    ]

    try:
        proc = subprocess.run(
            cmd,
            cwd=root_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:  # pragma: no cover - interactive tool
        messagebox.showerror("执行失败", f"无法运行 legacy.py\n{exc}")
        return

    output = []
    output.append(f"$ {' '.join(cmd)}\n\n")
    if proc.stdout:
        output.append("[stdout]\n")
        output.append(proc.stdout)
        output.append("\n")
    if proc.stderr:
        output.append("[stderr]\n")
        output.append(proc.stderr)
        output.append("\n")
    output.append(f"[exit code] {proc.returncode}\n")

    # 尝试读取 legacy 输出的 functions_full.json，展示 mycalls_meta
    try:
        base_name = Path(expand_path).stem
        if base_name.endswith(".233r"):
            base_name = base_name[:-5]
        if "." in base_name:
            base_name = base_name.split(".")[0]
        json_path = root_dir / "中间结果" / base_name / "生成dag图" / "functions_full.json"
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding="utf-8"))
            output.append(f"[mycalls_meta dump] {json_path}\n")
            for func, finfo in data.items():
                metas = finfo.get("mycalls_meta", [])
                output.append(f"{func}:\n")
                for meta in metas:
                    if isinstance(meta, dict):
                        name = meta.get("name")
                        extern = meta.get("extern")
                        file = meta.get("file")
                        line = meta.get("line")
                        col = meta.get("col")
                        output.append(
                            f"  - name={name}, extern={extern}, file={file}, line={line}, col={col}\n"
                        )
                    else:
                        output.append(f"  - {meta}\n")
            output.append("\n")
    except Exception as exc:  # pragma: no cover - best-effort logging
        output.append(f"[mycalls_meta dump failed] {exc}\n")

    output.append("\n")
    output_widget.insert(tk.END, "".join(output))
    output_widget.see(tk.END)
    if proc.returncode != 0:
        messagebox.showwarning("运行结束", f"legacy.py 返回码 {proc.returncode}")


def main() -> None:
    root = tk.Tk()
    root.title("legacy.py 测试器")

    src_var = tk.StringVar()
    expand_var = tk.StringVar()

    def pick_src() -> None:
        path = filedialog.askopenfilename(title="选择源文件")
        if path:
            src_var.set(path)

    def pick_expand() -> None:
        path = filedialog.askopenfilename(title="选择 expand 文件", filetypes=[("expand files", "*.expand"), ("所有文件", "*.*")])
        if path:
            expand_var.set(path)

    tk.Label(root, text="源文件 (--source-file)").grid(row=0, column=0, sticky="w", padx=5, pady=5)
    tk.Entry(root, textvariable=src_var, width=80).grid(row=0, column=1, padx=5, pady=5)
    tk.Button(root, text="浏览", command=pick_src).grid(row=0, column=2, padx=5, pady=5)

    tk.Label(root, text="expand 文件 (RTLFILE)").grid(row=1, column=0, sticky="w", padx=5, pady=5)
    tk.Entry(root, textvariable=expand_var, width=80).grid(row=1, column=1, padx=5, pady=5)
    tk.Button(root, text="浏览", command=pick_expand).grid(row=1, column=2, padx=5, pady=5)

    output = scrolledtext.ScrolledText(root, width=100, height=30)
    output.grid(row=3, column=0, columnspan=3, padx=5, pady=5, sticky="nsew")

    tk.Button(
        root,
        text="运行 legacy.py",
        command=lambda: run_legacy(src_var.get(), expand_var.get(), output),
    ).grid(row=2, column=0, columnspan=3, pady=5)

    root.grid_columnconfigure(1, weight=1)
    root.grid_rowconfigure(3, weight=1)
    root.mainloop()


if __name__ == "__main__":
    main()
