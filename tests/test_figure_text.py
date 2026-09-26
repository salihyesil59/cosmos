"""A2: a plot a screen reader can read.

The description is read off the finished figure rather than written by hand, so
these tests are in two halves: that the reading itself says the right things
about a figure built on purpose, and that every canvas in the app ends up with
one that mentions its axes.
"""

from __future__ import annotations

import os

import numpy as np
import pytest
from matplotlib.figure import Figure

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cosmos.gui.rendering import figure_text  # noqa: E402


def one_axes():
    fig = Figure()
    return fig, fig.add_subplot()


# ------------------------------------------------------------ the reading

def test_it_names_the_axes_and_their_range():
    fig, ax = one_axes()
    ax.set_xlabel("Redshift z")
    ax.set_ylabel("Distance (Mpc)")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5000)
    text = figure_text.describe(fig)
    assert "Redshift z, 0 to 10" in text
    assert "Distance (Mpc), 0 to 5e+03" in text


def test_an_unlabelled_axis_is_not_announced_as_vertical():
    """"Vertical axis vertical" is worse than saying nothing."""
    fig, ax = one_axes()
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    assert "axis vertical" not in figure_text.describe(fig)
    assert "Vertical axis 0 to 1" in figure_text.describe(fig)


def test_a_logarithmic_axis_says_so():
    fig, ax = one_axes()
    ax.set_xscale("log")
    ax.set_xlim(1, 1000)
    assert "logarithmic" in figure_text.describe(fig)


@pytest.mark.parametrize("ys, expected", [
    (np.linspace(1, 10, 50), "rises from 1 to 10"),
    (np.linspace(10, 1, 50), "falls from 10 to 1"),
    (np.full(50, 4.0), "flat at about 4"),
])
def test_it_says_which_way_a_curve_goes(ys, expected):
    fig, ax = one_axes()
    ax.plot(np.linspace(0, 1, 50), ys, label="curve")
    assert expected in figure_text.describe(fig)


def test_it_finds_a_peak_and_says_where():
    fig, ax = one_axes()
    x = np.linspace(0, 10, 101)
    ax.plot(x, -((x - 4) ** 2) + 20, label="hump")
    text = figure_text.describe(fig)
    assert "rises to about 20 near 4" in text
    assert "then falls" in text


def test_it_finds_a_trough_too():
    fig, ax = one_axes()
    x = np.linspace(0, 10, 101)
    ax.plot(x, (x - 7) ** 2, label="dip")
    text = figure_text.describe(fig)
    assert "falls to about 0 near 7" in text
    assert "then rises" in text


def test_scattered_points_are_counted_not_shaped():
    """Twenty measurements do not "rise"; there are twenty of them."""
    fig, ax = one_axes()
    ax.plot(np.arange(20), np.random.default_rng(0).normal(size=20), "o", label="measurements")
    text = figure_text.describe(fig)
    assert "measurements, 20 points" in text
    assert "rises" not in text


def test_one_point_is_not_1_points():
    fig, ax = one_axes()
    ax.plot([0.3], [0.7], "*", label="best fit")
    assert "best fit, 1 point." in figure_text.describe(fig) + "."


def test_unlabelled_series_are_left_out():
    """matplotlib names them _child0; reading that out helps nobody."""
    fig, ax = one_axes()
    ax.plot([0, 1], [0, 1])
    ax.plot([0, 1], [1, 0], label="named")
    text = figure_text.describe(fig)
    assert "_child" not in text
    assert "1 series" in text


def test_an_image_is_described_as_an_image():
    fig, ax = one_axes()
    ax.imshow(np.zeros((32, 64)))
    text = figure_text.describe(fig)
    assert "an image 64 by 32" in text
    assert "series" not in text


def test_bars_are_counted():
    fig, ax = one_axes()
    ax.bar([1, 2, 3], [4, 5, 6])
    assert "3 bars" in figure_text.describe(fig)


def test_panels_are_numbered_and_the_title_is_not_said_twice():
    fig = Figure()
    top, bottom = fig.subplots(2, 1)
    top.set_title("Hubble diagram")
    bottom.set_title("Residuals")
    text = figure_text.describe(fig)
    assert text.startswith("Hubble diagram.")
    assert "Panel 1 of 2." in text
    assert "Panel 2 of 2, Residuals." in text
    assert text.count("Hubble diagram") == 1


def test_an_empty_figure_says_nothing_rather_than_guessing():
    assert figure_text.describe(Figure()) == ""


# ---------------------------------------------------------- the whole app

@pytest.fixture(scope="module")
def window(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_figtext"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    # A canvas smaller than PlotWidget.MIN_DRAW_PX is not drawn at all, and an
    # undrawn figure has nothing to say. Give the window the size a person would.
    win.resize(1280, 860)
    win.show()
    app.processEvents()
    yield win
    win.close()


def plots_on(window, route):
    from PySide6.QtWidgets import QApplication

    from cosmos.gui.widgets.plot import PlotWidget

    window.navigate(route)
    for _ in range(20):
        QApplication.instance().processEvents()
    return window.stack.currentWidget().findChildren(PlotWidget)


def test_every_plot_in_every_simulator_can_be_read_out(window):
    from cosmos.gui.simulators.registry import SIMULATORS

    silent = []
    for sim_id in SIMULATORS:
        for plot in plots_on(window, f"sim:{sim_id}"):
            text = plot.description()
            if "axis" not in text:
                silent.append(f"{sim_id}/{plot._name}: {text[:60]!r}")
    assert not silent, "plots with nothing to say:\n  " + "\n  ".join(silent)


def test_a_canvas_can_be_reached_by_keyboard(window):
    """A description Qt will never focus is a description nobody hears."""
    from PySide6.QtCore import Qt

    for plot in plots_on(window, "sim:S1"):
        assert plot.canvas.focusPolicy() != Qt.NoFocus
        assert plot.canvas.accessibleName()


def test_the_description_follows_the_controls(window):
    """It is read off the figure, so it must move when the figure moves."""
    plots = plots_on(window, "sim:S5")
    simulator = window.stack.currentWidget().simulator
    plot = next(p for p in plots if p._name == "hubble_diagram")
    simulator.h0.setValue(200.0)
    simulator.recompute()
    before = plot.description()
    simulator.h0.setValue(600.0)
    simulator.recompute()
    assert plot.description() != before
