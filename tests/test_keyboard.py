"""A3: the whole app can be driven without a mouse, and you can see where you are.

Two things have to hold. Every control a person needs has to be reachable by Tab
— a button nothing can focus may as well not exist for someone who cannot use a
pointer — and wherever the focus lands has to be visible, or the keyboard user is
navigating blind.

Qt's default tab order is creation order, and because these pages are built from
the top down it already matches the visual order. That is worth a test rather
than a shrug: the day somebody builds a panel out of order, this says so.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QAbstractButton,
    QAbstractSlider,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QLineEdit,
    QScrollBar,
    QWidget,
)

OPERABLE = (QAbstractButton, QAbstractSlider, QComboBox, QLineEdit, QAbstractSpinBox)


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_keys"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    win.resize(1280, 860)
    win.show()
    app.processEvents()
    yield win
    win.close()


def pump(times: int = 12):
    for _ in range(times):
        QApplication.instance().processEvents()


def operable(page) -> list[QWidget]:
    """Controls somebody has to be able to reach to use the page."""
    found = []
    for child in page.findChildren(QWidget):
        if not isinstance(child, OPERABLE) or isinstance(child, QScrollBar):
            continue
        if isinstance(child.parent(), (QAbstractSpinBox, QLineEdit)):
            continue                       # the parts inside a spin box, not controls
        if child.isVisible() and child.isEnabled():
            found.append(child)
    return found


def tab_chain(page, limit: int = 4000) -> list[QWidget]:
    """Everything Tab would stop on inside this page, in the order it stops.

    Qt's focus chain is one ring for the whole window, and a widget built later
    can be spliced in anywhere on it — the buttons at the foot of a lesson land
    before the page does. So walk the entire ring back round to the page itself
    and keep the widgets that belong to it, rather than starting beside the page
    and stopping when the ring wraps.
    """
    seen, order = set(), []
    widget = page
    for _ in range(limit):
        widget = widget.nextInFocusChain()
        if widget is None or widget is page:
            break
        if id(widget) in seen:
            continue
        seen.add(id(widget))
        if not page.isAncestorOf(widget):
            continue
        if widget.focusPolicy() != Qt.NoFocus and widget.isVisible() and widget.isEnabled():
            order.append(widget)
    return order


def open_page(window, route):
    window.navigate(route)
    pump(14)
    return window.stack.currentWidget()


def test_every_control_in_every_simulator_is_reachable_by_tab(window):
    from cosmos.gui.simulators.registry import SIMULATORS

    stranded = {}
    for sim_id in SIMULATORS:
        page = open_page(window, f"sim:{sim_id}")
        reachable = {id(w) for w in tab_chain(page)}
        missed = [f"{type(w).__name__} {w.accessibleName() or ''}".strip()
                  for w in operable(page) if id(w) not in reachable]
        if missed:
            stranded[sim_id] = missed
    assert not stranded, ("controls no keyboard can reach:\n"
                          + "\n".join(f"  {k}: {', '.join(v)}" for k, v in stranded.items()))


def test_every_page_is_reachable_by_tab_too(window):
    routes = ["home", "glossary", "reference", "history", "notes", "progress",
              "problems", "review", "classroom", "lesson:L1.2"]
    stranded = {}
    for route in routes:
        page = open_page(window, route)
        reachable = {id(w) for w in tab_chain(page)}
        missed = [type(w).__name__ for w in operable(page) if id(w) not in reachable]
        if missed:
            stranded[route] = missed
    assert not stranded, str(stranded)


def test_the_controls_come_before_the_plot(window):
    """Reading order: set the thing up, then look at what it did."""
    from cosmos.gui.widgets.plot import PlotWidget

    page = open_page(window, "sim:S5")
    chain = tab_chain(page)
    canvases = {id(p.canvas) for p in page.findChildren(PlotWidget)}
    positions = [i for i, w in enumerate(chain) if id(w) in canvases]
    sliders = [i for i, w in enumerate(chain) if isinstance(w, QAbstractSlider)]
    assert positions and sliders
    assert min(sliders) < min(positions), "the plot is tabbed to before its own controls"


def test_the_tab_order_follows_the_page_down_the_controls(window):
    """Within the control column, Tab should go down the page, not around it."""
    page = open_page(window, "sim:S1")
    column = [w for w in tab_chain(page)
              if isinstance(w, (QAbstractSlider, QComboBox, QAbstractSpinBox))]
    tops = [w.mapTo(page, w.rect().topLeft()).y() for w in column]
    backwards = [(a, b) for a, b in zip(tops, tops[1:]) if b < a - 40]
    assert len(backwards) <= 1, f"tab order jumps back up the page: {backwards}"


# ------------------------------------------------------- seeing where you are

def test_a_focused_plot_shows_a_ring(window):
    """A2 made the canvas focusable; without this nobody can tell when it is."""
    from cosmos.gui.widgets.plot import PlotWidget

    page = open_page(window, "sim:S5")
    plot = page.findChildren(PlotWidget)[0]
    assert plot.canvas_frame.property("focused") == "no"
    plot.canvas.setFocus()
    pump()
    assert plot.canvas_frame.property("focused") == "yes"
    plot.canvas.clearFocus()
    pump()
    assert plot.canvas_frame.property("focused") == "no"


def test_the_theme_draws_a_focus_ring_on_the_things_that_take_focus(qt_app):
    """G17's rule, kept honest: the stylesheet must cover what can be focused."""
    from cosmos.gui.theme import theme

    sheet = QApplication.instance().styleSheet() or ""
    if not sheet:
        theme().apply(QApplication.instance())
        sheet = QApplication.instance().styleSheet()
    for selector in ("QPushButton:focus", "QComboBox:focus", "QSlider:focus",
                     "QLineEdit:focus", "QCheckBox:focus", "QRadioButton:focus",
                     'QFrame#plotFrame[focused="yes"]'):
        assert selector in sheet, f"nothing shows focus on {selector}"


def test_the_canvas_ring_does_not_move_the_plot(window):
    """The border is reserved when it is invisible, so focus must not reflow."""
    from cosmos.gui.widgets.plot import PlotWidget

    page = open_page(window, "sim:S5")
    plot = page.findChildren(PlotWidget)[0]
    before = plot.canvas.size()
    plot.canvas.setFocus()
    pump()
    assert plot.canvas.size() == before
