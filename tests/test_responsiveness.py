"""R2: no page should make you wait for it.

`A5` fixed the Reference page; measuring the rest found 28 of 44 pages taking
longer than a fifth of a second to open and two taking nearly four — the CMB Sky
Viewer and the Redshift Survey Slice, both of them computing before they drew
anything.

Timing in a test is a blunt instrument: a loaded machine can make any number
appear. These tests time nothing. They check the two things that made the
difference and can be stated exactly — that a plot in a tab nobody has opened is
not drawn, and that the blur that took most of those four seconds now agrees with
the loop it replaced.
"""

from __future__ import annotations

import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QTabWidget  # noqa: E402


@pytest.fixture(scope="module")
def window(tmp_path_factory):
    os.environ["COSMOS_DATA_DIR"] = str(tmp_path_factory.mktemp("cosmos_speed"))
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    win = create_window(app)
    win.resize(1280, 860)
    win.show()
    app.processEvents()
    yield win
    win.close()


def pump(times: int = 16):
    """Turn the event loop and let the clock move.

    Simulators coalesce their redraws behind a 40 ms timer, so draining the queue
    is not enough on its own: the timer needs time to pass as well.
    """
    from PySide6.QtTest import QTest

    for _ in range(max(times // 4, 1)):
        QTest.qWait(20)
    for _ in range(times):
        QApplication.instance().processEvents()


# ------------------------------------------------- work nobody asked for

def test_a_plot_in_an_unopened_tab_is_not_drawn(window):
    from cosmos.gui.widgets.plot import PlotWidget

    window.navigate("sim:S24")               # four tabs, one of them expensive
    pump()
    page = window.stack.currentWidget()
    tabs = page.findChildren(QTabWidget)
    assert tabs, "S24 is meant to have tabs"

    plots = page.findChildren(PlotWidget)
    drawn = [p for p in plots if p.figure.get_axes()]
    assert drawn, "the tab that is showing should have been drawn"
    assert len(drawn) < len(plots), "every tab was drawn, opened or not"


def test_opening_the_tab_draws_it(window):
    from cosmos.gui.widgets.plot import PlotWidget

    window.navigate("sim:S24")
    pump()
    page = window.stack.currentWidget()
    tabs = page.findChildren(QTabWidget)[0]
    for index in range(tabs.count()):
        tabs.setCurrentIndex(index)
        pump(6)
    assert all(p.figure.get_axes() for p in page.findChildren(PlotWidget)), \
        "a tab was opened and its plot still has nothing in it"


def test_a_plot_not_in_a_tab_is_drawn_straight_away(window):
    """Deferring must not mean the plot you are looking at arrives late."""
    from cosmos.gui.widgets.plot import PlotWidget

    window.navigate("sim:S6")
    pump()
    plots = window.stack.currentWidget().findChildren(PlotWidget)
    assert plots and all(p.figure.get_axes() for p in plots)


def test_every_simulator_shows_something_on_arrival(window):
    """Whatever is in front of you when the page opens must be drawn."""
    from cosmos.gui.simulators.registry import SIMULATORS
    from cosmos.gui.widgets.plot import PlotWidget

    empty = []
    for sim_id in SIMULATORS:
        window.navigate(f"sim:{sim_id}")
        pump(12)
        page = window.stack.currentWidget()
        visible = [p for p in page.findChildren(PlotWidget) if p.isVisible()]
        if visible and not any(p.figure.get_axes() for p in visible):
            empty.append(sim_id)
    assert not empty, "simulators that open with an empty plot in front of you: " + ", ".join(empty)


# ------------------------------------------------------- the blur it replaced

def test_the_fft_blur_agrees_with_the_loop_it_replaced():
    """The old per-row loop, kept here as the definition of the right answer."""
    import math

    from cosmos.physics import skymap

    def by_hand(sky, values, degrees):
        rows, columns = sky.shape
        result = skymap._gaussian_axis(values, degrees / (180.0 / rows), axis=0, wrap=False)
        per_column = 360.0 / columns
        cos_lat = np.cos(np.radians(sky.latitudes))
        for row in range(rows):
            sigma = degrees / (per_column * max(cos_lat[row], 1e-3))
            if sigma < 0.3:
                continue
            result[row] = skymap._gaussian_axis(result[row][None, :], sigma, axis=1, wrap=True)[0]
        return result

    sky = skymap.load()
    for degrees in (0.5, 2.0, 6.0):
        loop = by_hand(sky, sky.temperature, degrees)
        fft = skymap.smooth(sky, sky.temperature, degrees)
        assert fft.shape == loop.shape
        # The loop cut its kernel off at three sigma; this one does not, so they
        # are close rather than equal.
        assert abs(fft.std() / loop.std() - 1) < 0.01, degrees
        assert np.abs(fft - loop).max() < 0.05 * sky.temperature.std(), degrees
        assert math.isfinite(float(fft.mean()))


def test_blurring_by_nothing_changes_nothing():
    from cosmos.physics import skymap

    sky = skymap.load()
    assert skymap.smooth(sky, sky.temperature, 0.0) is sky.temperature


def test_a_wider_blur_leaves_less_structure():
    from cosmos.physics import skymap

    sky = skymap.load()
    spreads = [skymap.smooth(sky, sky.temperature, d).std() for d in (0.5, 2.0, 6.0, 10.0)]
    assert spreads == sorted(spreads, reverse=True), spreads
