"""Printing to PDF (G18) and classroom mode (G19)."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from cosmos import classroom  # noqa: E402
from cosmos.content.loader import load_curriculum, load_teacher_notes  # noqa: E402
from cosmos.progress import ProgressStore  # noqa: E402

CURRICULUM = load_curriculum()


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def store(tmp_path):
    return ProgressStore(tmp_path / "p.json")


# ------------------------------------------------------------ teacher notes
def test_every_lesson_has_a_teacher_note():
    notes = load_teacher_notes()
    assert set(notes) == set(CURRICULUM.lessons), "a lesson without notes, or a note without a lesson"
    for lesson_id, note in notes.items():
        assert note.lesson == lesson_id
        for field in (note.misconception, note.discussion, note.demonstrate):
            assert len(field) > 60, lesson_id          # a real note, not a placeholder
            assert "\n" not in field                    # the loader folds the YAML block


def test_a_note_renders_as_markdown():
    note = load_teacher_notes()["L5.7"]
    text = note.markdown()
    assert text.count("**") == 6                        # three bold labels
    assert "Common misconception" in text and "Show them" in text
    assert note.misconception in text
    custom = note.markdown({"misconception": "A", "discussion": "B", "demonstrate": "C"})
    assert custom.startswith("**A.** ")


def test_the_notes_say_something_specific():
    """A note that could be pasted into any lesson is not worth printing."""
    notes = load_teacher_notes()
    # Every misconception must be unique; they are the point of the exercise.
    texts = [n.misconception for n in notes.values()]
    assert len(set(texts)) == len(texts)
    # Most notes should point at a simulator by name.
    named = sum(1 for n in notes.values() if any(f"S{i}" in n.demonstrate for i in range(1, 24)))
    assert named > 0.7 * len(notes)


# ------------------------------------------------------------- the report
def test_an_empty_report_is_still_readable(store):
    report = classroom.build(store, CURRICULUM, date(2026, 6, 1))
    assert report.lessons_done == 0 and report.fraction == 0.0
    assert report.average_score is None
    assert report.lessons_total == len(CURRICULUM.lessons)
    assert len(report.levels) == len(CURRICULUM.levels)
    assert report.unopened_simulators                   # nothing opened yet
    text = classroom.markdown(report)
    assert "Progress report" in text and "2026-06-01" in text
    assert "—" in text                                  # no average to show
    assert "Worth going over again" not in text         # nothing completed, nothing shaky


def test_a_report_counts_what_the_learner_did(store):
    ids = CURRICULUM.ordered_ids
    store.record_quiz(ids[0], 0.72)                     # a bare pass
    store.record_quiz(ids[1], 1.0)                      # perfect
    store.record_quiz(ids[2], 0.5)                      # failed, not completed
    store.record_challenge("S1", "cmb-age")
    store.record_problem_attempt("p0-proxima", True)
    store.mark_opened("sim", "S1")

    report = classroom.build(store, CURRICULUM, date(2026, 6, 1))
    assert report.lessons_done == 2
    assert report.perfect_quizzes == 1
    assert report.average_score == pytest.approx((0.72 + 1.0 + 0.5) / 3)
    assert report.challenges_done == 1 and report.challenges_total > 30
    assert report.problems_solved == 1 and report.first_try_problems == 1
    assert report.minutes_of_lessons > 0
    assert "S1" not in report.unopened_simulators

    # The bare pass is flagged; the perfect one is not, and the failure is not completed.
    flagged = [lesson_id for lesson_id, _title, _score in report.shaky]
    assert flagged == [ids[0]]

    text = classroom.markdown(report)
    assert "2 / " in text and "Worth going over again" in text
    assert ids[0] in text and ids[1] not in text.split("Worth going over again")[1]


def test_the_report_has_a_row_for_every_level(store):
    report = classroom.build(store, CURRICULUM, date(2026, 6, 1))
    text = classroom.markdown(report)
    for level in CURRICULUM.levels:
        assert f"| {level.number} · {level.title} |" in text
    assert text.count("|---|---|---|") == 1


def test_report_labels_can_be_translated(store):
    report = classroom.build(store, CURRICULUM, date(2026, 6, 1))
    text = classroom.markdown(report, {"title": "Rapor", "summary": "Özet",
                                       "reading": "{minutes} dakika"})
    assert text.startswith("# Rapor")
    assert "## Özet" in text
    assert "dakika" in text


def test_the_review_deck_reaches_the_report(store):
    store.record_question("L0.1", 0, False, date(2026, 6, 1))
    report = classroom.build(store, CURRICULUM, date(2026, 6, 2))
    assert report.review_total == 1 and report.review_due == 1
    assert "Review deck" in classroom.markdown(report)


# -------------------------------------------------------------- printing
def test_a_lesson_prints_to_pdf(app, tmp_path):
    from cosmos.gui.rendering import pdf

    lesson = CURRICULUM.lessons["L5.7"]
    options = pdf.PdfOptions(title="Cosmos", subtitle=lesson.title)
    markdown = pdf.lesson_markdown(lesson, options)
    assert lesson.title in markdown and lesson.summary in markdown
    assert "### Quiz" in markdown and "### Answers" in markdown
    assert all(objective in markdown for objective in lesson.objectives)

    target = tmp_path / "lesson.pdf"
    pages = pdf.export(target, markdown, options)
    assert pages >= 3
    data = target.read_bytes()
    assert data.startswith(b"%PDF")
    assert len(data) > 50_000                            # the figures really are embedded


def test_the_quiz_and_objectives_can_be_left_out(app, tmp_path):
    from cosmos.gui.rendering import pdf

    lesson = CURRICULUM.lessons["L0.1"]
    plain = pdf.lesson_markdown(lesson, pdf.PdfOptions(include_quiz=False, include_objectives=False))
    assert "### Quiz" not in plain
    assert lesson.objectives[0] not in plain
    assert lesson.body in plain


def test_teacher_notes_go_onto_the_paper(app):
    from cosmos.gui.rendering import pdf

    lesson = CURRICULUM.lessons["L7.6"]
    note = load_teacher_notes()["L7.6"]
    options = pdf.PdfOptions(teacher_notes={"L7.6": note.markdown()})
    text = pdf.lesson_markdown(lesson, options)
    assert "Teacher notes" in text and note.discussion in text
    # Without the option, nothing of the sort appears.
    assert "Teacher notes" not in pdf.lesson_markdown(lesson, pdf.PdfOptions())


def test_a_level_prints_with_one_page_break_per_lesson(app, tmp_path):
    from PySide6.QtGui import QTextBlockFormat

    from cosmos.gui.rendering import pdf

    level = CURRICULUM.levels[0]
    lessons = [CURRICULUM.lessons[i] for i in level.lesson_ids]
    options = pdf.PdfOptions(title="Cosmos", subtitle=level.title)
    markdown = pdf.course_markdown(lessons, options)
    doc = pdf.build_document(markdown, options, 800.0)

    breaks, headings = 0, 0
    block = doc.begin()
    while block.isValid():
        if block.blockFormat().headingLevel() == 1:
            headings += 1
            if block.blockFormat().pageBreakPolicy() == QTextBlockFormat.PageBreak_AlwaysBefore:
                breaks += 1
        block = block.next()
    assert headings == len(lessons)
    assert breaks == len(lessons) - 1, "every lesson but the first starts on a fresh page"

    pages = pdf.export(tmp_path / "level.pdf", markdown, options)
    assert pages >= len(lessons)


def test_the_pdf_is_printed_in_the_light_palette(app):
    from cosmos.gui.rendering import pdf
    from cosmos.gui.theme import LIGHT, theme

    theme().set_theme("contrast")
    try:
        doc = pdf.build_document("# Title\n\nSome text.", pdf.PdfOptions(), 600.0)
        sheet = doc.defaultStyleSheet()
        assert LIGHT.text in sheet and LIGHT.accent in sheet
        assert "#ffffff" not in sheet.split("body")[1][:60]     # not the dark-on-black scheme
    finally:
        theme().set_theme("dark")
