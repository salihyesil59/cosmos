"""Build the reading edition of the course as a static website (E19).

    python tools/build_site.py                 # writes dist/site/
    python tools/build_site.py --out public    # somewhere else

Open dist/site/index.html in a browser, or put the folder on any web server
(GitHub Pages, a school intranet, a USB stick). Nothing is fetched from the
internet: formulas and figures are PNG files beside the pages.
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "site", help="output folder")
    args = parser.parse_args(argv)

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("MPLBACKEND", "Agg")
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])  # noqa: F841 (QImage needs it)
    from cosmos.gui.rendering.site import build_site

    start = time.perf_counter()
    report = build_site(args.out)
    print(f"{len(report.pages)} pages and {report.images} images, {report.bytes / 1e6:.1f} MB, "
          f"in {time.perf_counter() - start:.0f} s")
    print(f"open {args.out / 'index.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
