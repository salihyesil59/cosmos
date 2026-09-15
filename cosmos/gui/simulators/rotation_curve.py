"""S6 — Galaxy Rotation Curve."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QVBoxLayout
from scipy import optimize

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import ParameterSlider, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.physics import datasets, rotation

UNIT = 1e10  # slider masses are in units of 10^10 solar masses
R_MAX = 32.0
R_REPORT = 30.0


class RotationCurveSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.data = datasets.illustrative_rotation_data()
        self.radius = np.linspace(0.2, R_MAX, 300)

        visible = QGroupBox("Visible matter (stars and gas)")
        vl = QVBoxLayout(visible)
        self.bulge = ParameterSlider(
            "Bulge mass (10¹⁰ M☉)", 0.01, 10.0, 1.0, decimals=2, log=True,
            info=("Bulge", "The dense, roughly spherical collection of old stars at the centre of the galaxy."),
        )
        self.disk = ParameterSlider(
            "Disk mass (10¹⁰ M☉)", 0.1, 30.0, 5.0, decimals=2, log=True,
            info=("Disk", "The flat disk of stars and gas where the spiral arms are. Its brightness falls "
                  "exponentially with radius."),
        )
        self.scale = ParameterSlider(
            "Disk scale length (kpc)", 1.0, 8.0, 3.0, decimals=2, step=0.1,
            info=("Scale length", "The distance over which the disk's surface brightness drops by a factor e ≈ 2.7. "
                  "The Milky Way's is about 3 kpc."),
        )
        for w in (self.bulge, self.disk, self.scale):
            vl.addWidget(w)
        self.controls.addWidget(visible)

        dark = QGroupBox("Dark matter halo")
        dl = QVBoxLayout(dark)
        self.halo_on = QCheckBox("Include a dark matter halo")
        self.halo_on.setChecked(False)
        self.halo_on.setToolTip("Start without dark matter and see whether visible matter alone explains the data.")
        dl.addWidget(self.halo_on)
        self.halo = ParameterSlider(
            "Halo mass M200 (10¹⁰ M☉)", 1.0, 500.0, 30.0, decimals=1, log=True,
            info=("Halo mass", "Total dark matter mass within the radius where the average density is 200 times "
                  "the critical density (roughly 200 kpc for the Milky Way)."),
        )
        self.conc = ParameterSlider(
            "Concentration c", 3, 25, 10, decimals=1, step=0.5,
            info=("Concentration", "How centrally concentrated the NFW halo is. Larger values put more dark "
                  "matter near the centre."),
        )
        dl.addWidget(self.halo)
        dl.addWidget(self.conc)
        self.mond = QCheckBox("Use MOND instead of dark matter")
        self.mond.setToolTip("Modified Newtonian Dynamics: no dark matter, but gravity becomes stronger than "
                             "Newton's law at very low accelerations (below about 1.2 × 10⁻¹⁰ m/s²).")
        dl.addWidget(self.mond)
        fit = QPushButton("Fit halo to data")
        fit.setProperty("role", "primary")
        fit.setToolTip("Find the halo mass that best matches the data points for the current visible matter.")
        fit.clicked.connect(self._fit_halo)
        dl.addWidget(fit)
        self.controls.addWidget(dark)

        view = QGroupBox("Show")
        wl = QVBoxLayout(view)
        self.show_components = QCheckBox("Individual components")
        self.show_components.setChecked(True)
        self.show_kepler = QCheckBox("Keplerian fall-off (v ∝ 1/√r)")
        self.show_data = QCheckBox("Measured-style data points")
        self.show_data.setChecked(True)
        for w in (self.show_components, self.show_kepler, self.show_data):
            wl.addWidget(w)
            w.toggled.connect(self.schedule_update)
        wl.addWidget(muted_label("Data points are synthetic but have the flat shape measured in real spirals."))
        self.controls.addWidget(view)

        summary = QGroupBox(f"Inside {R_REPORT:.0f} kpc")
        sl = QVBoxLayout(summary)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        sl.addWidget(self.summary)
        self.controls.addWidget(summary)
        self.finish_controls()

        self.plot = PlotWidget(self._draw, csv_provider=self._csv, export_name="rotation_curve")
        self.display.addWidget(self.plot, 1)

        for w in (self.bulge, self.disk, self.scale, self.halo, self.conc):
            w.valueChanged.connect(self.schedule_update)
        self.halo_on.toggled.connect(self._halo_toggled)
        self.mond.toggled.connect(self._mond_toggled)
        self._halo_toggled(False)

    def bulge_mass(self) -> float:
        return self.bulge.value() * UNIT

    def disk_mass(self) -> float:
        return self.disk.value() * UNIT

    def halo_mass(self) -> float:
        return self.halo.value() * UNIT

    def _halo_toggled(self, on: bool) -> None:
        self.halo.setEnabled(on)
        self.conc.setEnabled(on)
        if on and self.mond.isChecked():
            self.mond.setChecked(False)
        self.schedule_update()

    def _mond_toggled(self, on: bool) -> None:
        if on and self.halo_on.isChecked():
            self.halo_on.setChecked(False)
        self.schedule_update()

    def model_velocity(self, r, bulge, disk, halo):
        """Total rotation speed of the current model (Newton + halo, or MOND)."""
        visible = rotation.total_velocity(bulge, disk)
        if self.mond.isChecked():
            return rotation.mond_velocity(r, visible)
        return rotation.total_velocity(bulge, disk, halo)

    def components(self, r):
        bulge = rotation.bulge_velocity(r, self.bulge_mass(), 0.5)
        disk = rotation.disk_velocity(r, self.disk_mass(), self.scale.value())
        halo = (
            rotation.nfw_velocity(r, self.halo_mass(), self.conc.value())
            if self.halo_on.isChecked()
            else np.zeros_like(np.asarray(r, dtype=float))
        )
        return bulge, disk, halo

    def recompute(self) -> None:
        r = np.array([R_REPORT])
        bulge, disk, halo = self.components(r)
        visible = float(rotation.total_velocity(bulge, disk)[0])
        total = float(self.model_velocity(r, bulge, disk, halo)[0])
        m_visible = float(rotation.enclosed_mass(R_REPORT, visible))
        m_total = float(rotation.enclosed_mass(R_REPORT, total))
        observed = float(np.interp(R_REPORT, self.data.radius_kpc, self.data.velocity_km_s))
        chi2 = self._chi2()
        dm_share = 1 - m_visible / m_total if m_total > 0 else 0
        share_label = "Missing mass MOND explains without dark matter" if self.mond.isChecked() else "Dark matter share"
        self.summary.setText(
            f"Speed from visible matter: <b>{visible:.0f} km/s</b><br>"
            f"Model total: <b>{total:.0f} km/s</b> (data ≈ {observed:.0f} km/s)<br>"
            f"Mass from visible matter: {m_visible:.2e} M☉<br>"
            f"Mass required by the model: {m_total:.2e} M☉<br>"
            f"{share_label}: <b>{dm_share:.0%}</b><br>"
            f"Fit quality χ²/point: <b>{chi2:.1f}</b> (about 1 is a good fit)"
        )
        self.plot.refresh()

    def _chi2(self, halo_mass: float | None = None) -> float:
        r = self.data.radius_kpc
        bulge = rotation.bulge_velocity(r, self.bulge_mass(), 0.5)
        disk = rotation.disk_velocity(r, self.disk_mass(), self.scale.value())
        if halo_mass is None:
            halo = rotation.nfw_velocity(r, self.halo_mass(), self.conc.value()) if self.halo_on.isChecked() else 0 * r
        else:
            halo = rotation.nfw_velocity(r, halo_mass, self.conc.value())
        model = self.model_velocity(r, bulge, disk, halo)
        return float(np.mean(((model - self.data.velocity_km_s) / self.data.error_km_s) ** 2))

    def _fit_halo(self) -> None:
        self.halo_on.setChecked(True)
        res = optimize.minimize_scalar(
            lambda logm: self._chi2(10**logm), bounds=(10, np.log10(5e12)), method="bounded"
        )
        self.halo.setValue(10**res.x / UNIT)
        self.recompute()

    def _draw(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        r = self.radius
        bulge, disk, halo = self.components(r)
        if self.show_data.isChecked():
            ax.errorbar(self.data.radius_kpc, self.data.velocity_km_s, yerr=self.data.error_km_s, fmt="o",
                        color=p.text, markersize=4, label="Data (illustrative)")
        if self.show_components.isChecked():
            ax.plot(r, bulge, color=p.series[4], linewidth=1.2, linestyle=":", label="Bulge")
            ax.plot(r, disk, color=p.series[1], linewidth=1.2, linestyle="--", label="Disk")
            if self.halo_on.isChecked():
                ax.plot(r, halo, color=p.series[2], linewidth=1.2, linestyle="-.", label="Dark matter halo")
        visible = rotation.total_velocity(bulge, disk)
        ax.plot(r, visible, color=p.series[3], linewidth=2, label="Visible matter only")
        if self.halo_on.isChecked():
            ax.plot(r, rotation.total_velocity(bulge, disk, halo), color=p.series[0], linewidth=2.6,
                    label="Visible + dark matter")
        if self.mond.isChecked():
            ax.plot(r, rotation.mond_velocity(r, visible), color=p.series[5], linewidth=2.6,
                    label="MOND (visible matter only)")
        if self.show_kepler.isChecked():
            rk = r[r > 8]
            ax.plot(rk, rotation.keplerian_velocity(rk, self.bulge_mass() + self.disk_mass()), color=p.muted,
                    linewidth=1, label="Keplerian: v ∝ 1/√r")
        ax.axvline(R_REPORT, color=p.border, linestyle=":")
        ax.set_xlim(0, R_MAX)
        ax.set_ylim(0, 350)
        ax.set_xlabel("Distance from the centre (kpc)")
        ax.set_ylabel("Orbital speed (km/s)")
        ax.set_title("Rotation curve of a spiral galaxy", fontsize=10)
        ax.legend(loc="lower right", fontsize=8, ncols=2)

    def _csv(self):
        r = self.radius
        bulge, disk, halo = self.components(r)
        total = self.model_velocity(r, bulge, disk, halo)
        rows = [[f"{x:.4g}", f"{b:.4g}", f"{d:.4g}", f"{h:.4g}", f"{t:.4g}"]
                for x, b, d, h, t in zip(r, bulge, disk, halo, total)]
        return ["radius_kpc", "bulge_km_s", "disk_km_s", "halo_km_s", "total_km_s"], rows
