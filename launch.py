from __future__ import annotations

import importlib
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parent
    parent_dir = repo_root.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

    package_name = repo_root.name
    package = importlib.import_module(package_name)

    return int(package.main(sys.argv[1:]))


if __name__ == "__main__":
    raise SystemExit(main())
