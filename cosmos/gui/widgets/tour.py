"""Guided tour: dims the window and highlights one widget at a time."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QEvent, QRect, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cosmos.gui.theme import theme


@dataclass
class TourStep:
    title: str
    text: str
    target: Callable[[], QWidget | None] | None = None
    before: Callable[[], None] | None = None  # e.g. navigate to a page first


class TourOverlay(QWidget):
    finished = Signal()

    def __init__(self, host: QWidget, steps: list[TourStep]):
        super().__init__(host)
        self.host = host
        self.steps = steps
        self.index = 0
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFocusPolicy(Qt.StrongFocus)

        self.bubble = QFrame(self)
        self.bubble.setProperty("card", True)
        self.bubble.setFixedWidth(360)
        bl = QVBoxLayout(self.bubble)
        bl.setContentsMargins(16, 14, 16, 12)
        self.counter = QLabel()
        self.counter.setProperty("role", "muted")
        self.title = QLabel()
        self.title.setProperty("role", "subtitle")
        self.title.setWordWrap(True)
        self.body = QLabel()
        self.body.setWordWrap(True)
        self.body.setTextFormat(Qt.RichText)
        bl.addWidget(self.counter)
        bl.addWidget(self.title)
        bl.addWidget(self.body)
        buttons = QHBoxLayout()
        self.skip = QPushButton("Skip tour")
        self.back = QPushButton("Back")
        self.next = QPushButton("Next")
        self.next.setProperty("role", "primary")
        buttons.addWidget(self.skip)
        buttons.addStretch(1)
        buttons.addWidget(self.back)
        buttons.addWidget(self.next)
        bl.addLayout(buttons)
        self.skip.clicked.connect(self.close_tour)
        self.back.clicked.connect(lambda: self.go(self.index - 1))
        self.next.clicked.connect(lambda: self.go(self.index + 1))

        host.installEventFilter(self)

    def start(self) -> None:
        self.setGeometry(self.host.rect())
        self.show()
        self.raise_()
        self.go(0)
        self.setFocus()

    def go(self, index: int) -> None:
        if index >= len(self.steps):
            self.close_tour()
            return
        self.index = max(0, index)
        step = self.steps[self.index]
        if step.before:
            step.before()
        self.counter.setText(f"Step {self.index + 1} of {len(self.steps)}")
        self.title.setText(step.title)
        self.body.setText(step.text)
        self.back.setEnabled(self.index > 0)
        self.next.setText("Finish" if self.index == len(self.steps) - 1 else "Next")
        self.bubble.adjustSize()
        self._place_bubble()
        self.update()

    def close_tour(self) -> None:
        self.host.removeEventFilter(self)
        self.hide()
        self.finished.emit()
        self.deleteLater()

    # ----------------------------------------------------------- geometry
    def _target_rect(self) -> QRect | None:
        step = self.steps[self.index]
        widget = step.target() if step.target else None
        if widget is None or not widget.isVisible():
            return None
        top_left = widget.mapTo(self.host, widget.rect().topLeft())
        return QRect(top_left, widget.size()).adjusted(-6, -6, 6, 6)

    def _place_bubble(self) -> None:
        rect = self._target_rect()
        bw, bh = self.bubble.width(), self.bubble.sizeHint().height()
        W, H = self.width(), self.height()
        if rect is None:
            x, y = (W - bw) // 2, (H - bh) // 2
        elif rect.right() + 16 + bw < W:
            x, y = rect.right() + 16, rect.top()
        elif rect.left() - 16 - bw > 0:
            x, y = rect.left() - 16 - bw, rect.top()
        elif rect.bottom() + 16 + bh < H:
            x, y = rect.left(), rect.bottom() + 16
        else:
            x, y = rect.left(), rect.top() - 16 - bh
        x = min(max(12, x), W - bw - 12)
        y = min(max(12, y), H - bh - 12)
        self.bubble.setGeometry(x, y, bw, bh)

    def eventFilter(self, obj, event):  # noqa: N802 (Qt override)
        if obj is self.host and event.type() == QEvent.Resize:
            self.setGeometry(self.host.rect())
            self._place_bubble()
        return False

    def paintEvent(self, _event):  # noqa: N802 (Qt override)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        rect = self._target_rect()
        if rect is not None:
            hole = QPainterPath()
            hole.addRoundedRect(QRectF(rect), 8, 8)
            path = path.subtracted(hole)
        painter.fillPath(path, QColor(0, 0, 0, 150))
        if rect is not None:
            pen = QPen(QColor(theme().palette.accent), 2.5)
            painter.setPen(pen)
            painter.drawRoundedRect(QRectF(rect), 8, 8)

    def mousePressEvent(self, event):  # noqa: N802 (Qt override)
        event.accept()  # block clicks on the dimmed window

    def keyPressEvent(self, event):  # noqa: N802 (Qt override)
        if event.key() == Qt.Key_Escape:
            self.close_tour()
        elif event.key() in (Qt.Key_Right, Qt.Key_Return, Qt.Key_Enter):
            self.go(self.index + 1)
        elif event.key() == Qt.Key_Left:
            self.go(self.index - 1)
