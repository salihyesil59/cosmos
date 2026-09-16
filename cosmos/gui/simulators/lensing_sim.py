"""S14 — Gravitational Lensing Simulator."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row
from cosmos.i18n import tr, tr_noop
from cosmos.physics import lensing
from cosmos.physics.presets import PRESETS

PIXELS = 360
FIXED_FIELD = {"point": 3.0, "galaxy": 8.0, "cluster": 160.0}   # arcsec across the view
LENS_TYPES = {
    "point": tr_noop("Point mass (star, black hole)"),
    "galaxy": tr_noop("Galaxy (isothermal sphere)"),
    "cluster": tr_noop("Galaxy cluster (several clumps)"),
}


class LensCanvas(QWidget):
    sourceMoved = Signal(float, float)   # position in arcsec

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(380, 380)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCursor(Qt.CrossCursor)
        self.setToolTip(tr("Drag to move the background source."))
        self.image: QImage | None = None
        self.field = 10.0
        self.circles: list[tuple[float, float, float]] = []
        self.source: tuple[float, float] | None = None
        self.caption = ""

    def _target(self) -> QRectF:
        side = min(self.width(), self.height()) - 8
        return QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)

    def _to_screen(self, x: float, y: float) -> QPointF:
        t = self._target()
        return QPointF(t.left() + (x / self.field + 0.5) * t.width(), t.top() + (0.5 - y / self.field) * t.height())

    def _to_sky(self, pos) -> tuple[float, float]:
        t = self._target()
        return ((pos.x() - t.left()) / t.width() - 0.5) * self.field, (0.5 - (pos.y() - t.top()) / t.height()) * self.field

    def mousePressEvent(self, event):  # noqa: N802
        self.sourceMoved.emit(*self._to_sky(event.position()))

    def mouseMoveEvent(self, event):  # noqa: N802
        if event.buttons() & Qt.LeftButton:
            self.sourceMoved.emit(*self._to_sky(event.position()))

    def set_frame(self, rgba, field, circles, source, caption) -> None:
        h, w, _ = rgba.shape
        self._buffer = np.ascontiguousarray(rgba)
        self.image = QImage(self._buffer.data, w, h, 4 * w, QImage.Format_RGBA8888)
        self.field, self.circles, self.source, self.caption = field, circles, source, caption
        self.update()

    def paintEvent(self, _event):  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), QColor("#020308"))
        if self.image is None:
            return
        target = self._target()
        painter.drawImage(target, self.image)
        painter.setPen(QPen(QColor(110, 168, 254, 170), 1.2, Qt.DashLine))
        scale = target.width() / self.field
        for x, y, r in self.circles:
            painter.drawEllipse(self._to_screen(x, y), r * scale, r * scale)
        if self.source is not None:
            painter.setPen(QPen(QColor(245, 179, 92, 220), 1.5))
            c = self._to_screen(*self.source)
            painter.drawLine(QPointF(c.x() - 7, c.y()), QPointF(c.x() + 7, c.y()))
            painter.drawLine(QPointF(c.x(), c.y() - 7), QPointF(c.x(), c.y() + 7))
        painter.setPen(QColor("#e6e9f2"))
        font = QFont()
        font.setPointSizeF(9)
        painter.setFont(font)
        painter.drawText(target.adjusted(10, 8, -10, -8), Qt.AlignLeft | Qt.AlignTop, self.caption)
        # Scale bar
        bar = self.field / 5
        y = target.bottom() - 16
        painter.setPen(QPen(QColor("#e6e9f2"), 2))
        painter.drawLine(QPointF(target.left() + 14, y), QPointF(target.left() + 14 + bar * scale, y))
        painter.drawText(QPointF(target.left() + 14, y - 6), f'{bar:.3g}″')


class LensingSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.cosmo = PRESETS["planck18"].cosmology
        self.source_pos = (0.6, 0.25)   # in units of the field / 10, rescaled per lens type
        self._sky_cache: dict[tuple, np.ndarray] = {}
        self._theta_e = 1.0

        lens = QGroupBox(tr("1 · The lens"))
        ll = QVBoxLayout(lens)
        self.kind = QComboBox()
        for key, label in LENS_TYPES.items():
            self.kind.addItem(tr(label), key)
        self.kind.setCurrentIndex(1)
        ll.addWidget(labelled_row(tr("Type"), self.kind, (
            tr("Lens models"),
            tr("A point mass bends light as 1/distance. An isothermal sphere, a good model of galaxies and "
                "clusters, bends light by the same angle at every distance."))))
        self.mass = ParameterSlider(
            tr("Mass (M☉)"), 1e8, 1e14, 1e11, decimals=0, log=True,
            info=(tr("Point mass"), tr("The Einstein radius grows as the square root of the mass.")),
        )
        self.sigma = ParameterSlider(
            tr("Velocity dispersion σ (km/s)"), 50, 1500, 250, decimals=0, step=10,
            info=(tr("Velocity dispersion"), tr("How fast stars or galaxies move inside the lens. It measures the "
                      "total mass: typical galaxies 150–300 km/s, clusters 800–1500 km/s. θ_E ∝ σ².")),
        )
        self.z_lens = ParameterSlider(tr("Lens redshift"), 0.05, 2.0, 0.4, decimals=2, step=0.05,
                                      info=(tr("Lens redshift"), tr("Lenses halfway to the source are the most efficient.")))
        self.z_source = ParameterSlider(tr("Source redshift"), 0.1, 6.0, 2.0, decimals=2, step=0.05,
                                        info=(tr("Source redshift"), tr("The source must lie behind the lens.")))
        for w in (self.mass, self.sigma, self.z_lens, self.z_source):
            ll.addWidget(w)
        self.controls.addWidget(lens)

        src = QGroupBox(tr("2 · The background"))
        sl = QVBoxLayout(src)
        self.background = QComboBox()
        self.background.addItem(tr("A single galaxy (drag to move)"), "single")
        self.background.addItem(tr("A field of galaxies"), "field")
        sl.addWidget(labelled_row(tr("Background"), self.background))
        self.source_size = ParameterSlider(tr("Source size (fraction of θ_E)"), 0.05, 0.8, 0.2, decimals=2, step=0.01)
        sl.addWidget(self.source_size)
        self.show_ring = QCheckBox(tr("Show Einstein radius"))
        self.show_ring.setChecked(True)
        self.show_source = QCheckBox(tr("Mark the true source position"))
        self.show_source.setChecked(True)
        self.no_lens = QCheckBox(tr("Switch the lens off"))
        self.auto_zoom = QCheckBox(tr("Zoom automatically to the Einstein radius"))
        self.auto_zoom.setToolTip(tr("Off: the view has a fixed size, so a heavier lens makes a visibly bigger ring. "
                                      "On: the view always spans four Einstein radii."))
        for w in (self.show_ring, self.show_source, self.no_lens, self.auto_zoom):
            sl.addWidget(w)
        self.controls.addWidget(src)

        results = QGroupBox(tr("Measurements"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("warning")
        self.banner.hide()
        self.display.addWidget(self.banner)
        self.canvas = LensCanvas()
        self.display.addWidget(self.canvas, 1)

        for w in (self.mass, self.sigma, self.z_lens, self.z_source, self.source_size):
            w.valueChanged.connect(self.schedule_update)
        for w in (self.show_ring, self.show_source, self.no_lens, self.auto_zoom):
            w.toggled.connect(self.schedule_update)
        self.kind.currentIndexChanged.connect(self._kind_changed)
        self.background.currentIndexChanged.connect(self.schedule_update)
        self.canvas.sourceMoved.connect(self._move_source)
        self._kind_changed()

    # ---------------------------------------------------------- physics
    def lens_kind(self) -> str:
        return self.kind.currentData()

    def einstein_radius(self) -> float:
        zl, zs = self.z_lens.value(), self.z_source.value()
        if self.lens_kind() == "point":
            return lensing.einstein_radius_point(self.cosmo, self.mass.value(), zl, zs)
        return lensing.einstein_radius_sis(self.cosmo, self.sigma.value(), zl, zs)

    def lenses(self, theta_e: float):
        kind = self.lens_kind()
        if kind == "point":
            return [("point", 0.0, 0.0, theta_e)]
        if kind == "galaxy":
            return [("sis", 0.0, 0.0, theta_e)]
        return [
            ("sis", 0.0, 0.0, theta_e),
            ("sis", 0.9 * theta_e, 0.5 * theta_e, 0.35 * theta_e),
            ("sis", -0.7 * theta_e, -0.8 * theta_e, 0.3 * theta_e),
            ("sis", 0.3 * theta_e, -1.1 * theta_e, 0.2 * theta_e),
        ]

    def _kind_changed(self) -> None:
        point = self.lens_kind() == "point"
        self.mass.setVisible(point)
        self.sigma.setVisible(not point)
        if self.lens_kind() == "cluster" and self.sigma.value() < 700:
            self.sigma.setValue(1100, emit=False)
        elif self.lens_kind() == "galaxy" and self.sigma.value() > 600:
            self.sigma.setValue(250, emit=False)
        self.schedule_update()

    def _move_source(self, x: float, y: float) -> None:
        theta_e = max(self._theta_e, 1e-12)
        self.source_pos = (x / theta_e, y / theta_e)
        self.recompute()

    def field_of_view(self, theta_e: float) -> float:
        if self.auto_zoom.isChecked():
            return 4.0 * theta_e
        return FIXED_FIELD[self.lens_kind()]

    def _field_sky(self, n: int) -> np.ndarray:
        key = (n,)
        if key not in self._sky_cache:
            self._sky_cache[key] = lensing.background_sky(n=n, field_arcsec=1.0, seed=5)
        return self._sky_cache[key]

    # ------------------------------------------------------------ render
    def recompute(self) -> None:
        zl, zs = self.z_lens.value(), self.z_source.value()
        if zs <= zl + 0.01:
            self.banner.set_message("warning", "The source must be <b>behind</b> the lens: increase the source "
                                    "redshift or decrease the lens redshift.")
            self.banner.show()
            self._theta_e = 1.0
            return
        self.banner.hide()
        theta_e = self._theta_e = self.einstein_radius()
        field = self.field_of_view(theta_e)   # arcsec across the image
        coords = (np.arange(PIXELS) + 0.5) / PIXELS * field - field / 2
        tx, ty = np.meshgrid(coords, coords[::-1])
        if self.no_lens.isChecked():
            bx, by = tx, ty
        else:
            dx, dy = lensing.deflection(tx, ty, self.lenses(theta_e))
            bx, by = tx - dx, ty - dy
        sx, sy = self.source_pos[0] * theta_e, self.source_pos[1] * theta_e

        if self.background.currentData() == "single":
            size = self.source_size.value() * theta_e
            brightness = lensing.source_galaxy(bx, by, sx, sy, size=size)
            rgb = np.stack([brightness, brightness * 0.8, brightness * 0.55], axis=-1)
            rgb = np.clip(rgb * 1.3, 0, 1)
        else:
            sky_n = 512
            sky = self._field_sky(sky_n)
            # The background tile spans the view; wrap around so the field is endless.
            u = ((bx / field + 0.5) * sky_n).astype(int) % sky_n
            v = ((0.5 - by / field) * sky_n).astype(int) % sky_n
            rgb = sky[v, u]
        rgba = np.concatenate([rgb, np.ones(rgb.shape[:2] + (1,))], axis=-1)
        rgba = (rgba * 255).astype(np.uint8)

        circles = [(x, y, r) for _k, x, y, r in self.lenses(theta_e)] if self.show_ring.isChecked() else []
        if self.lens_kind() == "cluster" and circles:
            circles = circles[:1]
        source = (sx, sy) if self.show_source.isChecked() and self.background.currentData() == "single" else None
        self.canvas.set_frame(rgba, field, circles, source, f"field of view {field:.3g}″ × {field:.3g}″")
        self._update_summary(theta_e)

    def _update_summary(self, theta_e: float) -> None:
        zl, zs = self.z_lens.value(), self.z_source.value()
        d_l, d_s, d_ls = lensing.lens_distances(self.cosmo, zl, zs)
        radius_kpc = theta_e / lensing.RAD_TO_ARCSEC * d_l * 1e3
        mass = lensing.mass_inside_einstein_radius(self.cosmo, theta_e, zl, zs)
        beta = math.hypot(*self.source_pos)  # in units of θ_E
        if self.lens_kind() == "point":
            images = 2
            mu = lensing.point_lens_magnification(beta, 1.0)
        elif self.lens_kind() == "galaxy":
            images = 2 if beta < 1 else 1
            mu = 2 / max(beta, 1e-3) if beta < 1 else (1 + 1 / beta)
        else:
            images = None
            mu = None
        lines = [
            f"Einstein radius θ_E: <b>{theta_e:.3g}″</b> ({radius_kpc:.3g} kpc at the lens)",
            f"Mass inside θ_E: <b>{mass:.3g} M☉</b>",
            f"Distances: D_l = {d_l:.0f} Mpc, D_s = {d_s:.0f} Mpc, D_ls = {d_ls:.0f} Mpc",
            f"Source offset β: {beta:.2f} θ_E",
        ]
        if images is not None and not self.no_lens.isChecked():
            lines.append(f"Images of a point source: <b>{images}</b>")
            lines.append(f"Total magnification: <b>{mu:.2f}×</b>")
        if self.lens_kind() == "point" and theta_e < 1e-3:
            lines.append("<i>Such tiny rings cannot be resolved: this is <b>microlensing</b>, seen only as "
                         "a temporary brightening.</i>")
        self.summary.setText("<br>".join(lines))

    def guide_extra(self) -> str:
        return (
            "### " + tr("The key formula") + "\n\n"
            + tr("For a point mass the Einstein radius is") + "\n\n"
            "$$\\theta_E = \\sqrt{\\frac{4GM}{c^2}\\frac{D_{ls}}{D_l D_s}}$$\n\n"
            + tr("Measuring the ring's size therefore **weighs** the lens, dark matter included.")
        )
