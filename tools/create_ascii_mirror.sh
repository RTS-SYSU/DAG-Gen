#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="${1:-$(pwd)}"
ROOT_DIR="$(cd "$ROOT_DIR" && pwd)"
MIRROR_DIR="$ROOT_DIR/ascii_links"

python3 - "$ROOT_DIR" "$MIRROR_DIR" <<'PY'
import hashlib
import os
import shutil
import sys

root = os.path.abspath(sys.argv[1])
mirror = os.path.abspath(sys.argv[2])

EXCLUDE_NAMES = {
    ".git",
    ".vscode",
    ".pytest_cache",
    "__pycache__",
    "ascii_links",
}


def encode_component(name: str) -> str:
    safe = []
    changed = False
    for ch in name:
        if ch.isascii() and (ch.isalnum() or ch in "._-"):
            safe.append(ch)
        else:
            changed = True
            safe.append(f"_u{ord(ch):04x}")
    candidate = "".join(safe).strip(".")
    if not candidate:
        candidate = "item"
        changed = True
    if changed:
        digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
        return f"{candidate}__{digest}"
    return candidate


def mirror_rel_path(rel_path: str) -> str:
    parts = [part for part in rel_path.split(os.sep) if part and part != "."]
    return os.path.join(*(encode_component(part) for part in parts)) if parts else ""


if os.path.lexists(mirror):
    shutil.rmtree(mirror)
os.makedirs(mirror, exist_ok=True)

for current_root, dirnames, filenames in os.walk(root):
    rel_root = os.path.relpath(current_root, root)
    if rel_root == ".":
        rel_root = ""

    dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDE_NAMES)
    filenames = sorted(f for f in filenames if f not in EXCLUDE_NAMES)

    mirror_root = os.path.join(mirror, mirror_rel_path(rel_root)) if rel_root else mirror
    os.makedirs(mirror_root, exist_ok=True)

    for dirname in dirnames:
        rel_dir = os.path.join(rel_root, dirname) if rel_root else dirname
        os.makedirs(os.path.join(mirror, mirror_rel_path(rel_dir)), exist_ok=True)

    for filename in filenames:
        rel_file = os.path.join(rel_root, filename) if rel_root else filename
        target = os.path.join(mirror, mirror_rel_path(rel_file))
        source = os.path.join(root, rel_file)
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        if os.path.lexists(target):
            os.unlink(target)
        os.symlink(source, target)

print(mirror)
PY
