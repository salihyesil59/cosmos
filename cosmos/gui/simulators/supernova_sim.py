"""S16 — Supernova Ia Discovery."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QRadioButton,
    QTabWidget,
    QVBoxLayout,
)

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, InfoButton, ParameterSlider, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import supernovae as sn
from cosmos.physics.cosmology import no_big_bang_boundary

CONFIDENCE = {2.30: "68%", 6.18: "95%", 11.83: "99.7%"}
PLANCK_H0 = 67.4
SHOES_H0 = 73.0


class SupernovaSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)

        data = QGroupBox(tr("1 · Data"))
        dl = QVBoxLayout(data)
        self.sample_box = QComboBox()
        for key, factory in sn.SAMPLES.items():
            sample = factory()
            self.sample_box.addItem(sample.label, key)
            self.sample_box.setItemData(self.sample_box.count() - 1, sample.description, Qt.ToolTipRole)
        dl.addWidget(labelled_row(tr("Sample"), self.sample_box, (
            tr("Three samples"),
            tr("The first two are generated inside the app from a flat universe with Ωm = 0.3, mimicking the "
                "numbers, redshifts and scatter of real surveys. The third is the real Pantheon+ compilation "
                "as published, so the fit you get is the measurement itself."))))
        self.flat = QCheckBox(tr("Assume a flat universe (ΩΛ = 1 − Ωm)"))
        self.flat.setToolTip(tr("An extra assumption supported by the CMB. It makes the evidence much stronger."))
        dl.addWidget(self.flat)
        self.controls.addWidget(data)

        models = QGroupBox(tr("2 · Compare with models"))
        ml = QVBoxLayout(models)
        self.model_boxes = {}
        for key, label, default in [
            ("empty", tr("Empty universe (Ωm = 0, ΩΛ = 0)"), True),
            ("eds", tr("Matter only (Ωm = 1, ΩΛ = 0)"), True),
            ("open", tr("Low density, no dark energy (Ωm = 0.3, ΩΛ = 0)"), False),
            ("best", tr("Best fit to the data"), True),
        ]:
            box = QCheckBox(label)
            box.setChecked(default)
            box.toggled.connect(self.schedule_update)
            ml.addWidget(box)
            self.model_boxes[key] = box
        self.controls.addWidget(models)

        calib = QGroupBox(tr("3 · Calibrate the brightness → H0"))
        cl = QVBoxLayout(calib)
        self.cepheid = QRadioButton(tr("Cepheids (M = {value})").format(value=sn.M_CEPHEID))
        self.cepheid.setToolTip(tr("Local distance ladder: parallax → Cepheids → supernovae (SH0ES)."))
        self.inverse = QRadioButton(tr("CMB + BAO (M = {value})")
                                    .format(value=f"{sn.M_INVERSE_LADDER:.2f}"))
        self.inverse.setToolTip(tr("Inverse distance ladder: the CMB sound horizon calibrates BAO, which calibrates "
                                    "the supernovae."))
        self.custom = QRadioButton(tr("Your own value"))
        self.cepheid.setChecked(True)
        group = QButtonGroup(self)
        for b in (self.cepheid, self.inverse, self.custom):
            group.addButton(b)
            cl.addWidget(b)
            b.toggled.connect(self.schedule_update)
        self.magnitude = ParameterSlider(tr("Absolute magnitude M"), -19.8, -18.8, -19.3, decimals=3, step=0.01)
        self.magnitude.valueChanged.connect(self.schedule_update)
        cl.addWidget(self.magnitude)
        cl.addWidget(InfoButton(
            tr("Why calibration matters"),
            tr("Supernovae tell us relative distances very precisely, but not the absolute scale. Their true "
                "brightness M must be calibrated with Cepheids (local) or with the sound horizon (early universe). "
                "The two calibrations differ by about 0.15 magnitudes: this is the Hubble tension."),
        ))
        self.controls.addWidget(calib)

        results = QGroupBox(tr("Results"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.hubble_plot = PlotWidget(self._draw_hubble, csv_provider=self._csv, export_name="supernova_hubble_diagram")
        self.plane_plot = PlotWidget(self._draw_plane, export_name="supernova_omega_plane")
        self.h0_plot = PlotWidget(self._draw_h0, export_name="supernova_h0")
        tabs.addTab(self.hubble_plot, tr("Hubble diagram"))
        tabs.addTab(self.plane_plot, tr("Ωm–ΩΛ plane"))
        tabs.addTab(self.h0_plot, tr("Hubble constant"))
        self.display.addWidget(tabs, 1)

        self.sample_box.currentIndexChanged.connect(self._load_sample)
        self.flat.toggled.connect(self.schedule_update)
        self._load_sample()

    # ------------------------------------------------------------ compute
    def _load_sample(self) -> None:
        self.sample = sn.SAMPLES[self.sample_box.currentData()]()
        if self.sample.real:
            self.banner.set_message(
                "success",
                tr("<b>Real measurements.</b> {citation}. The fit below is your own, made with diagonal errors "
                   "only, so it will not match the published numbers exactly.")
                .format(citation=self.sample.citation))
        else:
            self.banner.set_message(
                "info",
                tr("<b>Simulated data.</b> These supernovae are generated inside the app to resemble real "
                   "surveys, so you can repeat the 1998 analysis yourself. Switch the sample to Pantheon+ "
                   "for the real measurements."))
        self.fit = sn.fit_grid(self.sample, n=61)
        self.flat_fit = sn.fit_flat(self.sample)
        self.recompute()

    def absolute_magnitude(self) -> float:
        if self.cepheid.isChecked():
            return sn.M_CEPHEID
        if self.inverse.isChecked():
            return sn.M_INVERSE_LADDER
        return self.magnitude.value()

    def best(self) -> tuple[float, float]:
        if self.flat.isChecked():
            return self.flat_fit.best_om, self.flat_fit.best_ol
        return self.fit.best_om, self.fit.best_ol

    def hubble_constant(self) -> float:
        return self._h0_for(self.absolute_magnitude())

    def recompute(self) -> None:
        self.magnitude.setEnabled(self.custom.isChecked())
        om, ol = self.best()
        sigma = self.flat_fit.acceleration_sigma if self.flat.isChecked() else self.fit.acceleration_sigma
        h0 = self.hubble_constant()
        q0 = om / 2 - ol
        self.summary.setText(
            tr("Best fit: <b>Ωm = {om}, ΩΛ = {ol}</b>").format(om=f"{om:.2f}", ol=f"{ol:.2f}")
            + (" " + tr("(flat)") if self.flat.isChecked() else "") + "<br>"
            + tr("Deceleration parameter q0 = <b>{q0}</b> ({trend})<br>"
                 "Evidence for acceleration: <b>{sigma}σ</b><br>"
                 "Evidence for dark energy (ΩΛ > 0, no flatness assumed): {dark_energy}σ<br>"
                 "Hubble constant with this calibration: <b>{h0} km/s/Mpc</b><br>"
                 "Number of supernovae: {count}")
            .format(q0=f"{q0:+.2f}", trend=tr("accelerating") if q0 < 0 else tr("decelerating"),
                    sigma=f"{sigma:.1f}", dark_energy=f"{self.fit.dark_energy_sigma:.1f}",
                    h0=f"{h0:.1f}", count=len(self.sample.z))
        )
        for plot in (self.hubble_plot, self.plane_plot, self.h0_plot):
            plot.refresh()

    # --------------------------------------------------------------- plots
    def _draw_hubble(self, fig) -> None:
        p = theme().palette
        s = self.sample
        h0 = self.hubble_constant()
        big = 5 * np.log10(sn.C_KM_S / h0) + 25
        mu_obs = s.m - self.absolute_magnitude()
        z = np.logspace(np.log10(0.01), np.log10(s.z.max() * 1.05), 200)
        empty = sn.distance_modulus_shape(z, 0.0, 0.0) + big
        empty_at_data = sn.distance_modulus_shape(s.z, 0.0, 0.0) + big
        grid = fig.add_gridspec(2, 1, height_ratios=[2, 1.3], hspace=0.05)
        ax = fig.add_subplot(grid[0])
        ax2 = fig.add_subplot(grid[1], sharex=ax)
        ax.errorbar(s.z, mu_obs, yerr=s.error, fmt="o", markersize=2.5, color=p.muted, alpha=0.6, elinewidth=0.6,
                    label="Supernovae (real)" if self.sample.real else "Simulated supernovae")
        ax2.errorbar(s.z, mu_obs - empty_at_data, yerr=s.error, fmt="o", markersize=2.5, color=p.muted, alpha=0.4,
                     elinewidth=0.5)
        # Binned residuals are easier to read.
        edges = np.quantile(s.z, np.linspace(0, 1, 9))
        centres, means, errs = [], [], []
        for lo, hi in zip(edges[:-1], edges[1:]):
            sel = (s.z >= lo) & (s.z <= hi)
            if sel.sum() > 2:
                centres.append(np.mean(s.z[sel]))
                means.append(np.mean((mu_obs - empty_at_data)[sel]))
                errs.append(np.std((mu_obs - empty_at_data)[sel]) / np.sqrt(sel.sum()))
        ax2.errorbar(centres, means, yerr=errs, fmt="s", color=p.text, markersize=5, zorder=5, label="binned")
        best_om, best_ol = self.best()
        models = [
            ("empty", 0.0, 0.0, p.series[2], "Empty"),
            ("eds", 1.0, 0.0, p.series[3], "Matter only"),
            ("open", 0.3, 0.0, p.series[4], "Ωm = 0.3, no Λ"),
            ("best", best_om, best_ol, p.series[0], f"Best fit ({best_om:.2f}, {best_ol:.2f})"),
        ]
        for key, om, ol, color, label in models:
            if not self.model_boxes[key].isChecked():
                continue
            mu = sn.distance_modulus_shape(z, om, ol) + big
            ax.plot(z, mu, color=color, linewidth=1.8, label=label)
            ax2.plot(z, mu - empty, color=color, linewidth=1.8)
        ax.set_xscale("log")
        ax.set_ylabel("Distance modulus μ (mag)", fontsize=8)
        ax.legend(loc="upper left", fontsize=7)
        ax.tick_params(labelbottom=False)
        ax2.axhline(0, color=p.border)
        ax2.set_ylim(-0.8, 0.6)
        ax2.set_xlabel("Redshift z", fontsize=8)
        ax2.set_ylabel("μ − μ(empty)", fontsize=8)
        ax2.text(0.012, 0.4, "above zero: fainter than in an empty universe → acceleration", fontsize=7,
                 color=p.muted)

    def _draw_plane(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        f = self.fit
        delta = f.chi2 - f.chi2_min
        levels = sorted(CONFIDENCE)
        ax.contourf(f.om, f.ol, delta, levels=[0] + levels, colors=[p.mix(p.accent, a) for a in (0.75, 0.5, 0.28)])
        ax.contour(f.om, f.ol, delta, levels=levels, colors=[p.accent], linewidths=0.8)
        om = np.linspace(0, 1.5, 100)
        ax.plot(om, 1 - om, color=p.muted, linestyle="--", linewidth=1)
        ax.text(1.05, -0.12, "flat", color=p.muted, fontsize=8)
        ax.plot(om, om / 2, color=p.accent2, linestyle=":", linewidth=1.2)
        ax.text(1.2, 0.66, "accelerating ↑\ndecelerating ↓", color=p.accent2, fontsize=8)
        nbb = no_big_bang_boundary(np.clip(om, 1e-3, None))
        ax.fill_between(om, nbb, 2.0, color=p.danger, alpha=0.15, linewidth=0)
        ax.text(0.05, 1.85, "no Big Bang", color=p.danger, fontsize=8)
        ax.axhline(0, color=p.border, linewidth=0.8)
        best_om, best_ol = self.best()
        ax.scatter([best_om], [best_ol], color=p.text, marker="*", s=90, zorder=5, label="best fit")
        if self.flat.isChecked():
            ax.plot(self.flat_fit.om, 1 - self.flat_fit.om, color=p.success, linewidth=2, alpha=0.6,
                    label="models allowed by the flatness assumption")
        ax.set_xlim(0, 1.5)
        ax.set_ylim(-0.5, 2.0)
        ax.set_xlabel("Ωm")
        ax.set_ylabel("ΩΛ")
        ax.set_title("Confidence regions: 68%, 95% and 99.7%", fontsize=9)
        ax.legend(loc="lower right", fontsize=8)

    def _draw_h0(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        cep = self._h0_for(sn.M_CEPHEID)
        inv = self._h0_for(sn.M_INVERSE_LADDER)
        mine = self.hubble_constant()
        rows = [
            ("This sample, Cepheid calibration", cep, p.series[1]),
            ("This sample, CMB + BAO calibration", inv, p.series[0]),
            ("Your current choice", mine, p.text),
        ]
        for i, (label, value, color) in enumerate(rows):
            ax.barh(i, value, color=color, height=0.5)
            ax.text(value + 0.3, i, f"{value:.1f}", va="center", color=p.text, fontsize=9)
        ax.axvline(PLANCK_H0, color=p.series[0], linestyle="--", linewidth=1)
        ax.text(PLANCK_H0 - 0.2, 2.45, "Planck 2018: 67.4", color=p.series[0], fontsize=8, ha="right")
        ax.axvline(SHOES_H0, color=p.series[1], linestyle="--", linewidth=1)
        ax.text(SHOES_H0 + 0.2, 2.45, "SH0ES 2022: 73.0", color=p.series[1], fontsize=8)
        ax.set_yticks(range(len(rows)), [r[0] for r in rows])
        ax.set_xlim(60, 80)
        ax.set_xlabel("H0 (km/s/Mpc)")
        ax.set_title("Same supernovae, different calibration of their brightness", fontsize=9)

    def _h0_for(self, magnitude: float) -> float:
        om, ol = self.best()
        shape = sn.distance_modulus_shape(self.sample.z, om, ol)
        w = 1 / self.sample.error**2
        offset = float(np.sum(w * (self.sample.m - shape)) / np.sum(w))
        return sn.C_KM_S / 10 ** ((offset - magnitude - 25) / 5)

    def _csv(self):
        s = self.sample
        rows = [[f"{z:.4f}", f"{m:.3f}", f"{e:.3f}"] for z, m, e in zip(s.z, s.m, s.error)]
        return ["redshift", "apparent_magnitude", "error"], rows
