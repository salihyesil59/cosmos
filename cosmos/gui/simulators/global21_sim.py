"""S28 — 21-cm Global Signal Explorer."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QLabel, QPushButton, QTabWidget, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import global21 as g21

DEFAULTS = g21.Astrophysics()
IONOSPHERE_MHZ = 30.0          # below this the ionosphere blocks the sky from the ground


class Global21Simulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.result: g21.Signal | None = None
        self.report: dict = {}

        stars = QGroupBox(tr("1 · The first stars and galaxies"))
        sl = QVBoxLayout(stars)
        self.z_alpha = ParameterSlider(
            tr("Lyman-α coupling switches on at z"), 8.0, 30.0, DEFAULTS.z_alpha, decimals=1, step=0.5,
            info=(tr("The first starlight"),
                  tr("Ultraviolet photons from the first stars, redshifted into Lyman-α, tie the spin "
                     "temperature of hydrogen to the cold gas. That opens the cosmic-dawn trough. Earlier "
                     "stars move it to lower frequencies.")))
        self.z_heat = ParameterSlider(
            tr("X-ray heating switches on at z"), 6.0, 25.0, DEFAULTS.z_heat, decimals=1, step=0.5,
            info=(tr("The first X-rays"),
                  tr("X-ray binaries and early black holes heat the gas. Once it is warmer than the "
                     "background, the absorption turns into emission.")))
        self.heating = ParameterSlider(
            tr("Heating delivered (K)"), 0.0, 5000.0, DEFAULTS.heating, decimals=0, step=50,
            info=(tr("How much X-ray heating"),
                  tr("Zero means the gas is never heated: the trough keeps deepening until reionisation "
                     "removes the hydrogen.")))
        self.z_re = ParameterSlider(
            tr("Reionisation midpoint z"), 5.5, 12.0, DEFAULTS.z_re, decimals=1, step=0.1,
            info=(tr("The end of neutral hydrogen"),
                  tr("Planck's optical depth puts the midpoint at z ≈ 7.7. When the hydrogen is ionised, "
                     "there is nothing left to absorb or emit at 21 cm, and the signal vanishes.")))
        for w in (self.z_alpha, self.z_heat, self.heating, self.z_re):
            sl.addWidget(w)
        self.controls.addWidget(stars)

        exotic = QGroupBox(tr("2 · The EDGES puzzle"))
        el = QVBoxLayout(exotic)
        self.radio = ParameterSlider(
            tr("Extra radio background (× CMB at 78 MHz)"), 0.0, 5.0, 0.0, decimals=2, step=0.05,
            info=(tr("A brighter background"),
                  tr("One proposed explanation for the deep EDGES trough: if something besides the CMB "
                     "shone at radio wavelengths, there would be more light for the cold gas to absorb.")))
        self.show_edges = QCheckBox(tr("Show the EDGES 2018 measurement"))
        self.show_edges.setChecked(True)
        self.show_edges.setToolTip(tr("Bowman et al. (2018): a trough 0.5 K deep at 78 MHz. SARAS-3 (2022) "
                                      "did not see it."))
        reset = QPushButton(tr("Back to the standard model"))
        reset.clicked.connect(self._reset)
        for w in (self.radio, self.show_edges, reset):
            el.addWidget(w)
        self.controls.addWidget(exotic)

        results = QGroupBox(tr("What a radio telescope would see"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("The gas temperature is solved from recombination onwards; the first "
                                    "stars, X-ray heating and reionisation follow simple tanh histories. "
                                    "The foregrounds of our own Galaxy are 10⁴–10⁵ times brighter than "
                                    "this signal.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.signal_plot = PlotWidget(self._draw_signal, csv_provider=self._csv, export_name="global_21cm")
        self.temperature_plot = PlotWidget(self._draw_temperatures, export_name="spin_temperature")
        self.coupling_plot = PlotWidget(self._draw_couplings, export_name="21cm_couplings")
        tabs.addTab(self.signal_plot, tr("The global signal"))
        tabs.addTab(self.temperature_plot, tr("Three temperatures"))
        tabs.addTab(self.coupling_plot, tr("What couples the spins"))
        self.display.addWidget(tabs, 1)

        for w in (self.z_alpha, self.z_heat, self.heating, self.z_re, self.radio):
            w.valueChanged.connect(self.schedule_update)
        self.show_edges.toggled.connect(lambda *_: self.signal_plot.refresh())
        self.recompute()

    def _reset(self) -> None:
        self.z_alpha.setValue(DEFAULTS.z_alpha)
        self.z_heat.setValue(DEFAULTS.z_heat)
        self.heating.setValue(DEFAULTS.heating)
        self.z_re.setValue(DEFAULTS.z_re)
        self.radio.setValue(0.0)

    def astrophysics(self) -> g21.Astrophysics:
        return g21.Astrophysics(z_alpha=self.z_alpha.value(), z_heat=self.z_heat.value(),
                                heating=self.heating.value(), z_re=self.z_re.value(),
                                radio_excess=self.radio.value())

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        s = g21.signal(self.astrophysics())
        self.result = s
        dark, z_dark = s.dark_ages
        dawn, z_dawn = s.cosmic_dawn
        cross = s.heating_crossing
        self.report = {
            "z_alpha": self.z_alpha.value(), "z_heat": self.z_heat.value(), "heating": self.heating.value(),
            "z_re": self.z_re.value(), "radio": self.radio.value(),
            "dark_depth": dark, "dark_freq": float(g21.frequency(z_dark)),
            "dawn_depth": dawn, "dawn_freq": float(g21.frequency(z_dawn)), "dawn_z": z_dawn,
            "emission": s.emission_peak, "heated": math.isfinite(cross),
        }
        r = self.report
        lines = [
            tr("Dark-ages trough: <b>{depth} mK</b> at {freq} MHz (z = {z})")
            .format(depth=f"{dark:.0f}", freq=f"{r['dark_freq']:.0f}", z=f"{z_dark:.0f}"),
            tr("Cosmic-dawn trough: <b>{depth} mK</b> at {freq} MHz (z = {z})")
            .format(depth=f"{dawn:.0f}", freq=f"{r['dawn_freq']:.0f}", z=f"{z_dawn:.1f}"),
            (tr("Emission after heating: up to <b>{peak} mK</b>").format(peak=f"{s.emission_peak:.0f}")
             if s.emission_peak > 0.5 else tr("No emission: the gas never gets warmer than the background")),
            (tr("The gas is heated above the background at z = {z}").format(z=f"{cross:.1f}")
             if math.isfinite(cross) else tr("The gas stays colder than the background until reionisation")),
            tr("Compared with EDGES (−500 mK at 78 MHz): {ratio} as deep").format(ratio=f"{dawn / -500:.0%}"),
        ]
        self.summary.setText("<br>".join(lines))

        if dawn < -350:
            self.banner.set_message(
                "warning",
                tr("<b>As deep as EDGES.</b> A trough of {depth} mK needs more than standard physics: colder "
                   "gas than adiabatic cooling allows, or a brighter radio background than the CMB. SARAS-3 "
                   "looked for this signal and did not find it.").format(depth=f"{dawn:.0f}"))
        elif s.emission_peak <= 0.5:
            self.banner.set_message(
                "info",
                tr("<b>Never heated.</b> Without X-rays the gas keeps cooling, and the absorption only ends "
                   "when reionisation removes the neutral hydrogen."))
        else:
            self.banner.set_message(
                "success",
                tr("<b>Two troughs and a hump.</b> The dark-ages trough at about 16 MHz is set by physics "
                   "alone; the cosmic-dawn trough records the first stars, and the emission the first X-ray "
                   "sources. Everything is a few tens to a few hundred millikelvin."))
        for plot in (self.signal_plot, self.temperature_plot, self.coupling_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_signal(self, fig) -> None:
        p = theme().palette
        s = self.result
        ax = fig.add_subplot()
        ax.plot(s.nu, s.delta_tb, color=p.series[0], linewidth=2.4, label="your model")
        standard = g21.signal()
        ax.plot(standard.nu, standard.delta_tb, color=p.muted, linestyle="--", linewidth=1.2,
                label="standard model")
        if self.show_edges.isChecked():
            nu = np.linspace(51, 99, 200)
            ax.plot(nu, g21.edges_profile(nu), color=p.series[3], linewidth=1.8, label="EDGES 2018")
        ax.axhline(0, color=p.border, linewidth=1)
        ax.axvspan(0, IONOSPHERE_MHZ, color=p.muted, alpha=0.12)
        ax.text(IONOSPHERE_MHZ / 2, 0.04, "blocked by the\nionosphere", color=p.muted, fontsize=7,
                ha="center", va="bottom", transform=ax.get_xaxis_transform())
        ax.set_xlim(5, 200)
        low = min(float(s.delta_tb.min()), -60.0, -560.0 if self.show_edges.isChecked() else 0.0)
        ax.set_ylim(low * 1.1, max(float(s.delta_tb.max()), 20.0) * 1.4)
        ax.set_xlabel("observed frequency (MHz)", fontsize=8)
        ax.set_ylabel("21-cm brightness temperature δT_b (mK)", fontsize=8)
        top = ax.secondary_xaxis("top", functions=(lambda nu: g21.NU_21 / np.maximum(nu, 1e-3) - 1,
                                                   lambda z: g21.NU_21 / (1 + z)))
        top.set_xlabel("redshift z", fontsize=8)
        top.set_xticks([100, 50, 30, 20, 15, 10, 7])
        top.tick_params(labelsize=7)
        ax.set_title("The whole sky, averaged: absorption in the dark ages and at cosmic dawn", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower right")
        ax.tick_params(labelsize=7)

    def _draw_temperatures(self, fig) -> None:
        p = theme().palette
        s = self.result
        ax = fig.add_subplot()
        ax.loglog(1 + s.z, s.t_gamma, color=p.series[1], linewidth=2, label="radio background T_γ")
        ax.loglog(1 + s.z, s.t_gas, color=p.series[0], linewidth=2, label="gas T_K")
        ax.loglog(1 + s.z, s.t_spin, color=p.series[2], linewidth=2.2, linestyle="--", label="spin T_S")
        ax.invert_xaxis()
        ax.set_xlabel("1 + z  (time runs to the right)", fontsize=8)
        ax.set_ylabel("temperature (K)", fontsize=8)
        ax.set_title("Absorption wherever T_S < T_γ: the spins follow the gas when they are coupled to it",
                     fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _draw_couplings(self, fig) -> None:
        p = theme().palette
        s = self.result
        ax = fig.add_subplot()
        ax.loglog(1 + s.z, np.maximum(s.x_c, 1e-4), color=p.series[0], linewidth=2, label="collisions x_c")
        ax.loglog(1 + s.z, np.maximum(s.x_alpha, 1e-4), color=p.series[1], linewidth=2,
                  label="Lyman-α (Wouthuysen–Field) x_α")
        ax.loglog(1 + s.z, np.maximum(s.x_hi, 1e-4), color=p.series[2], linewidth=2, linestyle="--",
                  label="neutral fraction x_HI")
        ax.axhline(1, color=p.muted, linestyle=":", linewidth=1)
        ax.invert_xaxis()
        ax.set_ylim(1e-3, 1e3)
        ax.set_xlabel("1 + z  (time runs to the right)", fontsize=8)
        ax.set_ylabel("coupling coefficient", fontsize=8)
        ax.set_title("Above 1, a coupling wins against the CMB: first collisions, then starlight", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _csv(self):
        s = self.result
        rows = [[f"{z:.3f}", f"{nu:.3f}", f"{tg:.3f}", f"{tk:.3f}", f"{ts:.3f}", f"{tb:.3f}"]
                for z, nu, tg, tk, ts, tb in zip(s.z, s.nu, s.t_gamma, s.t_gas, s.t_spin, s.delta_tb)]
        return ["z", "frequency_MHz", "T_background_K", "T_gas_K", "T_spin_K", "delta_Tb_mK"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        return dict(self.report)

    def guide_extra(self) -> str:
        return (
            "### " + tr("Why this is so hard to measure") + "\n\n"
            + tr("The signal is a tenth of a kelvin. The radio glow of our own Galaxy at the same frequencies "
                 "is thousands of kelvin, so the foreground has to be removed to one part in 10⁵. It is "
                 "smooth in frequency and the signal is not, which is the only handle — and any wiggle the "
                 "instrument adds looks exactly like cosmology.")
        )
