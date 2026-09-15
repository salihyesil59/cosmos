"""Searchable glossary."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from cosmos.gui.context import AppContext
from cosmos.gui.widgets.common import muted_label, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser

GUIDE = """
## Glossary

All important terms of the course in one place.

- Type in the **search box** to filter by name or definition.
- Click a term to read its definition, related terms and the lessons where it
  is explained.
- Inside lessons, coloured terms open their definition directly in this Guide
  panel, so you never lose your place.
"""


class GlossaryPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.addWidget(title_label("Glossary"))
        root.addWidget(muted_label(f"{len(ctx.glossary)} terms. Search, then click a term to read it."))
        body = QHBoxLayout()
        left = QVBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search terms…  (e.g. redshift, parsec, dark matter)")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._filter)
        left.addWidget(self.search)
        self.list = QListWidget()
        self.list.setMaximumWidth(300)
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
        body.addWidget(self.view, 1)
        root.addLayout(body, 1)
        if self.list.count():
            self.list.setCurrentRow(0)

    def guide_markdown(self) -> str:
        return GUIDE

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
