"""S25 — Recombination Explorer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QTabWidget, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import constants as const
from cosmos.physics import recombination
from cosmos.physics.presets import get_preset

PLANCK_OMEGA_B_H2 = 0.02237


class RecombinationSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        planck = get_preset("planck18").cosmology
        self.H0, self.Om0 = planck.H0, planck.Om0
        self.result: recombination.RecombinationHistory | None = None
        self.report: dict = {}

        universe = QGroupBox(tr("1 · The universe"))
        ul = QVBoxLayout(universe)
        self.omega_b = ParameterSlider(
            tr("Baryon density Ωb h²"), 0.005, 0.10, PLANCK_OMEGA_B_H2, decimals=4, step=0.001,
            info=(tr("How many atoms there are"),
                  tr("More baryons per photon means more protons for every free electron to find, so "
                     "recombination happens a little earlier and is more complete. Planck measures "
                     "0.0224; the same number comes out of the deuterium made in the first minutes.")),
        )
        self.t_cmb = ParameterSlider(
            tr("CMB temperature today (K)"), 1.5, 6.0, const.T_CMB, decimals=3, step=0.05,
            info=(tr("A thought experiment"),
                  tr("Recombination happens at a fixed temperature, about 3000 K, not at a fixed "
                     "redshift. Make today's universe warmer and it had to cool for longer — it reached "
                     "3000 K at a higher redshift. Our universe is 2.7255 K.")),
        )
        reset = QPushButton(tr("Back to our universe"))
        reset.setToolTip(tr("Planck 2018: Ωb h² = 0.0224 and T = 2.7255 K."))
        reset.clicked.connect(self._reset)
        for w in (self.omega_b, self.t_cmb, reset):
            ul.addWidget(w)
        self.controls.addWidget(universe)

        show = QGroupBox(tr("2 · Compare"))
        sl = QVBoxLayout(show)
        self.show_saha = QCheckBox(tr("Show the Saha equilibrium curve"))
        self.show_saha.setChecked(True)
        self.show_saha.setToolTip(tr("What recombination would look like if every atom kept up with the "
                                     "falling temperature. It is always too early."))
        self.log_scale = QCheckBox(tr("Logarithmic ionisation axis"))
        self.log_scale.setChecked(True)
        self.log_scale.setToolTip(tr("Needed to see the few free electrons in ten thousand that never "
                                     "found a proton."))
        for w in (self.show_saha, self.log_scale):
            sl.addWidget(w)
        self.controls.addWidget(show)

        results = QGroupBox(tr("When the universe became transparent"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Hydrogen only, with Peebles' three-level atom. Helium recombines "
                                    "earlier and is left out; the full codes (RECFAST, HyRec) agree "
                                    "with the last-scattering redshift here to about 1%.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.ionisation_plot = PlotWidget(self._draw_ionisation, csv_provider=self._csv,
                                          export_name="recombination")
        self.visibility_plot = PlotWidget(self._draw_visibility, export_name="visibility_function")
        self.photons_plot = PlotWidget(self._draw_photons, export_name="ionising_photons")
        tabs.addTab(self.ionisation_plot, tr("Free electrons"))
        tabs.addTab(self.visibility_plot, tr("The last-scattering surface"))
        tabs.addTab(self.photons_plot, tr("Why so cold?"))
        self.display.addWidget(tabs, 1)

        for w in (self.omega_b, self.t_cmb):
            w.valueChanged.connect(self.schedule_update)
        for w in (self.show_saha, self.log_scale):
            w.toggled.connect(self._redraw)
        self.recompute()

    def _reset(self) -> None:
        self.omega_b.setValue(PLANCK_OMEGA_B_H2)
        self.t_cmb.setValue(const.T_CMB)

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        t0 = self.t_cmb.value()
        # Recombination follows the temperature, so the window of redshifts to solve
        # over moves with today's temperature.
        scale = const.T_CMB / t0
        h = recombination.history(self.omega_b.value(), self.H0, self.Om0, t_cmb=t0,
                                  z_start=1800 * scale, z_end=200 * scale, n=1201)
        self.result = h
        z_saha, z_half = h.z_half("saha"), h.z_half()
        planck = get_preset("planck18").cosmology
        cosmo = planck.with_params(Tcmb0=t0)
        age_kyr = float(cosmo.age(h.z_peak)) * 1e6
        self.report = {
            "omega_b_h2": self.omega_b.value(),
            "t_cmb": t0,
            "z_half_saha": z_saha,
            "z_half": z_half,
            "z_peak": h.z_peak,
            "t_peak": float(h.temperature(h.z_peak)),
            "t_half": float(h.temperature(z_half)),
            "width": h.width,
            "x_freeze": h.x_freeze,
            "age_kyr": age_kyr,
            "photons_per_baryon": recombination.photon_to_baryon_ratio(self.omega_b.value(), t0),
            "delay": z_saha - z_half,
            "t_equal": recombination.photons_equal_atoms_temperature(self.omega_b.value(), t0),
        }
        r = self.report
        self.summary.setText("<br>".join([
            tr("Half the hydrogen neutral at <b>z = {z}</b> ({temperature} K)")
            .format(z=f"{r['z_half']:.0f}", temperature=f"{r['t_half']:.0f}"),
            tr("Saha equilibrium would say z = {z} — {delay} too early in redshift")
            .format(z=f"{r['z_half_saha']:.0f}", delay=f"{r['delay']:.0f}"),
            tr("Last scattering: <b>z = {z}</b>, T = {temperature} K, age {age} thousand years")
            .format(z=f"{r['z_peak']:.0f}", temperature=f"{r['t_peak']:.0f}", age=f"{r['age_kyr']:.0f}"),
            tr("Thickness of the surface: Δz ≈ {width}").format(width=f"{r['width']:.0f}"),
            tr("Electrons that never recombine: <b>{fraction}</b> of all hydrogen")
            .format(fraction=f"{r['x_freeze']:.1e}"),
            tr("Photons per baryon: {ratio} billion").format(ratio=f"{r['photons_per_baryon'] / 1e9:.2f}"),
            tr("Ionising photons outnumber atoms until {temperature} K")
            .format(temperature=f"{r['t_equal']:.0f}"),
        ]))

        if abs(t0 - const.T_CMB) > 0.05:
            self.banner.set_message(
                "info",
                tr("<b>Same temperature, different redshift.</b> This universe is {today} K today, and it "
                   "still released its light at about {temperature} K — at z = {z} instead of 1090. "
                   "Atoms care about the temperature, not about the date.")
                .format(today=f"{t0:.2f}", temperature=f"{r['t_peak']:.0f}", z=f"{r['z_peak']:.0f}"))
        elif self.omega_b.value() < 0.012 or self.omega_b.value() > 0.04:
            self.banner.set_message(
                "warning",
                tr("<b>Not our universe.</b> With Ωb h² = {value} the last-scattering surface moves to "
                   "z = {z} and {fraction} of the electrons stay free. The measured peaks of the CMB "
                   "rule this out.").format(value=f"{self.omega_b.value():.4f}", z=f"{r['z_peak']:.0f}",
                                            fraction=f"{r['x_freeze']:.1e}"))
        else:
            self.banner.set_message(
                "success",
                tr("<b>Transparent at 3000 K, not at 158 000 K.</b> Hydrogen is bound by 13.6 eV, yet "
                   "it only stays neutral once the universe is fifty times cooler than that. There are "
                   "more than a billion photons for every atom, so even the rare ones in the far tail of "
                   "the spectrum outnumber the atoms until the universe is below about 6000 K."))
        self._redraw()

    def _redraw(self, *_args) -> None:
        for plot in (self.ionisation_plot, self.visibility_plot, self.photons_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_ionisation(self, fig) -> None:
        p = theme().palette
        h = self.result
        ax = fig.add_subplot()
        ax.plot(h.z, h.x_peebles, color=p.series[0], linewidth=2.2, label="Peebles three-level atom")
        if self.show_saha.isChecked():
            ax.plot(h.z, np.maximum(h.x_saha, 1e-12), color=p.series[1], linestyle="--", linewidth=1.8,
                    label="Saha equilibrium")
        ax.axvline(h.z_peak, color=p.accent2, linestyle=":", linewidth=1.3)
        ax.text(h.z_peak, 1.05 if not self.log_scale.isChecked() else 1.3, f" last scattering z = {h.z_peak:.0f}",
                color=p.accent2, fontsize=7.5, va="bottom")
        if self.log_scale.isChecked():
            ax.set_yscale("log")
            ax.set_ylim(1e-5, 2.5)
            ax.axhline(h.x_freeze, color=p.muted, linestyle=":", linewidth=1)
            ax.text(h.z[-1], h.x_freeze * 1.4, f"frozen out: {h.x_freeze:.1e} ", color=p.muted, fontsize=7.5,
                    ha="right")
        else:
            ax.set_ylim(0, 1.15)
        ax.set_xlim(h.z[0], h.z[-1])
        ax.set_xlabel("redshift z  (time runs to the right)", fontsize=8)
        ax.set_ylabel("free electrons per hydrogen nucleus  x_e", fontsize=8)
        ax.set_title("Recombination: the bottleneck at n = 2 delays it and leaves a residue", fontsize=9)
        top = ax.secondary_xaxis("top", functions=(lambda z: h.t_cmb * (1 + z), lambda t: t / h.t_cmb - 1))
        top.set_xlabel("temperature (K)", fontsize=8)
        top.tick_params(labelsize=7)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _draw_visibility(self, fig) -> None:
        p = theme().palette
        h = self.result
        grid = fig.add_gridspec(2, 1, height_ratios=[2, 1], hspace=0.08)
        ax = fig.add_subplot(grid[0])
        ax_tau = fig.add_subplot(grid[1], sharex=ax)
        ax.fill_between(h.z, h.visibility * 1e3, color=p.series[0], alpha=0.35)
        ax.plot(h.z, h.visibility * 1e3, color=p.series[0], linewidth=2)
        half = h.visibility.max() / 2 * 1e3
        above = h.z[h.visibility * 1e3 >= half]
        ax.hlines(half, above.min(), above.max(), color=p.accent2, linewidth=1.5,
                  label=f"thickness Δz ≈ {h.width:.0f}")
        ax.axvline(h.z_peak, color=p.accent2, linestyle=":", linewidth=1.2)
        ax.set_ylabel("g(z) × 1000", fontsize=8)
        ax.set_title("Where the CMB photons last scattered: a shell, not a surface", fontsize=9)
        ax.legend(fontsize=7.5)
        ax.tick_params(labelsize=7, labelbottom=False)
        ax_tau.semilogy(h.z, np.maximum(h.tau, 1e-4), color=p.series[2], linewidth=1.8)
        ax_tau.axhline(1, color=p.muted, linestyle="--", linewidth=1)
        left, right = min(1600 * h.t_cmb / const.T_CMB, h.z[0]), max(700 * h.t_cmb / const.T_CMB, h.z[-1])
        ax_tau.text(left, 1.3, " τ = 1: one scattering left", color=p.muted, fontsize=7, ha="left")
        ax_tau.set_ylabel("optical depth τ", fontsize=8)
        ax_tau.set_xlabel("redshift z", fontsize=8)
        ax_tau.set_xlim(left, right)
        ax_tau.set_ylim(1e-2, 1e3)
        ax_tau.tick_params(labelsize=7)

    def _draw_photons(self, fig) -> None:
        p = theme().palette
        h = self.result
        ax = fig.add_subplot()
        temperatures = np.linspace(2500, 9000, 120)
        ratio = [recombination.ionising_photons_per_baryon(t, self.omega_b.value(), h.t_cmb)
                 for t in temperatures]
        ax.semilogy(temperatures, ratio, color=p.series[3], linewidth=2.2,
                    label="photons above 13.6 eV per hydrogen atom")
        ax.axhline(1, color=p.muted, linestyle="--", linewidth=1)
        ax.text(temperatures[-1], 1.6, " one per atom", color=p.muted, fontsize=7.5, ha="left")
        ax.axvline(self.report["t_equal"], color=p.series[1], linestyle="--", linewidth=1.4,
                   label=f"as many ionising photons as atoms: {self.report['t_equal']:.0f} K")
        ax.axvline(self.report["t_half"], color=p.series[0], linestyle=":", linewidth=1.4,
                   label=f"half recombined: {self.report['t_half']:.0f} K")
        ax.set_xlabel("temperature (K)", fontsize=8)
        ax.set_ylabel("ionising photons per atom", fontsize=8)
        ax.set_title(f"13.6 eV is 158 000 K — but with {self.report['photons_per_baryon'] / 1e9:.1f} billion "
                     f"photons per atom, the rare energetic ones win until it is far colder",
                     fontsize=9)
        ax.invert_xaxis()
        ax.legend(fontsize=7.5, loc="upper right")
        ax.tick_params(labelsize=7)

    def _csv(self):
        h = self.result
        rows = [[f"{z:.1f}", f"{h.t_cmb * (1 + z):.1f}", f"{xs:.5e}", f"{xp:.5e}", f"{t:.5e}", f"{g:.5e}"]
                for z, xs, xp, t, g in zip(h.z[::4], h.x_saha[::4], h.x_peebles[::4], h.tau[::4],
                                           h.visibility[::4])]
        return ["z", "temperature_K", "x_saha", "x_peebles", "optical_depth", "visibility_per_dz"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        return dict(self.report, show_saha=self.show_saha.isChecked(), log_scale=self.log_scale.isChecked())

    def guide_extra(self) -> str:
        return (
            "### " + tr("Why not at 13.6 eV?") + "\n\n"
            + tr("An electron is bound to a proton by 13.6 eV, which corresponds to a temperature of "
                 "158 000 K. But the universe only became neutral at about 3000 K. The reason is the "
                 "photon-to-baryon ratio: with more than a billion photons for every atom, even the "
                 "tiny fraction in the far tail of the blackbody spectrum outnumbers the atoms. "
                 "The rough estimate kT ≈ 13.6 eV / ln(1/η) gives about 6000 K; the Saha equation "
                 "and the n = 2 bottleneck push the real answer lower still.")
        )
