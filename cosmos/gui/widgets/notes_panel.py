"""Notes panel (G11): a private notebook and a bookmark button for the current page."""

from __future__ import annotations

from PySide6.QtCore import QTimer, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.routes import is_noteworthy, route_title
from cosmos.gui.widgets.common import muted_label
from cosmos.i18n import tr

SAVE_DELAY_MS = 700


class NotesPanel(QWidget):
    """Shows the note attached to the page the learner is on."""

    bookmarksChanged = Signal()

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.route = ""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.page_label = QLabel()
        self.page_label.setWordWrap(True)
        self.page_label.setProperty("role", "subtitle")
        layout.addWidget(self.page_label)

        row = QHBoxLayout()
        self.bookmark_btn = QPushButton(tr("Bookmark this page"))
        nav_icons.set_glyph(self.bookmark_btn, "bookmark", 15)
        self.bookmark_btn.setCheckable(True)
        self.bookmark_btn.setToolTip(tr("Keep a link to this page in Notes & bookmarks (Ctrl+D)."))
        self.bookmark_btn.clicked.connect(self._toggle_bookmark)
        row.addWidget(self.bookmark_btn, 1)
        layout.addLayout(row)

        self.editor = QTextEdit()
        self.editor.setObjectName("noteEditor")
        self.editor.setPlaceholderText(tr("Your notes about this page…\n\nWrite down what surprised you, a number you "
                                          "want to remember, "
            "or a question to come back to. Notes are saved automatically on this computer.")
        )
        self.editor.setAcceptRichText(False)
        self.editor.textChanged.connect(self._schedule_save)
        layout.addWidget(self.editor, 1)

        self.status = muted_label("")
        layout.addWidget(self.status)
        # "&" in a button label would become a keyboard mnemonic.
        all_notes = QPushButton(tr("All notes && bookmarks"))
        nav_icons.set_glyph(all_notes, "notes", 15)
        all_notes.setToolTip(tr("Open the page that lists every note and bookmark, and lets you export them."))
        all_notes.clicked.connect(lambda: ctx.navigate("notes"))
        layout.addWidget(all_notes)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(SAVE_DELAY_MS)
        self._timer.timeout.connect(self.save)

    # ------------------------------------------------------------------ api
    def set_route(self, route: str) -> None:
        if route == self.route:
            return
        self.save()
        self.route = route if is_noteworthy(route) else ""
        enabled = bool(self.route)
        self.editor.setEnabled(enabled)
        self.bookmark_btn.setEnabled(enabled)
        if not enabled:
            self.page_label.setText(tr("This page cannot be bookmarked."))
            self.bookmark_btn.setChecked(False)
            self.bookmark_btn.setText(tr("Bookmark this page"))
            nav_icons.set_glyph(self.bookmark_btn, "bookmark", 15)
            self.editor.blockSignals(True)
            self.editor.setPlainText("")
            self.editor.blockSignals(False)
            self.status.setText("")
            return
        self.page_label.setText(route_title(self.ctx, self.route))
        self.page_label.setToolTip(route_title(self.ctx, self.route))
        self.editor.blockSignals(True)
        self.editor.setPlainText(self.ctx.store.note(self.route))
        self.editor.blockSignals(False)
        self._refresh_bookmark()
        self.status.setText(tr("Saved automatically.") if self.ctx.store.note(self.route) else "")

    def save(self) -> None:
        self._timer.stop()
        if not self.route:
            return
        text = self.editor.toPlainText()
        self.ctx.store.set_note(self.route, text)
        self.status.setText(tr("Saved on this computer.") if text.strip() else "")

    def toggle_bookmark(self) -> None:
        if self.route:
            self.bookmark_btn.setChecked(not self.bookmark_btn.isChecked())
            self._toggle_bookmark()

    # -------------------------------------------------------------- private
    def _schedule_save(self) -> None:
        self.status.setText(tr("Saving…"))
        self._timer.start()

    def _toggle_bookmark(self) -> None:
        if not self.route:
            return
        self.ctx.store.toggle_bookmark(self.route)
        self._refresh_bookmark()
        self.bookmarksChanged.emit()

    def _refresh_bookmark(self) -> None:
        marked = self.ctx.store.is_bookmarked(self.route)
        self.bookmark_btn.setChecked(marked)
        self.bookmark_btn.setText(tr("Bookmarked") if marked else tr("Bookmark this page"))
        nav_icons.set_glyph(self.bookmark_btn, "bookmarked" if marked else "bookmark", 15)
