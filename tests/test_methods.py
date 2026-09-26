"""V3: every simulator says how it works out the number it is showing.

A learner moving a slider and reading an answer cannot tell a textbook formula
from a fit, or an exact calculation from a teaching model good to fifteen per
cent. These tests insist that each simulator answers the three questions a
careful reader would ask — what is computed, whose method it follows, what it
leaves out — and that the formulas it names really are on the formula sheet.
"""

from __future__ import annotations

import pytest

from cosmos.gui.simulators.registry import SIMULATORS, Method


@pytest.fixture(scope="module")
def formulas():
    from cosmos.content.loader import load_formulas

    return {f.id: f for f in load_formulas()}


def catalogue() -> list:
    """Every simulator that ships with the app; plugins are somebody else's."""
    return [info for info in SIMULATORS.values() if not info.is_plugin]


def test_every_simulator_explains_itself():
    missing = [info.id for info in catalogue() if info.method is None]
    assert not missing, "no method note: " + ", ".join(missing)


def test_a_note_answers_all_three_questions():
    for info in catalogue():
        method = info.method
        assert isinstance(method, Method), info.id
        assert len(method.summary) > 80, f"{info.id}: the summary says too little"
        assert method.approximations, (
            f"{info.id}: nothing listed under what it leaves out. Every one of these is an "
            "approximation of something; if it really is exact, say that in the summary.")
        for line in (method.summary, *method.approximations, method.reference):
            assert line == line.strip(), f"{info.id}: stray whitespace in {line[:40]!r}"


def test_the_formulas_named_are_on_the_formula_sheet(formulas):
    """A note that cites an equation the app cannot show is worse than no note."""
    unknown = [(info.id, fid) for info in catalogue()
               for fid in (info.method.formulas if info.method else ())
               if fid not in formulas]
    assert not unknown, "formulas that do not exist: " + ", ".join(f"{s}:{f}" for s, f in unknown)


def test_the_simulators_doing_real_physics_cite_something():
    """Not every simulator has a paper behind it, but most should.

    Powers of Ten is arithmetic and the balloon is a metaphor; the ones fitting
    data or solving equations are following somebody, and should say who.
    """
    citing = [info.id for info in catalogue() if info.method and info.method.reference]
    assert len(citing) >= 20, f"only {len(citing)} of {len(catalogue())} name a reference"


def test_a_teaching_model_admits_it():
    """The three that are furthest from a research calculation must say so."""
    wording = {
        "S12": "teaching model",
        "S13": "two dimensions",
        "S23": "lognormal",
    }
    for sim_id, expected in wording.items():
        method = SIMULATORS[sim_id].method
        everything = " ".join([method.summary, *method.approximations]).lower()
        assert expected in everything, f"{sim_id} does not mention {expected!r}"


@pytest.fixture(scope="module")
def page(qt_app, tmp_path_factory):
    from cosmos.content.loader import load_curriculum, load_glossary
    from cosmos.gui.context import AppContext, AppSignals
    from cosmos.gui.pages.simulators import SimulatorHostPage
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path_factory.mktemp("methods") / "p.json")
    ctx = AppContext(load_curriculum(), load_glossary(), store, AppSignals())
    return SimulatorHostPage(ctx, SIMULATORS["S16"])


class TestThePage:
    """What the learner actually sees."""

    def test_the_guide_carries_the_method(self, page):
        guide = page.guide_markdown()
        assert "How this is computed" in guide
        assert "teaching fit" in guide
        assert "Follows:" in guide
        assert "What it leaves out" in guide

    def test_the_named_formulas_are_rendered_not_just_named(self, page):
        guide = page.guide_markdown()
        # Each one appears as display maths the panel can typeset.
        assert guide.count("$$") >= 2 * len(SIMULATORS["S16"].method.formulas)

    def test_the_method_comes_before_the_instructions(self, page):
        """It answers "what am I looking at", which comes before "how do I drive it"."""
        guide = page.guide_markdown()
        assert guide.index("How this is computed") < guide.index("How to use")

    def test_the_button_asks_for_the_guide_panel(self, page, qt_app):
        seen = []
        page.ctx.signals.guideRequested.connect(lambda: seen.append(True))
        page._show_method()
        assert seen == [True]

    def test_it_points_at_the_validation_table(self, page):
        """V3 and V4 are the same promise at two scales; the note links them."""
        assert "reference:data" in page.guide_markdown()


def test_a_simulator_without_a_note_still_builds(qt_app, tmp_path_factory):
    """A plugin nobody documented must not break the page it lives on."""
    import dataclasses

    from cosmos.content.loader import load_curriculum, load_glossary
    from cosmos.gui.context import AppContext, AppSignals
    from cosmos.gui.pages.simulators import SimulatorHostPage
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path_factory.mktemp("nomethod") / "p.json")
    ctx = AppContext(load_curriculum(), load_glossary(), store, AppSignals())
    bare = dataclasses.replace(SIMULATORS["S3"], method=None)
    page = SimulatorHostPage(ctx, bare)
    guide = page.guide_markdown()
    assert "How this is computed" not in guide
    assert "How to use" in guide
    page._show_method()          # harmless, and must not raise
