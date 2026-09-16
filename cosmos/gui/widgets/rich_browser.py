"""A QTextBrowser that renders lesson Markdown with formulas and app links."""

from __future__ import annotations

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QCursor, QDesktopServices, QImage, QTextDocument
from PySide6.QtWidgets import QTextBrowser, QToolTip

from cosmos.content.loader import load_glossary
from cosmos.gui.rendering.lesson_html import RenderContext, render_markdown, stylesheet
from cosmos.gui.theme import theme


class RichBrowser(QTextBrowser):
    """Displays Markdown content and turns app links into signals.

    Link schemes: ``glossary:key``, ``sim:S1``, ``lesson:L1.2``, ``route:...``;
    ``http(s)`` links open in the system browser.
    """

    glossaryRequested = Signal(str)
    simulatorRequested = Signal(str)
    lessonRequested = Signal(str)
    routeRequested = Signal(str)

    def __init__(self, parent=None, font_pt: float = 11.0):
        super().__init__(parent)
        self._font_pt = font_pt
        self._math_view = "full"
        self.document_info = None      # the last RenderedDocument, for callers that need its counts
        self._markdown = ""
        self._images: dict[str, QImage] = {}
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self._on_anchor)
        self.highlighted.connect(self._on_hover)
        theme().changed.connect(lambda _p: self._rerender())

    # ------------------------------------------------------------ content
    def set_math_view(self, mode: str) -> None:
        """Switch between the full and the intuitive (formula-free) rendering."""
        if mode != self._math_view:
            self._math_view = mode
            self._rerender()

    def set_markdown_content(self, text: str) -> None:
        self._markdown = text
        self._rerender()

    def _rerender(self) -> None:
        from cosmos.gui.simulators.registry import SIMULATORS

        p = theme().palette
        glossary = load_glossary()
        ctx = RenderContext(
            palette=p,
            font_pt=self._font_pt,
            device_ratio=max(1.0, self.devicePixelRatioF()),
            simulator_titles={k: v.title for k, v in SIMULATORS.items()},
            glossary_terms={k: v.definition for k, v in glossary.items()},
            math_view=self._math_view,
        )
        doc = render_markdown(self._markdown, ctx)
        self.document_info = doc
        self._images = {}
        for url, png in doc.images.items():
            img = QImage.fromData(png, "PNG")
            img.setDevicePixelRatio(ctx.device_ratio)
            self._images[url] = img
        scroll = self.verticalScrollBar().value()
        self.document().setDefaultStyleSheet(stylesheet(p, self._font_pt))
        self.document().setDocumentMargin(18)
        self.setHtml(doc.html)
        self.verticalScrollBar().setValue(scroll)

    def loadResource(self, kind: int, url: QUrl):  # noqa: N802 (Qt override)
        key = url.toString()
        if kind == QTextDocument.ImageResource and key in self._images:
            return self._images[key]
        return super().loadResource(kind, url)

    def scroll_to_end(self) -> None:
        bar = self.verticalScrollBar()
        bar.setValue(bar.maximum())

    def scroll_to_top(self) -> None:
        self.verticalScrollBar().setValue(0)

    # -------------------------------------------------------------- links
    def _on_anchor(self, url: QUrl) -> None:
        scheme, _, target = url.toString().partition(":")
        if scheme == "glossary":
            self.glossaryRequested.emit(target)
        elif scheme == "sim":
            self.simulatorRequested.emit(target)
        elif scheme == "lesson":
            self.lessonRequested.emit(target)
        elif scheme == "route":
            self.routeRequested.emit(target)
        elif scheme in ("http", "https"):
            QDesktopServices.openUrl(url)

    def _on_hover(self, url: QUrl) -> None:
        text = url.toString()
        if text.startswith("glossary:"):
            term = load_glossary().get(text.partition(":")[2])
            if term:
                QToolTip.showText(
                    QCursor.pos(),
                    f"<b>{term.term}</b><br>{term.definition}<br><i>Click to open in the Guide panel.</i>",
                    self,
                )
                return
        elif text.startswith("sim:"):
            self.viewport().setToolTip("Open this simulator")
            return
        QToolTip.hideText()
