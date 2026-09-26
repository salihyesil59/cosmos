"""Searchable glossary."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.widgets.common import muted_label, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Glossary

All important terms of the course in one place.

- Type in the **search box** to filter by name or definition.
- Click a term to read its definition, related terms and the lessons where it
  is explained.
- Inside lessons, coloured terms open their definition directly in this Guide
  panel, so you never lose your place.
- Press **Add to my flashcards** to learn a term for good: it comes back on the
  **Review** page as a card, on the same schedule as the quiz questions you missed.
""")


class GlossaryPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.current_key: str | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.addWidget(title_label(tr("Glossary")))
        root.addWidget(muted_label(f"{len(ctx.glossary)} terms. Search, then click a term to read it."))
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Search terms…  (e.g. redshift, parsec, dark matter)"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        left.addWidget(self.search)
        self.list = QListWidget()
        self.list.setMaximumWidth(300)
        self.list.setTextElideMode(Qt.ElideRight)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for key, term in ctx.glossary.items():
            item = QListWidgetItem(term.term)
            item.setData(Qt.UserRole, key)
            item.setToolTip(term.definition)
            self.list.addItem(item)
        self.list.currentItemChanged.connect(self._show_item)
        left.addWidget(self.list, 1)
        body.addLayout(left)
        self.view = RichBrowser(font_pt=11.5)
        self.view.glossaryRequested.connect(self.select)
        self.view.lessonRequested.connect(lambda i: ctx.navigate(f"lesson:{i}"))
        self.view.simulatorRequested.connect(lambda s: ctx.navigate(f"sim:{s}"))
        right = QVBoxLayout()
        right.addWidget(self.view, 1)
        actions = QHBoxLayout()
        self.flash_btn = QPushButton()
        self.flash_btn.setToolTip(tr("Flashcards come back on the Review page: tomorrow, then after 3, 7, 16 "
                                     "and 35 days, until you know the term for good."))
        self.flash_btn.clicked.connect(self._toggle_flashcard)
        actions.addWidget(self.flash_btn)
        actions.addStretch(1)
        right.addLayout(actions)
        body.addLayout(right, 1)
        root.addLayout(body, 1)
        if self.list.count():
            self.list.setCurrentRow(0)
        ctx.signals.progressChanged.connect(self._sync_flash_button)

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    def select(self, key: str) -> None:
        for i in range(self.list.count()):
            item = self.list.item(i)
            if item.data(Qt.UserRole) == key:
                self.search.clear()
                self.list.setCurrentItem(item)
                self.list.scrollToItem(item)
                return

    def _filter(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.list.count()):
            item = self.list.item(i)
            term = self.ctx.glossary[item.data(Qt.UserRole)]
            hit = not needle or needle in term.term.lower() or needle in term.definition.lower()
            item.setHidden(not hit)

    def _show_item(self, item: QListWidgetItem | None, _prev=None) -> None:
        if item is None:
            return
        term = self.ctx.glossary[item.data(Qt.UserRole)]
        md = [f"# {term.term}", "", term.definition, ""]
        if term.see_also:
            links = ", ".join(
                f"[[{k}|{self.ctx.glossary[k].term}]]" for k in term.see_also if k in self.ctx.glossary
            )
            md += [f"**See also:** {links}", ""]
        lessons = [lid for lid in term.lessons if lid in self.ctx.curriculum.lessons]
        if lessons:
            md += ["**Explained in:**", ""]
            md += [f"- [{lid} {self.ctx.curriculum.lessons[lid].title}](lesson:{lid})" for lid in lessons]
        self.view.set_markdown_content("\n".join(md))
        self.current_key = item.data(Qt.UserRole)
        self._sync_flash_button()

    def _sync_flash_button(self) -> None:
        key = self.current_key
        inside = key is not None and self.ctx.store.has_flashcard(key)
        self.flash_btn.setText(tr("In my flashcards — remove") if inside else tr("Add to my flashcards"))
        nav_icons.set_glyph(self.flash_btn, "check" if inside else "flashcards", 16)
        self.flash_btn.setEnabled(key is not None)

    def _toggle_flashcard(self) -> None:
        key = self.current_key
        if key is None:
            return
        store = self.ctx.store
        term = self.ctx.glossary[key].term
        if store.has_flashcard(key):
            store.remove_flashcard(key)
            message = tr("“{term}” removed from your flashcards").format(term=term)
        else:
            store.add_flashcards([key])
            message = tr("“{term}” added to your flashcards: it is due today on the Review page").format(term=term)
        self._sync_flash_button()
        self.ctx.signals.statusMessage.emit(message)
        self.ctx.signals.progressChanged.emit()
