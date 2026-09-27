"""R3: the reading edition says what the app says.

The static site ships with every release, and it had none of Phase 6 in it — no
record of where a measurement came from, no validation table, no method note on
a simulator. Somebody reading the web edition got a quietly less honest version
of the same course.

The text is not copied across: both render `cosmos.gui.rendering.data_methods`,
because a copy would start drifting the day it was made. These tests hold the two
to the same content.
"""

from __future__ import annotations

import os
import re

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def site(tmp_path_factory, qt_app):
    from cosmos.gui.rendering.site import build_site

    out = tmp_path_factory.mktemp("site_methods") / "site"
    build_site(out)
    return out


def text_of(path) -> str:
    """What a reader sees: tags removed and entities turned back into characters.

    "Lelli, McGaugh & Schombert" reaches the page as "&amp;", so comparing against
    the raw HTML would miss every citation with an ampersand in it.
    """
    import html as html_module

    markup = path.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", html_module.unescape(re.sub(r"<[^>]+>", " ", markup)))


# ----------------------------------------------------------- the data page

def test_the_site_has_a_data_and_methods_page(site):
    assert (site / "data.html").exists()


def test_it_names_every_measurement_and_every_invention(site):
    from cosmos import provenance

    body = text_of(site / "data.html")
    for measurement in provenance.MEASUREMENTS:
        assert measurement.title in body, measurement.title
        assert measurement.cite.split(";")[0][:20] in body, measurement.cite
    for generated in provenance.GENERATED:
        assert generated.title in body, generated.title


def test_it_keeps_the_real_and_the_generated_apart(site):
    body = text_of(site / "data.html")
    assert body.index("Real measurements") < body.index("Data the app generates")


def test_it_carries_the_validation_table(site):
    from cosmos import validation

    html = (site / "data.html").read_text(encoding="utf-8")
    body = text_of(site / "data.html")
    assert "How the physics is checked" in body
    assert html.count("<table") >= 3, "one table per kind of check"
    for check in validation.CHECKS[:4]:
        assert check.quantity in body, check.quantity


def test_its_links_point_inside_the_site_not_at_app_routes(site):
    """`sim:S5` means nothing in a browser."""
    html = (site / "data.html").read_text(encoding="utf-8")
    assert "simulators.html#S" in html
    assert 'href="sim:' not in html
    assert "reference:data" not in html


def test_it_is_reachable_from_every_page(site):
    for name in ("index.html", "glossary.html", "simulators.html", "formulas.html"):
        assert 'href="data.html"' in (site / name).read_text(encoding="utf-8"), name
    lesson = next((site / "lessons").glob("*.html"))
    assert '../data.html' in lesson.read_text(encoding="utf-8")


# ------------------------------------------------------ the method notes

def test_every_simulator_carries_its_method_note(site):
    from cosmos.gui.simulators.registry import SIMULATORS

    body = text_of(site / "simulators.html")
    assert body.count("How this is computed") == len(SIMULATORS)
    for info in SIMULATORS.values():
        if info.method is None:
            continue
        assert info.method.summary[:50] in body, info.id


def test_a_note_says_what_it_leaves_out(site):
    from cosmos.gui.simulators.registry import SIMULATORS

    body = text_of(site / "simulators.html")
    assert "What it leaves out" in body
    leaves_out = SIMULATORS["S12"].method.approximations[0]
    assert leaves_out[:40] in body


def test_the_notes_typeset_their_formulas(site):
    """A cited equation should be shown, not just named."""
    html = (site / "simulators.html").read_text(encoding="utf-8")
    assert html.count('class="formula"') > 20


# ---------------------------------------------------- app and site agree

def test_both_render_the_same_source(qt_app):
    """The check that matters: one text, two link styles."""
    from cosmos.gui.rendering import data_methods

    app_version = data_methods.data_markdown()
    site_version = data_methods.data_markdown(
        lambda sim, title: f"[{sim} {title}](simulators.html#{sim})")

    assert app_version != site_version, "the link style should differ"
    strip = lambda text: re.sub(r"\]\([^)]*\)", "]", text)          # noqa: E731
    assert strip(app_version) == strip(site_version), "the words should not"


def test_the_app_page_still_shows_it(qt_app, tmp_path_factory):
    from cosmos.content.loader import load_curriculum, load_glossary
    from cosmos.gui.context import AppContext, AppSignals
    from cosmos.gui.pages.reference import ReferencePage
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path_factory.mktemp("r3") / "p.json")
    page = ReferencePage(AppContext(load_curriculum(), load_glossary(), store, AppSignals()))
    page.refresh()
    page.open_target("data")
    body = page.data_view.toPlainText()
    assert "Data and methods" in body
    assert "Pantheon" in body
