"""Integrity checks for lessons, quizzes, glossary and their cross-references."""

import re

import pytest

from cosmos.content.loader import load_curriculum, load_glossary

CURRICULUM = load_curriculum()
GLOSSARY = load_glossary()
LESSON_IDS = list(CURRICULUM.lessons)
from cosmos.gui.simulators.registry import SIMULATORS  # noqa: E402

SIMULATOR_IDS = set(SIMULATORS)


def test_every_level_has_lessons():
    assert [lv.number for lv in CURRICULUM.levels] == list(range(len(CURRICULUM.levels)))
    assert all(lv.lesson_ids for lv in CURRICULUM.levels)


@pytest.mark.parametrize("lesson_id", LESSON_IDS)
def test_prerequisites_exist_and_come_earlier(lesson_id):
    order = CURRICULUM.ordered_ids
    for pre in CURRICULUM.lessons[lesson_id].prerequisites:
        assert pre in CURRICULUM.lessons, f"{lesson_id}: unknown prerequisite {pre}"
        assert order.index(pre) < order.index(lesson_id), f"{lesson_id}: prerequisite {pre} comes later"


@pytest.mark.parametrize("lesson_id", LESSON_IDS)
def test_quiz_is_well_formed(lesson_id):
    quiz = CURRICULUM.lessons[lesson_id].quiz
    assert len(quiz) >= 4, f"{lesson_id} needs at least 4 quiz questions"
    for q in quiz:
        assert len(q.choices) >= 3
        assert 0 <= q.answer < len(q.choices)
        assert len(set(q.choices)) == len(q.choices)
        assert q.explanation


@pytest.mark.parametrize("lesson_id", LESSON_IDS)
def test_lesson_links_resolve(lesson_id):
    lesson = CURRICULUM.lessons[lesson_id]
    body = lesson.body
    for key in re.findall(r"\[\[([\w-]+)", body):
        assert key in GLOSSARY, f"{lesson_id}: unknown glossary term {key}"
    for target in re.findall(r"\(lesson:([\w.]+)\)", body):
        assert target in CURRICULUM.lessons, f"{lesson_id}: unknown lesson link {target}"
    for sim in re.findall(r"^:::try\s+(S\d+)", body, flags=re.MULTILINE):
        assert sim in SIMULATOR_IDS
    for sim in lesson.simulators:
        assert sim in SIMULATOR_IDS


def test_glossary_cross_references():
    for key, term in GLOSSARY.items():
        for other in term.see_also:
            assert other in GLOSSARY, f"{key}: unknown see_also {other}"
        for lesson in term.lessons:
            assert lesson in CURRICULUM.lessons, f"{key}: unknown lesson {lesson}"


@pytest.mark.parametrize("lesson_id", LESSON_IDS)
def test_formulas_render(lesson_id):
    from cosmos.gui.rendering import math as mathrender
    from cosmos.gui.rendering.lesson_html import _DISPLAY_MATH, _INLINE_MATH

    body = CURRICULUM.lessons[lesson_id].body
    formulas = [m.group(1) for m in _DISPLAY_MATH.finditer(body)]
    body = _DISPLAY_MATH.sub("", body)
    formulas += [m.group(1) for m in _INLINE_MATH.finditer(body)]
    for tex in formulas:
        mathrender.validate(" ".join(tex.split()))


def test_figures_exist():
    from cosmos.gui.rendering import figures

    names = set()
    for lesson in CURRICULUM.lessons.values():
        names.update(re.findall(r"\{\{figure:(\w+)\}\}", lesson.body))
    assert names <= set(figures.available())


def test_objectives_are_plain_text():
    for lesson in CURRICULUM.lessons.values():
        for objective in lesson.objectives:
            # A colon in an unquoted YAML list item silently becomes a mapping.
            assert isinstance(objective, str), f"{lesson.id}: objective {objective!r} is not text"


def test_formula_sheet_is_valid():
    from cosmos.content.loader import load_formulas
    from cosmos.gui.rendering import math as mathrender

    formulas = load_formulas()
    assert len(formulas) > 40
    ids = [f.id for f in formulas]
    assert len(ids) == len(set(ids))
    for f in formulas:
        assert f.title and f.group and f.description
        mathrender.validate(f.formula)
        for tex in re.findall(r"\$([^$]+)\$", f.symbols + " " + f.description):
            mathrender.validate(tex)
        assert f.lesson is None or f.lesson in CURRICULUM.lessons, f"{f.id}: unknown lesson {f.lesson}"
    # Every level of the course should be represented somewhere on the sheet.
    covered = {CURRICULUM.lessons[f.lesson].level for f in formulas if f.lesson}
    assert covered >= {0, 1, 2, 3, 4, 5, 6}


def test_every_lesson_ends_with_something_to_remember():
    """G24: the closing Summary / What to remember section becomes the lesson's card."""
    for lesson in CURRICULUM.lessons.values():
        points = lesson.remember
        assert len(points) >= 3, f"{lesson.id} needs a closing summary with at least three points"
        assert all(len(point) > 10 for point in points), lesson.id


@pytest.mark.parametrize("lesson_id", LESSON_IDS)
def test_no_stray_callout_markers(lesson_id):
    """A ':::' left over (for example after a one-line ':::try') would show up as text."""
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtGui import QGuiApplication

    from cosmos.gui.rendering.lesson_html import RenderContext, render_markdown
    from cosmos.gui.theme import LIGHT

    QGuiApplication.instance() or QGuiApplication([])
    body = CURRICULUM.lessons[lesson_id].body
    html = render_markdown(body.replace("{{figure:", "{{nofigure:"), RenderContext(palette=LIGHT)).html
    assert ":::" not in html, f"{lesson_id} has a stray ':::' marker"
