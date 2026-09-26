"""Monochrome interface icons, drawn in code.

Emoji look different on every operating system and sit on a different baseline
from the text next to them, which is what made the navigation feel unsettled.
These glyphs are drawn with the same pen on the same 24x24 grid, take the colour
of the current theme, and line up with whatever font is in use.
"""

from __future__ import annotations

from collections.abc import Sequence

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

from cosmos.gui.theme import theme

GRID = 24.0          # every glyph below is drawn inside a 24x24 square
STROKE = 1.7         # one pen width for the whole set, so nothing looks heavier
OVERSAMPLE = 4       # draw large and let Qt scale down: crisp on any display


def _stroke(painter: QPainter, color: QColor, width: float = STROKE) -> None:
    pen = QPen(color, width)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)


def _polyline(painter: QPainter, points: list[tuple[float, float]], close: bool = False) -> None:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(QPointF(*point))
    if close:
        path.closeSubpath()
    painter.drawPath(path)


def _arrow_head(painter: QPainter, color: QColor, angle: float, box: QRectF,
                length: float = 3.4, half_width: float = 2.6) -> None:
    """A solid triangle on the rim of ``box``, pointing the way the arc travels."""
    import math

    radians = math.radians(angle)
    cx, cy = box.center().x(), box.center().y()
    radius = box.width() / 2
    px, py = cx + radius * math.cos(radians), cy - radius * math.sin(radians)
    # Travelling clockwise, the tangent at this angle points here:
    dx, dy = math.sin(radians), math.cos(radians)
    nx, ny = -dy, dx
    _filled(painter, color, [
        (px + dx * length, py + dy * length),
        (px - dx * length * 0.4 + nx * half_width, py - dy * length * 0.4 + ny * half_width),
        (px - dx * length * 0.4 - nx * half_width, py - dy * length * 0.4 - ny * half_width),
    ])


def _filled(painter: QPainter, color: QColor, points: list[tuple[float, float]]) -> None:
    path = QPainterPath(QPointF(*points[0]))
    for point in points[1:]:
        path.lineTo(QPointF(*point))
    path.closeSubpath()
    painter.setPen(Qt.NoPen)
    painter.setBrush(color)
    painter.drawPath(path)


# --------------------------------------------------------------- the glyphs
def _home(p: QPainter, c: QColor) -> None:
    _stroke(p, c)
    _polyline(p, [(3.5, 11.5), (12, 4.5), (20.5, 11.5)])
    _polyline(p, [(6, 10), (6, 19.5), (18, 19.5), (18, 10)])


def _course(p: QPainter, c: QColor) -> None:
    """A closed book with a spine: the course as a whole."""
    _stroke(p, c)
    p.drawRoundedRect(QRectF(5, 4, 14, 16), 2, 2)
    p.drawLine(QPointF(8.5, 4), QPointF(8.5, 20))
    _stroke(p, c, 1.4)
    p.drawLine(QPointF(11.5, 8.5), QPointF(16.2, 8.5))
    p.drawLine(QPointF(11.5, 12), QPointF(16.2, 12))


def _glossary(p: QPainter, c: QColor) -> None:
    """An open book: look a word up."""
    _stroke(p, c)
    path = QPainterPath(QPointF(12, 7))
    path.cubicTo(QPointF(10, 5), QPointF(7, 4.6), QPointF(3.8, 5.2))
    path.lineTo(QPointF(3.8, 18))
    path.cubicTo(QPointF(7, 17.4), QPointF(10, 17.8), QPointF(12, 19.6))
    p.drawPath(path)
    path = QPainterPath(QPointF(12, 7))
    path.cubicTo(QPointF(14, 5), QPointF(17, 4.6), QPointF(20.2, 5.2))
    path.lineTo(QPointF(20.2, 18))
    path.cubicTo(QPointF(17, 17.4), QPointF(14, 17.8), QPointF(12, 19.6))
    p.drawPath(path)
    p.drawLine(QPointF(12, 7), QPointF(12, 19.6))


def _simulator(p: QPainter, c: QColor) -> None:
    """A flask: something to experiment with."""
    _stroke(p, c)
    p.drawLine(QPointF(9, 3.5), QPointF(15, 3.5))
    _polyline(p, [(10.5, 3.5), (10.5, 10), (5.6, 18.4)])
    _polyline(p, [(13.5, 3.5), (13.5, 10), (18.4, 18.4)])
    _polyline(p, [(5.6, 18.4), (6.6, 20), (17.4, 20), (18.4, 18.4)])
    p.drawLine(QPointF(8.2, 14), QPointF(15.8, 14))


def _problems(p: QPainter, c: QColor) -> None:
    """A pencil: work it out yourself."""
    _stroke(p, c)
    _polyline(p, [(4, 20), (5.4, 16.2), (15.8, 5.2), (18.8, 8.2), (8.4, 19.2)], close=True)
    p.drawLine(QPointF(5.4, 16.2), QPointF(8.4, 19.2))


def _reference(p: QPainter, c: QColor) -> None:
    """A sigma: the formula sheet."""
    _stroke(p, c)
    _polyline(p, [(17, 5), (7, 5), (13, 12), (7, 19), (17, 19)])


def _history(p: QPainter, c: QColor) -> None:
    _stroke(p, c)
    p.drawEllipse(QRectF(4, 4, 16, 16))
    _polyline(p, [(12, 7.5), (12, 12.3), (15.6, 14.4)])


def _search(p: QPainter, c: QColor) -> None:
    _stroke(p, c)
    p.drawEllipse(QRectF(4, 4, 12, 12))
    p.drawLine(QPointF(14.6, 14.6), QPointF(20, 20))


def _notes(p: QPainter, c: QColor) -> None:
    _stroke(p, c)
    _polyline(p, [(5.5, 3.5), (14, 3.5), (18.5, 8), (18.5, 20.5), (5.5, 20.5)], close=True)
    _polyline(p, [(14, 3.5), (14, 8), (18.5, 8)])
    p.drawLine(QPointF(8.5, 12.5), QPointF(15.5, 12.5))
    p.drawLine(QPointF(8.5, 16), QPointF(13.5, 16))


def _review(p: QPainter, c: QColor) -> None:
    """A circular arrow: the questions come back around."""
    _stroke(p, c)
    box = QRectF(4.5, 4.5, 15, 15)
    path = QPainterPath()
    path.arcMoveTo(box, 60)
    path.arcTo(box, 60, -280)
    p.drawPath(path)
    _arrow_head(p, c, angle=140, box=box)


def _progress(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 1.4)
    p.drawLine(QPointF(4, 20), QPointF(20, 20))
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    for x, top in ((6.0, 14.0), (10.5, 9.5), (15.0, 5.0)):
        p.drawRoundedRect(QRectF(x, top, 3.2, 18.2 - top), 1.2, 1.2)


def _classroom(p: QPainter, c: QColor) -> None:
    """A graduation cap."""
    _stroke(p, c)
    _polyline(p, [(12, 4), (21, 8.6), (12, 13.2), (3, 8.6)], close=True)
    path = QPainterPath(QPointF(7, 10.7))
    path.lineTo(QPointF(7, 16.2))
    path.quadTo(QPointF(12, 19.4), QPointF(17, 16.2))
    path.lineTo(QPointF(17, 10.7))
    p.drawPath(path)


def _back(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.0)
    _polyline(p, [(14.5, 5), (8, 12), (14.5, 19)])


def _forward(p: QPainter, c: QColor) -> None:
    _stroke(p, c, 2.0)
    _polyline(p, [(9.5, 5), (16, 12), (9.5, 19)])


def _play(p: QPainter, c: QColor) -> None:
    _filled(p, c, [(8, 4.8), (19, 12), (8, 19.2)])


def _guide(p: QPainter, c: QColor) -> None:
    """A lamp: the panel that explains the page."""
    _stroke(p, c)
    p.drawEllipse(QRectF(6.5, 3.5, 11, 11))
    _polyline(p, [(9.5, 13.2), (9.5, 16), (14.5, 16), (14.5, 13.2)])
    p.drawLine(QPointF(10.5, 19), QPointF(13.5, 19))


def _tutor(p: QPainter, c: QColor) -> None:
    """A speech bubble."""
    _stroke(p, c)
    p.drawRoundedRect(QRectF(3.5, 4.5, 17, 12), 3, 3)
    _polyline(p, [(8.5, 16.5), (8.5, 20.5), (13, 16.5)])


def _theme(p: QPainter, c: QColor) -> None:
    """A circle half filled: light and dark."""
    _stroke(p, c)
    p.drawEllipse(QRectF(4, 4, 16, 16))
    path = QPainterPath()
    path.arcMoveTo(QRectF(4, 4, 16, 16), 90)
    path.arcTo(QRectF(4, 4, 16, 16), 90, -180)
    path.closeSubpath()
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    p.drawPath(path)


def _tour(p: QPainter, c: QColor) -> None:
    """A compass needle."""
    _stroke(p, c)
    p.drawEllipse(QRectF(4, 4, 16, 16))
    _filled(p, c, [(16.6, 7.4), (13.8, 13.8), (7.4, 16.6), (10.2, 10.2)])


def _star(p: QPainter, c: QColor, fill: bool = False) -> None:
    points = []
    import math

    for index in range(10):
        angle = math.radians(-90 + index * 36)
        radius = 8.6 if index % 2 == 0 else 3.9
        points.append((12 + radius * math.cos(angle), 12 + radius * math.sin(angle)))
    if fill:
        _filled(p, c, points)
    else:
        _stroke(p, c, 1.5)
        _polyline(p, points, close=True)


def _bookmark(p: QPainter, c: QColor) -> None:
    _star(p, c, fill=False)


def _bookmarked(p: QPainter, c: QColor) -> None:
    _star(p, c, fill=True)


def _panel(p: QPainter, c: QColor) -> None:
    """A window with a side column: show or hide the navigation."""
    _stroke(p, c)
    p.drawRoundedRect(QRectF(3.5, 4.5, 17, 15), 2, 2)
    p.drawLine(QPointF(9.5, 4.5), QPointF(9.5, 19.5))


def _focus(p: QPainter, c: QColor) -> None:
    """A dashed frame: move the keyboard to the next area."""
    pen = QPen(c, 1.6)
    pen.setCapStyle(Qt.RoundCap)
    pen.setDashPattern([2.0, 2.0])
    p.setPen(pen)
    p.setBrush(Qt.NoBrush)
    p.drawRoundedRect(QRectF(4.5, 4.5, 15, 15), 2, 2)


def _constants(p: QPainter, c: QColor) -> None:
    """A balance: the measured numbers everything else is weighed against."""
    _stroke(p, c)
    p.drawLine(QPointF(4.6, 7.8), QPointF(19.4, 7.8))       # the beam
    p.drawLine(QPointF(12, 7.8), QPointF(12, 19))           # the post
    p.drawLine(QPointF(8.5, 19.5), QPointF(15.5, 19.5))     # its foot
    _stroke(p, c, 1.4)
    for x in (5.6, 18.4):
        p.drawLine(QPointF(x, 7.8), QPointF(x, 10.8))       # the cord
        bowl = QPainterPath(QPointF(x - 3.4, 10.8))         # the pan, hanging from it
        bowl.quadTo(QPointF(x, 16.4), QPointF(x + 3.4, 10.8))
        p.drawPath(bowl)


def _models(p: QPainter, c: QColor) -> None:
    """A world with a meridian and an equator: one whole universe, one set of numbers.

    A galaxy would be the obvious drawing, but a tilted ellipse with a bright middle
    reads as an eye at 16 pixels. A globe stays a globe at every size.
    """
    _stroke(p, c)
    p.drawEllipse(QRectF(3.5, 3.5, 17, 17))
    p.drawEllipse(QRectF(8.7, 3.5, 6.6, 17))
    p.drawLine(QPointF(3.6, 12), QPointF(20.4, 12))


def _data(p: QPainter, c: QColor) -> None:
    """A table: the numbers behind the figures, and where they came from."""
    _stroke(p, c)
    p.drawRoundedRect(QRectF(3.5, 5, 17, 14), 2, 2)
    p.drawLine(QPointF(3.5, 9.4), QPointF(20.5, 9.4))
    _stroke(p, c, 1.4)
    p.drawLine(QPointF(3.5, 14.2), QPointF(20.5, 14.2))
    p.drawLine(QPointF(10.6, 9.4), QPointF(10.6, 19))


def _timeline(p: QPainter, c: QColor) -> None:
    """Moments on a line: the history, in order."""
    _stroke(p, c, 1.4)
    p.drawLine(QPointF(3.0, 12), QPointF(21.0, 12))
    _stroke(p, c, 1.6)
    for x in (5.6, 12.0, 18.4):          # three moments, strung along it
        p.drawEllipse(QRectF(x - 2.2, 9.8, 4.4, 4.4))


def _people(p: QPainter, c: QColor) -> None:
    """Two figures: the people who did the work."""
    _stroke(p, c)
    p.drawEllipse(QRectF(6.0, 4.6, 6.0, 6.0))
    box = QRectF(3.6, 12.8, 10.8, 10.8)
    path = QPainterPath()
    path.arcMoveTo(box, 0)
    path.arcTo(box, 0, 180)
    p.drawPath(path)
    _stroke(p, c, 1.4)
    p.drawEllipse(QRectF(14.2, 6.8, 4.6, 4.6))
    box = QRectF(12.6, 14.2, 8.8, 8.8)
    path = QPainterPath()
    path.arcMoveTo(box, 76)
    path.arcTo(box, 76, -76)
    p.drawPath(path)


def _flashcards(p: QPainter, c: QColor) -> None:
    """A card with another behind it: the deck that brings a term back."""
    front = QRectF(4.5, 7.5, 11.5, 12.5)
    behind = QPainterPath()
    behind.addRoundedRect(QRectF(8, 4.5, 11.5, 12.5), 2, 2)
    # The back card stops where the front one covers it, rather than drawing through it.
    hole = QPainterPath()
    hole.addRoundedRect(front.adjusted(-1.3, -1.3, 1.3, 1.3), 2.8, 2.8)
    _stroke(p, c)
    p.drawPath(behind.subtracted(hole))
    p.drawRoundedRect(front, 2, 2)
    _stroke(p, c, 1.4)
    p.drawLine(QPointF(7.4, 13.8), QPointF(13.1, 13.8))      # a word on the front card


def _check(p: QPainter, c: QColor) -> None:
    """A tick: that one is done, or right."""
    _stroke(p, c, 2.0)
    _polyline(p, [(5, 12.6), (9.8, 17.4), (19, 6.8)])


def _cross(p: QPainter, c: QColor) -> None:
    """A cross: not that one, or close this."""
    _stroke(p, c, 2.0)
    p.drawLine(QPointF(6.4, 6.4), QPointF(17.6, 17.6))
    p.drawLine(QPointF(17.6, 6.4), QPointF(6.4, 17.6))


def _pause(p: QPainter, c: QColor) -> None:
    p.setPen(Qt.NoPen)
    p.setBrush(c)
    p.drawRoundedRect(QRectF(7.2, 5, 3.6, 14), 1.4, 1.4)
    p.drawRoundedRect(QRectF(13.2, 5, 3.6, 14), 1.4, 1.4)


def _telescope(p: QPainter, c: QColor) -> None:
    """A telescope on its stand: go and look."""
    p.save()
    p.translate(11.6, 9.0)
    p.rotate(-28)
    _stroke(p, c, 1.5)
    _polyline(p, [(-8.2, -2.2), (8.2, -3.5), (8.2, 3.5), (-8.2, 2.2)], close=True)
    p.drawLine(QPointF(-2.0, -2.7), QPointF(-2.0, 2.7))
    p.restore()
    _stroke(p, c, 1.5)
    p.drawLine(QPointF(11.6, 12.4), QPointF(8.0, 20.2))
    p.drawLine(QPointF(11.6, 12.4), QPointF(15.2, 20.2))


def _pin(p: QPainter, c: QColor) -> None:
    """A drawing pin: keep this one on the plot."""
    _stroke(p, c)
    p.drawLine(QPointF(8.5, 4.2), QPointF(15.5, 4.2))
    _polyline(p, [(10.2, 4.2), (10.2, 9.4), (6.6, 13.4), (17.4, 13.4), (13.8, 9.4), (13.8, 4.2)])
    p.drawLine(QPointF(12, 13.4), QPointF(12, 20))


def _export(p: QPainter, c: QColor) -> None:
    """An arrow into a tray: take it out of the app as a file."""
    _stroke(p, c)
    p.drawLine(QPointF(12, 3.8), QPointF(12, 14.4))
    _polyline(p, [(7.8, 10.4), (12, 14.8), (16.2, 10.4)])
    _polyline(p, [(4.5, 15.6), (4.5, 20), (19.5, 20), (19.5, 15.6)])


GLYPHS = {
    "home": _home,
    "course": _course,
    "glossary": _glossary,
    "simulator": _simulator,
    "problems": _problems,
    "reference": _reference,
    "history": _history,
    "search": _search,
    "notes": _notes,
    "review": _review,
    "progress": _progress,
    "classroom": _classroom,
    "back": _back,
    "forward": _forward,
    "continue": _play,
    "guide": _guide,
    "tutor": _tutor,
    "theme": _theme,
    "tour": _tour,
    "bookmark": _bookmark,
    "bookmarked": _bookmarked,
    "panel": _panel,
    "focus": _focus,
    "constants": _constants,
    "models": _models,
    "data": _data,
    "timeline": _timeline,
    "people": _people,
    "flashcards": _flashcards,
    "check": _check,
    "cross": _cross,
    "close": _cross,
    "pause": _pause,
    "telescope": _telescope,
    "pin": _pin,
    "export": _export,
    "reset": _review,          # going round again, whether it is a question or a simulation
}

_cache: dict[tuple[str, str, int], QIcon] = {}


def icon(name: str, color: str | None = None, size: int = 18) -> QIcon:
    """The named glyph, in the theme's text colour unless another is given."""
    glyph = GLYPHS.get(name)
    if glyph is None:
        return QIcon()
    color = color or theme().palette.text
    key = (name, color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    side = size * OVERSAMPLE
    pixmap = QPixmap(side, side)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.scale(side / GRID, side / GRID)
    glyph(painter, QColor(color))
    painter.end()
    built = QIcon(pixmap)
    _cache[key] = built
    return built


def text_icon(character: str, color: str | None = None, size: int = 18) -> QIcon:
    """A simulator's own symbol, drawn on the same grid and in the same colour.

    The simulators are told apart by a mathematical or geometric sign rather than a
    hand-drawn glyph. Painting the sign into an icon, instead of pasting it into a
    label, puts it on the same baseline and gives it the theme's colour.
    """
    if not character:
        return QIcon()
    color = color or theme().palette.text
    key = (f"text:{character}", color, size)
    cached = _cache.get(key)
    if cached is not None:
        return cached
    side = size * OVERSAMPLE
    pixmap = QPixmap(side, side)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setRenderHint(QPainter.TextAntialiasing)
    painter.scale(side / GRID, side / GRID)
    font = painter.font()
    font.setPixelSize(17)
    painter.setFont(font)
    painter.setPen(QColor(color))
    painter.drawText(QRectF(0, 0, GRID, GRID), Qt.AlignCenter, character)
    painter.end()
    built = QIcon(pixmap)
    _cache[key] = built
    return built


def _ink(widget) -> str | None:
    """The colour a glyph should take on this widget.

    A primary button is filled with the accent and writes its label in the accent's
    own ink, which is the opposite of the page's text colour; a glyph drawn in the
    page's colour would disappear into it.
    """
    return theme().palette.accent_text if widget.property("role") == "primary" else None


def set_glyph(widget, name: str, size: int = 18) -> None:
    """Put a glyph on a button or an action, and leave its name on the widget.

    A theme change redraws every glyph in the window by looking for that name, so
    an icon set this way follows the colours instead of staying in the old ones.
    Set the widget's ``role`` before calling this, so the glyph can match it.
    """
    widget.setProperty("glyph", name)
    widget.setProperty("glyph_size", size)
    widget.setIcon(icon(name, _ink(widget), size=size))


def set_tab_glyphs(tabs, names: Sequence[str | None], size: int = 16) -> None:
    """Icon a row of tabs in order, and leave the names on the tab widget.

    ``None`` skips a tab. As with :func:`set_glyph`, the names are what a theme
    change follows to redraw them.
    """
    tabs.setProperty("glyphs", list(names))
    tabs.setProperty("glyph_size", size)
    for index, name in enumerate(names):
        if name and index < tabs.count():
            tabs.setTabIcon(index, icon(name, size=size))


def clear_cache() -> None:
    """Forget the drawn icons, so the next theme draws its own."""
    _cache.clear()
