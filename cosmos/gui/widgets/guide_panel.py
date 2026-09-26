"""The Guide panel: context help for the current page and glossary look-ups."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.widgets.common import card, muted_label, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr


class GuidePanel(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.setObjectName("guidePanel")
        self.setMinimumWidth(280)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Glossary term card, hidden until a term is requested.
        self.term_card = card()
        tc = QVBoxLayout(self.term_card)
        tc.setContentsMargins(12, 10, 12, 10)
        head = QHBoxLayout()
        self.term_kicker = muted_label(tr("GLOSSARY"))
        head.addWidget(self.term_kicker)
        head.addStretch(1)
        close = QPushButton()
        nav_icons.set_glyph(close, "close", 12)
        close.setFixedWidth(30)
        close.setToolTip(tr("Hide this definition"))
        close.clicked.connect(lambda: self.term_card.hide())
        head.addWidget(close)
        tc.addLayout(head)
        self.term_title = title_label("", "subtitle")
        self.term_body = QLabel()
        self.term_body.setWordWrap(True)
        self.term_body.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.term_links = QLabel()
        self.term_links.setWordWrap(True)
        self.term_links.linkActivated.connect(self._on_link)
        open_btn = QPushButton(tr("Open in Glossary"))
        open_btn.clicked.connect(lambda: self.ctx.navigate(f"glossary:{self._term_key}"))
        tc.addWidget(self.term_title)
        tc.addWidget(self.term_body)
        tc.addWidget(self.term_links)
        tc.addWidget(open_btn, 0, Qt.AlignLeft)
        self.term_card.hide()
        self._term_key = ""
        layout.addWidget(self.term_card)

        self.browser = RichBrowser(font_pt=10.0)
        self.browser.glossaryRequested.connect(self.show_term)
        self.browser.simulatorRequested.connect(lambda s: self.ctx.navigate(f"sim:{s}"))
        self.browser.lessonRequested.connect(lambda i: self.ctx.navigate(f"lesson:{i}"))
        self.browser.routeRequested.connect(self.ctx.navigate)
        layout.addWidget(self.browser, 1)

        ctx.signals.glossaryRequested.connect(self.show_term)

    def set_context(self, markdown_text: str) -> None:
        self.browser.set_markdown_content(markdown_text)
        self.browser.scroll_to_top()

    def show_term(self, key: str) -> None:
        term = self.ctx.glossary.get(key)
        if not term:
            return
        self._term_key = key
        self.term_title.setText(term.term)
        self.term_body.setText(term.definition)
        links = []
        for other in term.see_also:
            if other in self.ctx.glossary:
                links.append(f'<a href="glossary:{other}">{self.ctx.glossary[other].term}</a>')
        lesson_links = [
            f'<a href="lesson:{lid}">{lid}</a>' for lid in term.lessons if lid in self.ctx.curriculum.lessons
        ]
        parts = []
        if links:
            parts.append(tr("See also:") + " " + ", ".join(links))
        if lesson_links:
            parts.append(tr("Lessons:") + " " + ", ".join(lesson_links))
        self.term_links.setText("<br>".join(parts))
        self.term_links.setVisible(bool(parts))
        self.term_card.show()
        # Make sure the dock is visible.
        dock = self.parentWidget()
        if dock is not None and not dock.isVisible():
            dock.show()

    def _on_link(self, link: str) -> None:
        scheme, _, target = link.partition(":")
        if scheme == "glossary":
            self.show_term(target)
        else:
            self.ctx.navigate(link)
