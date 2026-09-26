"""A5: the Reference page should not make anybody wait for it.

It used to build all four tabs before it appeared: the constants, the models
table — the first thing in the app to import the physics engine — the data
record, and 76 equations for matplotlib to typeset. Two and a half seconds of
frozen window for a page that is mostly text.

Now each tab is built when it is first looked at, and the formula sheet is
typeset a few at a time so the window keeps answering while it fills.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture
def page(qt_app, tmp_path_factory):
    from cosmos.content.loader import load_curriculum, load_glossary
    from cosmos.gui.context import AppContext, AppSignals
    from cosmos.gui.pages.reference import ReferencePage
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path_factory.mktemp("refspeed") / "p.json")
    ctx = AppContext(load_curriculum(), load_glossary(), store, AppSignals())
    return ReferencePage(ctx)


def pump(times: int = 3):
    for _ in range(times):
        QApplication.instance().processEvents()


def finish_typesetting(page, limit: int = 20000):
    turns = 0
    while page._pending_maths and turns < limit:
        pump(1)
        turns += 1
    pump()
    return turns


def test_opening_the_page_does_not_build_the_tabs_nobody_asked_for(page):
    page.refresh()
    pump()
    assert page.models_view.toPlainText() == ""
    assert page.data_view.toPlainText() == ""
    assert page.constants_view.toPlainText() == ""


def test_the_formula_sheet_says_it_is_working_before_it_is_done(page):
    page.refresh()
    pump()
    text = page.formula_view.toPlainText()
    assert "Formula sheet" in text
    # Either it is still typesetting, or the cache was already warm from another
    # test in this process and it went straight to the formulas.
    assert "Typesetting" in text or "Hubble" in text


def test_the_formulas_arrive(page):
    page.refresh()
    finish_typesetting(page)
    text = page.formula_view.toPlainText()
    assert "Typesetting" not in text
    assert len(text) > 500
    assert not page._pending_maths


def test_typesetting_hands_the_loop_back_between_batches(page):
    """The point of the batches: the window answers while the maths arrives.

    The cache is emptied first, because otherwise this passes by doing nothing
    whenever another test in the same process has already drawn the formulas.
    """
    from cosmos.gui.rendering import math as mathrender

    mathrender.render_png.cache_clear()
    mathrender._rendered.clear()

    page.refresh()
    pump()
    assert page._pending_maths, "nothing to typeset even with an empty cache"
    assert len(page._pending_maths) <= len(page.formulas)
    turns = finish_typesetting(page)
    assert turns > 1, "the whole sheet went in one turn; nothing was spread"


def test_each_tab_is_built_when_it_is_shown(page):
    page.refresh()
    finish_typesetting(page)
    for index in range(page.tabs.count()):
        page.tabs.setCurrentIndex(index)
        pump()
    assert page.models_view.toPlainText() != ""
    assert page.data_view.toPlainText() != ""
    assert page.constants_view.toPlainText() != ""


def test_a_tab_is_built_once_not_every_time(page):
    page.refresh()
    finish_typesetting(page)
    page.tabs.setCurrentIndex(2)
    pump()
    built = set(page._built)
    page.tabs.setCurrentIndex(0)
    page.tabs.setCurrentIndex(2)
    pump()
    assert page._built == built


def test_the_route_to_the_data_tab_builds_it(page):
    """Help -> Data & methods jumps straight there, so it must fill on arrival."""
    page.refresh()
    page.open_target("data")
    pump()
    assert page.data_view.toPlainText() != ""
    assert "Data and methods" in page.data_view.toPlainText()


def test_filtering_the_formulas_still_works_after_typesetting(page):
    page.refresh()
    finish_typesetting(page)
    page.search.setText("redshift")
    pump()
    text = page.formula_view.toPlainText()
    assert "Redshift" in text
    assert "Einstein radius" not in text


def test_the_renderer_remembers_what_it_has_drawn(qt_app):
    from cosmos.gui.rendering import math as mathrender
    from cosmos.gui.theme import theme

    colour = theme().palette.text
    tex = r"E = mc^2"
    assert not mathrender.is_cached(tex, colour, 33.0)
    mathrender.render_png(tex, colour, 33.0)
    assert mathrender.is_cached(tex, colour, 33.0)
    assert not mathrender.is_cached(tex, colour, 34.0)       # a different size is different work
