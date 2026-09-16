"""Search page (G10): one box that looks through the whole course."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from cosmos.gui.context import AppContext
from cosmos.gui.search import KIND_COUNTS, KIND_LABELS, search
from cosmos.gui.widgets.common import muted_label, title_label
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Search

One box for the whole course: lesson text, glossary definitions, simulators and
the formula sheet.

- Type at least two letters. Results are ranked, with the best match first.
- The small label on the left of each result says what it is: a **lesson**, a
  glossary **term**, a **simulator** or a **formula**.
- Press **Enter** or click a result to open it.
- Searching for a lesson id such as `L4.3` finds the lesson and everything that
  refers to it.

The toolbar search box (Ctrl+F) always brings you back here.
""")


class SearchPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.hits = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.addWidget(title_label(tr("Search")))
        root.addWidget(muted_label(tr("Lessons, glossary terms, simulators and formulas.")))
        self.box = QLineEdit()
        self.box.setObjectName("searchPageBox")
        self.box.setPlaceholderText(tr("What are you looking for?  (e.g. dark energy, horizon, L4.3, Friedmann)"))
        self.box.setClearButtonEnabled(True)
        self.box.textChanged.connect(self._update)
        self.box.returnPressed.connect(self._open_first)
        root.addWidget(self.box)
        self.count = muted_label("")
        root.addWidget(self.count)
        self.list = QListWidget()
        self.list.setObjectName("searchResults")
        self.list.setWordWrap(True)
        self.list.setSpacing(2)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemActivated.connect(self._open_item)
        self.list.itemClicked.connect(self._open_item)
        root.addWidget(self.list, 1)

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    # ------------------------------------------------------------------ api
    def set_query(self, text: str) -> None:
        if text != self.box.text():
            self.box.setText(text)
        else:
            self._update()
        self.box.setFocus()
        self.box.selectAll()

    def _update(self, *_args) -> None:
        query = self.box.text()
        self.hits = search(self.ctx, query)
        self.list.clear()
        if len(query.strip()) < 2:
            self.count.setText(tr("Type at least two letters."))
            return
        kinds = {k: sum(1 for h in self.hits if h.kind == k) for k in KIND_LABELS}
        summary = ", ".join(tr(KIND_COUNTS[k][0] if n == 1 else KIND_COUNTS[k][1]).format(n=n)
                            for k, n in kinds.items() if n)
        self.count.setText(tr("{count} results — {summary}").format(count=len(self.hits), summary=summary)
                           if self.hits else tr("Nothing found. Try a shorter or more common word."))
        for hit in self.hits:
            item = QListWidgetItem(f"{hit.icon}  {hit.title}\n      {hit.label} · {hit.subtitle}\n      {hit.snippet}")
            item.setData(Qt.UserRole, hit.route)
            item.setToolTip(tr("Open {route}").format(route=hit.route))
            self.list.addItem(item)
        if self.hits:
            self.list.setCurrentRow(0)

    def _open_first(self) -> None:
        if self.hits:
            self.ctx.navigate(self.hits[0].route)

    def _open_item(self, item: QListWidgetItem) -> None:
        route = item.data(Qt.UserRole)
        if route:
            self.ctx.navigate(route)


class SearchBox(QLineEdit):
    """The toolbar search field; Enter opens the Search page with the query."""

    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setObjectName("toolbarSearch")
        self.setPlaceholderText(tr("Search the course…  (Ctrl+F)"))
        self.setClearButtonEnabled(True)
        self.setMaximumWidth(280)
        self.setToolTip(tr("Search lessons, glossary, simulators and formulas. Press Enter for all results."))
        self.returnPressed.connect(self._go)

    def _go(self) -> None:
        text = self.text().strip()
        if text:
            self.ctx.navigate(f"search:{text}")
