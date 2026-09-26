"""D2: every page fits inside the smallest window the app says it supports.

The interface grew page by page, and nothing checked that the result still fitted:
a lesson's row of buttons, a glossary term or a simulator's controls could quietly
run past the edge of the window and be cut off. These tests open every page at the
declared minimum size and insist that nothing has to be scrolled sideways to be
seen — except the two things that are meant to be dragged, the lesson map and the
history timeline, which say so with a ``scrolls_sideways`` property.
"""

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QFontInfo, QFontMetrics  # noqa: E402
from PySide6.QtWidgets import QAbstractScrollArea, QApplication  # noqa: E402


def needs_real_fonts() -> None:
    """Skip rather than lie: with no fonts every glyph is the same empty box."""
    metrics = QFontMetrics(QApplication.instance().font())
    if metrics.horizontalAdvance("i") == metrics.horizontalAdvance("W"):
        pytest.skip("no usable fonts in this environment, so widths mean nothing")


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_layout"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    win.show()
    app.processEvents()
    yield win
    win.close()


def pump():
    QApplication.instance().processEvents()


def every_route(window) -> list[str]:
    """Every page a learner can reach, the whole course and every simulator."""
    from cosmos.gui.simulators.registry import SIMULATORS

    static = ["home", "sims", "glossary", "reference", "history", "notes", "progress",
              "problems", "review", "classroom", "search:redshift"]
    lessons = [f"lesson:{lesson_id}" for lesson_id in window.ctx.curriculum.ordered_ids]
    return static + lessons + [f"sim:{sim_id}" for sim_id in SIMULATORS]


def shrink_to_minimum(window) -> None:
    needs_real_fonts()
    for dock in (window.guide_dock, window.notes_dock, window.tutor_dock):
        dock.hide()
    window.resize(window.minimumWidth(), window.minimumHeight())
    pump()


def test_every_page_fits_the_smallest_window(window):
    """One sweep of the whole app, looking for both ways a page can overflow.

    The two checks share a sweep on purpose: opening all 58 lessons and all 29
    simulators is the expensive part of this file, and doing it twice also made a
    Windows-only scipy flake (a temporary file it fails to reopen) much more likely.
    """
    shrink_to_minimum(window)
    too_wide, sideways = [], []
    for route in every_route(window):
        window.navigate(route)
        pump()
        page = window.stack.currentWidget()
        needed = page.minimumSizeHint().width()
        if needed > page.width():
            too_wide.append(f"{route} needs {needed}px, has {page.width()}px")
        for area in page.findChildren(QAbstractScrollArea):
            if area.property("scrolls_sideways"):
                continue          # a map or a timeline: dragging it is the point
            bar = area.horizontalScrollBar()
            if bar.isVisible() and bar.maximum() > 0:
                name = area.objectName() or type(area).__name__
                sideways.append(f"{route}/{name} runs {bar.maximum()}px past the edge")
    assert not too_wide, "cut off at the smallest window size: " + "; ".join(too_wide)
    assert not sideways, "sideways scrolling nobody asked for: " + "; ".join(sideways)


def test_the_measurements_are_of_the_font_the_app_draws(window):
    """A width only means something if the text is the text the learner sees.

    Left to Qt, every widget asks for the generic "Sans Serif" and gets whatever the
    platform hands back. Headless, that was the first family in the font folder, a
    serif with no semibold face, so every heading and primary button was drawn in a
    synthetic bold whose width drifted with whatever else the run had loaded — and
    these checks measured a window nobody has ever seen.
    """
    from cosmos.gui.theme import INTERFACE_FONT

    if not INTERFACE_FONT:
        pytest.skip("this platform uses whatever font Qt hands back")
    font = QApplication.instance().font()
    assert font.family() == INTERFACE_FONT, f"the interface asks for {font.family()}"
    # What it asks for is not always what it gets: a missing family is quietly replaced.
    assert QFontInfo(font).family() == INTERFACE_FONT, (
        f"{INTERFACE_FONT} is not installed here; Qt drew {QFontInfo(font).family()} instead")


def test_the_declared_minimum_size_is_honest(window):
    """The window must really work at the size it lets you shrink to."""
    shrink_to_minimum(window)
    # It should also be a size a modest screen can give: 1024x768 less the taskbar.
    assert window.minimumWidth() <= 1024 and window.minimumHeight() <= 700
    window.navigate("home")
    pump()
    needed = window.minimumSizeHint()
    assert needed.width() <= window.minimumWidth(), (
        f"the window says it works at {window.minimumWidth()}px wide but needs {needed.width()}px")
    assert needed.height() <= window.minimumHeight(), (
        f"the window says it works at {window.minimumHeight()}px tall but needs {needed.height()}px")


def test_the_declared_minimum_holds_in_every_theme(window):
    """All three palettes have to fit the same window, not just the one in use."""
    from cosmos.gui.theme import THEME_ORDER, theme

    shrink_to_minimum(window)
    window.navigate("home")
    pump()
    for name in THEME_ORDER:
        theme().set_theme(name)
        pump()
        needed = window.minimumSizeHint()
        assert needed.width() <= window.minimumWidth(), (
            f"in the {name} theme the window needs {needed.width()}px of {window.minimumWidth()}px")
        assert needed.height() <= window.minimumHeight(), (
            f"in the {name} theme the window needs {needed.height()}px of {window.minimumHeight()}px")


def test_a_page_that_cannot_shrink_scrolls_instead(window):
    """The two tall pages scroll up and down rather than lose their bottom half."""
    shrink_to_minimum(window)
    for route in ("progress", "sim:S1"):
        window.navigate(route)
        pump()
        page = window.stack.currentWidget()
        areas = [a for a in page.findChildren(QAbstractScrollArea)
                 if a.parent() is page or a.parentWidget() is page]
        assert areas, f"{route} has no way to scroll if it does not fit"
        assert page.minimumSizeHint().height() <= window.minimumHeight(), route
