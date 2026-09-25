"""V5: a lesson figure that invents its data has to say so, on the figure.

Detected rather than declared. A figure that asks numpy for random numbers is
showing something nobody measured, and a learner scrolling past it has only the
words on the picture to tell them that. So every figure is rendered with the
random generator under watch, and one that used it must carry a plain word
somewhere a reader will see.

What this does not catch: data invented without randomness — a hand-built curve
presented as though it were observed. Nothing mechanical finds that; it is the
reviewer's job. What it does catch is the common case, and every new figure that
forgets.
"""

from __future__ import annotations

import importlib

import numpy as np
import pytest
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from cosmos.gui.rendering import figures
from cosmos.gui.theme import theme

#: Words that tell a reader the numbers were not measured. Deliberately plain:
#: "model" and "example" are not here, because a figure of real measurements
#: compared with a model says "model" too.
HONEST_WORDS = ("not real data", "simulated", "simulation", "synthetic", "illustrat",
                "toy", "mock", "invented", "generated")

#: Loading one of these means the figure is showing somebody's measurements.
REAL_DATA_LOADERS = (
    ("cosmos.physics.datasets", "load_pantheon_plus"),
    ("cosmos.physics.datasets", "load_sparc_galaxy"),
    ("cosmos.physics.datasets", "load_hubble_1929"),
    ("cosmos.physics.skymap", "load"),
    ("cosmos.physics.sdss", "load"),
)


def _clear_caches() -> None:
    """Cached points would hide the randomness that made them the first time."""
    for module in (figures, importlib.import_module("cosmos.physics.datasets")):
        for value in vars(module).values():
            if hasattr(value, "cache_clear"):
                value.cache_clear()


def _visible_words(fig: Figure) -> str:
    """Everything the figure puts in front of a reader."""
    bits = [t.get_text() for t in fig.texts]
    for ax in fig.axes:
        bits += [ax.get_title(), ax.get_xlabel(), ax.get_ylabel()]
        bits += [t.get_text() for t in ax.texts]
        if (legend := ax.get_legend()) is not None:
            bits += [t.get_text() for t in legend.get_texts()]
    return " ".join(bits).lower()


def _clipped_titles(fig: Figure) -> list[str]:
    """Titles that run off the edge of the picture.

    A label nobody can read is not a label. Long titles do not shrink or wrap —
    matplotlib draws them and lets the figure edge cut them off — so this is the
    price of adding a word to one, and it is easy to do by accident.
    """
    fig.canvas.draw()
    page = fig.bbox
    clipped = []
    for text in [*fig.texts, *(ax.title for ax in fig.axes)]:
        if not text.get_text():
            continue
        box = text.get_window_extent()
        if box.x0 < page.x0 - 1 or box.x1 > page.x1 + 1:
            clipped.append(text.get_text())
    return clipped


def _render_watched(name: str) -> tuple[str, bool, list[str], list[str]]:
    """Draw one figure: its words, whether it rolled dice, what it loaded, what is clipped."""
    _clear_caches()
    rolled: list[bool] = []
    loaded: list[str] = []
    real_default_rng = np.random.default_rng
    restore: list[tuple[object, str, object]] = []

    def watched_rng(*args, **kwargs):
        rolled.append(True)
        return real_default_rng(*args, **kwargs)

    np.random.default_rng = watched_rng
    for module_name, attribute in REAL_DATA_LOADERS:
        module = importlib.import_module(module_name)
        original = getattr(module, attribute)

        def watcher(*args, _original=original, _name=attribute, **kwargs):
            loaded.append(_name)
            return _original(*args, **kwargs)

        setattr(module, attribute, watcher)
        restore.append((module, attribute, original))

    fig = Figure(figsize=(6.4, 3.4), dpi=100)
    FigureCanvasAgg(fig)
    try:
        figures._REGISTRY[name](fig, theme().palette)
        if fig.get_layout_engine() is None:
            fig.tight_layout()                    # what render_png does before saving
        return _visible_words(fig), bool(rolled), sorted(set(loaded)), _clipped_titles(fig)
    finally:
        np.random.default_rng = real_default_rng
        for module, attribute, original in restore:
            setattr(module, attribute, original)


@pytest.fixture(scope="module")
def rendered(qt_app):
    """Every figure in the course, drawn once."""
    figures._load_all()
    return {name: _render_watched(name) for name in sorted(figures._REGISTRY)}


def test_the_course_has_figures_to_check(rendered):
    assert len(rendered) > 50


def test_no_invented_figure_passes_itself_off_as_real(rendered):
    unlabelled = [
        name for name, (words, invented, real, _clipped) in rendered.items()
        if invented and not real and not any(word in words for word in HONEST_WORDS)
    ]
    assert not unlabelled, (
        "these figures draw data the app made up and say nothing about it: "
        + ", ".join(unlabelled)
        + ". Put one of "
        + ", ".join(HONEST_WORDS)
        + " in the title, an axis label or the legend."
    )


def test_a_figure_of_real_measurements_is_not_called_simulated(rendered):
    """The opposite mistake: apologising for data that was actually taken."""
    for name, (words, _invented, real, _clipped) in rendered.items():
        if not real:
            continue
        assert "not real data" not in words, f"{name} shows {', '.join(real)} but disowns it"


def test_every_figure_a_lesson_asks_for_exists(rendered):
    """A figure named in a lesson but missing would silently show nothing."""
    import re

    from cosmos.content.loader import load_curriculum

    for lesson in load_curriculum().lessons.values():
        for wanted in re.findall(r"\{\{figure:([a-z0-9_]+)\}\}", lesson.body):
            assert wanted in rendered, f"{lesson.id} asks for a figure called {wanted}"


def test_the_watch_would_actually_notice(qt_app):
    """A guard that never fires is worse than none, so prove it fires."""
    figures._load_all()
    name = "_v5_probe"

    @figures.figure(name)
    def _probe(fig, p):
        rng = np.random.default_rng(0)
        fig.add_subplot().plot(rng.normal(size=5))

    try:
        words, invented, real, _clipped = _render_watched(name)
        assert invented, "randomness went unnoticed"
        assert not real
        assert not any(word in words for word in HONEST_WORDS)
    finally:
        del figures._REGISTRY[name]


def test_no_title_runs_off_the_edge_of_its_figure(rendered):
    """An honest label that is cut in half is not an honest label.

    Two of the labels added for V5 pushed their titles past the edge, which is
    how this check came to exist.
    """
    guilty = {name: clipped for name, (_w, _i, _r, clipped) in rendered.items() if clipped}
    assert not guilty, "clipped titles: " + "; ".join(
        f"{name}: {' / '.join(lines)}" for name, lines in guilty.items())
