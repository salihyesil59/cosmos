"""Guidance features: intuitive view (G7), challenges (G8), history (G12), badges (G13)."""

import os

import pytest

from cosmos.achievements import ACHIEVEMENTS, BY_ID
from cosmos.content.loader import load_challenges, load_curriculum, load_history
from cosmos.gui.challenges import challenge_met, condition_met, unmet_fields
from cosmos.progress import ProgressStore

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

CURRICULUM = load_curriculum()
CHALLENGES = load_challenges()
EVENTS, SCIENTISTS = load_history()


# ----------------------------------------------------------------- G8 content
def test_challenge_content_is_well_formed():
    from cosmos.gui.simulators.registry import SIMULATORS

    assert CHALLENGES and set(CHALLENGES) <= set(SIMULATORS)
    seen = set()
    for simulator, steps in CHALLENGES.items():
        assert steps, f"{simulator} has no challenges"
        for step in steps:
            assert step.key not in seen
            seen.add(step.key)
            assert step.task and step.hint and step.success
            assert step.check, f"{step.key} has nothing to check"
            for condition in step.check:
                assert "field" in condition
                assert set(condition) <= {"field", "min", "max", "equals", "contains", "is_true", "is_false"}


def test_condition_evaluation():
    state = {"z": 1090.0, "preset": "planck18", "fate": "big crunch", "halo": False}
    assert condition_met({"field": "z", "min": 1000, "max": 1200}, state)
    assert not condition_met({"field": "z", "min": 1200}, state)
    assert condition_met({"field": "preset", "equals": "Planck18"}, state)      # case-insensitive
    assert condition_met({"field": "fate", "contains": "crunch"}, state)
    assert condition_met({"field": "halo", "is_false": True}, state)
    assert not condition_met({"field": "halo", "is_true": True}, state)
    assert not condition_met({"field": "missing", "min": 1}, state)             # unknown field never passes
    with pytest.raises(ValueError):
        condition_met({"field": "z", "wobble": 3}, state)
    challenge = CHALLENGES["S1"][0]
    assert not challenge_met(challenge, {"z": 0, "preset": "eds"})
    assert "z" in unmet_fields(challenge, {"z": 0, "preset": "planck18"})


# --------------------------------------------------------------- G12 content
def test_history_content():
    assert len(EVENTS) > 25 and len(SCIENTISTS) > 10
    assert [e.year for e in EVENTS] == sorted(e.year for e in EVENTS)
    for event in EVENTS:
        assert 1500 < event.year <= 2030
        assert event.kind in ("idea", "theory", "observation", "problem")
        assert event.lesson is None or event.lesson in CURRICULUM.lessons
        assert event.title and event.who and event.description
    for scientist in SCIENTISTS:
        assert scientist.contribution and scientist.story
        for lesson in scientist.lessons:
            assert lesson in CURRICULUM.lessons, f"{scientist.name}: unknown lesson {lesson}"
    kinds = {e.kind for e in EVENTS}
    assert kinds == {"idea", "theory", "observation", "problem"}


# ------------------------------------------------------------------ G13 rules
def test_achievements_unlock_in_order(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    assert store.refresh_achievements(CURRICULUM) == []
    assert not any(a.is_earned(store, CURRICULUM) for a in ACHIEVEMENTS)

    store.record_quiz(CURRICULUM.ordered_ids[0], 1.0)
    new = store.refresh_achievements(CURRICULUM)
    assert {"first-steps", "perfect-quiz"} <= set(new)
    assert store.refresh_achievements(CURRICULUM) == []          # only once

    store.record_challenge("S1", "cmb-age")
    assert "challenger" in store.refresh_achievements(CURRICULUM)
    for route in ("lesson:L1.1", "lesson:L1.2", "sim:S1"):
        store.set_note(route, "note")
    assert "note-taker" in store.refresh_achievements(CURRICULUM)

    for lesson_id in CURRICULUM.levels[0].lesson_ids:
        store.record_quiz(lesson_id, 1.0)
    assert "level-clear" in store.refresh_achievements(CURRICULUM)

    for lesson_id in CURRICULUM.ordered_ids:
        store.record_quiz(lesson_id, 1.0)
    earned = set(store.data.achievements) | set(store.refresh_achievements(CURRICULUM))
    assert {"graduate", "all-levels", "advanced", "halfway", "five-perfect"} <= earned
    assert BY_ID["graduate"].state(store, CURRICULUM) == (len(CURRICULUM.lessons), len(CURRICULUM.lessons))


def test_reset_keeps_the_learners_own_writing(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    store.record_quiz("L0.1", 1.0)
    store.set_note("lesson:L0.1", "mine")
    store.toggle_bookmark("sim:S1")
    store.record_challenge("S1", "cmb-age")
    store.refresh_achievements(CURRICULUM)
    store.reset()
    assert store.data.notes == {"lesson:L0.1": "mine"}
    assert store.data.bookmarks == ["sim:S1"]
    assert store.data.completed == {} and store.data.challenges_done == [] and store.data.achievements == {}


# ------------------------------------------------------------------- G7 views
@pytest.mark.parametrize("lesson_id", ["L2.1", "L2.3", "L4.3", "L6.3"])
def test_intuitive_view_hides_the_mathematics(lesson_id):
    from PySide6.QtWidgets import QApplication

    from cosmos.gui.rendering.lesson_html import FULL_VIEW, INTUITIVE_VIEW, RenderContext, render_markdown
    from cosmos.gui.theme import THEMES

    QApplication.instance() or QApplication([])
    body = CURRICULUM.lessons[lesson_id].body
    full = render_markdown(body, RenderContext(palette=THEMES["dark"], math_view=FULL_VIEW))
    plain = render_markdown(body, RenderContext(palette=THEMES["dark"], math_view=INTUITIVE_VIEW))
    assert full.hidden_formulas == 0 and full.hidden_blocks == 0
    assert plain.hidden_formulas > 0
    assert len(plain.images) < len(full.images)
    assert "<p>" in plain.html                                   # there is still a lesson to read
