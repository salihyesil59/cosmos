"""V1: the record of where the data comes from has to stay true.

A page that says "this is real and that is generated" is worth less than nothing
if it goes stale. These tests tie ``cosmos/provenance.py`` to the files actually
on disk, the simulators that actually exist, and the README that ships beside the
data.
"""

from __future__ import annotations

import re

import pytest

from cosmos import provenance


#: Files in cosmos/data that the app writes about itself rather than measures.
#: Named one by one on purpose: the rule is that a data file justifies itself,
#: and a pattern here would let a real data set slip in behind it.
OUR_OWN_RECORDS = {"validation.json"}


def test_every_bundled_data_file_is_accounted_for():
    """No file may sit in the data folder without saying where it came from."""
    on_disk = {
        f"external/{p.name}" for p in provenance.EXTERNAL_DIR.iterdir()
        if p.is_file() and p.name != "README.md"
    }
    on_disk |= {p.name for p in provenance.DATA_DIR.iterdir()
                if p.is_file() and p.name not in OUR_OWN_RECORDS}
    described = provenance.bundled_files()
    assert on_disk - described == set(), "a data file with no entry in cosmos/provenance.py"
    assert described - on_disk == set(), "an entry in cosmos/provenance.py with no file"


def test_the_files_are_where_the_record_says():
    for m in provenance.MEASUREMENTS:
        assert m.path.is_file(), m.file


def test_every_measurement_can_be_cited():
    for m in provenance.MEASUREMENTS:
        assert m.title and m.holds and m.terms, m.file
        assert m.cite, f"{m.file} has no paper to cite"
        assert m.url.startswith("http"), m.file
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", m.retrieved), f"{m.file}: {m.retrieved}"
        assert m.used_by or m.figures, f"{m.file} is bundled but never used"


def test_every_generated_source_says_how_it_is_made():
    for g in provenance.GENERATED:
        assert g.title and g.holds and g.how, g.title
        assert g.module.startswith("cosmos."), g.title
        assert g.shown_in or g.figures, f"{g.title} is generated but never shown"


def test_the_modules_that_generate_the_data_exist():
    import importlib

    for g in provenance.GENERATED:
        importlib.import_module(g.module)


def test_every_simulator_named_is_a_simulator():
    from cosmos.gui.simulators.registry import SIMULATORS

    for m in provenance.MEASUREMENTS:
        for sim in m.used_by:
            assert sim in SIMULATORS, f"{m.file} claims {sim}"
    for g in provenance.GENERATED:
        for sim in g.shown_in:
            assert sim in SIMULATORS, f"{g.title} claims {sim}"


def test_every_lesson_named_is_a_lesson():
    """The prose says things like "the figure in L3.2"; those must exist."""
    from cosmos.content.loader import load_curriculum

    lessons = load_curriculum().lessons
    for text in [m.figures for m in provenance.MEASUREMENTS] + [g.figures for g in provenance.GENERATED]:
        for lesson_id in re.findall(r"\bL\d+\.\d+\b", text):
            assert lesson_id in lessons, lesson_id


def test_the_external_readme_lists_the_same_files():
    """The data folder travels without the app; its README must agree with us."""
    readme = (provenance.EXTERNAL_DIR / "README.md").read_text(encoding="utf-8")
    for m in provenance.MEASUREMENTS:
        if m.file.startswith("external/"):
            assert m.file.removeprefix("external/") in readme, m.file


def test_sources_for_finds_both_kinds():
    real, made = provenance.sources_for("S6")
    assert [m.file for m in real] == ["external/Rotmod_LTG.zip", "external/SPARC_Lelli2016c.mrt"]
    assert [g.title for g in made] == ["An illustrative rotation curve"]


@pytest.fixture(scope="module")
def page(qt_app, tmp_path_factory):
    from cosmos.content.loader import load_curriculum, load_glossary
    from cosmos.gui.context import AppContext, AppSignals
    from cosmos.gui.pages.reference import ReferencePage
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path_factory.mktemp("provenance") / "p.json")
    ctx = AppContext(load_curriculum(), load_glossary(), store, AppSignals())
    view = ReferencePage(ctx)
    view.refresh()
    return view


class TestTheDataTab:
    """The page that shows all this."""

    def test_it_names_every_source(self, page):
        text = page.data_view.toPlainText()
        for m in provenance.MEASUREMENTS:
            assert m.title in text, m.title
        for g in provenance.GENERATED:
            assert g.title in text, g.title

    def test_it_separates_the_real_from_the_generated(self, page):
        text = page.data_view.toPlainText()
        assert "Real measurements" in text
        assert "Data the app generates" in text
        assert text.index("Real measurements") < text.index("Data the app generates")

    def test_the_route_opens_it(self, page):
        page.tabs.setCurrentIndex(0)
        page.open_target("data")
        assert page.tabs.currentWidget() is page.data_view

    def test_the_route_still_opens_a_formula(self, page):
        first = page.formulas[0]
        page.open_target(first.id)
        assert page.tabs.currentIndex() == 0
        assert page.search.text() == first.title


def test_the_apps_own_records_are_what_they_claim_to_be():
    """The exception above is only for files the app produced itself."""
    from cosmos import validation

    assert OUR_OWN_RECORDS == {validation.RECORD.name}
    assert validation.RECORD.parent == provenance.DATA_DIR
    assert validation.read_record() is not None
