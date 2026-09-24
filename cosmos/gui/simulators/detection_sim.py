"""S29 — Dark Matter Detection."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QPushButton, QTabWidget, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr, tr_noop
from cosmos.physics import detection as det

CUSTOM = "custom"
EXPERIMENT_LABELS = {
    "lz": tr_noop("A large xenon detector (like LZ, 2024)"),
    "argon": tr_noop("A large argon detector (like DarkSide-20k)"),
    "germanium": tr_noop("A cryogenic germanium detector (like SuperCDMS)"),
    "silicon": tr_noop("A small, very low threshold silicon detector"),
}
TARGET_LABELS = {
    "xenon": tr_noop("Xenon (A = 131)"),
    "argon": tr_noop("Argon (A = 40)"),
    "germanium": tr_noop("Germanium (A = 73)"),
    "silicon": tr_noop("Silicon (A = 28)"),
}
MASSES = np.geomspace(1.0, 1e4, 70)
LZ_2024 = (36.0, 2.2e-48)          # the published best limit, for orientation


def sci(value: float) -> str:
    """1.2 × 10⁻⁴⁶ as rich text."""
    if not math.isfinite(value) or value <= 0:
        return "–"
    exponent = math.floor(math.log10(value))
    return f"{value / 10**exponent:.1f} × 10<sup>{exponent}</sup>"


class DetectionSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self._applying = False
        self._run = 0
        self.report: dict = {}
        self._curves: dict = {}

        box = QGroupBox(tr("1 · The detector"))
        bl = QVBoxLayout(box)
        self.preset = QComboBox()
        for key in det.EXPERIMENTS:
            self.preset.addItem(tr(EXPERIMENT_LABELS[key]), key)
        self.preset.addItem(tr("Your own settings"), CUSTOM)
        bl.addWidget(labelled_row(tr("Experiment"), self.preset, (
            tr("Big and quiet, or small and sensitive"),
            tr("Heavy xenon and argon detectors hold tonnes of target and see heavy WIMPs best. Small "
               "cryogenic crystals feel far gentler recoils, so they reach light WIMPs that the big "
               "detectors cannot."))))
        self.target = QComboBox()
        for key in det.TARGETS:
            self.target.addItem(tr(TARGET_LABELS[key]), key)
        bl.addWidget(labelled_row(tr("Target nucleus"), self.target, (
            tr("Why heavy nuclei"),
            tr("A WIMP scatters off the whole nucleus at once, so the cross-section grows as A². But a "
               "heavy nucleus recoils less from a light WIMP, just as a truck barely moves when a "
               "tennis ball hits it."))))
        self.exposure = ParameterSlider(
            tr("Exposure (tonne-years)"), 1e-4, 1000.0, 4.2, decimals=4, log=True,
            info=(tr("Mass × time"), tr("Twice the target for twice as long gives four times the events — "
                                        "and, with no background, a limit four times lower.")))
        self.threshold = ParameterSlider(
            tr("Energy threshold (keV)"), 0.05, 50.0, 5.0, decimals=2, log=True,
            info=(tr("The gentlest recoil you can see"),
                  tr("A light WIMP can only give small kicks. Below the threshold they are lost, which is "
                     "why every detector goes blind below some WIMP mass.")))
        self.background = ParameterSlider(
            tr("Expected background events"), 0.0, 50.0, 1.0, decimals=1, step=0.5,
            info=(tr("What else makes a recoil"),
                  tr("Radioactivity, neutrons and, eventually, neutrinos from the Sun and the atmosphere "
                     "produce events that look like a WIMP. With background, a null result limits less.")))
        for w in (self.exposure, self.threshold, self.background):
            bl.addWidget(w)
        self.controls.addWidget(box)

        wimp = QGroupBox(tr("2 · The WIMP"))
        wl = QVBoxLayout(wimp)
        self.mass = ParameterSlider(
            tr("WIMP mass (GeV)"), 1.0, 1e4, 50.0, decimals=1, log=True,
            info=(tr("How heavy"), tr("A proton is about 1 GeV. The classic WIMP is tens to thousands of GeV.")))
        self.log_sigma = ParameterSlider(
            tr("Cross-section per nucleon: log₁₀ σ (cm²)"), -50.0, -40.0, -48.0, decimals=1, step=0.1,
            info=(tr("How strongly it scatters"),
                  tr("The weak force gives about 10⁻³⁹ cm². Experiments now reach below 10⁻⁴⁷: a WIMP, if "
                     "it exists, talks to ordinary matter far more weakly than the weak force. −46 on this "
                     "slider means 10⁻⁴⁶ cm².")))
        rerun = QPushButton(tr("Run the experiment again"))
        rerun.setToolTip(tr("Draw a new set of events: the same expectation, a different random outcome."))
        rerun.clicked.connect(self._rerun)
        for w in (self.mass, self.log_sigma, rerun):
            wl.addWidget(w)
        self.controls.addWidget(wimp)

        results = QGroupBox(tr("What the experiment would see"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Standard Halo Model (0.3 GeV/cm³, 220 km/s), spin-independent "
                                    "scattering, Helm form factor, perfect efficiency above threshold. "
                                    "Real limits also fold in detector efficiency and energy resolution.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.spectrum_plot = PlotWidget(self._draw_spectrum, csv_provider=self._csv, export_name="recoil_spectrum")
        self.exclusion_plot = PlotWidget(self._draw_exclusion, export_name="exclusion_curve")
        self.run_plot = PlotWidget(self._draw_run, export_name="simulated_run")
        self.modulation_plot = PlotWidget(self._draw_modulation, export_name="annual_modulation")
        tabs.addTab(self.spectrum_plot, tr("Recoil spectrum"))
        tabs.addTab(self.exclusion_plot, tr("Exclusion curve"))
        tabs.addTab(self.run_plot, tr("A simulated run"))
        tabs.addTab(self.modulation_plot, tr("Annual modulation"))
        self.display.addWidget(tabs, 1)

        self.preset.currentIndexChanged.connect(self._preset_changed)
        self.target.currentIndexChanged.connect(self._detector_moved)
        for w in (self.exposure, self.threshold, self.background):
            w.valueChanged.connect(self._detector_moved)
        for w in (self.mass, self.log_sigma):
            w.valueChanged.connect(self.schedule_update)
        self._preset_changed()

    # ----------------------------------------------------------- controls
    def _preset_changed(self, *_args) -> None:
        key = self.preset.currentData()
        if key == CUSTOM:
            return
        e = det.EXPERIMENTS[key]
        self._applying = True
        try:
            self.target.setCurrentIndex(self.target.findData(e.target))
            self.exposure.setValue(e.exposure)
            self.threshold.setValue(e.threshold)
            self.background.setValue(e.background)
        finally:
            self._applying = False
        self.schedule_update()

    def _detector_moved(self, *_args) -> None:
        if not self._applying:
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(self.preset.findData(CUSTOM))
            self.preset.blockSignals(False)
        self.schedule_update()

    def _rerun(self) -> None:
        self._run += 1
        self.run_plot.refresh()

    @property
    def sigma_value(self) -> float:
        return 10.0 ** self.log_sigma.value()

    def e_max(self) -> float:
        key = self.preset.currentData()
        if key != CUSTOM:
            return det.EXPERIMENTS[key].e_max
        return max(50.0, 10 * self.threshold.value())

    def settings(self) -> dict:
        return dict(target=self.target.currentData(), exposure=self.exposure.value(),
                    threshold=self.threshold.value(), e_max=self.e_max(), background=self.background.value())

    def curve(self, **settings) -> np.ndarray:
        key = tuple(sorted((k, round(v, 8) if isinstance(v, float) else v) for k, v in settings.items()))
        if key not in self._curves:
            if len(self._curves) > 16:
                self._curves.clear()
            self._curves[key] = det.exclusion_curve(MASSES, **settings)
        return self._curves[key]

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        s = self.settings()
        m, sigma = self.mass.value(), self.sigma_value
        signal = det.expected_events(m, sigma, s["target"], s["exposure"], s["threshold"], s["e_max"])
        limit = det.exclusion_curve([m], **s)[0]
        significance = det.discovery_significance(signal, s["background"])
        self.report = {
            "preset": self.preset.currentData(), "target": s["target"], "exposure": s["exposure"],
            "threshold": s["threshold"], "background": s["background"], "mass": m, "sigma": sigma,
            "signal": signal, "limit": float(limit) if math.isfinite(limit) else 1.0,
            "excluded": bool(math.isfinite(limit) and sigma > limit),
            "significance": min(significance, 100.0),
        }
        r = self.report
        self.summary.setText("<br>".join([
            tr("Expected WIMP events: <b>{signal}</b>").format(signal=f"{signal:.3g}"),
            tr("Expected background events: {background}").format(background=f"{s['background']:.1f}"),
            (tr("A null result would exclude σ above <b>{limit} cm²</b> at this mass")
             .format(limit=sci(limit)) if math.isfinite(limit)
             else tr("<b>Blind at this mass:</b> no recoil gets above the threshold")),
            tr("Significance if this WIMP is real: <b>{sigma}σ</b>").format(sigma=f"{r['significance']:.1f}"),
        ]))

        if not math.isfinite(limit):
            self.banner.set_message(
                "warning",
                tr("<b>Too light to see.</b> A {mass} GeV WIMP cannot push a {target} nucleus above {threshold} "
                   "keV. Light dark matter needs light nuclei and very low thresholds.")
                .format(mass=f"{m:.1f}", target=tr(TARGET_LABELS[s["target"]]).split(" (")[0].lower(),
                        threshold=f"{s['threshold']:.2f}"))
        elif significance >= 5:
            self.banner.set_message(
                "success",
                tr("<b>A discovery.</b> {signal} events over a background of {background}: {sigma}σ. "
                   "This WIMP would have been found — which is also why a detector that saw nothing rules "
                   "it out.").format(signal=f"{signal:.0f}", background=f"{s['background']:.1f}",
                                     sigma=f"{significance:.1f}"))
        elif r["excluded"]:
            self.banner.set_message(
                "info",
                tr("<b>Excluded, but not discovered.</b> This WIMP would give {signal} events. If the "
                   "detector sees only its background, that is too many to hide — the WIMP is ruled out "
                   "at 90% confidence without ever being detected.").format(signal=f"{signal:.1f}"))
        else:
            self.banner.set_message(
                "info",
                tr("<b>Hidden.</b> {signal} expected events is too few to notice. This WIMP lies below the "
                   "exclusion curve: to find it, the detector needs more exposure, less background or a "
                   "lower threshold.").format(signal=f"{signal:.2f}"))
        for plot in (self.spectrum_plot, self.exclusion_plot, self.run_plot, self.modulation_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_spectrum(self, fig) -> None:
        p = theme().palette
        m, sigma, s = self.mass.value(), self.sigma_value, self.settings()
        ax = fig.add_subplot()
        e = np.geomspace(0.05, 200, 400)
        for i, key in enumerate(det.TARGETS):
            rate = det.differential_rate(e, m, sigma, key) * 1000 * 365.25
            mine = key == s["target"]
            ax.loglog(e, np.maximum(rate, 1e-30), color=p.series[i], linewidth=2.4 if mine else 1.2,
                      alpha=1.0 if mine else 0.7, label=det.TARGETS[key].label + (" (yours)" if mine else ""))
        ax.axvspan(s["threshold"], s["e_max"], color=p.accent2, alpha=0.1)
        ax.axvline(s["threshold"], color=p.accent2, linestyle="--", linewidth=1.2)
        ax.text(s["threshold"], 0.03, " threshold", color=p.accent2, fontsize=7.5, rotation=90, va="bottom",
                transform=ax.get_xaxis_transform())
        peak = max(float((det.differential_rate(e, m, sigma, s["target"]) * 365250).max()), 1e-6)
        ax.set_ylim(max(peak * 1e-6, 1e-8), peak * 20)
        ax.set_xlim(0.05, 200)
        ax.set_xlabel("nuclear recoil energy (keV)", fontsize=8)
        ax.set_ylabel("events per keV per tonne-year", fontsize=8)
        ax.set_title(f"A {m:.0f} GeV WIMP at σ = {sigma:.1e} cm²: falling spectra, heavy nuclei cut off first",
                     fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _draw_exclusion(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        for i, (_key, e) in enumerate(det.EXPERIMENTS.items()):
            curve = self.curve(target=e.target, exposure=e.exposure, threshold=e.threshold, e_max=e.e_max,
                               background=e.background)
            ax.loglog(MASSES, curve, color=p.series[(i + 1) % len(p.series)], linewidth=1.0, alpha=0.6,
                      linestyle="--", label=e.label.split(" (")[0])
        mine = self.curve(**self.settings())
        ax.loglog(MASSES, mine, color=p.series[0], linewidth=2.6, label="your detector")
        ax.fill_between(MASSES, np.where(np.isfinite(mine), mine, 1e-38), 1e-38, color=p.series[0], alpha=0.12)
        ax.plot([LZ_2024[0]], [LZ_2024[1]], "*", color=p.warning, markersize=11,
                label="best published limit (LZ 2024)")
        colour = p.danger if self.report.get("excluded") else p.success
        ax.plot([self.mass.value()], [self.sigma_value], "o", color=colour, markersize=9,
                markeredgecolor=p.text, label="your WIMP")
        ax.set_xlim(1, 1e4)
        ax.set_ylim(1e-50, 1e-38)
        ax.set_xlabel("WIMP mass (GeV)", fontsize=8)
        ax.set_ylabel("cross-section per nucleon σn (cm²)", fontsize=8)
        ax.set_title("Everything in the shaded region would have been seen: a null result rules it out",
                     fontsize=9)
        ax.legend(fontsize=7, loc="upper right")
        ax.tick_params(labelsize=7)

    def _draw_run(self, fig) -> None:
        p = theme().palette
        s = self.settings()
        rng = np.random.default_rng(1000 + self._run)
        n_bg = rng.poisson(s["background"])
        n_sig = rng.poisson(min(self.report["signal"], 1e5))
        bins = np.geomspace(s["threshold"], s["e_max"], 25)
        background = np.exp(rng.uniform(math.log(s["threshold"]), math.log(s["e_max"]), n_bg))
        e = np.geomspace(s["threshold"], s["e_max"], 400)
        rate = det.differential_rate(e, self.mass.value(), self.sigma_value, s["target"])
        signal = np.array([])
        if n_sig and rate.sum() > 0:
            cdf = np.cumsum(rate * np.gradient(e))
            signal = np.interp(rng.uniform(0, cdf[-1], n_sig), cdf, e)
        ax = fig.add_subplot()
        ax.hist([background, signal], bins=bins, stacked=True, color=[p.muted, p.series[0]],
                label=[f"background: {n_bg}", f"WIMPs: {n_sig}"])
        ax.set_xscale("log")
        ax.set_xlabel("recoil energy (keV)", fontsize=8)
        ax.set_ylabel("events", fontsize=8)
        ax.set_title(f"One run of the experiment: {n_bg + n_sig} events seen, "
                     f"{s['background']:.1f} expected from background alone", fontsize=9)
        ax.legend(fontsize=7.5)
        ax.tick_params(labelsize=7)

    def _draw_modulation(self, fig) -> None:
        p = theme().palette
        s = self.settings()
        days, counts = det.modulation(self.mass.value(), self.sigma_value, s["target"], 1.0,
                                      s["threshold"], s["e_max"], np.arange(0, 366, 6))
        ax = fig.add_subplot()
        mean = counts.mean()
        if mean <= 0:
            ax.text(0.5, 0.5, "No events above threshold, so nothing to modulate.", ha="center", va="center",
                    transform=ax.transAxes, color=p.muted)
            ax.set_axis_off()
            return
        relative = (counts / mean - 1) * 100
        ax.plot(days, relative, color=p.series[0], linewidth=2.4)
        ax.axhline(0, color=p.muted, linewidth=1)
        ax.axvline(det.PEAK_DAY, color=p.accent2, linestyle=":", linewidth=1.2)
        ax.text(det.PEAK_DAY, 0.97, " 2 June", color=p.accent2, fontsize=7.5, va="top",
                transform=ax.get_xaxis_transform())
        amplitude = (counts.max() - counts.min()) / (counts.max() + counts.min()) * 100
        ax.set_xlabel("day of the year", fontsize=8)
        ax.set_ylabel("rate relative to the yearly mean (%)", fontsize=8)
        ax.set_title(f"The Earth runs into the halo wind hardest in June: a {amplitude:.1f}% annual modulation",
                     fontsize=9)
        ax.tick_params(labelsize=7)

    def _csv(self):
        s = self.settings()
        mine = self.curve(**s)
        rows = [[f"{m:.4g}", f"{c:.4e}" if math.isfinite(c) else "inf"] for m, c in zip(MASSES, mine)]
        return ["wimp_mass_GeV", "sigma_n_limit_cm2"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        return dict(self.report)

    def guide_extra(self) -> str:
        return (
            "### " + tr("Excluded is not the same as not there") + "\n\n"
            + tr("An exclusion curve says: if a WIMP had this mass and this cross-section, the detector would "
                 "have seen enough events to notice, and it did not. Below the curve nothing is ruled out. "
                 "Each new experiment pushes the curve down — until the background from solar and "
                 "atmospheric neutrinos, the neutrino fog, makes further progress very slow.")
        )
