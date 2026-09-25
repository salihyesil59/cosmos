"""Test-wide Qt setup: headless, but with real fonts.

The offscreen platform finds no fonts of its own on some systems, and then every
glyph is drawn as the same empty box. Text still "measures", but every letter is
the same width as every other, so anything that depends on how wide a label is —
above all the layout checks in ``test_layout.py`` — would be measuring fiction.
Pointing Qt at the system font folder before the application exists fixes that for
every test in one place.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if not os.environ.get("QT_QPA_FONTDIR"):
    for candidate in (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
                      Path("/usr/share/fonts"),
                      Path("/System/Library/Fonts")):
        if candidate.is_dir():
            os.environ["QT_QPA_FONTDIR"] = str(candidate)
            break
