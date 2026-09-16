"""Global search (G10) and notes/bookmarks (G11)."""

import pytest

from cosmos.content.loader import load_curriculum, load_glossary
from cosmos.gui.context import AppContext, AppSignals
from cosmos.gui.routes import is_noteworthy, route_title
from cosmos.gui.search import search
from cosmos.progress import ProgressStore


@pytest.fixture
def ctx(tmp_path):
    return AppContext(load_curriculum(), load_glossary(), ProgressStore(tmp_path / "p.json"), AppSignals())


def routes(hits):
    return [h.route for h in hits]


def test_search_finds_lessons_and_terms(ctx):
    assert search(ctx, "a") == []                                   # too short to be useful
    hits = search(ctx, "dark energy")
    assert "lesson:L3.3" in routes(hits)
    assert any(h.kind == "glossary" for h in hits)
    assert all(h.score > 0 for h in hits)
    assert routes(search(ctx, "L4.3"))[0] == "lesson:L4.3"          # an id search is exact
    assert {"glossary:olbers-paradox", "lesson:L0.6", "sim:S17"} <= set(routes(search(ctx, "Olbers"))[:4])


def test_search_covers_every_source(ctx):
    kinds = {h.kind for q in ("horizon", "helium", "lensing", "Friedmann") for h in search(ctx, q)}
    assert kinds == {"lesson", "glossary", "simulator", "formula"}
    formula_hits = [h for h in search(ctx, "Friedmann") if h.kind == "formula"]
    assert formula_hits and formula_hits[0].route.startswith("reference:")


def test_search_snippets_are_plain_text(ctx):
    for hit in search(ctx, "recombination"):
        assert "{{" not in hit.snippet and "[[" not in hit.snippet and ":::" not in hit.snippet
        assert len(hit.snippet) < 300


def test_notes_and_bookmarks_round_trip(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    assert store.note("lesson:L1.1") == ""
    store.set_note("lesson:L1.1", "  parsec = 3.26 ly  ")
    assert store.note("lesson:L1.1") == "parsec = 3.26 ly"
    assert store.toggle_bookmark("sim:S10") is True
    assert store.is_bookmarked("sim:S10")
    reloaded = ProgressStore(tmp_path / "p.json")
    assert reloaded.note("lesson:L1.1") == "parsec = 3.26 ly"
    assert reloaded.data.bookmarks == ["sim:S10"]
    assert reloaded.toggle_bookmark("sim:S10") is False
    reloaded.set_note("lesson:L1.1", "   ")
    assert "lesson:L1.1" not in reloaded.data.notes
    reloaded.remove_bookmark("nothing:here")            # removing an unknown route is harmless


def test_route_titles(ctx):
    assert route_title(ctx, "lesson:L4.3").endswith("Big Bang Nucleosynthesis")
    assert "Interactive Cosmic Timeline" in route_title(ctx, "sim:S10")
    assert "glossary" in route_title(ctx, "glossary:redshift")
    assert route_title(ctx, "reference") == "∑  Reference"
    assert route_title(ctx, "lesson:L9.9") == "•  lesson:L9.9"      # deleted lesson still shows something
    assert is_noteworthy("lesson:L1.1") and not is_noteworthy("search:abc")
