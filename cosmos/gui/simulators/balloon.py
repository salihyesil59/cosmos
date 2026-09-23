"""S7 — Balloon & Raisin-Bread Expansion."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import ParameterSlider
from cosmos.i18n import tr

A_START, A_END = 1.0, 3.0
N_GALAXIES = 40
GRID = 8


class ExpansionCanvas(QWidget):
    homeChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMouseTracking(True)
        self.setToolTip(tr("Click a galaxy to stand on it."))
        rng = random.Random(7)
        # Comoving positions in units of grid cells, centred on the origin.
        self.galaxies = [
            (rng.uniform(-GRID / 2, GRID / 2), rng.uniform(-GRID / 2, GRID / 2), rng.choice([0, 1, 2, 4, 5]))
            for _ in range(N_GALAXIES)
        ]
        self.galaxies[0] = (0.0, 0.0, 1)
        self.home = 0
        self.a = A_START
        self.show_grid = True
        self.show_arrows = True
        theme().changed.connect(lambda _p: self.update())

    def _cell_px(self) -> float:
        return min(self.width(), self.height()) / (GRID * A_END) * 0.95

    def _screen(self, x: float, y: float) -> QPointF:
        hx, hy, _ = self.galaxies[self.home]
        s = self._cell_px() * self.a
        return QPointF(self.width() / 2 + (x - hx) * s, self.height() / 2 + (y - hy) * s)

    def mousePressEvent(self, event):  # noqa: N802
        pos = event.position()
        best, best_d = None, 18.0
        for i, (x, y, _c) in enumerate(self.galaxies):
            pt = self._screen(x, y)
            d = math.hypot(pt.x() - pos.x(), pt.y() - pos.y())
            if d < best_d:
                best, best_d = i, d
        if best is not None:
            self.home = best
            self.homeChanged.emit(best)
            self.update()

    def paintEvent(self, _event):  # noqa: N802
        p = theme().palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#070a12"))
        s = self._cell_px() * self.a
        hx, hy, _ = self.galaxies[self.home]

        if self.show_grid:
            painter.setPen(QPen(QColor(110, 168, 254, 45), 1))
            for k in range(-GRID // 2, GRID // 2 + 1):
                a = self._screen(k, -GRID / 2)
                b = self._screen(k, GRID / 2)
                painter.drawLine(a, b)
                a = self._screen(-GRID / 2, k)
                b = self._screen(GRID / 2, k)
                painter.drawLine(a, b)

        if self.show_arrows:
            # Recession velocity v = H d, drawn with a fixed H so arrow length ∝ distance.
            pen = QPen(QColor(p.accent2), 1.4)
            painter.setPen(pen)
            for i, (x, y, _c) in enumerate(self.galaxies):
                if i == self.home:
                    continue
                start = self._screen(x, y)
                dx, dy = (x - hx) * s, (y - hy) * s
                end = QPointF(start.x() + dx * 0.25, start.y() + dy * 0.25)
                painter.drawLine(start, end)
                ang = math.atan2(end.y() - start.y(), end.x() - start.x())
                head = QPainterPath()
                head.moveTo(end)
                head.lineTo(end.x() - 7 * math.cos(ang - 0.4), end.y() - 7 * math.sin(ang - 0.4))
                head.moveTo(end)
                head.lineTo(end.x() - 7 * math.cos(ang + 0.4), end.y() - 7 * math.sin(ang + 0.4))
                painter.drawPath(head)

        font = QFont()
        font.setPointSizeF(8.5)
        painter.setFont(font)
        for i, (x, y, c) in enumerate(self.galaxies):
            pt = self._screen(x, y)
            color = QColor(p.series[c % 6])
            radius = 5.5
            if i == self.home:
                painter.setPen(QPen(QColor("#ffffff"), 2))
                painter.setBrush(QColor(p.success))
                painter.drawEllipse(pt, radius + 3, radius + 3)
                painter.drawText(QPointF(pt.x() + 12, pt.y() - 8), "You are here")
            else:
                painter.setPen(Qt.NoPen)
                painter.setBrush(color)
                painter.drawEllipse(pt, radius, radius * 0.6)

        painter.setPen(QColor("#e6e9f2"))
        painter.drawText(QRectF(12, 8, 400, 20), Qt.AlignLeft, f"Scale factor a = {self.a:.2f}")


class LightWave(QWidget):
    """A strip showing a light wave whose wavelength grows with the scale factor."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(90)
        self.a_emit: float | None = None
        self.a = A_START
        theme().changed.connect(lambda _p: self.update())

    def paintEvent(self, _event):  # noqa: N802
        p = theme().palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(p.surface))
        painter.setPen(QColor(p.muted))
        if self.a_emit is None:
            painter.drawText(self.rect(), Qt.AlignCenter, "Press “Emit light” to send a light wave and watch it stretch.")
            return
        stretch = self.a / self.a_emit
        z = stretch - 1
        wavelength = 28 * stretch
        mid = self.height() / 2 + 8
        path = QPainterPath()
        path.moveTo(0, mid)
        for x in range(0, self.width(), 2):
            path.lineTo(x, mid - 18 * math.sin(2 * math.pi * x / wavelength))
        hue = max(0.0, 0.66 - 0.66 * min(z / 2, 1.0))  # blue → red as it stretches
        painter.setPen(QPen(QColor.fromHsvF(hue, 0.8, 1.0), 2.2))
        painter.drawPath(path)
        painter.setPen(QColor(p.text))
        painter.drawText(QRectF(10, 2, self.width() - 20, 18), Qt.AlignLeft,
                         f"Wavelength × {stretch:.2f}  →  redshift z = {z:.2f}")


class BalloonSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        play_box = QGroupBox(tr("Expansion"))
        pl = QVBoxLayout(play_box)
        row = QHBoxLayout()
        self.play = QPushButton(tr("▶ Play"))
        self.play.setCheckable(True)
        self.play.setProperty("role", "primary")
        self.play.toggled.connect(self._toggle)
        reset = QPushButton(tr("⟲ Reset"))
        reset.clicked.connect(self._reset)
        row.addWidget(self.play)
        row.addWidget(reset)
        pl.addLayout(row)
        self.speed = ParameterSlider(
            tr("Speed"), 0.2, 3.0, 1.0, decimals=1, step=0.1,
            info=(tr("Animation speed"), tr("Only changes how fast the animation runs, not the physics.")),
        )
        pl.addWidget(self.speed)
        self.scale = ParameterSlider(
            tr("Scale factor a"), A_START, A_END, A_START, decimals=4, step=0.05,
            info=(tr("Scale factor"), tr("Drag to set the size of the universe directly. a = 2 means every distance is "
                      "twice as large as at the start.")),
        )
        pl.addWidget(self.scale)
        self.controls.addWidget(play_box)

        show = QGroupBox(tr("Show"))
        sl = QVBoxLayout(show)
        self.grid_box = QCheckBox(tr("Comoving grid"))
        self.grid_box.setChecked(True)
        self.grid_box.setToolTip(tr("The grid stretches with space. Galaxies keep their grid coordinates."))
        self.arrow_box = QCheckBox(tr("Recession velocity arrows"))
        self.arrow_box.setChecked(True)
        self.arrow_box.setToolTip(tr("Arrow length ∝ recession speed ∝ distance from the galaxy you stand on."))
        sl.addWidget(self.grid_box)
        sl.addWidget(self.arrow_box)
        self.emit_btn = QPushButton(tr("💡 Emit light"))
        self.emit_btn.setToolTip(tr("Emit a light wave now; watch its wavelength grow as the universe expands."))
        self.emit_btn.clicked.connect(self._emit_light)
        sl.addWidget(self.emit_btn)
        self.controls.addWidget(show)

        facts = QGroupBox(tr("Measurements from your galaxy"))
        fl = QVBoxLayout(facts)
        self.facts = QLabel()
        self.facts.setWordWrap(True)
        self.facts.setTextFormat(Qt.RichText)
        fl.addWidget(self.facts)
        self.controls.addWidget(facts)
        self.finish_controls()

        self.canvas = ExpansionCanvas()
        self.wave = LightWave()
        self.display.addWidget(self.canvas, 1)
        self.display.addWidget(self.wave)

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self._tick)
        self.scale.valueChanged.connect(self._set_a)
        self.grid_box.toggled.connect(self._toggle_options)
        self.arrow_box.toggled.connect(self._toggle_options)
        self.canvas.homeChanged.connect(lambda _i: self._update_facts())
        self._set_a(A_START)

    def _toggle_options(self, *_args) -> None:
        self.canvas.show_grid = self.grid_box.isChecked()
        self.canvas.show_arrows = self.arrow_box.isChecked()
        self.canvas.update()

    def _toggle(self, on: bool) -> None:
        self.play.setText(tr("⏸ Pause") if on else tr("▶ Play"))
        if on:
            if self.scale.value() >= A_END - 1e-6:
                self.scale.setValue(A_START)
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        # Exponential growth: the same fractional expansion per frame (constant H).
        a = self.scale.value() * (1 + 0.004 * self.speed.value())
        if a >= A_END:
            a = A_END
            self.play.setChecked(False)
        self.scale.setValue(a)

    def _reset(self) -> None:
        self.play.setChecked(False)
        self.wave.a_emit = None
        self.scale.setValue(A_START)

    def _emit_light(self) -> None:
        self.wave.a_emit = self.scale.value()
        self.wave.update()
        if not self.play.isChecked() and self.scale.value() < A_END:
            self.play.setChecked(True)

    def _set_a(self, a: float) -> None:
        self.canvas.a = a
        self.wave.a = a
        self.canvas.update()
        self.wave.update()
        self._update_facts()

    def _update_facts(self) -> None:
        c = self.canvas
        hx, hy, _ = c.galaxies[c.home]
        dists = sorted(
            (math.hypot(x - hx, y - hy), i) for i, (x, y, _k) in enumerate(c.galaxies) if i != c.home
        )
        near_d, _ = dists[0]
        far_d, _ = dists[-1]
        a = c.a
        self.facts.setText(
            tr("Scale factor: <b>{a}</b> (distances × {growth} since the start)<br><br>"
               "Nearest galaxy: comoving {near} cells → proper <b>{near_proper}</b> cells<br>"
               "Farthest galaxy: comoving {far} cells → proper <b>{far_proper}</b> cells<br><br>"
               "The farthest galaxy is {ratio}× farther away and recedes <b>{ratio}× faster</b>: "
               "v ∝ d, the Hubble–Lemaître law.<br><br>"
               "<i>Click another galaxy: the pattern is identical. There is no centre.</i>")
            .format(a=f"{a:.2f}", growth=f"{a / A_START:.2f}", near=f"{near_d:.2f}",
                    near_proper=f"{near_d * a:.2f}", far=f"{far_d:.2f}", far_proper=f"{far_d * a:.2f}",
                    ratio=f"{far_d / near_d:.1f}")
        )

    def on_hidden(self) -> None:
        self.play.setChecked(False)
