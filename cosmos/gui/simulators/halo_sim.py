"""S27 — Halo Mass Function Explorer."""

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
from cosmos.physics import halos
from cosmos.physics.cosmology import Cosmology
from cosmos.physics.structure import DELTA_C

PLANCK_SIGMA8, PLANCK_OM, H0 = 0.811, 0.311, 67.66
MODELS = (("sheth-tormen", tr_noop("Sheth–Tormen (fits simulations)")),
          ("press-schechter", tr_noop("Press–Schechter (the original)")))
TIME_MASSES = (1e8, 1e11, 1e14)          # tracked across cosmic time, M☉/h


def power_of_ten(value: float, html: bool = True) -> str:
    """1.2 × 10⁵ as rich text for labels, or as mathtext for plots."""
    if not math.isfinite(value) or value <= 0:
        return "–"
    exponent = math.floor(math.log10(value))
    mantissa = value / 10**exponent
    if html:
        return f"{mantissa:.1f} × 10<sup>{exponent}</sup>"
    return rf"${mantissa:.1f}\times10^{{{exponent}}}$"


class HaloSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self._models: dict[tuple[float, float], halos.HaloModel] = {}
        self.report: dict = {}

        universe = QGroupBox(tr("1 · The universe"))
        ul = QVBoxLayout(universe)
        self.sigma8 = ParameterSlider(
            tr("Clumpiness σ8"), 0.5, 1.1, PLANCK_SIGMA8, decimals=3, step=0.01,
            info=(tr("How lumpy matter is"),
                  tr("The rms fluctuation of matter in spheres of 8 Mpc/h today. Planck measures 0.811; "
                     "weak lensing surveys tend to find a little less, which is the S8 tension. The biggest "
                     "clusters are rare peaks, and their number depends on σ8 exponentially.")))
        self.om = ParameterSlider(
            tr("Matter Ωm"), 0.15, 0.5, PLANCK_OM, decimals=3, step=0.01,
            info=(tr("How much there is to collapse"),
                  tr("More matter means more mass in every volume, and structure that grows faster. The "
                     "universe is kept flat: dark energy makes up the rest.")))
        reset = QPushButton(tr("Back to Planck 2018"))
        reset.setToolTip(tr("σ8 = 0.811 and Ωm = 0.311."))
        reset.clicked.connect(self._reset)
        for w in (self.sigma8, self.om, reset):
            ul.addWidget(w)
        self.controls.addWidget(universe)

        when = QGroupBox(tr("2 · When and what"))
        wl = QVBoxLayout(when)
        self.redshift = ParameterSlider(
            tr("Redshift z"), 0.0, 20.0, 0.0, decimals=1, step=0.5,
            info=(tr("Going back in time"),
                  tr("At high redshift the fluctuations were smaller, so only small haloes had collapsed "
                     "yet. z = 20 is 180 million years after the Big Bang, when the first stars formed.")))
        self.threshold = ParameterSlider(
            tr("Cluster mass threshold (M☉/h)"), 1e13, 3e15, 1e15, decimals=0, log=True,
            info=(tr("What counts as a cluster"),
                  tr("Surveys count clusters above a mass limit. The heavier the limit, the rarer the "
                     "clusters and the more sensitive their number is to σ8.")))
        self.model = QComboBox()
        for key, label in MODELS:
            self.model.addItem(tr(label), key)
        wl.addWidget(self.redshift)
        wl.addWidget(self.threshold)
        wl.addWidget(labelled_row(tr("Mass function"), self.model, (
            tr("Two recipes"),
            tr("Press and Schechter (1974) assumed spherical collapse. Sheth and Tormen (1999) allowed "
               "ellipsoids and matched N-body simulations: more massive haloes, fewer small ones."))))
        self.controls.addWidget(when)

        results = QGroupBox(tr("What the universe has built"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Linear theory with the Eisenstein–Hu power spectrum and a flat universe. "
                                    "Masses are in M☉/h and densities per comoving (Mpc/h)³, as in the "
                                    "research literature.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.mass_plot = PlotWidget(self._draw_mass_function, csv_provider=self._csv,
                                    export_name="halo_mass_function")
        self.counts_plot = PlotWidget(self._draw_counts, export_name="cluster_counts")
        self.peaks_plot = PlotWidget(self._draw_peaks, export_name="sigma_of_mass")
        self.time_plot = PlotWidget(self._draw_time, export_name="haloes_across_time")
        tabs.addTab(self.mass_plot, tr("Mass function"))
        tabs.addTab(self.counts_plot, tr("Clusters on the sky"))
        tabs.addTab(self.peaks_plot, tr("Rare peaks"))
        tabs.addTab(self.time_plot, tr("Across cosmic time"))
        self.display.addWidget(tabs, 1)

        for w in (self.sigma8, self.om, self.redshift, self.threshold):
            w.valueChanged.connect(self.schedule_update)
        self.model.currentIndexChanged.connect(self.schedule_update)
        self.recompute()

    def _reset(self) -> None:
        self.sigma8.setValue(PLANCK_SIGMA8)
        self.om.setValue(PLANCK_OM)

    def halo_model(self, sigma8: float, om: float) -> halos.HaloModel:
        key = (round(sigma8, 4), round(om, 4))
        if key not in self._models:
            if len(self._models) > 12:
                self._models.clear()
            cosmo = Cosmology.flat(H0=H0, Om0=om, Ob0=0.049)
            self._models[key] = halos.HaloModel(cosmo, sigma8=sigma8)
        return self._models[key]

    @property
    def current(self) -> halos.HaloModel:
        return self.halo_model(self.sigma8.value(), self.om.value())

    @property
    def planck(self) -> halos.HaloModel:
        return self.halo_model(PLANCK_SIGMA8, PLANCK_OM)

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        m, model, z = self.current, self.model.currentData(), self.redshift.value()
        threshold = self.threshold.value()
        clusters = m.all_sky_counts(threshold, 1.0, model)
        planck_clusters = self.planck.all_sky_counts(threshold, 1.0, model)
        first = m.n_above_mass(halos.ATOMIC_COOLING_MASS, z, model)
        m_star = m.nonlinear_mass(z)
        self.report = {
            "sigma8": self.sigma8.value(), "om": self.om.value(), "z": z, "model": model,
            "threshold": threshold, "clusters": clusters, "ratio": clusters / max(planck_clusters, 1e-300),
            "m_star": m_star if math.isfinite(m_star) else 0.0,
            "n_clusters_here": m.n_above_mass(1e14, z, model) * 1e9,       # per (Gpc/h)³
            "first_haloes": first,
            "first_redshift": m.redshift_of_density(halos.ATOMIC_COOLING_MASS, 1.0, model),
        }
        r = self.report
        star = (tr("Typical halo forming now (M*): <b>{mass} M☉/h</b>").format(mass=power_of_ten(m_star))
                if math.isfinite(m_star) else tr("Typical halo forming now (M*): <b>below 10⁵ M☉/h</b>"))
        self.summary.setText("<br>".join([
            star,
            tr("Clusters above 10¹⁴ M☉/h at this redshift: {count} per (Gpc/h)³")
            .format(count=power_of_ten(r["n_clusters_here"])),
            tr("Haloes that can make the first stars (above 10⁸ M☉/h): {count} per (Mpc/h)³")
            .format(count=power_of_ten(first)),
            tr("Clusters above {mass} M☉/h on the whole sky out to z = 1: <b>{count}</b>")
            .format(mass=power_of_ten(threshold), count=f"{clusters:,.0f}".replace(",", " ")),
            tr("That is <b>{ratio}×</b> what Planck's σ8 predicts").format(ratio=f"{r['ratio']:.2f}"),
        ]))

        if abs(r["ratio"] - 1) > 0.5 and abs(self.sigma8.value() / PLANCK_SIGMA8 - 1) < 0.15:
            self.banner.set_message(
                "info",
                tr("<b>A small change, a big effect.</b> σ8 is {percent} away from Planck's value, and the "
                   "number of massive clusters has changed by a factor {ratio}. The rarest objects are the "
                   "most sensitive — that is why cluster counts measure σ8.")
                .format(percent=f"{self.sigma8.value() / PLANCK_SIGMA8 - 1:+.0%}", ratio=f"{r['ratio']:.1f}"))
        elif z >= 6:
            self.banner.set_message(
                "info",
                tr("<b>Cosmic dawn.</b> At z = {z} there are no clusters and almost no galaxies — only small "
                   "haloes, and the gas in the ones above 10⁸ M☉/h is just able to cool and form the first "
                   "stars. Structure grows from the bottom up.").format(z=f"{z:.0f}"))
        else:
            self.banner.set_message(
                "success",
                tr("<b>Bottom up.</b> Small haloes form first and merge into larger ones. Today the typical "
                   "collapsing halo is a group of galaxies; the heaviest clusters are rare peaks that only "
                   "just had time to form."))
        for plot in (self.mass_plot, self.counts_plot, self.peaks_plot, self.time_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_mass_function(self, fig) -> None:
        p = theme().palette
        m, model, z = self.current, self.model.currentData(), self.redshift.value()
        ax = fig.add_subplot()
        floor = 1e-30
        for zz, style, label in ((0.0, ":", "today"),):
            if z > 0:
                ax.loglog(m.masses, np.maximum(m.dn_dlnm(zz, model), floor), color=p.muted, linestyle=style,
                          linewidth=1.3, label=f"your universe, {label}")
        ax.loglog(m.masses, np.maximum(m.dn_dlnm(z, model), floor), color=p.series[0], linewidth=2.4,
                  label=f"your universe, z = {z:.1f}")
        ax.loglog(self.planck.masses, np.maximum(self.planck.dn_dlnm(z, model), floor), color=p.series[1],
                  linestyle="--", linewidth=1.4, label=f"Planck 2018, z = {z:.1f}")
        other = "press-schechter" if model == "sheth-tormen" else "sheth-tormen"
        ax.loglog(m.masses, np.maximum(m.dn_dlnm(z, other), floor), color=p.series[4], linestyle="-.",
                  linewidth=1.1, alpha=0.8, label=dict(MODELS)[other].split(" (")[0])
        ax.axvline(halos.ATOMIC_COOLING_MASS, color=p.series[2], linestyle=":", linewidth=1)
        ax.text(halos.ATOMIC_COOLING_MASS, 3e-10, " first stars", color=p.series[2], fontsize=7, rotation=90,
                va="bottom")
        ax.axvline(1e14, color=p.series[3], linestyle=":", linewidth=1)
        ax.text(1e14, 3e-10, " clusters", color=p.series[3], fontsize=7, rotation=90, va="bottom")
        ax.set_ylim(1e-10, 1e3)
        ax.set_xlabel("halo mass M (M☉/h)", fontsize=8)
        ax.set_ylabel("dn / dln M  (h/Mpc)³", fontsize=8)
        ax.set_title("How many haloes of each mass: a power law, cut off exponentially", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _draw_counts(self, fig) -> None:
        p = theme().palette
        model = self.model.currentData()
        om = self.om.value()
        ax = fig.add_subplot()
        chosen = self.sigma8.value()
        values = sorted({0.7, PLANCK_SIGMA8, 0.9, round(chosen, 3)})
        for i, s8 in enumerate(values):
            m = self.halo_model(s8, om)
            curve = m.all_sky_curve(1.0, model)
            mine = abs(s8 - chosen) < 1e-6
            ax.loglog(m.masses, np.maximum(curve, 1e-3), linewidth=2.6 if mine else 1.3,
                      color=p.series[0] if mine else p.series[(i + 1) % len(p.series)],
                      linestyle="-" if mine else "--", label=f"σ8 = {s8:.3f}" + (" (yours)" if mine else ""))
        ax.axvline(self.threshold.value(), color=p.accent2, linewidth=1.2)
        ax.axhline(1, color=p.muted, linestyle=":", linewidth=1)
        ax.text(1.2e13, 1.4, "one on the whole sky", color=p.muted, fontsize=7.5)
        ax.set_xlim(1e13, 1e16)
        ax.set_ylim(0.1, 1e7)
        ax.set_xlabel("mass threshold M (M☉/h)", fontsize=8)
        ax.set_ylabel("haloes heavier than M, whole sky, z < 1", fontsize=8)
        ax.set_title(f"Your threshold: {self.report['clusters']:,.0f} clusters, "
                     f"{self.report['ratio']:.2f}× the Planck prediction".replace(",", " "), fontsize=9)
        ax.legend(fontsize=7.5, loc="upper right")
        ax.tick_params(labelsize=7)

    def _draw_peaks(self, fig) -> None:
        p = theme().palette
        m, z = self.current, self.redshift.value()
        ax = fig.add_subplot()
        sigma = m.sigma(z)
        ax.loglog(m.masses, sigma, color=p.series[0], linewidth=2.4, label=f"σ(M) at z = {z:.1f}")
        for n, colour in ((1, p.series[2]), (2, p.series[1]), (3, p.series[3])):
            ax.axhline(DELTA_C / n, color=colour, linestyle="--", linewidth=1.2,
                       label=f"{n}σ peaks collapse where σ = δc/{n}" if n > 1 else "typical (1σ): σ = δc = 1.686")
        ax.set_xlabel("halo mass M (M☉/h)", fontsize=8)
        ax.set_ylabel("rms linear fluctuation σ(M, z)", fontsize=8)
        ax.set_ylim(0.05, 30)
        ax.set_title("A halo forms where the smoothed field passes δc: small masses first", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _draw_time(self, fig) -> None:
        p = theme().palette
        m, model = self.current, self.model.currentData()
        zs = np.linspace(0, 20, 81)
        m.growth_many(zs)
        ax = fig.add_subplot()
        for i, mass in enumerate(TIME_MASSES):
            n = [m.n_above_mass(mass, z, model) for z in zs]
            ax.semilogy(zs, np.maximum(n, 1e-40), color=p.series[i], linewidth=2.2,
                        label=f"haloes above {power_of_ten(mass, html=False)} M☉/h")
        ax.axvline(self.redshift.value(), color=p.accent2, linestyle=":", linewidth=1.3)
        ax.axhline(1e-9, color=p.muted, linestyle="--", linewidth=1)
        ax.text(20, 2e-9, " one per (Gpc/h)³", color=p.muted, fontsize=7.5, ha="left")
        ax.set_ylim(1e-15, 1e3)
        ax.set_xlim(20, 0)
        ax.set_xlabel("redshift z  (time runs to the right)", fontsize=8)
        ax.set_ylabel("n(>M)  (h/Mpc)³", fontsize=8)
        ax.set_title("Hierarchical growth: small haloes first, clusters only recently", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower right")
        ax.tick_params(labelsize=7)

    def _csv(self):
        m, model, z = self.current, self.model.currentData(), self.redshift.value()
        dn, cumulative, sigma = m.dn_dlnm(z, model), m.n_above(z, model), m.sigma(z)
        rows = [[f"{mass:.4e}", f"{s:.5g}", f"{d:.5e}", f"{c:.5e}"]
                for mass, s, d, c in zip(m.masses, sigma, dn, cumulative)]
        return ["mass_Msun_per_h", "sigma", "dn_dlnM_h3_Mpc-3", "n_above_h3_Mpc-3"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        return dict(self.report)

    def guide_extra(self) -> str:
        return (
            "### " + tr("Why rare things measure σ8") + "\n\n"
            + tr("The number of haloes of mass M falls as $e^{-\\nu^2/2}$ with $\\nu = \\delta_c / \\sigma(M)$. "
                 "For the heaviest clusters ν is 3 or 4, and there a 10% change in σ8 changes the count by "
                 "a factor of two or more. Galaxy-cluster surveys such as eROSITA, SPT and Euclid use this "
                 "to weigh the clumpiness of the universe.")
        )
