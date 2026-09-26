"""A1: every control the app makes announces itself.

Qt builds an accessible name out of a widget's text, so a button with a label
needs nobody's help. The ones that reach a screen reader as an unnamed "slider"
or "button" are the controls with no text of their own: the sliders and spin
boxes whose label sits beside them rather than in them, the icon-only buttons,
and the search boxes that say what they are in a placeholder which disappears the
moment you type.

This sweep counts them. When it was written the app had 577 of them.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

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

#: What a person can operate, and therefore has to be able to identify.
INTERACTIVE = (QAbstractButton, QAbstractSlider, QComboBox, QLineEdit)


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_a11y"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    win.show()
    app.processEvents()
    yield win
    win.close()


def pump():
    QApplication.instance().processEvents()


def is_qt_furniture(widget: QWidget) -> bool:
    """Qt's own parts, which Qt names itself and nobody here creates.

    The clear button inside a line edit, the line edit inside a spin box, the
    corner button of a table, every scroll bar. Naming them is not ours to do,
    and pretending otherwise would make this sweep lie about its own coverage.
    """
    if isinstance(widget, QScrollBar):
        return True
    if widget.objectName().startswith("qt_"):
        return True
    parent = widget.parent()
    return isinstance(parent, (QAbstractSpinBox, QLineEdit))


def nameless(page: QWidget) -> list[str]:
    """Controls with neither a name nor visible text of their own."""
    found = []
    for child in page.findChildren(QWidget):
        if not isinstance(child, INTERACTIVE) or is_qt_furniture(child):
            continue
        text = child.text() if isinstance(child, QAbstractButton) else ""
        if child.accessibleName() or text:
            continue
        hint = child.toolTip() or child.objectName() or "no tooltip either"
        found.append(f"{type(child).__name__} ({hint[:50]})")
    return found


def every_route(window) -> list[str]:
    from cosmos.gui.simulators.registry import SIMULATORS

    static = ["home", "sims", "glossary", "reference", "history", "notes", "progress",
              "problems", "review", "classroom", "search:redshift"]
    return static + [f"sim:{s}" for s in SIMULATORS] + ["lesson:L1.2", "lesson:L7.2"]


def test_every_control_in_the_app_can_be_announced(window):
    unnamed = {}
    for route in every_route(window):
        window.navigate(route)
        pump()
        found = nameless(window.stack.currentWidget())
        if found:
            unnamed[route] = found
    assert not unnamed, (
        "a screen reader would announce these as an unnamed control:\n"
        + "\n".join(f"  {route}: {', '.join(items)}" for route, items in unnamed.items()))


def test_the_panels_are_covered_too(window):
    for dock in (window.guide_dock, window.notes_dock, window.tutor_dock):
        assert not nameless(dock.widget()), dock.objectName()


def test_the_sweep_would_notice(window, qt_app):
    """A guard that cannot fail is not a guard."""
    from PySide6.QtWidgets import QPushButton

    page = window.stack.currentWidget()
    offender = QPushButton(page)
    offender.setIcon(page.style().standardIcon(page.style().StandardPixmap.SP_ArrowLeft))
    try:
        assert any("QPushButton" in item for item in nameless(page))
    finally:
        offender.setParent(None)
        offender.deleteLater()


# ------------------------------------------------------- the pieces that do it

def test_a_label_beside_a_slider_becomes_its_name(qt_app):
    from cosmos.gui.widgets.common import ParameterSlider

    slider = ParameterSlider("Ω<sub>m</sub> matter density", 0.0, 1.0, 0.3,
                             tooltip="How much matter the universe contains")
    assert slider.slider.accessibleName() == "Ω m matter density"
    assert slider.spin.accessibleName() == "Ω m matter density"
    assert "matter" in slider.spin.accessibleDescription()


def test_a_labelled_row_names_the_control_in_it(qt_app):
    from PySide6.QtWidgets import QComboBox

    from cosmos.gui.widgets.common import labelled_row

    box = QComboBox()
    row = labelled_row("Sample", box, ("Which sample", "Two are simulated, one is real."))
    assert row is not None          # the row owns the combo; dropping it deletes it
    assert box.accessibleName() == "Sample"
    assert box.accessibleDescription() == "Two are simulated, one is real."


def test_a_placeholder_becomes_the_name_of_a_search_box(qt_app):
    from PySide6.QtWidgets import QLineEdit

    from cosmos.gui.widgets.common import placeholder

    edit = QLineEdit()
    placeholder(edit, "Search terms…  (e.g. redshift, parsec)")
    assert edit.placeholderText().startswith("Search terms")
    assert edit.accessibleName() == "Search terms"


def test_markup_is_not_read_aloud(qt_app):
    from cosmos.gui.widgets.common import strip_markup

    assert strip_markup("Ω<sub>b</sub> h<sup>2</sup>") == "Ω b h 2"
    assert strip_markup("<b>Careful:</b><br>this is a fit") == "Careful: this is a fit"
    assert strip_markup("  spaced   out  ") == "spaced out"


def test_an_info_button_is_not_called_question_mark(qt_app):
    from cosmos.gui.widgets.common import InfoButton

    button = InfoButton("Hubble constant", "The expansion rate <b>today</b>.")
    assert button.text() == "?"
    assert "Hubble constant" in button.accessibleName()
    assert button.accessibleDescription() == "The expansion rate today ."
