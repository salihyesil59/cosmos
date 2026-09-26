"""S13 — 2D N-body Structure Formation."""

from __future__ import annotations

import numpy as np
from matplotlib import colormaps
from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QImage, QPainter
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui import nav_icons
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import InfoButton, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics.nbody import NBodyConfig, NBodySimulation

COLORMAPS = {"Magma": "magma", "Inferno": "inferno", "Viridis": "viridis", "Cubehelix": "cubehelix"}


class DensityCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.image: QImage | None = None
        self.caption = ""

    def set_image(self, rgba: np.ndarray, caption: str) -> None:
        h, w, _ = rgba.shape
        self._buffer = np.ascontiguousarray(rgba)
        self.image = QImage(self._buffer.data, w, h, 4 * w, QImage.Format_RGBA8888)
        self.caption = caption
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#05070d"))
        if self.image is None:
            return
        side = min(self.width(), self.height()) - 8
        target = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawImage(target, self.image)
        painter.setPen(QColor("#e6e9f2"))
        font = QFont()
        font.setPointSizeF(9)
        painter.setFont(font)
        painter.drawText(target.adjusted(10, 8, -10, -8), Qt.AlignLeft | Qt.AlignTop, self.caption)


class NBodySimulator(SimulatorBase):
    D_MAX = 4.0

    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.history: list[tuple[float, float]] = []

        ic = QGroupBox(tr("1 · Initial ripples"))
        il = QVBoxLayout(ic)
        self.index = ParameterSlider(
            tr("Spectral index n"), -2.5, 0.5, -1.0, decimals=2, step=0.1,
            info=(tr("Power spectrum slope"),
                  tr("Initial fluctuations have power P(k) ∝ kⁿ. Smaller n puts more power on large scales (big "
                     "coherent structures); larger n gives more small clumps.")),
        )
        self.strength = ParameterSlider(
            tr("Fluctuation strength"), 0.4, 2.0, 1.0, decimals=2, step=0.05,
            info=(tr("Amplitude"), tr("RMS density contrast per grid cell when the growth factor reaches D = 1. "
                      "Stronger ripples collapse earlier.")),
        )
        il.addWidget(self.index)
        il.addWidget(self.strength)
        dm_row = QHBoxLayout()
        self.cold = QRadioButton(tr("Cold dark matter"))
        self.warm = QRadioButton(tr("Warm dark matter"))
        self.cold.setChecked(True)
        group = QButtonGroup(self)
        group.addButton(self.cold)
        group.addButton(self.warm)
        dm_row.addWidget(self.cold)
        dm_row.addWidget(self.warm)
        dm_row.addWidget(InfoButton(
            tr("Cold or warm?"),
            tr("Cold dark matter particles move slowly, so fluctuations survive on all scales. Warm dark matter "
                "particles move fast enough early on to smooth out the smallest ripples, so fewer small halos form."),
        ))
        il.addLayout(dm_row)
        self.cutoff = ParameterSlider(
            tr("Free-streaming scale (cells)"), 1.0, 12.0, 5.0, decimals=1, step=0.5,
            info=(tr("Cutoff"), tr("Fluctuations smaller than this are erased in the warm dark matter model.")),
        )
        il.addWidget(self.cutoff)
        self.seed = QSpinBox()
        self.seed.setRange(1, 9999)
        self.seed.setValue(42)
        self.seed.setToolTip(tr("Different numbers give different random universes with the same statistics."))
        il.addWidget(labelled_row(tr("Random seed"), self.seed))
        self.resolution = QComboBox()
        self.resolution.addItem(tr("96 × 96 particles (fast)"), 96)
        self.resolution.addItem(tr("128 × 128 particles"), 128)
        self.resolution.addItem(tr("192 × 192 particles (detailed)"), 192)
        self.resolution.setCurrentIndex(1)
        il.addWidget(labelled_row(tr("Resolution"), self.resolution))
        new = QPushButton(tr("Apply and restart"))
        new.setToolTip(tr("Create new initial conditions with these settings."))
        new.clicked.connect(self.restart)
        il.addWidget(new)
        self.controls.addWidget(ic)

        run = QGroupBox(tr("2 · Run"))
        rl = QVBoxLayout(run)
        buttons = QHBoxLayout()
        self.play = QPushButton(tr("Play"))
        nav_icons.set_glyph(self.play, "continue", 14)
        self.play.setProperty("role", "primary")
        self.play.setCheckable(True)
        self.play.toggled.connect(self._toggle)
        step = QPushButton(tr("Step"))
        step.setToolTip(tr("Advance a little bit"))
        step.clicked.connect(lambda: self._advance(3))
        reset = QPushButton(tr("Reset"))
        reset.clicked.connect(self.restart)
        for b in (self.play, step, reset):
            buttons.addWidget(b)
        rl.addLayout(buttons)
        self.speed = ParameterSlider(tr("Speed (steps per frame)"), 1, 8, 2, decimals=0, step=1)
        rl.addWidget(self.speed)
        self.cmap = QComboBox()
        self.cmap.addItems(list(COLORMAPS))
        self.cmap.currentIndexChanged.connect(self._render)
        rl.addWidget(labelled_row(tr("Colours"), self.cmap))
        self.controls.addWidget(run)

        stats = QGroupBox(tr("What is happening"))
        sl = QVBoxLayout(stats)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        sl.addWidget(self.summary)
        sl.addWidget(muted_label(tr("A two-dimensional toy universe in a periodic box. Real simulations are 3D "
                            "and use billions of particles, but the physics is the same.")))
        self.controls.addWidget(stats)
        self.finish_controls()

        split = QSplitter(Qt.Vertical)
        self.canvas = DensityCanvas()
        split.addWidget(self.canvas)
        self.plot = PlotWidget(self._draw_growth, toolbar=False)
        self.plot.canvas.setMinimumHeight(160)
        split.addWidget(self.plot)
        split.setSizes([620, 220])
        self.display.addWidget(split, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(lambda: self._advance(int(self.speed.value())))
        self.warm.toggled.connect(lambda on: self.cutoff.setEnabled(on))
        self.cutoff.setEnabled(False)
        self.restart()

    # ---------------------------------------------------------- control
    def config(self) -> NBodyConfig:
        n = int(self.resolution.currentData())
        return NBodyConfig(
            particles_per_side=n,
            grid=n,
            spectral_index=self.index.value(),
            amplitude=self.strength.value(),
            cutoff=self.cutoff.value() if self.warm.isChecked() else 0.0,
            seed=self.seed.value(),
        )

    def restart(self) -> None:
        self.play.setChecked(False)
        self.sim = NBodySimulation(self.config())
        self.linear_start = float(self.sim.density().std()) / self.sim.growth
        self.history = [(self.sim.growth, float(self.sim.density().std()))]
        self._render()

    def _toggle(self, on: bool) -> None:
        self.play.setText(tr("Pause") if on else tr("Play"))
        nav_icons.set_glyph(self.play, "pause" if on else "continue", 14)
        if on:
            if self.sim.growth >= self.D_MAX - 1e-6:
                self.restart()
                self.play.setChecked(True)
                return
            self.timer.start()
        else:
            self.timer.stop()

    def _advance(self, steps: int) -> None:
        for _ in range(max(1, steps)):
            if self.sim.growth >= self.D_MAX:
                self.play.setChecked(False)
                break
            d = self.sim.growth
            self.sim.step(min(0.03, 0.04 * d, self.D_MAX - d))
        self.history.append((self.sim.growth, float(self.sim.density().std())))
        self._render()

    def recompute(self) -> None:
        self._render()

    def on_hidden(self) -> None:
        self.play.setChecked(False)

    # ----------------------------------------------------------- render
    def _render(self) -> None:
        sim = self.sim
        img = sim.density_image()
        cmap = colormaps[COLORMAPS[self.cmap.currentText()]]
        rgba = (cmap(np.flipud(img.T)) * 255).astype(np.uint8)
        d = sim.growth
        epoch = (f"z ≈ {1 / d - 1:.1f}" if d < 1
                 else (tr("today") if abs(d - 1) < 0.02 else tr("future")))
        self.canvas.set_image(rgba, tr("growth factor D = {d}  ({epoch} in an Einstein–de Sitter universe)")
                              .format(d=f"{d:.2f}", epoch=epoch))
        sigma = float(sim.density().std())
        collapsed = sim.collapsed_fraction()
        linear = self.linear_start * d
        phase = (tr("linear: ripples simply grow") if sigma < 0.3 else
                 tr("quasi-linear: sheets and filaments form") if collapsed < 0.05 else
                 tr("non-linear: halos collapse and merge"))
        self.summary.setText(
            tr("Growth factor D: <b>{d}</b><br>"
               "RMS density contrast: <b>{sigma}</b> (linear theory: {linear})<br>"
               "Particles in dense clumps (δ > 4): <b>{collapsed}</b><br>"
               "Steps: {steps}<br>"
               "Stage: <b>{phase}</b>")
            .format(d=f"{d:.2f}", sigma=f"{sigma:.2f}", linear=f"{linear:.2f}",
                    collapsed=f"{collapsed:.0%}", steps=sim.steps, phase=phase)
        )
        self.plot.refresh()

    def _draw_growth(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        if self.history:
            d, s = np.array(self.history).T
            dd = np.linspace(0.01, self.D_MAX, 100)
            ax.plot(dd, self.linear_start * dd, color=p.muted, linestyle="--", label="Linear theory δ ∝ D")
            ax.plot(d, s, color=p.series[1], linewidth=2, label="Simulation")
        ax.set_xlim(0, self.D_MAX)
        ax.set_xlabel("Growth factor D", fontsize=8)
        ax.set_ylabel("RMS δ", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.legend(loc="upper left", fontsize=7)
