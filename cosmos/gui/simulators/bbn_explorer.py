"""S11 — BBN Abundance Explorer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr, tr_noop
from cosmos.physics import bbn

ETA_MIN, ETA_MAX = 0.5, 20.0
LABELS = {"Yp": tr_noop("Helium-4 (mass fraction Yₚ)"), "D/H": tr_noop("Deuterium D/H"),
          "He3/H": tr_noop("Helium-3 ³He/H"), "Li7/H": tr_noop("Lithium-7 ⁷Li/H")}


class BBNExplorerSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.ab = None

        baryons = QGroupBox(tr("1 · Density of ordinary matter"))
        bl = QVBoxLayout(baryons)
        self.eta = ParameterSlider(
            tr("η₁₀  baryons per 10¹⁰ photons"), ETA_MIN, ETA_MAX,
            float(bbn.eta10_from_omega_b_h2(bbn.PLANCK_OMEGA_B_H2[0])), decimals=2, log=True,
            info=(tr("Baryon-to-photon ratio"),
                  tr("The number of protons and neutrons per photon, multiplied by 10¹⁰. It is the only free "
                          "parameter of standard nucleosynthesis. It is fixed by the density of ordinary matter: "
                          "η₁₀ = 273.9 Ω_b h².")),
        )
        bl.addWidget(self.eta)
        self.omega_label = QLabel()
        self.omega_label.setTextFormat(Qt.RichText)
        bl.addWidget(self.omega_label)
        row = QHBoxLayout()
        planck = QPushButton(tr("Planck CMB value"))
        planck.setToolTip(tr("Set the baryon density measured from the acoustic peaks of the CMB."))
        planck.clicked.connect(lambda: self.eta.setValue(float(bbn.eta10_from_omega_b_h2(bbn.PLANCK_OMEGA_B_H2[0]))))
        deut = QPushButton(tr("From deuterium"))
        deut.setToolTip(tr("Set the baryon density that reproduces the measured deuterium abundance."))
        deut.clicked.connect(self._from_deuterium)
        row.addWidget(planck)
        row.addWidget(deut)
        bl.addLayout(row)
        self.controls.addWidget(baryons)

        physics = QGroupBox(tr("2 · Change the physics"))
        pl = QVBoxLayout(physics)
        self.delta_neff = ParameterSlider(
            tr("ΔN_eff  extra neutrino-like species"), -1.0, 3.0, 0.0, decimals=2, step=0.1,
            info=(tr("Extra relativistic species"),
                  tr("Extra light particles add energy density, so the universe expands faster during BBN. Weak "
                          "reactions freeze out earlier with more neutrons, and more helium forms. BBN limits "
                          "ΔN_eff to about ±0.3.")),
        )
        pl.addWidget(self.delta_neff)
        self.lifetime = ParameterSlider(
            tr("Neutron lifetime (s)"), 860.0, 900.0, bbn.NEUTRON_LIFETIME_S, decimals=1, step=0.5,
            info=(tr("Neutron lifetime"),
                  tr("A free neutron decays in about 15 minutes. A longer lifetime leaves more neutrons when "
                          "deuterium finally forms, so more helium. Bottle experiments measure 878.4 s, beam "
                          "experiments about 888 s: an unsolved discrepancy.")),
        )
        pl.addWidget(self.lifetime)
        reset = QPushButton(tr("Standard physics"))
        reset.clicked.connect(self._reset_physics)
        pl.addWidget(reset)
        self.controls.addWidget(physics)

        view = QGroupBox(tr("3 · Show"))
        vl = QVBoxLayout(view)
        self.show_obs = QCheckBox(tr("Observed primordial abundances"))
        self.show_obs.setChecked(True)
        self.show_cmb = QCheckBox(tr("Baryon density from the CMB (Planck)"))
        self.show_cmb.setChecked(True)
        for box in (self.show_obs, self.show_cmb):
            box.toggled.connect(self.schedule_update)
            vl.addWidget(box)
        self.controls.addWidget(view)

        results = QGroupBox(tr("Predictions"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info")
        self.display.addWidget(self.banner)
        self.plot = PlotWidget(self._draw, export_name="bbn_abundances", csv_provider=self._csv)
        self.display.addWidget(self.plot, 1)

        for slider in (self.eta, self.delta_neff, self.lifetime):
            slider.valueChanged.connect(self.schedule_update)
        self.recompute()

    # ------------------------------------------------------------ model
    def _from_deuterium(self) -> None:
        eta = bbn.eta10_from_deuterium(bbn.OBSERVED["D/H"][0], self.delta_neff.value())
        self.eta.setValue(float(np.clip(eta, ETA_MIN, ETA_MAX)))

    def _reset_physics(self) -> None:
        self.delta_neff.setValue(0.0, emit=False)
        self.lifetime.setValue(bbn.NEUTRON_LIFETIME_S)

    def _abundances(self, eta):
        return bbn.abundances(eta, self.delta_neff.value(), self.lifetime.value())

    def state(self) -> dict:
        ab = self.ab if self.ab is not None else self._abundances(self.eta.value())
        return {
            "eta10": self.eta.value(),
            "omega_b_h2": float(bbn.omega_b_h2_from_eta10(self.eta.value())),
            "delta_neff": self.delta_neff.value(),
            "neutron_lifetime": self.lifetime.value(),
            "yp": float(ab.yp),
            "d_h": float(ab.d_h),
            "li7_h": float(ab.li7_h),
        }

    def recompute(self) -> None:
        eta = self.eta.value()
        self.ab = self._abundances(eta)
        omega = float(bbn.omega_b_h2_from_eta10(eta))
        self.omega_label.setText(
            tr("Ω_b h² = <b>{omega}</b>, so Ω_b = {omega_only} for h = 0.674<br>"
               "Planck CMB: Ω_b h² = {planck} ± {error}")
            .format(omega=f"{omega:.4f}", omega_only=f"{omega / 0.674**2:.3f}",
                    planck=bbn.PLANCK_OMEGA_B_H2[0], error=bbn.PLANCK_OMEGA_B_H2[1])
        )
        tension = bbn.tensions(self.ab)
        values = bbn.predicted(self.ab)
        lines = []
        for key, value in values.items():
            obs, err = bbn.OBSERVED[key]
            fmt = "{:.4f}" if key == "Yp" else "{:.3g}"
            mark = "✓" if abs(tension[key]) < 2 else "✗"
            lines.append(f"{mark} " + tr("{element}: <b>{value}</b> (observed {observed} ± {error}; "
                                        "{tension}σ)")
                         .format(element=tr(LABELS[key]), value=fmt.format(value),
                                 observed=fmt.format(obs), error=fmt.format(err),
                                 tension=f"{tension[key]:+.1f}"))
        t_d = bbn.deuterium_bottleneck_temperature(eta * 1e-10)
        y_simple, t_nuc = bbn.simple_helium_estimate(eta * 1e-10, self.lifetime.value(), self.delta_neff.value())
        lines += [
            "",
            tr("Deuterium survives below T ≈ <b>{kev} keV</b> ({kelvin} K), about <b>{minutes} minutes</b> "
               "after the Big Bang").format(kev=f"{t_d * 1e3:.0f}", kelvin=f"{t_d * 1.16e10:.2e}",
                                            minutes=f"{t_nuc / 60:.1f}"),
            tr("Back-of-the-envelope helium (all neutrons left then → ⁴He): Y ≈ {value}")
            .format(value=f"{y_simple:.3f}"),
            tr("Expansion speed-up during BBN: S = {value}")
            .format(value=f"{bbn.speedup_factor(self.delta_neff.value()):.3f}"),
        ]
        self.summary.setText("<br>".join(lines))
        good = [k for k, s in tension.items() if abs(s) < 2]
        if len(good) == 4:
            self.banner.set_message("success", tr("<b>All four light elements agree with observations.</b>"))
        elif set(good) >= {"Yp", "D/H", "He3/H"}:
            self.banner.set_message(
                "warning",
                tr("<b>Helium and deuterium agree, lithium does not.</b> This is the cosmological lithium "
                   "problem: the prediction is about three times the lithium seen in old stars. Most "
                   "astronomers suspect the stars have destroyed some of their lithium."))
        else:
            bad = ", ".join(tr(LABELS[k]) for k in tension if k not in good)
            self.banner.set_message("danger", tr("<b>This universe does not match the observed abundances:</b> "
                                                 "{elements}.").format(elements=bad))
        self.plot.refresh()

    # ---------------------------------------------------------------- draw
    def _draw(self, fig) -> None:
        if self.ab is None:
            return
        p = theme().palette
        eta_now = self.eta.value()
        grid_eta = np.logspace(np.log10(ETA_MIN), np.log10(ETA_MAX), 300)
        curve = self._abundances(grid_eta)
        standard = bbn.abundances(grid_eta)
        gs = fig.add_gridspec(3, 2, width_ratios=[1.25, 1])
        ax_y = fig.add_subplot(gs[0, 0])
        ax_d = fig.add_subplot(gs[1, 0], sharex=ax_y)
        ax_li = fig.add_subplot(gs[2, 0], sharex=ax_y)
        planck = bbn.eta10_from_omega_b_h2(bbn.PLANCK_OMEGA_B_H2[0])
        planck_err = bbn.ETA10_PER_OMEGA_B_H2 * bbn.PLANCK_OMEGA_B_H2[1]
        changed = self.delta_neff.value() != 0 or self.lifetime.value() != bbn.NEUTRON_LIFETIME_S

        panels = [(ax_y, [("Yp", curve.yp, standard.yp, p.series[0])]),
                  (ax_d, [("D/H", curve.d_h, standard.d_h, p.series[1]),
                          ("He3/H", curve.he3_h, standard.he3_h, p.series[4])]),
                  (ax_li, [("Li7/H", curve.li7_h, standard.li7_h, p.series[3])])]
        for ax, series in panels:
            for key, values, std, colour in series:
                ax.plot(grid_eta, values, color=colour, linewidth=2, label=LABELS[key])
                if changed:
                    ax.plot(grid_eta, std, color=colour, linewidth=1, linestyle="--", alpha=0.6)
                if self.show_obs.isChecked():
                    obs, err = bbn.OBSERVED[key]
                    ax.axhspan(obs - err, obs + err, color=colour, alpha=0.25, linewidth=0)
            if self.show_cmb.isChecked():
                ax.axvspan(planck - 2 * planck_err, planck + 2 * planck_err, color=p.success, alpha=0.25, linewidth=0)
            ax.axvline(eta_now, color=p.text, linewidth=1.2)
            ax.set_xscale("log")
            ax.legend(loc="best", fontsize=6.5)
            ax.tick_params(labelsize=7)
        ax_y.set_ylim(0.20, 0.30)
        ax_y.set_ylabel("Yₚ", fontsize=8)
        ax_y.set_title("Bands: observed.  Green: CMB." + ("  Dashed: standard physics." if changed else ""), fontsize=8)
        ax_d.set_yscale("log")
        ax_d.set_ylim(3e-6, 5e-4)
        ax_d.set_ylabel("relative to H", fontsize=8)
        ax_li.set_yscale("log")
        ax_li.set_ylim(5e-11, 3e-9)
        ax_li.set_ylabel("relative to H", fontsize=8)
        ax_li.set_xlabel("η₁₀ (baryons per 10¹⁰ photons)", fontsize=8)
        for ax in (ax_y, ax_d):
            ax.tick_params(labelbottom=False)

        ax = fig.add_subplot(gs[0:2, 1])
        times = np.logspace(0, 4, 300)
        xn = bbn.neutron_fraction(times, self.lifetime.value(), self.delta_neff.value())
        y_simple, t_nuc = bbn.simple_helium_estimate(eta_now * 1e-10, self.lifetime.value(), self.delta_neff.value())
        ax.plot(times, xn, color=p.series[5], linewidth=2, label="neutrons per nucleon")
        ax.axvline(t_nuc, color=p.accent2, linestyle="--", linewidth=1.2, label="deuterium bottleneck opens")
        ax.plot([t_nuc], [y_simple / 2], "o", color=p.accent2)
        ax.annotate(f"  Y ≈ 2 Xₙ = {y_simple:.3f}", (t_nuc, y_simple / 2), fontsize=7, color=p.text)
        ax.set_xscale("log")
        ax.set_ylim(0, 0.2)
        ax.set_xlabel("time after the Big Bang (s)", fontsize=7)
        ax.set_ylabel("neutron fraction Xₙ", fontsize=8)
        ax.set_title("Neutrons decay while waiting", fontsize=7)
        ax.legend(loc="lower left", fontsize=6.5)
        ax.tick_params(labelsize=7)

        ax = fig.add_subplot(gs[2, 1])
        x_h = 1 - float(self.ab.yp)
        masses = [x_h, float(self.ab.yp), 2 * float(self.ab.d_h) * x_h, 3 * float(self.ab.he3_h) * x_h,
                  7 * float(self.ab.li7_h) * x_h]
        names = ["H", "⁴He", "D", "³He", "⁷Li"]
        ax.barh(names, masses, color=[p.series[6], p.series[0], p.series[1], p.series[4], p.series[3]])
        ax.set_xscale("log")
        ax.set_xlim(1e-10, 2)
        ax.invert_yaxis()
        ax.set_xlabel("share of matter by mass", fontsize=7)
        ax.tick_params(labelsize=7)

    def _csv(self):
        grid = np.logspace(np.log10(ETA_MIN), np.log10(ETA_MAX), 200)
        ab = self._abundances(grid)
        rows = [[f"{e:.4f}", f"{float(bbn.omega_b_h2_from_eta10(e)):.5f}", f"{y:.5f}", f"{d:.4e}", f"{h:.4e}",
                 f"{li:.4e}"]
                for e, y, d, h, li in zip(grid, ab.yp, ab.d_h, ab.he3_h, ab.li7_h)]
        return ["eta10", "omega_b_h2", "Yp", "D_H", "He3_H", "Li7_H"], rows

    def guide_extra(self) -> str:
        return (
            "### " + tr("About the model") + "\n\n"
            + tr(
                "The curves come from fitting formulas that reproduce full nuclear reaction network calculations to a "
                "few percent near the observed baryon density (Steigman 2007, 2012); far from it they are only "
                "qualitative. The neutron-fraction panel is the simple picture from lesson L4.3: neutrons freeze out "
                "at about 0.8 MeV and decay until deuterium can survive.")
        )
