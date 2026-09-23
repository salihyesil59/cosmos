"""Deprecated: use ``tools/build_app.py``, which builds for every platform (E11)."""

from __future__ import annotations

import sys

from build_app import main

if __name__ == "__main__":
    print("tools/build_exe.py is now tools/build_app.py.\n")
    raise SystemExit(main(sys.argv[1:]))
