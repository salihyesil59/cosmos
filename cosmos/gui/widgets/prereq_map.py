"""A map of all lessons, their prerequisites and the learner's status."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene, QGraphicsView

from cosmos.gui.context import AppContext
from cosmos.gui.theme import theme
from cosmos.progress import LessonStatus

NODE_W, NODE_H = 210, 58
COL_GAP, ROW_GAP = 70, 18
HEADER_H = 50


class LessonNode(QGraphicsItem):
    def __init__(self, lesson_id: str, title: str, status: LessonStatus, on_click):
        super().__init__()
        self.lesson_id, self.title, self.status, self.on_click = lesson_id, title, status, on_click
        self.hover = False
        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"{lesson_id} — {title}\nStatus: {status.value}\nClick to open the lesson.")

    def boundingRect(self):  # noqa: N802
        return QRectF(0, 0, NODE_W, NODE_H)

    def paint(self, painter: QPainter, _option, _widget=None):
        p = theme().palette
        color = {
            LessonStatus.COMPLETED: p.success,
            LessonStatus.READY: p.accent,
            LessonStatus.NOT_READY: p.muted,
        }[self.status]
        painter.setRenderHint(QPainter.Antialiasing)
        fill = QColor(p.mix(color, 0.28 if self.hover else 0.14))
        painter.setBrush(QBrush(fill))
        painter.setPen(QPen(QColor(color), 2 if self.status is not LessonStatus.NOT_READY else 1))
        painter.drawRoundedRect(self.boundingRect().adjusted(1, 1, -1, -1), 9, 9)
        painter.setPen(QColor(color))
        f = QFont()
        f.setPointSizeF(8.5)
        f.setBold(True)
        painter.setFont(f)
        mark = {"completed": "✓ ", "ready": "● ", "not ready": "○ "}[self.status.value]
        painter.drawText(QRectF(10, 6, NODE_W - 20, 16), Qt.AlignLeft, mark + self.lesson_id)
        painter.setPen(QColor(p.text))
        f.setBold(False)
        f.setPointSizeF(9)
        painter.setFont(f)
        painter.drawText(QRectF(10, 22, NODE_W - 20, 32), Qt.AlignLeft | Qt.TextWordWrap, self.title)

    def hoverEnterEvent(self, _e):  # noqa: N802
        self.hover = True
        self.update()

    def hoverLeaveEvent(self, _e):  # noqa: N802
        self.hover = False
        self.update()

    def mousePressEvent(self, _e):  # noqa: N802
        self.on_click(self.lesson_id)


class PrerequisiteMap(QGraphicsView):
    lessonClicked = Signal(str)

    def __init__(self, ctx: AppContext, parent=None):
        super().__init__(parent)
        self.ctx = ctx
        self.setScene(QGraphicsScene(self))
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setMinimumHeight(360)
        theme().changed.connect(lambda _p: self.rebuild())
        ctx.signals.progressChanged.connect(self.rebuild)
        self.rebuild()

    def rebuild(self) -> None:
        p = theme().palette
        scene = self.scene()
        scene.clear()
        self.setBackgroundBrush(QColor(p.surface))
        cur, store = self.ctx.curriculum, self.ctx.store
        positions: dict[str, QPointF] = {}
        for col, level in enumerate(cur.levels):
            x = col * (NODE_W + COL_GAP)
            header = scene.addText(f"Level {level.number}\n{level.title}")
            header.setDefaultTextColor(QColor(p.accent))
            f = QFont()
            f.setBold(True)
            header.setFont(f)
            header.setTextWidth(NODE_W)
            header.setPos(x, 0)
            for row, lesson_id in enumerate(level.lesson_ids):
                y = HEADER_H + row * (NODE_H + ROW_GAP)
                node = LessonNode(
                    lesson_id, cur.lessons[lesson_id].title, store.status(cur, lesson_id), self.lessonClicked.emit
                )
                node.setPos(x, y)
                node.setZValue(2)
                scene.addItem(node)
                positions[lesson_id] = QPointF(x, y)

        for lesson_id, lesson in cur.lessons.items():
            end = positions[lesson_id]
            for pre in lesson.prerequisites:
                if pre not in positions:
                    continue
                start = positions[pre]
                done = store.is_completed(pre)
                pen = QPen(QColor(p.success if done else p.border), 1.6)
                if not done:
                    pen.setStyle(Qt.DashLine)
                path = QPainterPath()
                if start.x() == end.x():  # same level: route along the left side
                    a = QPointF(start.x(), start.y() + NODE_H / 2)
                    b = QPointF(end.x(), end.y() + NODE_H / 2)
                    path.moveTo(a)
                    path.cubicTo(a - QPointF(28, 0), b - QPointF(28, 0), b)
                else:
                    a = QPointF(start.x() + NODE_W, start.y() + NODE_H / 2)
                    b = QPointF(end.x(), end.y() + NODE_H / 2)
                    mid = (a.x() + b.x()) / 2
                    path.moveTo(a)
                    path.cubicTo(QPointF(mid, a.y()), QPointF(mid, b.y()), b)
                item = scene.addPath(path, pen)
                item.setZValue(1)
        scene.setSceneRect(scene.itemsBoundingRect().adjusted(-40, -10, 20, 20))
