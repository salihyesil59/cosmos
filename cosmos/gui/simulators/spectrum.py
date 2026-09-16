"""S4 — Spectrum & Redshift Simulator."""

from __future__ import annotations

import math
import random

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import (
    QButtonGroup,
    QGroupBox,
    QLabel,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider
from cosmos.i18n import tr
from cosmos.physics import spectra
from cosmos.physics.presets import PRESETS

LAMBDA_MIN, LAMBDA_MAX = 300.0, 4000.0


class SpectrumView(QWidget):
    """Two spectrum strips on a logarithmic wavelength axis."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(330)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.strips: list[tuple[str, float, bool]] = [("Laboratory (rest frame)", 0.0, True), ("Observed", 0.0, True)]
        theme().changed.connect(lambda _p: self.update())

    def set_strips(self, strips: list[tuple[str, float, bool]]) -> None:
        self.strips = strips
        self.update()

    def _x(self, wavelength: float, left: float, width: float) -> float:
        frac = (math.log10(wavelength) - math.log10(LAMBDA_MIN)) / (math.log10(LAMBDA_MAX) - math.log10(LAMBDA_MIN))
        return left + frac * width

    def paintEvent(self, _event):  # noqa: N802
        p = theme().palette
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor(p.surface))
        left, right = 20, 20
        width = self.width() - left - right
        strip_h = 70
        gap = 95
        top = 40
        font = QFont()
        font.setPointSizeF(9)
        painter.setFont(font)

        for i, (label, z, show_z) in enumerate(self.strips):
            y = top + i * (strip_h + gap)
            painter.setPen(QColor(p.text))
            bold = QFont(font)
            bold.setBold(True)
            painter.setFont(bold)
            painter.drawText(QPointF(left, y - 8), f"{label}   (z = {z:.4g})" if show_z else f"{label}   (z = ?)")
            painter.setFont(font)
            # Background: grey for invisible bands, rainbow for visible light.
            painter.fillRect(QRectF(left, y, width, strip_h), QColor(p.surface_alt))
            x0 = self._x(spectra.VISIBLE_MIN_NM, left, width)
            x1 = self._x(spectra.VISIBLE_MAX_NM, left, width)
            grad = QLinearGradient(x0, 0, x1, 0)
            for k in range(0, 41):
                wl = spectra.VISIBLE_MIN_NM + (spectra.VISIBLE_MAX_NM - spectra.VISIBLE_MIN_NM) * k / 40
                xpos = (self._x(wl, left, width) - x0) / (x1 - x0)
                grad.setColorAt(xpos, QColor(*spectra.wavelength_to_rgb(wl)))
            painter.fillRect(QRectF(x0, y, x1 - x0, strip_h), grad)
            # Absorption lines.
            for line in spectra.SPECTRAL_LINES:
                wl = spectra.observed_wavelength(line.wavelength_nm, z)
                if not LAMBDA_MIN <= wl <= LAMBDA_MAX:
                    continue
                x = self._x(wl, left, width)
                visible = spectra.VISIBLE_MIN_NM <= wl <= spectra.VISIBLE_MAX_NM
                painter.setPen(QPen(QColor("#000000") if visible else QColor(p.text), 2.2))
                painter.drawLine(QPointF(x, y), QPointF(x, y + strip_h))
                painter.setPen(QColor(p.muted))
                row = spectra.SPECTRAL_LINES.index(line) % 4
                label_y = y + strip_h + 4 + row * 15
                painter.drawLine(QPointF(x, y + strip_h), QPointF(x, label_y + 2))
                painter.drawText(QRectF(x + 2, label_y, 80, 14), Qt.AlignLeft, line.name)

        # Axis.
        axis_y = top + len(self.strips) * (strip_h + gap) - gap + 78
        painter.setPen(QPen(QColor(p.muted), 1))
        painter.drawLine(QPointF(left, axis_y), QPointF(left + width, axis_y))
        for tick in (300, 400, 500, 600, 700, 1000, 1500, 2000, 3000, 4000):
            x = self._x(tick, left, width)
            painter.drawLine(QPointF(x, axis_y - 4), QPointF(x, axis_y + 4))
            painter.drawText(QRectF(x - 30, axis_y + 6, 60, 16), Qt.AlignCenter, f"{tick}")
        painter.drawText(QRectF(left, axis_y + 22, width, 16), Qt.AlignCenter,
                         "Wavelength (nm, logarithmic)   ·   UV ← visible light → infrared")


class SpectrumSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.challenge_z: float | None = None
        self.cosmo = PRESETS["planck18"].cosmology

        mode_box = QGroupBox(tr("1 · What causes the shift?"))
        ml = QVBoxLayout(mode_box)
        self.doppler = QRadioButton(tr("Doppler motion (a moving light source)"))
        self.doppler.setToolTip(tr("A star or galaxy moving towards or away from us through space."))
        self.cosmic = QRadioButton(tr("Cosmic expansion (a distant galaxy)"))
        self.cosmic.setToolTip(tr("Light stretched by the expansion of the universe: 1 + z = 1/a."))
        self.mode = QButtonGroup(self)
        self.mode.addButton(self.doppler, 0)
        self.mode.addButton(self.cosmic, 1)
        self.doppler.setChecked(True)
        ml.addWidget(self.doppler)
        ml.addWidget(self.cosmic)
        self.controls.addWidget(mode_box)

        shift_box = QGroupBox(tr("2 · Amount of shift"))
        sl = QVBoxLayout(shift_box)
        self.velocity = ParameterSlider(
            tr("Radial velocity (km/s)"), -250000, 250000, 0.0, decimals=0, step=1000,
            info=(tr("Radial velocity"), tr("Positive: moving away (redshift). Negative: approaching (blueshift). "
                      "The relativistic Doppler formula is used, so the speed never reaches c.")),
        )
        self.redshift = ParameterSlider(
            tr("Redshift z"), 0.001, 12.0, 0.5, decimals=3, log=True,
            info=(tr("Cosmological redshift"), tr("How much the universe has expanded since the light left the galaxy: "
                      "1 + z = 1/a.")),
        )
        sl.addWidget(self.velocity)
        sl.addWidget(self.redshift)
        self.controls.addWidget(shift_box)

        read_box = QGroupBox(tr("Readout"))
        rl = QVBoxLayout(read_box)
        self.readout = QLabel()
        self.readout.setWordWrap(True)
        self.readout.setTextFormat(Qt.RichText)
        rl.addWidget(self.readout)
        self.controls.addWidget(read_box)

        challenge = QGroupBox(tr("Challenge: Mystery galaxy"))
        cl = QVBoxLayout(challenge)
        hint = QLabel(tr("Match the redshift of an unknown galaxy by lining up the lines."))
        hint.setWordWrap(True)
        cl.addWidget(hint)
        self.new_challenge = QPushButton(tr("🔭 New mystery galaxy"))
        self.new_challenge.clicked.connect(self._start_challenge)
        self.check = QPushButton(tr("Check my answer"))
        self.check.setEnabled(False)
        self.check.clicked.connect(self._check_challenge)
        cl.addWidget(self.new_challenge)
        cl.addWidget(self.check)
        self.controls.addWidget(challenge)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.banner.hide()
        self.display.addWidget(self.banner)
        self.view = SpectrumView()
        self.display.addWidget(self.view, 1)

        self.mode.idToggled.connect(lambda *_: self._mode_changed())
        self.velocity.valueChanged.connect(lambda _v: self.recompute())
        self.redshift.valueChanged.connect(lambda _v: self.recompute())
        self._mode_changed()

    def current_z(self) -> float:
        if self.doppler.isChecked():
            return spectra.relativistic_doppler_z(self.velocity.value())
        return self.redshift.value()

    def _mode_changed(self) -> None:
        cosmic = self.cosmic.isChecked()
        self.velocity.setVisible(not cosmic)
        self.redshift.setVisible(cosmic)
        self.recompute()

    def recompute(self) -> None:
        z = self.current_z()
        halpha = spectra.observed_wavelength(656.28, z)
        lines = [
            tr("Redshift z = <b>{z}</b>").format(z=f"{z:+.4f}"),
            tr("Every wavelength × <b>{factor}</b>").format(factor=f"{1 + z:.4f}"),
            tr("Hα (656.3 nm) observed at <b>{wavelength} nm</b> ({band})")
            .format(wavelength=f"{halpha:.1f}", band=spectra.band_name(halpha)),
        ]
        if self.doppler.isChecked():
            v = self.velocity.value()
            direction = tr("receding") if v > 0 else tr("approaching") if v < 0 else tr("at rest")
            lines.append(tr("Source is <b>{direction}</b> at {speed} km/s = {fraction}% of c")
                         .format(direction=direction, speed=f"{abs(v):,.0f}".replace(",", " "),
                                 fraction=f"{abs(v) / 2997.92458:.2f}"))
            lines.append(tr("Simple estimate z ≈ v/c = {z}")
                         .format(z=f"{spectra.classical_doppler_z(v):+.4f}"))
        else:
            a = 1 / (1 + z)
            lines += [
                tr("Universe size at emission: <b>{a}</b> × today").format(a=f"{a:.3f}"),
                tr("Light travelled for <b>{years} billion years</b>")
                .format(years=f"{self.cosmo.lookback_time(z):.2f}"),
                tr("Universe was <b>{years} billion years</b> old (Planck 2018)")
                .format(years=f"{self.cosmo.age(z):.2f}"),
            ]
        self.readout.setText("<br>".join(lines))
        if self.challenge_z is None:
            self.view.set_strips([(tr("Laboratory (rest frame)"), 0.0, True), (tr("Observed"), z, True)])
        else:
            self.view.set_strips([(tr("Mystery galaxy"), self.challenge_z, False),
                                  (tr("Your guess"), z, True)])

    def _start_challenge(self) -> None:
        self.cosmic.setChecked(True)
        self.challenge_z = round(random.uniform(0.05, 3.0), 3)
        self.check.setEnabled(True)
        self.banner.set_message(
            "info",
            tr("<b>Mystery galaxy!</b> Its spectrum is in the upper strip. Move the redshift slider until the "
               "lines in your guess line up with the mystery spectrum, then press <b>Check my answer</b>."),
        )
        self.banner.show()
        self.redshift.setValue(0.01)

    def _check_challenge(self) -> None:
        if self.challenge_z is None:
            return
        guess = self.redshift.value()
        error = abs(guess - self.challenge_z) / (1 + self.challenge_z)
        if error < 0.01:
            self.banner.set_message(
                "success",
                tr("<b>Excellent!</b> The true redshift is z = {truth}. Your guess {guess} is within {error}. "
                   "The light left this galaxy {years} billion years ago.")
                .format(truth=self.challenge_z, guess=f"{guess:.3f}", error=f"{error:.1%}",
                        years=f"{self.cosmo.lookback_time(self.challenge_z):.1f}"),
            )
            self.challenge_z = None
            self.check.setEnabled(False)
            self.recompute()
        else:
            hint = tr("higher") if guess < self.challenge_z else tr("lower")
            self.banner.set_message("warning", tr("Not yet: the lines do not match. Try a <b>{hint}</b> "
                                                  "redshift.").format(hint=hint))
