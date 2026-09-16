"""S3 — Powers of Ten Zoom."""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.widgets.common import ParameterSlider, labelled_row
from cosmos.i18n import tr
from cosmos.physics import constants as const

LOG_MIN, LOG_MAX = -1.0, 27.5


@dataclass(frozen=True)
class CosmicObject:
    name: str
    size_m: float           # diameter (or diameter of the orbit / distance circle)
    kind: str               # "body", "orbit", "region"
    color: str
    description: str


OBJECTS = [
    CosmicObject("Human", 1.7, "body", "#f5b35c", "About 1.7 m tall. Light crosses this in 6 nanoseconds."),
    CosmicObject("Football pitch", 105, "region", "#4fd18b", "About 105 m long."),
    CosmicObject("Mount Everest (height)", 8.85e3, "region", "#9aa4bd", "8.85 km above sea level."),
    CosmicObject("Large city", 5.0e4, "region", "#b58cff", "A metropolis spans roughly 50 km."),
    CosmicObject("Moon", 3.474e6, "body", "#c9ced9", "Diameter 3 474 km."),
    CosmicObject("Earth", 1.2742e7, "body", "#6ea8fe", "Diameter 12 742 km. Light circles it 7.5 times per second."),
    CosmicObject("Jupiter", 1.3982e8, "body", "#e0b084", "The largest planet, 11 times wider than Earth."),
    CosmicObject("Moon's orbit", 7.688e8, "orbit", "#c9ced9", "The Moon orbits 384 400 km away; light takes 1.3 s."),
    CosmicObject("Sun", 1.3927e9, "body", "#ffd166", "Diameter 1.39 million km, 109 Earths across."),
    CosmicObject("Earth's orbit", 2 * const.AU, "orbit", "#6ea8fe", "1 AU from the Sun; sunlight takes 8.3 minutes."),
    CosmicObject("Neptune's orbit", 60.2 * const.AU, "orbit", "#4dd0e1", "30 AU from the Sun; light takes 4 hours."),
    CosmicObject("Heliopause", 240 * const.AU, "orbit", "#9aa4bd", "Where the solar wind meets interstellar gas, ~120 AU."),
    CosmicObject("Oort cloud", 2e5 * const.AU, "orbit", "#9aa4bd", "Icy bodies up to ~100 000 AU from the Sun."),
    CosmicObject("Nearest star (Proxima)", 2 * 4.24 * const.LIGHT_YEAR, "orbit", "#ef6b73",
                 "4.24 light-years away: the circle has this radius."),
    CosmicObject("Orion Nebula", 24 * const.LIGHT_YEAR, "region", "#ef6b73", "A star-forming cloud 24 light-years across."),
    CosmicObject("Milky Way", 1.0e5 * const.LIGHT_YEAR, "galaxy", "#e6e9f2",
                 "Our galaxy: ~100 000 light-years across, 100–400 billion stars."),
    CosmicObject("Andromeda distance", 2 * 2.5e6 * const.LIGHT_YEAR, "orbit", "#b58cff",
                 "Andromeda is 2.5 million light-years away (0.78 Mpc)."),
    CosmicObject("Local Group", 1.0e7 * const.LIGHT_YEAR, "region", "#f5b35c", "About 80 galaxies within ~3 Mpc."),
    CosmicObject("Virgo Cluster distance", 2 * 5.4e7 * const.LIGHT_YEAR, "orbit", "#4fd18b",
                 "The nearest large cluster, 16.5 Mpc away."),
    CosmicObject("Laniakea supercluster", 5.2e8 * const.LIGHT_YEAR, "region", "#6ea8fe",
                 "Our home supercluster, ~160 Mpc across, containing ~100 000 galaxies."),
    CosmicObject("Largest voids and filaments", 3e9 * const.LIGHT_YEAR, "web", "#9aa4bd",
                 "Above ~1 Gpc the cosmic web looks statistically uniform: the cosmological principle."),
    CosmicObject("Observable universe", 9.3e10 * const.LIGHT_YEAR, "universe", "#f5b35c",
                 "About 93 billion light-years across (radius 46 billion ly). The CMB comes from near its edge."),
]


def best_unit(metres: float) -> str:
    units = [
        (const.GPC, "Gpc"), (const.MPC, "Mpc"), (const.KPC, "kpc"), (const.LIGHT_YEAR, "ly"),
        (const.AU, "AU"), (1e3, "km"), (1.0, "m"),
    ]
    for size, name in units:
        if metres >= size:
            return f"{metres / size:,.3g} {name}".replace(",", " ")
    return f"{metres * 100:.3g} cm"


def light_time(metres: float) -> str:
    seconds = metres / const.C
    for size, name in [(const.YEAR * 1e9, "billion years"), (const.YEAR * 1e6, "million years"),
                       (const.YEAR, "years"), (86400, "days"), (3600, "hours"), (60, "minutes"), (1, "seconds")]:
        if seconds >= size:
            return f"{seconds / size:.3g} {name}"
    return f"{seconds * 1e9:.3g} nanoseconds"


class ZoomView(QWidget):
    zoomed = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.log_width = 0.5
        self.setMinimumSize(420, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rng = random.Random(10)
        self.stars = [(rng.random(), rng.random(), rng.random()) for _ in range(260)]
        self.setToolTip(tr("Scroll the mouse wheel to zoom in and out."))

    def set_log_width(self, value: float) -> None:
        self.log_width = min(max(value, LOG_MIN), LOG_MAX)
        self.update()

    def wheelEvent(self, event):  # noqa: N802
        steps = event.angleDelta().y() / 120
        self.set_log_width(self.log_width - 0.1 * steps)
        self.zoomed.emit(self.log_width)

    def paintEvent(self, _event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), QColor("#05070d"))
        # Background star field that twinkles slightly with zoom level.
        for x, y, b in self.stars:
            alpha = int(60 + 120 * b * (0.5 + 0.5 * math.sin(self.log_width * 3 + b * 10)))
            painter.setPen(QColor(255, 255, 255, alpha))
            painter.drawPoint(QPointF(x * w, y * h))

        view_m = 10 ** self.log_width
        scale = min(w, h) * 0.9 / view_m  # pixels per metre
        cx, cy = w / 2, h / 2
        font = QFont()
        font.setPointSizeF(9)
        painter.setFont(font)
        for obj in OBJECTS:
            diameter_px = obj.size_m * scale
            if diameter_px < 3 or diameter_px > 6 * max(w, h):
                continue
            ratio = diameter_px / (min(w, h) * 0.9)
            fade = 1.0 if 0.02 < ratio < 1.6 else max(0.15, min(1.0, 0.02 / ratio if ratio <= 0.02 else 1.6 / ratio))
            color = QColor(obj.color)
            color.setAlphaF(fade)
            r = diameter_px / 2
            rect = QRectF(cx - r, cy - r, 2 * r, 2 * r)
            if obj.kind == "body":
                grad = QRadialGradient(QPointF(cx - r * 0.3, cy - r * 0.3), r * 1.2)
                grad.setColorAt(0, color.lighter(140))
                grad.setColorAt(1, color.darker(160))
                painter.setBrush(grad)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(rect)
            elif obj.kind == "galaxy":
                grad = QRadialGradient(QPointF(cx, cy), r)
                core = QColor(255, 240, 200, int(220 * fade))
                edge = QColor(obj.color)
                edge.setAlpha(0)
                grad.setColorAt(0, core)
                grad.setColorAt(0.25, QColor(200, 210, 255, int(120 * fade)))
                grad.setColorAt(1, edge)
                painter.setBrush(grad)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(QRectF(cx - r, cy - r * 0.35, 2 * r, 0.7 * r))
            elif obj.kind == "web":
                pen = QPen(color, 1)
                painter.setPen(pen)
                rng = random.Random(3)
                for _ in range(60):
                    x1, y1 = cx + (rng.random() - 0.5) * 2 * r, cy + (rng.random() - 0.5) * 2 * r
                    painter.drawLine(QPointF(x1, y1), QPointF(x1 + (rng.random() - 0.5) * r * 0.5,
                                                              y1 + (rng.random() - 0.5) * r * 0.5))
            elif obj.kind == "universe":
                pen = QPen(color, 3)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(rect)
            else:
                pen = QPen(color, 1.5, Qt.DashLine if obj.kind == "orbit" else Qt.SolidLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(rect)
            if 0.01 < ratio < 1.8:
                painter.setPen(color)
                label_y = cy - r - 6 if r < h / 2 - 20 else 22
                painter.drawText(QRectF(cx - 150, label_y - 16, 300, 18), Qt.AlignCenter, obj.name)

        # Scale bar: the largest 1-2-5 step that fits into a third of the view.
        target = view_m / 3
        exp = math.floor(math.log10(target))
        nice = max(m * 10**exp for m in (1, 2, 5) if m * 10**exp <= target)
        bar_px = nice * scale
        painter.setPen(QPen(QColor("#e6e9f2"), 2))
        y = h - 24
        painter.drawLine(QPointF(20, y), QPointF(20 + bar_px, y))
        painter.drawLine(QPointF(20, y - 5), QPointF(20, y + 5))
        painter.drawLine(QPointF(20 + bar_px, y - 5), QPointF(20 + bar_px, y + 5))
        painter.drawText(QPointF(24, y - 8), best_unit(nice))


class PowersOfTenSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        box = QGroupBox(tr("Zoom"))
        bl = QVBoxLayout(box)
        self.slider = ParameterSlider(
            tr("Field of view: 10^x metres"), LOG_MIN, LOG_MAX, 0.5, decimals=2, step=0.1,
            info=(tr("Powers of ten"), tr("Each whole step multiplies the width of the view by ten.")),
        )
        bl.addWidget(self.slider)
        self.play = QPushButton(tr("▶ Play"))
        self.play.setCheckable(True)
        self.play.setToolTip(tr("Fly automatically from the current scale outward. Click again to pause."))
        self.play.toggled.connect(self._toggle_play)
        bl.addWidget(self.play)
        self.direction = QComboBox()
        self.direction.addItems([tr("Zoom out"), tr("Zoom in")])
        bl.addWidget(labelled_row(tr("Direction"), self.direction))
        self.jump = QComboBox()
        self.jump.addItem(tr("Choose an object…"))
        for obj in OBJECTS:
            self.jump.addItem(obj.name)
        self.jump.activated.connect(self._jump_to)
        bl.addWidget(labelled_row(tr("Jump to"), self.jump))
        self.controls.addWidget(box)

        readout = QGroupBox(tr("At this scale"))
        rl = QVBoxLayout(readout)
        self.width_label = QLabel()
        self.width_label.setWordWrap(True)
        self.width_label.setTextFormat(Qt.RichText)
        rl.addWidget(self.width_label)
        self.controls.addWidget(readout)

        visible = QGroupBox(tr("What you are looking at"))
        vl = QVBoxLayout(visible)
        self.visible_label = QLabel()
        self.visible_label.setWordWrap(True)
        self.visible_label.setTextFormat(Qt.RichText)
        vl.addWidget(self.visible_label)
        self.controls.addWidget(visible)
        self.finish_controls()

        self.view = ZoomView()
        self.display.addWidget(self.view, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self._tick)
        self.slider.valueChanged.connect(self._set_zoom)
        self.view.zoomed.connect(lambda v: self.slider.setValue(v))
        self._set_zoom(self.slider.value())

    def _set_zoom(self, value: float) -> None:
        self.view.set_log_width(value)
        view_m = 10**value
        self.width_label.setText(
            f"Width of view: <b>{view_m:.3g} m</b><br>= <b>{best_unit(view_m)}</b><br>"
            f"Light needs <b>{light_time(view_m)}</b> to cross it."
        )
        items = [o for o in OBJECTS if 0.05 * view_m < o.size_m < 1.5 * view_m]
        if items:
            self.visible_label.setText("<br><br>".join(f"<b>{o.name}</b><br>{o.description}" for o in items))
        else:
            self.visible_label.setText(tr("<i>Mostly empty space at this scale. Keep zooming!</i>"))

    def _toggle_play(self, on: bool) -> None:
        self.play.setText("⏸ Pause" if on else "▶ Play")
        if on:
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        step = 0.03 if self.direction.currentIndex() == 0 else -0.03
        value = self.slider.value() + step
        if value >= LOG_MAX or value <= LOG_MIN:
            self.play.setChecked(False)
            value = min(max(value, LOG_MIN), LOG_MAX)
        self.slider.setValue(value)

    def _jump_to(self, index: int) -> None:
        if index <= 0:
            return
        obj = OBJECTS[index - 1]
        self.slider.setValue(math.log10(obj.size_m * 1.25))

    def on_hidden(self) -> None:
        self.play.setChecked(False)
