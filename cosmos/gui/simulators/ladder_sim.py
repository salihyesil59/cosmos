"""S20 — Distance Ladder Builder."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr, tr_noop
from cosmos.physics import ladder

MONTE_CARLO_RUNS = 300

RUNG_NAMES = {
    "parallax": tr_noop("1 · Parallaxes → Leavitt law"),
    "calibrators": tr_noop("2 · Cepheid hosts → supernova M_B"),
    "flow": tr_noop("3 · Hubble-flow supernovae → H0"),
}


class LadderSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.result: ladder.LadderResult | None = None
        self.shift = 0.0
        self.monte_carlo: np.ndarray | None = None
        self._loading = False

        universe = QGroupBox(tr("0 · The toy universe"))
        ul = QVBoxLayout(universe)
        self.preset = QComboBox()
        self.preset.addItem(tr("Custom"), "custom")
        for key, (label, _settings) in ladder.PRESETS.items():
            self.preset.addItem(physics(label), key)
        ul.addWidget(labelled_row(tr("Observing programme"), self.preset, (
            tr("Presets"),
            tr("Toy versions of real programmes: how many stars and supernovae they measured and how precisely. "
               "The numbers they produce here are simulated, not the published results."))))
        self.true_h0 = ParameterSlider(
            tr("True H0 of the toy universe"), 60, 80, 73.0, decimals=1, step=0.5,
            info=(tr("Why can you set the truth?"),
                  tr("In a simulation you know the answer, so you can see whether the ladder recovers it. "
                     "Real astronomers never get this luxury — which is why systematic errors are so hard "
                     "to catch.")),
        )
        self.seed = ParameterSlider(tr("Random seed"), 1, 999, 1, decimals=0, step=1)
        ul.addWidget(self.true_h0)
        ul.addWidget(self.seed)
        self.controls.addWidget(universe)

        rung1 = QGroupBox(tr(RUNG_NAMES["parallax"]))
        r1 = QVBoxLayout(rung1)
        self.n_parallax = ParameterSlider(
            tr("Milky Way Cepheids with parallaxes"), 3, 300, 20, decimals=0, log=True,
            info=(tr("The first rung"),
                  tr("Parallax is pure geometry: the tiny shift of a star as the Earth orbits the Sun. It gives "
                     "the distance to nearby Cepheids, and so their true brightness.")),
        )
        self.parallax_error = ParameterSlider(
            tr("Parallax error (µas)"), 5, 500, 30, decimals=0, log=True,
            info=(tr("Micro-arcseconds"),
                  tr("A µas is the width of a coin on the Moon seen from Earth. Hipparcos reached about "
                     "1000 µas, HST spatial scanning and Gaia about 20–30 µas for these stars.")),
        )
        self.parallax_offset = ParameterSlider(
            tr("Parallax zero-point offset (µas) — systematic"), -40, 40, 0, decimals=1, step=1,
            info=(tr("A systematic error"),
                  tr("If every parallax is off by the same small amount, averaging more stars does not help. "
                     "Gaia's parallax zero point is corrected at the level of about 10–20 µas.")),
        )
        for w in (self.n_parallax, self.parallax_error, self.parallax_offset):
            r1.addWidget(w)
        self.controls.addWidget(rung1)

        rung2 = QGroupBox(tr(RUNG_NAMES["calibrators"]))
        r2 = QVBoxLayout(rung2)
        self.n_hosts = ParameterSlider(
            tr("Galaxies with Cepheids and a supernova"), 2, 100, 20, decimals=0, log=True,
            info=(tr("The bottleneck"),
                  tr("A type Ia supernova must explode in a galaxy close enough for HST or JWST to resolve its "
                     "Cepheids. Only about one such event happens every year or two.")),
        )
        self.per_host = ParameterSlider(tr("Cepheids per galaxy"), 5, 200, 40, decimals=0, log=True)
        self.cepheid_scatter = ParameterSlider(
            tr("Leavitt law scatter (mag)"), 0.05, 0.40, 0.15, decimals=2, step=0.01,
            info=(tr("Intrinsic scatter"),
                  tr("Cepheids of the same period are not exactly equally bright. Near-infrared observations "
                     "reduce the scatter and the effect of dust.")),
        )
        self.crowding = ParameterSlider(
            tr("Crowding bias (mag) — systematic"), -0.10, 0.10, 0.0, decimals=3, step=0.005,
            info=(tr("Blended stars"),
                  tr("In a distant galaxy a Cepheid can blend with its neighbours and look brighter than it is. "
                     "Positive values make every host look closer. JWST's sharper images test exactly this.")),
        )
        for w in (self.n_hosts, self.per_host, self.cepheid_scatter, self.crowding):
            r2.addWidget(w)
        self.controls.addWidget(rung2)

        rung3 = QGroupBox(tr(RUNG_NAMES["flow"]))
        r3 = QVBoxLayout(rung3)
        self.n_flow = ParameterSlider(
            tr("Supernovae in the Hubble flow"), 10, 2000, 100, decimals=0, log=True,
            info=(tr("Far enough to ignore local motions"),
                  tr("Between z ≈ 0.023 and 0.15 the expansion dominates over the galaxies' own motions, yet "
                     "the result hardly depends on dark energy.")),
        )
        self.sn_scatter = ParameterSlider(tr("Supernova scatter (mag)"), 0.08, 0.30, 0.13, decimals=2, step=0.01)
        r3.addWidget(self.n_flow)
        r3.addWidget(self.sn_scatter)
        self.controls.addWidget(rung3)

        row = QHBoxLayout()
        observe = QPushButton(tr("🔭 New observation"))
        observe.setProperty("role", "primary")
        observe.setToolTip(tr("The same programme with new random measurement errors."))
        observe.clicked.connect(self._new_observation)
        repeat = QPushButton(tr("Repeat {count}×").format(count=MONTE_CARLO_RUNS))
        repeat.setToolTip(tr("Run the whole ladder many times: the spread of H0 is the real error bar."))
        repeat.clicked.connect(self.run_monte_carlo)
        row.addWidget(observe)
        row.addWidget(repeat)
        self.controls.addLayout(row)

        results = QGroupBox(tr("Your H0"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Simulated measurements. Real ladders add anchors such as the LMC and "
                                    "NGC 4258, and fit everything at once.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.rungs_plot = PlotWidget(self._draw_rungs, csv_provider=self._csv, export_name="distance_ladder")
        self.budget_plot = PlotWidget(self._draw_budget, export_name="h0_error_budget")
        tabs.addTab(self.rungs_plot, tr("The three rungs"))
        tabs.addTab(self.budget_plot, tr("Error budget"))
        self.display.addWidget(tabs, 1)

        self.inputs = (self.true_h0, self.seed, self.n_parallax, self.parallax_error, self.parallax_offset,
                       self.n_hosts, self.per_host, self.cepheid_scatter, self.crowding, self.n_flow,
                       self.sn_scatter)
        for w in self.inputs:
            w.valueChanged.connect(self._changed)
        self.preset.currentIndexChanged.connect(self._load_preset)
        self.recompute()

    # ------------------------------------------------------------ inputs
    def settings(self) -> ladder.LadderSettings:
        return ladder.LadderSettings(
            true_h0=self.true_h0.value(),
            n_parallax=int(round(self.n_parallax.value())),
            parallax_error_uas=self.parallax_error.value(),
            parallax_offset_uas=self.parallax_offset.value(),
            n_hosts=int(round(self.n_hosts.value())),
            cepheids_per_host=int(round(self.per_host.value())),
            cepheid_scatter=self.cepheid_scatter.value(),
            crowding_bias=self.crowding.value(),
            n_flow=int(round(self.n_flow.value())),
            sn_scatter=self.sn_scatter.value(),
            seed=int(self.seed.value()),
        )

    def _load_preset(self, *_args) -> None:
        key = self.preset.currentData()
        if key not in ladder.PRESETS:
            return
        s = ladder.PRESETS[key][1]
        self._loading = True
        for widget, value in ((self.n_parallax, s.n_parallax), (self.parallax_error, s.parallax_error_uas),
                              (self.parallax_offset, 0.0), (self.n_hosts, s.n_hosts),
                              (self.per_host, s.cepheids_per_host), (self.cepheid_scatter, s.cepheid_scatter),
                              (self.crowding, 0.0), (self.n_flow, s.n_flow), (self.sn_scatter, s.sn_scatter)):
            widget.setValue(value, emit=False)
        self._loading = False
        self.monte_carlo = None
        self.recompute()

    def _changed(self, *_args) -> None:
        if self._loading:
            return
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(0)
        self.preset.blockSignals(False)
        self.monte_carlo = None
        self.schedule_update()

    def _new_observation(self) -> None:
        self.seed.setValue(int(self.seed.value()) % 999 + 1)

    def run_monte_carlo(self) -> None:
        self.monte_carlo = ladder.monte_carlo(self.settings(), MONTE_CARLO_RUNS)
        self._refresh_text()
        self.budget_plot.refresh()

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        s = self.settings()
        self.result = ladder.build(s)
        self.shift = ladder.systematic_shift(s)
        self._refresh_text()
        self.rungs_plot.refresh()
        self.budget_plot.refresh()

    def _refresh_text(self) -> None:
        r = self.result
        tension = r.tension_with(ladder.PLANCK_H0)
        lines = [
            tr("H0 = <b>{h0} ± {error} km/s/Mpc</b> ({percent}%)")
            .format(h0=f"{r.h0:.2f}", error=f"{r.h0_error:.2f}", percent=f"{r.error_percent:.2f}"),
            tr("True value of this toy universe: {truth}; off by {miss}")
            .format(truth=f"{r.settings.true_h0:.1f}", miss=f"{r.h0 - r.settings.true_h0:+.2f}"),
            "",
        ]
        for key in ladder.RUNGS:
            lines.append(tr("{rung}: ± {percent}%").format(rung=tr(RUNG_NAMES[key]),
                                                           percent=f"{r.budget_percent[key]:.2f}"))
        lines += ["", tr("Systematic shift, not in the error bar: <b>{shift} km/s/Mpc</b>")
                  .format(shift=f"{self.shift:+.2f}")]
        if self.monte_carlo is not None:
            lines.append(tr("{count} repeats: mean {mean}, spread ± {spread}")
                         .format(count=len(self.monte_carlo), mean=f"{self.monte_carlo.mean():.2f}",
                                 spread=f"{self.monte_carlo.std(ddof=1):.2f}"))
        lines.append(tr("Difference from Planck (67.4 ± 0.5): <b>{sigma}σ</b>").format(sigma=f"{tension:.1f}"))
        self.summary.setText("<br>".join(lines))

        dominant = tr(RUNG_NAMES[r.dominant])
        if abs(self.shift) > max(r.h0_error, 0.3):
            self.banner.set_message(
                "danger",
                tr("<b>The systematic error is larger than the error bar.</b> H0 is shifted by {shift} km/s/Mpc, "
                   "and no amount of extra data will reveal it — only an independent check can.")
                .format(shift=f"{self.shift:+.2f}"))
        else:
            self.banner.set_message(
                "info",
                tr("<b>Simulated ladder.</b> The weakest rung right now is <b>{rung}</b>: improving the others "
                   "hardly changes the total, because errors add in quadrature.").format(rung=dominant))

    # ------------------------------------------------------------- plots
    def _draw_rungs(self, fig) -> None:
        p = theme().palette
        r = self.result
        axes = fig.subplots(1, 3)

        ax = axes[0]
        r1 = r.rung1
        mu = ladder.distance_modulus(1e6 / r1.parallax_uas)
        absolute = r1.apparent_mag - mu
        err = 5 / ladder.LN10 * r1.parallax_error_uas / r1.parallax_uas
        ax.errorbar(r1.log_period, absolute, yerr=err, fmt="o", markersize=3, color=p.series[0],
                    elinewidth=0.6, alpha=0.8)
        lp = np.linspace(0.3, 1.7, 20)
        ax.plot(lp, ladder.leavitt_magnitude(lp, r1.zero_point), color=p.accent2, linewidth=1.8,
                label=f"a = {r1.zero_point:.3f} ± {r1.zero_point_error:.3f}")
        ax.invert_yaxis()
        ax.set_xlabel("log period (days)", fontsize=8)
        ax.set_ylabel("absolute magnitude M", fontsize=8)
        ax.set_title("1 · Leavitt law from parallaxes", fontsize=9)
        ax.legend(fontsize=7, loc="lower right")

        ax = axes[1]
        r2 = r.rung2
        mb = r2.sn_mag - r2.modulus
        err = np.sqrt(r.settings.sn_scatter**2 + r2.modulus_error**2)
        ax.errorbar(r2.modulus, mb, yerr=err, fmt="s", markersize=3.5, color=p.series[1], elinewidth=0.6)
        ax.axhline(r2.sn_absolute, color=p.accent2, linewidth=1.8,
                   label=f"M_B = {r2.sn_absolute:.3f} ± {r2.sn_absolute_error:.3f}")
        ax.axhline(ladder.SN_ABSOLUTE_MAGNITUDE, color=p.muted, linestyle=":", linewidth=1, label="true M_B")
        ax.invert_yaxis()
        ax.set_xlabel("Cepheid distance modulus μ", fontsize=8)
        ax.set_ylabel("supernova M_B = m − μ", fontsize=8)
        ax.set_title("2 · Calibrating the supernovae", fontsize=9)
        ax.legend(fontsize=7, loc="lower right")

        ax = axes[2]
        r3 = r.rung3
        mu_flow = r3.mag - r2.sn_absolute
        distance = 10 ** ((mu_flow - 25) / 5)
        velocity = ladder.C_KM_S * r3.z * ladder.expansion_factor(r3.z)
        ax.plot(distance, velocity, "o", markersize=2.5, color=p.series[2], alpha=0.6)
        d = np.linspace(0, distance.max() * 1.05, 20)
        ax.plot(d, r.h0 * d, color=p.accent2, linewidth=1.8, label=f"H0 = {r.h0:.1f}")
        ax.plot(d, ladder.PLANCK_H0[0] * d, color=p.muted, linestyle="--", linewidth=1, label="Planck 67.4")
        ax.set_xlabel("distance (Mpc)", fontsize=8)
        ax.set_ylabel("cz f(z)  (km/s)", fontsize=8)
        ax.set_title("3 · The Hubble flow", fontsize=9)
        ax.legend(fontsize=7, loc="upper left")
        for axis in axes:
            axis.tick_params(labelsize=7)

    def _draw_budget(self, fig) -> None:
        p = theme().palette
        r = self.result
        left, right = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1.2]})

        names = ["parallax", "calibrators", "flow"]
        values = [r.budget_percent[k] for k in names]
        labels = ["1 · parallax", "2 · calibrators", "3 · Hubble flow", "total (quadrature)", "systematic shift"]
        bars = values + [r.error_percent, 100 * abs(self.shift) / r.h0]
        colours = [p.series[0], p.series[1], p.series[2], p.text, p.danger]
        y = np.arange(len(bars))[::-1]
        left.barh(y, bars, color=colours, alpha=0.85)
        for yi, value in zip(y, bars):
            left.text(value, yi, f" {value:.2f}%", va="center", fontsize=7, color=p.text)
        left.set_yticks(y)
        left.set_yticklabels(labels, fontsize=7)
        left.set_xlabel("uncertainty on H0 (%)", fontsize=8)
        left.set_xlim(0, max(bars) * 1.35 + 0.1)
        left.set_title("Where the error bar comes from", fontsize=9)

        ax = right
        grid = np.linspace(60, 86, 400)
        for (value, error), colour, label in ((ladder.PLANCK_H0, p.series[3], "Planck 2018 (CMB)"),
                                              (ladder.SHOES_H0, p.series[4], "SH0ES 2022")):
            ax.axvspan(value - error, value + error, color=colour, alpha=0.18, linewidth=0, label=label)
        if self.monte_carlo is not None:
            ax.hist(self.monte_carlo, bins=30, density=True, color=p.series[0], alpha=0.7,
                    label=f"{len(self.monte_carlo)} repeats of your ladder")
        gaussian = np.exp(-0.5 * ((grid - r.h0) / r.h0_error) ** 2) / (r.h0_error * np.sqrt(2 * np.pi))
        ax.plot(grid, gaussian, color=p.accent2, linewidth=1.8, label="this observation ± error")
        ax.axvline(r.settings.true_h0, color=p.text, linestyle=":", linewidth=1.2, label="true value")
        ax.set_xlim(max(55, r.h0 - 5 * r.h0_error), min(95, r.h0 + 5 * r.h0_error))
        ax.set_xlabel("H0 (km/s/Mpc)", fontsize=8)
        ax.set_yticks([])
        ax.set_title("Your H0 and the tension", fontsize=9)
        ax.legend(fontsize=6.5, loc="upper left")
        for axis in (left, right):
            axis.tick_params(labelsize=7)

    def _csv(self):
        r = self.result
        rows = [["parallax", f"{lp:.4f}", f"{par:.2f}", f"{m:.4f}", ""]
                for lp, par, m in zip(r.rung1.log_period, r.rung1.parallax_uas, r.rung1.apparent_mag)]
        rows += [["host", "", "", f"{sn_mag:.4f}", f"{mu:.4f}"]
                 for sn_mag, mu in zip(r.rung2.sn_mag, r.rung2.modulus)]
        rows += [["flow", f"{z:.5f}", "", f"{m:.4f}", ""] for z, m in zip(r.rung3.z, r.rung3.mag)]
        return ["rung", "log_period_or_z", "parallax_uas", "apparent_mag", "cepheid_modulus"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        r = self.result
        mc_spread = float(self.monte_carlo.std(ddof=1)) if self.monte_carlo is not None else float("nan")
        return {
            "preset": self.preset.currentData(),
            "h0": r.h0,
            "h0_error": r.h0_error,
            "error_percent": r.error_percent,
            "dominant": r.dominant,
            "n_parallax": r.settings.n_parallax,
            "parallax_error": r.settings.parallax_error_uas,
            "parallax_offset": r.settings.parallax_offset_uas,
            "n_hosts": r.settings.n_hosts,
            "n_flow": r.settings.n_flow,
            "systematic_shift": abs(self.shift),
            "tension_sigma": r.tension_with(ladder.PLANCK_H0),
            "mc_runs": 0 if self.monte_carlo is None else len(self.monte_carlo),
            "mc_mismatch": abs(mc_spread / r.h0_error - 1) if self.monte_carlo is not None else float("nan"),
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("How the errors combine") + "\n\n"
            + tr("The three rungs are independent, so their percentage errors add **in quadrature**:\n\n"
                 "$$\\sigma_{H_0}/H_0 = \\sqrt{\\sigma_1^2 + \\sigma_2^2 + \\sigma_3^2}$$\n\n"
                 "Halving the largest term helps far more than eliminating the smallest. A **systematic** "
                 "shift is different: it moves the answer without widening the error bar, and repeating "
                 "the measurement reproduces it faithfully.")
        )
