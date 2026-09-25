"""Notes & bookmarks page (G11): everything the learner saved, in one list."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.context import AppContext
from cosmos.gui.routes import route_icon, route_title
from cosmos.gui.widgets.common import card, centred, muted_label, title_label
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Notes & bookmarks

Everything you saved while working through the course.

- **Bookmarks** are pages you marked with the ☆ button in the Notes panel (or
  Ctrl+D). Click one to go straight back to it.
- **Notes** are your own words, one note per page. Open the page and edit the
  note in the Notes panel on the right.
- **Export** writes all of it into a single Markdown file you can keep or print.

Notes live on this computer only, in the same file as your progress. Nothing is
uploaded anywhere.
""")


class NotesPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(8)
        head = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(title_label(tr("Notes & bookmarks")))
        self.subtitle = muted_label("")
        heading.addWidget(self.subtitle)
        head.addLayout(heading, 1)
        self.export_btn = QPushButton(tr("⬇  Export as Markdown…"))
        self.export_btn.setToolTip(tr("Save every bookmark and note into one text file."))
        self.export_btn.clicked.connect(self.export)
        head.addWidget(self.export_btn, 0, Qt.AlignTop)
        root.addLayout(head)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        host = QWidget()
        self.body = QVBoxLayout(host)
        self.body.setContentsMargins(0, 0, 8, 0)
        self.body.setSpacing(10)
        scroll.setWidget(centred(host))
        root.addWidget(scroll, 1)
        self.refresh()

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    # ------------------------------------------------------------------ api
    def refresh(self) -> None:
        while self.body.count():
            widget = self.body.takeAt(0).widget()
            if widget is not None:
                # Unparent at once: deleteLater alone would leave the old cards on screen.
                # Hide first, or the parentless widget is briefly a window of its own and
                # can steal the keyboard focus.
                widget.hide()
                widget.setParent(None)
                widget.deleteLater()
        store = self.ctx.store
        bookmarks, notes = list(store.data.bookmarks), dict(store.data.notes)
        self.subtitle.setText(tr("{bookmarks} bookmarks · {notes} notes")
                              .format(bookmarks=len(bookmarks), notes=len(notes)))
        self.export_btn.setEnabled(bool(bookmarks or notes))

        self.body.addWidget(title_label(tr("Bookmarks"), "subtitle"))
        if not bookmarks:
            self.body.addWidget(muted_label(tr("No bookmarks yet. Open any lesson or simulator and press ☆ in the "
                                               "Notes panel (Ctrl+D).")))
        for route in bookmarks:
            self.body.addWidget(self._bookmark_card(route))

        self.body.addWidget(title_label(tr("Notes"), "subtitle"))
        if not notes:
            self.body.addWidget(muted_label(tr("No notes yet. The Notes panel on the right of every page is your "
                                               "private notebook.")))
        for route, text in notes.items():
            self.body.addWidget(self._note_card(route, text))
        self.body.addStretch(1)

    def export(self) -> None:
        store = self.ctx.store
        if not (store.data.bookmarks or store.data.notes):
            return
        suggestion = str(Path.home() / "cosmos-notes.md")
        path, _ = QFileDialog.getSaveFileName(self, tr("Export notes"), suggestion,
                                          tr("Markdown (*.md);;Text (*.txt)"))
        if not path:
            return
        try:
            Path(path).write_text(self.as_markdown(), encoding="utf-8")
        except OSError as exc:
            QMessageBox.warning(self, tr("Export failed"),
                               tr("The file could not be written:") + f"\n{exc}")
            return
        self.subtitle.setText(tr("Exported to {path}").format(path=path))

    def as_markdown(self) -> str:
        store = self.ctx.store
        lines = ["# Cosmos — my notes", "", f"Exported {datetime.now():%Y-%m-%d %H:%M}", ""]
        if store.data.bookmarks:
            lines += ["## Bookmarks", ""]
            lines += [f"- {route_title(self.ctx, r)}" for r in store.data.bookmarks]
            lines.append("")
        if store.data.notes:
            lines += ["## Notes", ""]
            for route, text in store.data.notes.items():
                lines += [f"### {route_title(self.ctx, route)}", "", text.strip(), ""]
        return "\n".join(lines)

    # -------------------------------------------------------------- private
    def _row(self, route: str, extra: QWidget | None = None) -> QWidget:
        frame = card()
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        top = QHBoxLayout()
        mark = QLabel()
        mark.setPixmap(route_icon(self.ctx, route).pixmap(16, 16))
        top.addWidget(mark, 0, Qt.AlignTop)
        label = QLabel(route_title(self.ctx, route))
        label.setWordWrap(True)
        top.addWidget(label, 1)
        open_btn = QPushButton(tr("Open"))
        open_btn.clicked.connect(lambda _=False, r=route: self.ctx.navigate(r))
        top.addWidget(open_btn)
        layout.addLayout(top)
        if extra is not None:
            layout.addWidget(extra)
        frame.layout_top = top
        return frame

    def _bookmark_card(self, route: str) -> QWidget:
        frame = self._row(route)
        remove = QPushButton(tr("Remove"))
        remove.setToolTip(tr("Remove this bookmark. Your note for the page is kept."))
        remove.clicked.connect(lambda _=False, r=route: self._remove_bookmark(r))
        frame.layout_top.addWidget(remove)
        return frame

    def _note_card(self, route: str, text: str) -> QWidget:
        preview = QLabel(text if len(text) < 600 else text[:600] + " …")
        preview.setWordWrap(True)
        preview.setProperty("role", "muted")
        frame = self._row(route, preview)
        delete = QPushButton(tr("Delete note"))
        delete.clicked.connect(lambda _=False, r=route: self._delete_note(r))
        frame.layout_top.addWidget(delete)
        return frame

    def _remove_bookmark(self, route: str) -> None:
        self.ctx.store.remove_bookmark(route)
        self.refresh()
        self.ctx.signals.notesChanged.emit()

    def _delete_note(self, route: str) -> None:
        confirm = QMessageBox.question(
            self, tr("Delete note"),
            tr("Delete your note for {page}?").format(page=route_title(self.ctx, route)))
        if confirm is QMessageBox.Yes:
            self.ctx.store.set_note(route, "")
            self.refresh()
            self.ctx.signals.notesChanged.emit()
