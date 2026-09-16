"""S18 — Build Your Own Universe."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QTabWidget, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, PresetSelector, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr
from cosmos.physics import cmb
from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology, Fate
from cosmos.physics.presets import PRESETS


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool | None      # None: could not be evaluated
    value: str
    requirement: str
    explanation: str


def report_card(c: Cosmology, first_peak: float | None) -> list[Check]:
    """Compare a universe with key observations (approximate, rounded constraints)."""
    age = c.age() if c.has_big_bang() else math.nan
    omega_b = c.Ob0 * c.h**2
    q0 = float(c.deceleration_parameter(0.0))
    checks = [
        Check("Older than the oldest stars", age >= 12.5 if math.isfinite(age) else False,
              f"{age:.2f} Gyr" if math.isfinite(age) else "no Big Bang", "age ≥ 12.5 Gyr",
              "Globular clusters and white dwarfs contain stars about 12–13.5 billion years old."),
        Check("Hubble constant", 66 <= c.H0 <= 75, f"{c.H0:.1f} km/s/Mpc", "66–75 km/s/Mpc",
              "The CMB gives about 67, Cepheids and supernovae about 73; values outside this range are excluded."),
        Check("Flat space", abs(c.Ok0) <= 0.005, f"Ωk = {c.Ok0:+.4f}", "|Ωk| ≤ 0.005",
              "The CMB acoustic scale combined with BAO shows that space is flat to about 0.2%."),
        Check("Ordinary matter", abs(omega_b - 0.0224) <= 0.0015, f"Ωb h² = {omega_b:.4f}", "0.0224 ± 0.0015",
              "Big Bang nucleosynthesis (deuterium) and the CMB peak heights agree on this value."),
        Check("Total matter", abs(c.Om0 - 0.31) <= 0.04, f"Ωm = {c.Om0:.3f}", "0.31 ± 0.04",
              "Measured by the CMB, baryon acoustic oscillations and galaxy clusters."),
        Check("Accelerating today", q0 < 0, f"q0 = {q0:+.2f}", "q0 < 0",
              "Type Ia supernovae show that the expansion is speeding up."),
        Check("First CMB peak", None if first_peak is None else abs(first_peak - 220) <= 10,
              "—" if first_peak is None else f"ℓ ≈ {first_peak:.0f}", "ℓ = 220 ± 10",
              "The position of the first acoustic peak measures geometry and distances (teaching model)."),
        Check("Radiation and neutrinos", c.Tcmb0 > 0 and abs(c.Neff - 3.0) <= 0.4,
              f"N_eff = {c.Neff:.2f}" if c.Tcmb0 > 0 else "no radiation", "CMB present, N_eff = 3.0 ± 0.4",
              "The CMB exists, and BBN plus CMB measure about three neutrino species."),
        Check("Dark energy behaviour", abs(c.w0 + 1) <= 0.3 and c.w0 + c.wa < 0,
              f"w0 = {c.w0:.2f}, wa = {c.wa:+.2f}", "w0 = −1 ± 0.3 and w0 + wa < 0",
              "Supernovae, BAO and the CMB allow a cosmological constant or a mildly evolving dark energy."),
    ]
    return checks


class SandboxSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.cosmo = PRESETS["planck18"].cosmology
        self.reference = self.cosmo
        self.spec = None
        self.reference_spec = cmb.spectrum()
        self.checks: list[Check] = []

        top = QGroupBox(tr("Start from"))
        tl = QVBoxLayout(top)
        self.preset = PresetSelector()
        tl.addWidget(labelled_row(tr("Preset"), self.preset))
        self.controls.addWidget(top)

        expansion = QGroupBox(tr("1 · Expansion and ingredients"))
        el = QVBoxLayout(expansion)
        self.h0 = ParameterSlider(tr("H0 (km/s/Mpc)"), 40, 100, 67.66, decimals=2, step=0.5)
        self.ob = ParameterSlider(tr("Ωb ordinary matter"), 0.0, 0.3, 0.049, decimals=4, step=0.002)
        self.oc = ParameterSlider(tr("Ωc dark matter"), 0.0, 1.5, 0.2607, decimals=4, step=0.01)
        self.flat = QCheckBox(tr("Keep space flat (dark energy fills the rest)"))
        self.flat.setChecked(True)
        self.ode = ParameterSlider(tr("ΩΛ dark energy"), -0.5, 2.0, 0.6889, decimals=4, step=0.01)
        self.radiation = QCheckBox(tr("Include radiation (CMB and neutrinos)"))
        self.radiation.setChecked(True)
        self.neff = ParameterSlider(tr("N_eff neutrino species"), 0.0, 6.0, 3.046, decimals=2, step=0.1)
        for w in (self.h0, self.ob, self.oc, self.flat, self.ode, self.radiation, self.neff):
            el.addWidget(w)
        self.controls.addWidget(expansion)

        de = QGroupBox(tr("2 · Dark energy"))
        dl = QVBoxLayout(de)
        self.w0 = ParameterSlider(
            tr("w0 today"), -2.0, 0.0, -1.0, decimals=2, step=0.02,
            info=(tr("Equation of state today"), tr("w = −1 is a cosmological constant. w < −1 is phantom energy that "
                      "grows as space expands and can end in a Big Rip.")),
        )
        self.wa = ParameterSlider(
            tr("wa evolution"), -2.0, 2.0, 0.0, decimals=2, step=0.05,
            info=(tr("Evolution"), tr("w(a) = w0 + wa (1 − a). Negative wa means dark energy was stronger in the past "
                      "and is weakening, as recent DESI results hint.")),
        )
        dl.addWidget(self.w0)
        dl.addWidget(self.wa)
        self.controls.addWidget(de)

        early = QGroupBox(tr("3 · Early universe"))
        yl = QVBoxLayout(early)
        self.n_s = ParameterSlider(tr("nₛ spectral index"), 0.8, 1.2, 0.9665, decimals=4, step=0.005)
        yl.addWidget(self.n_s)
        self.controls.addWidget(early)

        reset = QPushButton(tr("Reset to Planck 2018"))
        reset.clicked.connect(lambda: self.preset.set_key("planck18", emit=True))
        self.controls.addWidget(reset)
        self.finish_controls()

        self.score = Banner("info")
        self.display.addWidget(self.score)
        tabs = QTabWidget()
        self.report = RichBrowser(font_pt=10.5)
        self.expansion_plot = PlotWidget(self._draw_expansion, export_name="my_universe_expansion")
        self.cmb_plot = PlotWidget(self._draw_cmb, export_name="my_universe_cmb")
        tabs.addTab(self.report, tr("Report card"))
        tabs.addTab(self.expansion_plot, tr("History and contents"))
        tabs.addTab(self.cmb_plot, tr("CMB"))
        self.display.addWidget(tabs, 1)

        for w in (self.h0, self.ob, self.oc, self.ode, self.neff, self.w0, self.wa, self.n_s):
            w.valueChanged.connect(self._user_changed)
        for w in (self.flat, self.radiation):
            w.toggled.connect(self._user_changed)
        self.preset.presetChosen.connect(self._load_preset)
        self._loading = False
        self.preset.set_key("planck18", emit=True)

    # ------------------------------------------------------------ inputs
    def _load_preset(self, key: str) -> None:
        c = PRESETS[key].cosmology
        self._loading = True
        self.h0.setValue(c.H0, emit=False)
        self.ob.setValue(min(c.Ob0, c.Om0), emit=False)
        self.oc.setValue(max(c.Om0 - c.Ob0, 0.0), emit=False)
        self.radiation.setChecked(c.Tcmb0 > 0)
        self.neff.setValue(c.Neff, emit=False)
        self.flat.setChecked(abs(c.Ok0) < 1e-6)
        self.ode.setValue(c.Ode0, emit=False)
        self.w0.setValue(c.w0, emit=False)
        self.wa.setValue(c.wa, emit=False)
        self._loading = False
        self.recompute()

    def _user_changed(self, *_args) -> None:
        if self._loading:
            return
        self.preset.set_key("custom")
        self.schedule_update()

    def build(self) -> Cosmology:
        om = self.ob.value() + self.oc.value()
        tcmb = const.T_CMB if self.radiation.isChecked() else 0.0
        c = Cosmology(H0=self.h0.value(), Om0=om, Ode0=self.ode.value(), Ob0=self.ob.value(), Tcmb0=tcmb,
                      Neff=self.neff.value(), w0=self.w0.value(), wa=self.wa.value(), name="My universe")
        if self.flat.isChecked():
            c = c.with_params(Ode0=1.0 - om - c.Or0)
        return c

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        self.ode.setEnabled(not self.flat.isChecked())
        self.neff.setEnabled(self.radiation.isChecked())
        c = self.cosmo = self.build()
        if self.flat.isChecked():
            self.ode.setValue(c.Ode0, emit=False)
        first_peak = None
        self.spec = None
        if c.has_big_bang() and c.Ob0 > 0.002 and c.Om0 - c.Ob0 > 0.01 and c.Tcmb0 > 0:
            try:
                params = cmb.CMBParameters(
                    omega_b=c.Ob0 * c.h**2, omega_c=(c.Om0 - c.Ob0) * c.h**2, h=c.h, omega_k=c.Ok0,
                    n_s=self.n_s.value(), w0=c.w0, wa=c.wa, neff=c.Neff,
                )
                self.spec = cmb.spectrum(params)
                first_peak = self.spec.peaks[0][0] if self.spec.peaks else None
            except (ValueError, ZeroDivisionError, IndexError):
                self.spec = None
        self.checks = report_card(c, first_peak)
        passed = sum(1 for ch in self.checks if ch.passed)
        total = sum(1 for ch in self.checks if ch.passed is not None)
        kind = "success" if passed == total else "warning" if passed >= total - 2 else "danger"
        self.score.set_message(kind, f"<b>Your universe passes {passed} of {total} observational tests.</b> "
                               "Open the report card to see which observations agree or disagree.")
        self.report.set_markdown_content(self._report_markdown(c))
        self.expansion_plot.refresh()
        self.cmb_plot.refresh()

    def _report_markdown(self, c: Cosmology) -> str:
        fate = c.fate()
        lines = ["## Your universe", ""]
        if c.has_big_bang():
            lines.append(f"- **Age:** {c.age():.2f} billion years")
        else:
            lines.append("- **Age:** undefined, this universe has no Big Bang")
        lines.append(f"- **Geometry:** {c.geometry} (Ωk = {c.Ok0:+.4f})")
        lines.append(f"- **Today:** matter {c.Om0:.1%}, dark energy {c.Ode0:.1%}, radiation {c.Or0:.3%}")
        lines.append(f"- **Fate:** {fate.value}. {fate.explanation}")
        if fate is Fate.BIG_RIP:
            lines.append(f"- **Big Rip in:** {c.big_rip_time():.1f} billion years")
        q = c.deceleration_parameter(np.linspace(0, 3, 301))
        if q[0] < 0 and np.any(q > 0):
            z_acc = float(np.linspace(0, 3, 301)[np.argmax(q > 0)])
            lines.append(f"- **Acceleration began:** at redshift ≈ {z_acc:.2f}")
        if math.isfinite(c.z_equality):
            lines.append(f"- **Matter–radiation equality:** z ≈ {c.z_equality:.0f}")
        lines += ["", "## Report card", "",
                  "| | Test | Your universe | Required |", "|---|---|---|---|"]
        for ch in self.checks:
            mark = "✓" if ch.passed else ("–" if ch.passed is None else "✗")
            lines.append(f"| {mark} | {ch.name} | {ch.value} | {ch.requirement} |")
        lines += ["", "### Why these tests", ""]
        lines += [f"- **{ch.name}:** {ch.explanation}" for ch in self.checks]
        lines += ["", ":::note About these tests",
                  "The requirements are rounded summaries of current measurements, not exact statistical limits.",
                  ":::"]
        return "\n".join(lines)

    # ------------------------------------------------------------- plots
    def _draw_expansion(self, fig) -> None:
        p = theme().palette
        c = self.cosmo
        ax = fig.add_subplot(1, 2, 1)
        for model, color, label in [(self.reference, p.muted, "Planck 2018"), (c, p.series[0], "Your universe")]:
            try:
                hist = model.expansion_history(t_future=40, a_max=8)
                ax.plot(hist.t, hist.a, color=color, linewidth=2 if model is c else 1.4,
                        linestyle="-" if model is c else "--", label=label)
            except Exception:  # noqa: BLE001 - exotic parameter combinations
                continue
        ax.axvline(0, color=p.border, linestyle=":")
        ax.set_xlim(-25, 40)
        ax.set_ylim(0, 5)
        ax.set_xlabel("Time from today (Gyr)", fontsize=8)
        ax.set_ylabel("Scale factor a", fontsize=8)
        ax.set_title("Expansion history", fontsize=9)
        ax.legend(loc="upper left", fontsize=7)

        ax = fig.add_subplot(1, 2, 2)
        a = np.logspace(-6, 1, 400)
        with np.errstate(over="ignore", invalid="ignore"):
            e2 = c.E2_of_a(a)
            parts = [c.Or0 * a**-4 / e2, c.Om0 * a**-3 / e2, c.Ode0 * c.de_density_ratio(a) / e2,
                     np.abs(c.Ok0) * a**-2 / e2]
        parts = [np.clip(np.nan_to_num(x), 0, None) for x in parts]
        ax.stackplot(np.log10(a), parts[0], parts[1], parts[2], parts[3],
                     colors=[p.series[3], p.series[0], p.series[2], p.border],
                     labels=["radiation", "matter", "dark energy", "|curvature|"], alpha=0.85)
        ax.axvline(0, color=p.text, linestyle=":", linewidth=1)
        ax.set_xlim(-6, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel("log₁₀ scale factor", fontsize=8)
        ax.set_ylabel("Share of the energy density", fontsize=8)
        ax.set_title("What dominated when", fontsize=9)
        ax.legend(loc="center left", fontsize=7)
        for axis in fig.axes:
            axis.tick_params(labelsize=7)

    def _draw_cmb(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        ax.plot(self.reference_spec.ell, self.reference_spec.d_ell, color=p.muted, linestyle="--",
                linewidth=1.3, label="Planck 2018 model")
        if self.spec is not None:
            ax.plot(self.spec.ell, self.spec.d_ell, color=p.series[0], linewidth=2, label="Your universe")
        else:
            ax.text(0.5, 0.6, "No CMB prediction: this universe needs radiation, baryons, dark matter "
                    "and a Big Bang", transform=ax.transAxes, ha="center", color=p.text, fontsize=9)
        ax.set_xlim(0, 2500)
        ax.set_ylim(0, None)
        ax.set_xlabel("Multipole ℓ")
        ax.set_ylabel("ℓ(ℓ+1)Cℓ / 2π  (μK²)")
        ax.set_title("CMB temperature spectrum (teaching model)", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
