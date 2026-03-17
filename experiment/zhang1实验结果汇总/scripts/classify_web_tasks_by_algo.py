#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Optional


def _infer_algo(summary: dict) -> Optional[str]:
    def from_c_file(d: dict) -> Optional[str]:
        c_file = d.get("c_file")
        if not isinstance(c_file, str):
            return None
        # .../effective_line_merge/<algo>/source_*.c
        marker = "/effective_line_merge/"
        if marker in c_file:
            rest = c_file.split(marker, 1)[1]
            algo = rest.split("/", 1)[0].strip()
            return algo or None
        return None

    def from_compile_cmd(d: dict) -> Optional[str]:
        cmd = d.get("compile_cmd")
        if not isinstance(cmd, str):
            return None
        # include path often ends with .../baseline/<algo> or .../prio/<algo>
        for part in cmd.replace("\n", " ").split():
            if "/baseline/" in part:
                rest = part.split("/baseline/", 1)[1]
                algo = rest.split("/", 1)[0].strip()
                if algo:
                    return algo
            if "/prio/" in part:
                rest = part.split("/prio/", 1)[1]
                algo = rest.split("/", 1)[0].strip()
                if algo:
                    return algo
        return None

    for key in ("baseline", "prio"):
        v = summary.get(key)
        if isinstance(v, dict):
            algo = from_c_file(v) or from_compile_cmd(v)
            if algo:
                return algo
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Classify zhang1 web_tasks runs into per-algo folders by reading summary.json.")
    ap.add_argument(
        "--root",
        default="experiment/zhang1实验结果汇总",
        help="Root directory (default: experiment/zhang1实验结果汇总)",
    )
    ap.add_argument(
        "--suite",
        default="web_tasks",
        help="Suite directory name containing runs (default: web_tasks)",
    )
    ap.add_argument(
        "--mode",
        choices=["copy", "move"],
        default="copy",
        help="copy: keep original suite runs; move: relocate runs into algo dirs (default: copy)",
    )
    ap.add_argument("--dry-run", action="store_true", help="Only print actions, do not change filesystem.")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve()
    while not ((repo_root / "cli.py").exists() and (repo_root / "__main__.py").exists()) and repo_root.parent != repo_root:
        repo_root = repo_root.parent
    if not ((repo_root / "cli.py").exists() and (repo_root / "__main__.py").exists()):
        raise RuntimeError("Cannot locate repo root.")

    root = (repo_root / args.root).resolve()
    suite_dir = root / args.suite
    if not suite_dir.exists():
        print(f"Suite dir not found: {suite_dir}")
        return 1

    run_dirs = sorted([p for p in suite_dir.iterdir() if p.is_dir() and not p.name.startswith(".")])
    if not run_dirs:
        print(f"No runs under: {suite_dir}")
        return 1

    op = shutil.copytree if args.mode == "copy" else shutil.move
    copied = 0
    skipped = 0
    for run_dir in run_dirs:
        summary_path = run_dir / "summary.json"
        if not summary_path.exists():
            print(f"skip(no summary.json): {run_dir}")
            skipped += 1
            continue
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip(bad json): {summary_path} err={e}")
            skipped += 1
            continue

        algo = _infer_algo(summary)
        if not algo:
            print(f"skip(cannot infer algo): {summary_path}")
            skipped += 1
            continue

        dst = root / algo / run_dir.name
        if dst.exists():
            print(f"skip(exists): {dst}")
            skipped += 1
            continue

        print(f"{args.mode}: {run_dir} -> {dst}")
        if not args.dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if op is shutil.copytree:
                shutil.copytree(run_dir, dst)
            else:
                shutil.move(str(run_dir), str(dst))
        copied += 1

    print(f"Done. {args.mode}={copied} skipped={skipped} suite={suite_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
