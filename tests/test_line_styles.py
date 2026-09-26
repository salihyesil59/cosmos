"""A6: no plot asks you to tell its lines apart by colour alone.

A legend of seven colours is a legend of one line to a reader who cannot
distinguish hue, and no palette can fix that — `A4` tried and found that seven
hues at a readable contrast cannot also be seven lightnesses without becoming a
single ramp. Shape is the channel that is free, so curves that would otherwise
look alike are given distinct dashes after the figure is drawn.
"""

from __future__ import annotations

import os
from collections import Counter

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from matplotlib.figure import Figure  # noqa: E402

from cosmos.gui.theme import DASHES, _style_key, separate_by_style, style_axes, theme  # noqa: E402

NO_MARKER = ("", "None", " ", None)


def look_alike(fig) -> list[str]:
    """Labelled curves on one axes that a reader could not tell apart by shape."""
    clashes = []
    for number, ax in enumerate(fig.get_axes(), 1):
        curves = [(_style_key(line), line.get_label()) for line in ax.lines
                  if line.get_label() and not line.get_label().startswith("_")
                  and line.get_marker() in NO_MARKER and len(line.get_ydata()) > 1]
        if len(curves) < 2:
            continue
        counts = Counter(key for key, _ in curves)
        same = [label for key, label in curves if counts[key] > 1]
        if len(same) >= 2:
            clashes.append(f"panel {number}: {', '.join(same[:4])}")
    return clashes


def a_plot(count: int, **kwargs):
    fig = Figure()
    ax = fig.add_subplot()
    x = np.linspace(0, 1, 20)
    for i in range(count):
        ax.plot(x, x * (i + 1), label=f"curve {i}", **kwargs)
    return fig, ax


# ------------------------------------------------------------- the whole app

def test_no_lesson_figure_needs_colour_vision(qt_app):
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    from cosmos.gui.rendering import figures

    figures._load_all()
    palette = theme().palette
    guilty = {}
    for name in sorted(figures._REGISTRY):
        fig = Figure(figsize=(6.4, 3.4), dpi=100)
        FigureCanvasAgg(fig)
        figures._REGISTRY[name](fig, palette)
        for ax in fig.get_axes():          # what render_png does before saving
            style_axes(ax, palette)
        if clashes := look_alike(fig):
            guilty[name] = clashes
    assert not guilty, ("figures telling their lines apart by colour alone:\n  "
                        + "\n  ".join(f"{k}: {v[0]}" for k, v in guilty.items()))


def test_no_simulator_plot_needs_colour_vision(window_for_styles):
    from cosmos.gui.simulators.registry import SIMULATORS
    from cosmos.gui.widgets.plot import PlotWidget
    from PySide6.QtWidgets import QApplication

    window = window_for_styles
    guilty = {}
    for sim_id in SIMULATORS:
        window.navigate(f"sim:{sim_id}")
        for _ in range(18):
            QApplication.instance().processEvents()
        for plot in window.stack.currentWidget().findChildren(PlotWidget):
            if clashes := look_alike(plot.figure):
                guilty[f"{sim_id}/{plot._name}"] = clashes
    assert not guilty, ("plots telling their lines apart by colour alone:\n  "
                        + "\n  ".join(f"{k}: {v[0]}" for k, v in guilty.items()))


@pytest.fixture(scope="module")
def window_for_styles(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_styles"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    win.resize(1280, 860)
    win.show()
    app.processEvents()
    yield win
    win.close()


# ---------------------------------------------------------------- the rule

def test_curves_that_looked_alike_no_longer_do(qt_app):
    fig, ax = a_plot(4)
    assert look_alike(fig)
    separate_by_style(ax)
    assert not look_alike(fig)


def test_the_first_curve_keeps_the_solid_line(qt_app):
    """The busiest line on a crowded plot should stay the easiest to read."""
    fig, ax = a_plot(3)
    separate_by_style(ax)
    assert ax.lines[0].get_linestyle() == "-"


def test_one_curve_is_left_alone(qt_app):
    fig, ax = a_plot(1)
    separate_by_style(ax)
    assert ax.lines[0].get_linestyle() == "-"


def test_a_line_dashed_on_purpose_keeps_its_dashes(qt_app):
    """Somebody chose that; the rule is for accidents, not decisions."""
    fig = Figure()
    ax = fig.add_subplot()
    x = np.linspace(0, 1, 20)
    ax.plot(x, x, label="measured")
    deliberate, = ax.plot(x, x * 2, "--", label="model")
    before = _style_key(deliberate)
    separate_by_style(ax)
    assert _style_key(deliberate) == before


def test_a_replacement_never_collides_with_a_style_already_there(qt_app):
    """The bug this rule had at first: handing out "--" where "--" already was."""
    fig = Figure()
    ax = fig.add_subplot()
    x = np.linspace(0, 1, 20)
    ax.plot(x, x, label="a")                      # solid
    ax.plot(x, x * 2, "--", label="b")            # already dashed
    ax.plot(x, x * 3, label="c")                  # solid: must not become "--"
    separate_by_style(ax)
    assert not look_alike(fig)


def test_markers_are_already_a_second_channel(qt_app):
    fig = Figure()
    ax = fig.add_subplot()
    x = np.linspace(0, 1, 20)
    first, = ax.plot(x, x, "o", label="points")
    second, = ax.plot(x, x * 2, "s", label="squares")
    separate_by_style(ax)
    assert first.get_linestyle() == second.get_linestyle(), "markers distinguish these already"


def test_unlabelled_lines_are_left_out(qt_app):
    """They are scaffolding — guides, axes, a hundred MCMC chains."""
    fig = Figure()
    ax = fig.add_subplot()
    x = np.linspace(0, 1, 20)
    quiet = [ax.plot(x, x * i)[0] for i in range(1, 5)]
    separate_by_style(ax)
    assert {line.get_linestyle() for line in quiet} == {"-"}


def test_an_axes_can_ask_to_be_left_alone(qt_app):
    fig, ax = a_plot(3)
    ax.set(gid="keep-styles")
    separate_by_style(ax)
    assert {line.get_linestyle() for line in ax.lines} == {"-"}


def test_there_are_enough_styles_for_a_crowded_plot(qt_app):
    fig, ax = a_plot(len(DASHES))
    separate_by_style(ax)
    assert not look_alike(fig)
    assert len({_style_key(line) for line in ax.lines}) == len(DASHES)


def test_it_survives_being_applied_twice(qt_app):
    """style_axes runs on every redraw; the second pass must change nothing."""
    fig, ax = a_plot(4)
    separate_by_style(ax)
    once = [_style_key(line) for line in ax.lines]
    separate_by_style(ax)
    assert [_style_key(line) for line in ax.lines] == once
