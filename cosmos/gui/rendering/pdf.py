"""Printing lessons and reports to PDF (G18).

The app already turns lesson Markdown into rich text for the reader; the same
renderer produces the pages here, with three differences that matter on paper:

* the **light palette**, whatever the learner is using on screen, because nobody
  wants to print a black page;
* a **page break before every lesson**, so a handout can be stapled per lesson;
* a footer with the page number and the course name.

Only QtGui is needed — ``QPdfWriter`` is not part of the print-support module — so
this adds nothing to what the packaged app already ships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from PySide6.QtCore import QMarginsF, QRectF, QSizeF, Qt, QUrl
from PySide6.QtGui import (
    QImage,
    QPageLayout,
    QPageSize,
    QPainter,
    QPdfWriter,
    QTextBlockFormat,
    QTextCursor,
    QTextDocument,
)

from cosmos.content.models import Lesson
from cosmos.gui.rendering.lesson_html import FULL_VIEW, RenderContext, render_markdown, stylesheet
from cosmos.gui.theme import LIGHT
from cosmos.i18n import tr

RESOLUTION = 150                      # dots per inch; enough for figures, small enough to email
MARGIN_MM = 16.0
FOOTER_MM = 8.0


@dataclass
class PdfOptions:
    """What goes on the paper."""

    title: str = "Cosmos"
    subtitle: str = ""
    math_view: str = FULL_VIEW
    include_quiz: bool = True
    include_objectives: bool = True
    teacher_notes: dict[str, str] = field(default_factory=dict)   # lesson id -> Markdown (G19)
    font_pt: float = 10.5


# ------------------------------------------------------------------ content
def lesson_markdown(lesson: Lesson, options: PdfOptions) -> str:
    """One lesson as Markdown, with the extras a printed copy wants."""
    parts = [f"# {lesson.id} · {lesson.title}", "", f"*{lesson.summary}*", ""]
    if options.include_objectives and lesson.objectives:
        parts += ["### " + tr("What you will learn"), ""]
        parts += [f"- {line}" for line in lesson.objectives]
        parts.append("")
    parts.append(lesson.body)
    if options.include_quiz and lesson.quiz:
        parts += ["", "---", "", "### " + tr("Quiz"), ""]
        for number, question in enumerate(lesson.quiz, start=1):
            parts.append(f"**{number}. {question.prompt}**")
            parts.append("")
            for index, choice in enumerate(question.choices):
                parts.append(f"- {chr(ord('a') + index)}) {choice}")
            parts.append("")
        parts += ["### " + tr("Answers"), ""]
        for number, question in enumerate(lesson.quiz, start=1):
            letter = chr(ord("a") + question.answer)
            parts.append(f"{number}. **{letter})** {question.explanation}")
        parts.append("")
    notes = options.teacher_notes.get(lesson.id)
    if notes:
        parts += ["", "---", "", "### " + tr("Teacher notes"), "", notes, ""]
    return "\n".join(parts)


def course_markdown(lessons: list[Lesson], options: PdfOptions) -> str:
    """Several lessons, each starting on its own page."""
    return "\n\n".join(lesson_markdown(lesson, options) for lesson in lessons)


# -------------------------------------------------------------- the document
def build_document(markdown: str, options: PdfOptions, width_px: float) -> QTextDocument:
    """A paginated QTextDocument in the light palette, with its figures attached."""
    from cosmos.content.loader import load_glossary
    from cosmos.gui.simulators.registry import SIMULATORS

    ctx = RenderContext(
        palette=LIGHT,
        font_pt=options.font_pt,
        device_ratio=1.0,
        simulator_titles={key: info.title for key, info in SIMULATORS.items()},
        glossary_terms={key: term.definition for key, term in load_glossary().items()},
        math_view=options.math_view,
    )
    rendered = render_markdown(markdown, ctx)

    doc = QTextDocument()
    doc.setDefaultStyleSheet(stylesheet(LIGHT, options.font_pt))
    doc.setDocumentMargin(0)
    for url, png in rendered.images.items():
        image = QImage.fromData(png, "PNG")
        doc.addResource(QTextDocument.ImageResource, QUrl(url), image)
    doc.setHtml(rendered.html)
    doc.setTextWidth(width_px)
    _break_pages_before_lessons(doc)
    return doc


def _break_pages_before_lessons(doc: QTextDocument) -> None:
    """Start every top-level heading on a fresh page, except the very first."""
    cursor = QTextCursor(doc)
    block = doc.begin()
    first = True
    while block.isValid():
        if block.blockFormat().headingLevel() == 1:
            if not first:
                cursor.setPosition(block.position())
                fmt = QTextBlockFormat(block.blockFormat())
                fmt.setPageBreakPolicy(QTextBlockFormat.PageBreak_AlwaysBefore)
                cursor.setBlockFormat(fmt)
            first = False
        block = block.next()


def _writer(path: Path, options: PdfOptions) -> QPdfWriter:
    writer = QPdfWriter(str(path))
    writer.setResolution(RESOLUTION)
    writer.setTitle(options.title)
    writer.setCreator("Cosmos")
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(MARGIN_MM, MARGIN_MM, MARGIN_MM, MARGIN_MM + FOOTER_MM),
                          QPageLayout.Millimeter)
    return writer


def export(path: str | Path, markdown: str, options: PdfOptions) -> int:
    """Write the Markdown to ``path`` as a PDF. Returns the number of pages."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    writer = _writer(target, options)
    body = QRectF(writer.pageLayout().paintRectPixels(writer.resolution()))
    doc = build_document(markdown, options, body.width())
    doc.setPageSize(QSizeF(body.width(), body.height()))
    pages = max(doc.pageCount(), 1)

    painter = QPainter(writer)
    footer = _footer_text(options)
    for page in range(pages):
        if page:
            writer.newPage()
        painter.save()
        painter.translate(0, -page * body.height())
        doc.drawContents(painter, QRectF(0, page * body.height(), body.width(), body.height()))
        painter.restore()
        _draw_footer(painter, body, footer, page + 1, pages)
    painter.end()
    return pages


def _footer_text(options: PdfOptions) -> str:
    stamp = date.today().isoformat()
    return f"{options.title} — {options.subtitle} — {stamp}" if options.subtitle \
        else f"{options.title} — {stamp}"


def _draw_footer(painter: QPainter, body: QRectF, text: str, page: int, pages: int) -> None:
    painter.save()
    painter.setPen(Qt.gray)
    font = painter.font()
    font.setPointSizeF(7.5)
    painter.setFont(font)
    strip = QRectF(0, body.height() + RESOLUTION * FOOTER_MM / 25.4 * 0.3, body.width(),
                   RESOLUTION * FOOTER_MM / 25.4)
    painter.drawText(strip, Qt.AlignLeft | Qt.AlignVCenter, text)
    painter.drawText(strip, Qt.AlignRight | Qt.AlignVCenter, f"{page} / {pages}")
    painter.restore()
