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

from PySide6.QtGui import QFontMetrics  # noqa: E402
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


def test_no_page_is_wider_than_the_window_it_lives_in(window):
    shrink_to_minimum(window)
    too_wide = []
    for route in every_route(window):
        window.navigate(route)
        pump()
        page = window.stack.currentWidget()
        needed = page.minimumSizeHint().width()
        if needed > page.width():
            too_wide.append(f"{route} needs {needed}px, has {page.width()}px")
    assert not too_wide, "cut off at the smallest window size: " + "; ".join(too_wide)


def test_nothing_has_to_be_scrolled_sideways(window):
    shrink_to_minimum(window)
    offenders = []
    for route in every_route(window):
        window.navigate(route)
        pump()
        for area in window.stack.currentWidget().findChildren(QAbstractScrollArea):
            if area.property("scrolls_sideways"):
                continue          # a map or a timeline: dragging it is the point
            bar = area.horizontalScrollBar()
            if bar.isVisible() and bar.maximum() > 0:
                name = area.objectName() or type(area).__name__
                offenders.append(f"{route}/{name} runs {bar.maximum()}px past the edge")
    assert not offenders, "sideways scrolling nobody asked for: " + "; ".join(offenders)


def test_the_declared_minimum_size_is_honest(window):
    """The window must really work at the size it lets you shrink to."""
    shrink_to_minimum(window)
    window.navigate("home")
    pump()
    needed = window.minimumSizeHint()
    assert needed.width() <= window.minimumWidth(), (
        f"the window says it works at {window.minimumWidth()}px wide but needs {needed.width()}px")
    assert needed.height() <= window.minimumHeight(), (
        f"the window says it works at {window.minimumHeight()}px tall but needs {needed.height()}px")


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
