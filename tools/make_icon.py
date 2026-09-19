"""Draw the application icon and write it out for every platform.

Run it after changing the design::

    python tools/make_icon.py

It writes two files into ``cosmos/gui/resources``: a multi-size ``cosmos.ico`` for
Windows and the packaged executable, and a 512-pixel ``cosmos.png`` that Linux
desktop entries use and that ``tools/build_app.py`` turns into a macOS ``.icns``.
"""

from __future__ import annotations

import io
import math
import sys
from pathlib import Path

from PIL import Image
from PySide6.QtCore import QBuffer, QByteArray, QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QImage, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "cosmos" / "gui" / "resources"
TARGET = RESOURCES / "cosmos.ico"
PNG = RESOURCES / "cosmos.png"      # Linux .desktop icon, and the source for macOS .icns
SIZES = [16, 24, 32, 48, 64, 128, 256]

BACKGROUND = "#0b1020"
RING = "#6ea8fe"
CORE = "#f5b35c"
STAR = "#e6e9f2"


def draw(size: int = 512) -> QImage:
    image = QImage(size, size, QImage.Format_ARGB32)
    image.fill(Qt.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    s = size / 512

    # Deep-space disc.
    sky = QRadialGradient(QPointF(size * 0.42, size * 0.38), size * 0.62)
    sky.setColorAt(0.0, QColor("#1b2340"))
    sky.setColorAt(1.0, QColor(BACKGROUND))
    painter.setBrush(QBrush(sky))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(QRectF(0, 0, size, size))

    # Scattered stars.
    painter.setBrush(QColor(STAR))
    for fx, fy, fr in [(0.18, 0.22, 4), (0.78, 0.18, 3), (0.86, 0.62, 4),
                       (0.24, 0.78, 3), (0.62, 0.86, 3), (0.12, 0.52, 2.5)]:
        painter.drawEllipse(QPointF(fx * size, fy * size), fr * s * 2, fr * s * 2)

    # An orbit, drawn as a flattened ellipse, and the glowing core.
    painter.save()
    painter.translate(size / 2, size / 2)
    painter.rotate(-24)
    pen = QPen(QColor(RING), 14 * s)
    painter.setPen(pen)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(-size * 0.36, -size * 0.17, size * 0.72, size * 0.34))
    painter.restore()

    glow = QRadialGradient(QPointF(size / 2, size / 2), size * 0.2)
    glow.setColorAt(0.0, QColor(CORE))
    glow.setColorAt(0.6, QColor(CORE).darker(140))
    glow.setColorAt(1.0, QColor(0, 0, 0, 0))
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(glow))
    painter.drawEllipse(QPointF(size / 2, size / 2), size * 0.2, size * 0.2)

    # A small planet riding the orbit.
    angle = math.radians(-24)
    px = size / 2 + math.cos(angle) * size * 0.36
    py = size / 2 + math.sin(angle) * size * 0.36 * 0.47
    painter.setBrush(QColor(STAR))
    painter.drawEllipse(QPointF(px, py), 16 * s, 16 * s)
    painter.end()
    return image


def main() -> int:
    QApplication(sys.argv)
    qbytes = QByteArray()
    buffer = QBuffer(qbytes)
    buffer.open(QBuffer.WriteOnly)
    draw().save(buffer, "PNG")                      # Qt draws, Pillow packs the sizes into one .ico
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(io.BytesIO(bytes(qbytes.data()))) as pil:
        pil.save(TARGET, format="ICO", sizes=[(s, s) for s in SIZES])
        pil.save(PNG, format="PNG")
    for path in (TARGET, PNG):
        print(f"wrote {path} ({path.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
