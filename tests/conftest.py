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

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

if not os.environ.get("QT_QPA_FONTDIR"):
    for candidate in (Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts",
                      Path("/usr/share/fonts"),
                      Path("/System/Library/Fonts")):
        if candidate.is_dir():
            os.environ["QT_QPA_FONTDIR"] = str(candidate)
            break


_pinned_face: dict = {}


@pytest.fixture(autouse=True)
def keep_the_bold_face_loaded():
    """Hold the semibold face open, so Qt cannot lose it halfway through a run.

    Qt drops a font engine it has not drawn with for half a minute. Headless, pointed
    at a font folder rather than the system's own font stack, it sometimes fails to
    load this one back: ``QFontInfo`` then reports no family at all, and every heading
    and primary button — the ones the stylesheet asks for at weight 600 — is measured
    in a substitute half as wide again as the face the app really draws. One live font
    per interface font keeps the engine in the cache, and the widths stay honest.
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is not None:
        from PySide6.QtGui import QFont, QFontMetrics

        wanted = (app.font().family(), app.font().pointSizeF())
        if _pinned_face.get("for") != wanted:
            bold = QFont(app.font())
            bold.setWeight(QFont.Weight(600))
            QFontMetrics(bold).horizontalAdvance("W")      # measuring is what loads it
            _pinned_face["for"], _pinned_face["font"] = wanted, bold
    yield


@pytest.fixture(autouse=True)
def theme_stays_put():
    """A test that changes the theme or the text size puts them back afterwards.

    The theme manager is one object for the whole process, so a test that leaves the
    interface on the high-contrast palette, or at 120% text, hands that state to
    every test after it — and the layout checks then measure something nobody asked
    for. Nothing is imported here for tests that never touch the interface.
    """
    import sys

    module = sys.modules.get("cosmos.gui.theme")
    before = (module.theme().name, module.theme().scale) if module else None
    yield
    module = sys.modules.get("cosmos.gui.theme")
    if module is None or before is None:
        return
    from PySide6.QtWidgets import QApplication

    manager = module.theme()
    if QApplication.instance() is None or (manager.name, manager.scale) == before:
        return
    manager.set_theme(before[0])
    manager.set_scale(before[1])


@pytest.fixture(scope="session")
def qt_app():
    """A Qt application, for tests that draw something but need no window."""
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])
