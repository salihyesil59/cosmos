"""Classroom page (G19): the progress report, and the teacher notes for every lesson."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cosmos import classroom
from cosmos.content.loader import load_teacher_notes
from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.widgets.common import muted_label, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Classroom

Everything the app has recorded about this learner, written out so that somebody else
can read it.

- **The report** lists lessons completed, quiz averages per level, challenges,
  problems, badges and the review deck. *Worth going over again* picks out lessons
  that were passed but only just — a 70% pass leaves a lot unlearned.
- **Teacher notes** are per-lesson: the misconception that reliably comes up, a
  discussion question with no one-line answer, and what to demonstrate. Switch
  **Classroom mode** on and they appear as a tab in every lesson, and can be printed
  with it.
- **Export** writes the report as Markdown, or as a PDF to hand in.

The report is read from this computer and written only when you ask. Nothing is
uploaded, and the app has no idea who the learner is.
""")

REPORT_LABELS = {
    "title": tr_noop("Progress report"),
    "generated": tr_noop("Generated"),
    "summary": tr_noop("Summary"),
    "lessons": tr_noop("Lessons completed"),
    "reading": tr_noop("about {minutes} minutes of reading"),
    "average": tr_noop("Average quiz score"),
    "perfect": tr_noop("perfect"),
    "challenges": tr_noop("Simulator challenges"),
    "problems": tr_noop("Worked problems"),
    "first_try": tr_noop("at the first attempt"),
    "badges": tr_noop("Badges"),
    "review": tr_noop("Review deck"),
    "waiting": tr_noop("waiting"),
    "due": tr_noop("due today"),
    "learned": tr_noop("learned for good"),
    "last": tr_noop("Last lesson completed"),
    "by_level": tr_noop("By level"),
    "level": tr_noop("Level"),
    "lessons_short": tr_noop("Lessons"),
    "average_short": tr_noop("Average quiz"),
    "attention": tr_noop("Worth going over again"),
    "shaky_intro": tr_noop("Completed, but only just. A pass at 70% leaves plenty unlearned."),
    "unopened": tr_noop("Simulators not yet opened"),
    "footer": tr_noop("Everything in this report is read from this computer only. "
                      "Nothing was uploaded."),
}

NOTE_LABELS = {
    "misconception": tr_noop("Common misconception"),
    "discussion": tr_noop("Discussion question"),
    "demonstrate": tr_noop("Show them"),
}


def report_labels() -> dict[str, str]:
    return {key: tr(text) for key, text in REPORT_LABELS.items()}


def note_labels() -> dict[str, str]:
    return {key: tr(text) for key, text in NOTE_LABELS.items()}


class ClassroomPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(title_label(tr("Classroom")))
        heading.addWidget(muted_label(
            tr("A progress report to hand on, and teacher notes for every lesson.")))
        head.addLayout(heading, 1)
        self.markdown_btn = QPushButton(tr("Export as Markdown…"))
        self.markdown_btn.clicked.connect(self.export_markdown)
        self.pdf_btn = QPushButton(tr("Export as PDF…"))
        self.pdf_btn.clicked.connect(self.export_pdf)
        for button in (self.markdown_btn, self.pdf_btn):
            nav_icons.set_glyph(button, "export", 15)
        for button in (self.markdown_btn, self.pdf_btn):
            head.addWidget(button, 0, Qt.AlignTop)
        root.addLayout(head)

        self.mode = QCheckBox(tr("Classroom mode: show teacher notes inside every lesson"))
        self.mode.setToolTip(tr("Adds a Teacher notes tab to each lesson and includes the notes when you "
                                "print it. It changes nothing about the learner's progress."))
        self.mode.toggled.connect(self._mode_changed)
        root.addWidget(self.mode)

        self.browser = RichBrowser(font_pt=10.5)
        self.browser.lessonRequested.connect(lambda i: ctx.navigate(f"lesson:{i}"))
        self.browser.simulatorRequested.connect(lambda i: ctx.navigate(f"sim:{i}"))
        root.addWidget(self.browser, 1)

    # ------------------------------------------------------------- content
    def refresh(self) -> None:
        self.mode.blockSignals(True)
        self.mode.setChecked(self.ctx.store.data.classroom)
        self.mode.blockSignals(False)
        self.browser.set_markdown_content(self.report_markdown())

    def report(self) -> classroom.Report:
        return classroom.build(self.ctx.store, self.ctx.curriculum)

    def report_markdown(self) -> str:
        return classroom.markdown(self.report(), report_labels())

    def notes_markdown(self) -> str:
        """Every teacher note, as one printable appendix."""
        notes = load_teacher_notes()
        labels = note_labels()
        parts = ["# " + tr("Teacher notes"), ""]
        for level in self.ctx.curriculum.levels:
            parts += [f"## {tr('Level')} {level.number} · {level.title}", ""]
            for lesson_id in level.lesson_ids:
                note = notes.get(lesson_id)
                if note is None:
                    continue
                lesson = self.ctx.curriculum.lessons[lesson_id]
                parts += [f"### {lesson_id} · {lesson.title}", "", note.markdown(labels), ""]
        return "\n".join(parts)

    # ------------------------------------------------------------ handlers
    def _mode_changed(self, on: bool) -> None:
        self.ctx.store.data.classroom = bool(on)
        self.ctx.store.save()
        self.ctx.signals.progressChanged.emit()

    def export_markdown(self) -> None:
        path, _filter = QFileDialog.getSaveFileName(
            self, tr("Save the report"), "cosmos_progress_report.md", "Markdown (*.md)")
        if not path:
            return
        text = self.report_markdown()
        if self.ctx.store.data.classroom:
            text += "\n\n" + self.notes_markdown()
        try:
            Path(path).write_text(text, encoding="utf-8")
        except OSError as error:
            QMessageBox.warning(self, tr("Could not save the report"), str(error))
            return
        self.ctx.signals.statusMessage.emit(tr("Saved the report to {path}").format(path=path))

    def export_pdf(self) -> None:
        from cosmos.gui.rendering import pdf

        path, _filter = QFileDialog.getSaveFileName(
            self, tr("Save the report"), "cosmos_progress_report.pdf", "PDF (*.pdf)")
        if not path:
            return
        text = self.report_markdown()
        if self.ctx.store.data.classroom:
            text += "\n\n" + self.notes_markdown()
        options = pdf.PdfOptions(title=tr("Cosmos"), subtitle=tr("Progress report"))
        try:
            pages = pdf.export(path, text, options)
        except OSError as error:
            QMessageBox.warning(self, tr("Could not save the report"), str(error))
            return
        self.ctx.signals.statusMessage.emit(
            tr("Saved {pages} page(s) to {path}").format(pages=pages, path=path))

    def guide_markdown(self) -> str:
        return tr(GUIDE)
