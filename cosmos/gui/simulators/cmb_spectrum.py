"""S12 — CMB Power Spectrum Explorer."""

from __future__ import annotations

from dataclasses import replace

import numpy as np
from matplotlib.ticker import NullFormatter, ScalarFormatter
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QLabel,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
)

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr, tr_noop
from cosmos.physics import camb_backend, cmb

PATCH_DEG = 20.0
TEACHING, EXACT = "teaching", "camb"

TEACHING_NOTE = tr_noop(
    "<b>Teaching model.</b> Peak positions follow the real sound horizon and distance; peak heights are "
    "approximate (about 15%). Install the optional package <code>camb</code> to switch this simulator to "
    "exact spectra from a Boltzmann code."
)
EXACT_NOTE = tr_noop(
    "<b>CAMB {version}.</b> Every curve on this page is now a full Boltzmann calculation of the lensed "
    "TT spectrum — the same code research papers use. Each update takes about half a second."
)


class CMBSpectrumSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        base = cmb.PLANCK
        self._exact_cache: dict = {}
        self._computing = False
        self.reference = cmb.spectrum(base)
        self.spec = self.reference

        matter = QGroupBox(tr("1 · Contents of the universe"))
        ml = QVBoxLayout(matter)
        self.omega_b = ParameterSlider(
            tr("Ωb h²  ordinary matter"), 0.005, 0.05, base.omega_b, decimals=4, step=0.001,
            info=(tr("Baryon density"), tr("More baryons make the plasma heavier. Compressions (odd peaks: 1st, 3rd) "
                      "get stronger than rarefactions (even peaks), and damping moves to smaller scales.")),
        )
        self.omega_c = ParameterSlider(
            tr("Ωc h²  dark matter"), 0.03, 0.4, base.omega_c, decimals=4, step=0.005,
            info=(tr("Cold dark matter density"),
                  tr("More dark matter means matter dominates earlier, so gravitational potentials decay less and the "
                     "radiation driving that boosts the peaks weakens.")),
        )
        self.h = ParameterSlider(
            tr("h = H0 / 100"), 0.5, 0.9, base.h, decimals=4, step=0.005,
            info=(tr("Hubble constant"), tr("Changes the distance to the last scattering surface and therefore the "
                                            "angle the sound horizon covers. The peaks shift sideways.")),
        )
        self.omega_k = ParameterSlider(
            tr("Ωk  curvature"), -0.15, 0.15, 0.0, decimals=3, step=0.005,
            info=(tr("Spatial curvature"), tr("Positive (open): light rays diverge, spots look smaller, peaks move to "
                      "higher ℓ. Negative (closed): spots look larger, peaks move to lower ℓ. Dark energy is "
                      "adjusted so that the total adds up.")),
        )
        for w in (self.omega_b, self.omega_c, self.h, self.omega_k):
            ml.addWidget(w)
        self.controls.addWidget(matter)

        early = QGroupBox(tr("2 · Initial fluctuations and reionisation"))
        el = QVBoxLayout(early)
        self.n_s = ParameterSlider(
            tr("nₛ  spectral index"), 0.8, 1.2, base.n_s, decimals=4, step=0.005,
            info=(tr("Spectral index"), tr("nₛ = 1 means equal strength on all scales. Values below 1 (Planck: 0.965) "
                      "give slightly weaker small-scale fluctuations, as predicted by inflation.")),
        )
        self.a_s = ParameterSlider(
            tr("Aₛ × 10⁹  amplitude"), 1.0, 4.0, base.a_s * 1e9, decimals=3, step=0.05,
            info=(tr("Amplitude"), tr("Overall strength of the primordial fluctuations. Scales the whole spectrum.")),
        )
        self.tau = ParameterSlider(
            tr("τ  reionisation optical depth"), 0.0, 0.2, base.tau, decimals=3, step=0.005,
            info=(tr("Optical depth"), tr("When the first stars reionised the universe, free electrons scattered some "
                                          "CMB "
                      "photons again, smoothing small-scale fluctuations by a factor e^(−2τ).")),
        )
        for w in (self.n_s, self.a_s, self.tau):
            el.addWidget(w)
        self.controls.addWidget(early)

        engine = QGroupBox(tr("3 · How the spectrum is computed"))
        gl = QVBoxLayout(engine)
        self.backend = QComboBox()
        self.backend.addItem(tr("Teaching model (instant)"), TEACHING)
        self.backend.addItem(tr("CAMB — exact Boltzmann code"), EXACT)
        if not camb_backend.available():
            self.backend.model().item(1).setEnabled(False)
            self.backend.setItemData(1, "Not installed. Run: pip install camb", Qt.ToolTipRole)
        gl.addWidget(labelled_row(tr("Engine"), self.backend, (
            tr("Two engines"),
            tr("The teaching model is an analytic approximation that reacts instantly, which is what you want "
                "while dragging a slider. CAMB solves the Boltzmann equations properly: slower, but exact. "
                "Comparing the two is a good way to see what the approximation gets right."))))
        self.engine_note = QLabel()
        self.engine_note.setWordWrap(True)
        self.engine_note.setProperty("role", "muted")
        gl.addWidget(self.engine_note)
        self.controls.addWidget(engine)

        pol = QGroupBox(tr("4 · Polarisation"))
        pl = QVBoxLayout(pol)
        self.tensor_r = ParameterSlider(
            tr("Tensor-to-scalar ratio r"), 0.0, 0.3, 0.0, decimals=3, step=0.005,
            info=(tr("The signature of inflation"),
                  tr("Gravitational waves from inflation are the only thing that can make B modes at "
                     "recombination. Their strength relative to the density ripples is r, and measuring it "
                     "would give the energy scale at which inflation happened.")),
        )
        self.a_lens = ParameterSlider(
            tr("Lensing amplitude A_lens"), 0.0, 1.5, 1.0, decimals=2, step=0.05,
            info=(tr("Delensing"),
                  tr("Lensing by the matter between us and the CMB bends the E modes and turns a little of "
                     "them into B modes. That foreground of our own making can be subtracted if the matter "
                     "distribution is known well enough: A_lens = 0.1 means 90% removed.")),
        )
        self.dust = ParameterSlider(
            tr("Polarised dust at ℓ = 80 (μK²)"), 0.0, 0.1, cmb.POLARISATION["dust_150"],
            decimals=4, step=0.002,
            info=(tr("The Galaxy is in the way"),
                  tr("Spinning dust grains in the Milky Way align with the magnetic field and emit polarised "
                     "light, with B modes of their own. In 2014 BICEP2 announced r = 0.2 from a signal that "
                     "turned out to be mostly this.")),
        )
        for w in (self.tensor_r, self.a_lens, self.dust):
            pl.addWidget(w)
        self.controls.addWidget(pol)

        view = QGroupBox(tr("5 · Display"))
        vl = QVBoxLayout(view)
        self.show_reference = QCheckBox(tr("Show the Planck 2018 model for comparison"))
        self.show_reference.setChecked(True)
        self.log_axis = QCheckBox(tr("Logarithmic ℓ axis"))
        self.show_peaks = QCheckBox(tr("Mark the acoustic peaks"))
        self.show_peaks.setChecked(True)
        for w in (self.show_reference, self.log_axis, self.show_peaks):
            vl.addWidget(w)
            w.toggled.connect(self.schedule_update)
        reset = QPushButton(tr("Reset to Planck 2018"))
        reset.clicked.connect(self.reset)
        vl.addWidget(reset)
        self.controls.addWidget(view)

        results = QGroupBox(tr("What the model gives"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", tr(TEACHING_NOTE))
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.plot = PlotWidget(self._draw_spectrum, csv_provider=self._csv, export_name="cmb_power_spectrum")
        self.map_plot = PlotWidget(self._draw_maps, export_name="cmb_sky_patch")
        self.pol_plot = PlotWidget(self._draw_polarisation, csv_provider=self._csv_polarisation,
                                   export_name="cmb_polarisation")
        self.bb_plot = PlotWidget(self._draw_bmodes, export_name="cmb_b_modes")
        tabs.addTab(self.plot, tr("Power spectrum"))
        tabs.addTab(self.pol_plot, tr("E modes and TE"))
        tabs.addTab(self.bb_plot, tr("B modes"))
        tabs.addTab(self.map_plot, tr("What the sky looks like"))
        self.display.addWidget(tabs, 1)

        for w in (self.omega_b, self.omega_c, self.h, self.omega_k, self.n_s, self.a_s, self.tau,
                  self.tensor_r, self.a_lens, self.dust):
            w.valueChanged.connect(self.schedule_update)
        self.backend.currentIndexChanged.connect(self._backend_changed)
        self._backend_changed()

    # ----------------------------------------------------------- engines
    def engine(self) -> str:
        return self.backend.currentData()

    def _backend_changed(self, *_args) -> None:
        exact = self.engine() == EXACT
        # A Boltzmann run takes about half a second, so wait a little longer before recomputing.
        self._update_timer.setInterval(450 if exact else 40)
        if exact:
            self.banner.set_message("info", tr(EXACT_NOTE).format(version=camb_backend.version()))
            self.engine_note.setText(tr("Exact spectra. Sliders react after a short pause."))
        else:
            self.banner.set_message("info", tr(TEACHING_NOTE))
            self.engine_note.setText(
                tr("Instant approximation.") if camb_backend.available()
                else tr("CAMB is not installed; only the teaching model is available."))
        self.reference = self._compute(cmb.PLANCK)
        self.recompute()

    def _compute(self, params: cmb.CMBParameters) -> cmb.CMBSpectrum:
        """The spectrum of one model, from whichever engine is selected."""
        if self.engine() != EXACT:
            return cmb.spectrum(params)
        key = (params, )
        if key in self._exact_cache:
            return self._exact_cache[key]
        QGuiApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            spec = camb_backend.spectrum(params)
        except Exception as exc:                     # noqa: BLE001 - CAMB rejects extreme parameters
            self.banner.set_message("warning", tr("<b>CAMB could not compute this universe:</b> {error}")
                                    .format(error=exc))
            spec = cmb.spectrum(params)
        finally:
            QGuiApplication.restoreOverrideCursor()
        self._exact_cache[key] = spec
        if len(self._exact_cache) > 24:              # keep the cache small
            self._exact_cache.pop(next(iter(self._exact_cache)))
        return spec

    # ------------------------------------------------------------ model
    def parameters(self) -> cmb.CMBParameters:
        return replace(
            cmb.PLANCK,
            omega_b=self.omega_b.value(),
            omega_c=self.omega_c.value(),
            h=self.h.value(),
            omega_k=self.omega_k.value(),
            n_s=self.n_s.value(),
            a_s=self.a_s.value() * 1e-9,
            tau=self.tau.value(),
        )

    def reset(self) -> None:
        base = cmb.PLANCK
        for slider, value in [
            (self.omega_b, base.omega_b), (self.omega_c, base.omega_c), (self.h, base.h), (self.omega_k, 0.0),
            (self.n_s, base.n_s), (self.a_s, base.a_s * 1e9), (self.tau, base.tau),
            (self.tensor_r, 0.0), (self.a_lens, 1.0), (self.dust, cmb.POLARISATION["dust_150"]),
        ]:
            slider.setValue(value, emit=False)
        self.recompute()

    def recompute(self) -> None:
        if self._computing:          # a Boltzmann run must never be re-entered
            return
        self._computing = True
        try:
            self._recompute()
        finally:
            self._computing = False

    def _recompute(self) -> None:
        params = self.parameters()
        cosmo = params.cosmology()
        valid = cosmo.has_big_bang() and cosmo.Ode0 > -0.5
        if not valid:
            self.summary.setText(tr("<b>This combination has no Big Bang.</b> Reduce the curvature or dark matter."))
            return
        self.spec = spec = self._compute(params)
        peaks = spec.peaks
        rows = []
        for i, (ell, d) in enumerate(peaks[:3]):
            ref = self.reference.peaks[i][0]
            rows.append(tr("Peak {number}: ℓ = <b>{ell}</b> ({height} μK²; Planck model ℓ = {reference})")
                        .format(number=i + 1, ell=f"{ell:.0f}", height=f"{d:.0f}", reference=f"{ref:.0f}"))
        ratio = peaks[0][1] / peaks[1][1] if len(peaks) > 1 else float("nan")
        self.summary.setText(
            "<br>".join(rows) + "<br>"
            + tr("Height ratio peak 1 / peak 2: <b>{ratio}</b><br>"
                 "Sound horizon at decoupling rₛ: <b>{sound_horizon} Mpc</b><br>"
                 "Distance to last scattering: <b>{distance} Gpc</b><br>"
                 "Acoustic angle θ*: <b>{angle}°</b><br>"
                 "Decoupling redshift z*: <b>{z_star}</b><br>"
                 "Baryon loading R*: <b>{loading}</b><br>"
                 "Derived: Ωm = {omega_m}, ΩΛ = {omega_lambda}, age = {age} Gyr")
            .format(ratio=f"{ratio:.2f}", sound_horizon=f"{spec.r_s:.1f}", distance=f"{spec.d_m / 1e3:.2f}",
                    angle=f"{np.degrees(spec.theta_star):.3f}", z_star=f"{spec.z_star:.0f}",
                    loading=f"{spec.r_star:.2f}", omega_m=f"{cosmo.Om0:.3f}",
                    omega_lambda=f"{cosmo.Ode0:.3f}", age=f"{cosmo.age():.2f}")
        )
        self.pol = cmb.polarisation(params, r=self.tensor_r.value(), a_lens=self.a_lens.value(),
                                    dust=self.dust.value())
        for plot in (self.plot, self.pol_plot, self.bb_plot, self.map_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_spectrum(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        if self.show_reference.isChecked():
            ax.plot(self.reference.ell, self.reference.d_ell, color=p.muted, linewidth=1.3, linestyle="--",
                    label="Planck 2018")
        ax.plot(self.spec.ell, self.spec.d_ell, color=p.series[0], linewidth=2.2, label="Your universe")
        if self.show_peaks.isChecked():
            for i, (ell, d) in enumerate(self.spec.peaks[:5]):
                ax.scatter([ell], [d], color=p.accent2, zorder=4, s=18)
                ax.annotate(str(i + 1), (ell, d), textcoords="offset points", xytext=(0, 7), ha="center",
                            color=p.accent2, fontsize=8)
        if self.log_axis.isChecked():
            ax.set_xscale("log")
            ax.set_xlim(2, cmb.ELL_MAX)
        else:
            ax.set_xlim(0, cmb.ELL_MAX)
        top = max(float(np.nanmax(self.spec.d_ell)), float(np.nanmax(self.reference.d_ell)))
        ax.set_ylim(0, top * 1.15 if np.isfinite(top) and top > 0 else 7000)
        ax.set_xlabel("Multipole ℓ   (angular size ≈ 180° / ℓ)")
        ax.set_ylabel("ℓ(ℓ+1)Cℓ / 2π  (μK²)")
        ax.legend(loc="upper right", fontsize=8)

    def _draw_maps(self, fig) -> None:
        p = theme().palette
        axes = fig.subplots(1, 2)
        maps = [
            (cmb.sky_patch(self.spec, PATCH_DEG, 256, seed=21), "Your universe"),
            (cmb.sky_patch(self.reference, PATCH_DEG, 256, seed=21), "Planck 2018 model"),
        ]
        limit = 3 * float(np.std(maps[1][0]))
        for ax, (patch, title) in zip(axes, maps):
            ax.imshow(patch, cmap="RdBu_r", extent=(0, PATCH_DEG, 0, PATCH_DEG), vmin=-limit, vmax=limit,
                      origin="lower")
            ax.set_title(f"{title}  (rms {patch.std():.0f} μK)", fontsize=9, color=p.text)
            ax.set_xlabel("degrees")
        fig.suptitle("Simulated 20° × 20° sky patches with the same random seed", fontsize=9, color=p.text)

    def _draw_polarisation(self, fig) -> None:
        p = theme().palette
        pol = self.pol
        top, bottom = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [1, 1], "hspace": 0.12})
        top.plot(pol.ell, pol.ee, color=p.series[0], linewidth=2, label="EE (E modes)")
        scaled = self.spec.d_ell / 120.0
        top.plot(self.spec.ell, scaled, color=p.muted, linewidth=1.1, linestyle="--",
                 label="TT / 120, for comparison")
        for ell, height in cmb.find_peaks(pol.ell, pol.ee, limit=4):
            top.scatter([ell], [height], color=p.accent2, s=16, zorder=4)
        top.set_ylabel("E-mode power (μK²)", fontsize=8)
        top.set_ylim(0, max(float(np.nanmax(pol.ee)), 1.0) * 1.2)
        top.legend(fontsize=7.5, loc="upper left")
        top.set_title("E-mode peaks fall where the temperature peaks do not", fontsize=9)

        bottom.axhline(0, color=p.border, linewidth=1)
        bottom.plot(pol.ell, pol.te, color=p.series[1], linewidth=1.8, label="TE (temperature × E)")
        bottom.set_xlabel("Multipole ℓ", fontsize=8)
        bottom.set_ylabel("TE cross-power (μK²)", fontsize=8)
        bottom.legend(fontsize=7.5, loc="upper left")
        for axis in (top, bottom):
            axis.set_xlim(2, cmb.ELL_MAX)
            axis.tick_params(labelsize=7)

    def _draw_bmodes(self, fig) -> None:
        p = theme().palette
        pol = self.pol
        ax = fig.add_subplot()
        ax.plot(pol.ell, pol.bb_lensing, color=p.muted, linewidth=1.8,
                label=f"lensing B modes (A_lens = {pol.a_lens:.2f})")
        ax.plot(pol.ell, pol.bb_dust, color=p.warning, linewidth=1.6, linestyle="-.",
                label="polarised Galactic dust")
        limit = cmb.polarisation(self.parameters(), r=cmb.BICEP_LIMIT_R, dust=0.0)
        ax.plot(pol.ell, limit.bb_tensor, color=p.border, linewidth=1.2, linestyle=":",
                label=f"r = {cmb.BICEP_LIMIT_R} (today's upper limit)")
        if pol.r > 0:
            ax.plot(pol.ell, pol.bb_tensor, color=p.series[0], linewidth=2.2,
                    label=f"primordial B modes, r = {pol.r:.3f}")
        ax.plot(pol.ell, pol.bb_total, color=p.danger, linewidth=1.3, linestyle="--", label="what you measure")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_xlim(2, cmb.ELL_MAX)
        ax.set_ylim(1e-5, 1.0)
        for axis in (ax.xaxis,):
            axis.set_major_formatter(ScalarFormatter())
            axis.set_minor_formatter(NullFormatter())
        ax.set_xticks([2, 10, 80, 300, 1000, 2500])
        ax.axvline(80, color=p.border, linewidth=0.9, linestyle=":")
        ax.text(80, 0.6, " ℓ = 80: where inflation would show", color=p.muted, fontsize=7, va="top")
        ax.set_xlabel("Multipole ℓ")
        ax.set_ylabel("B-mode power (μK²)")
        ax.set_title("B modes: a curl in the polarisation that density ripples cannot make", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower right")

    def _csv_polarisation(self):
        pol = self.pol
        rows = [[f"{ell:.0f}", f"{ee:.4f}", f"{te:.4f}", f"{bl:.6f}", f"{bt:.6f}", f"{bd:.6f}"]
                for ell, ee, te, bl, bt, bd in zip(pol.ell, pol.ee, pol.te, pol.bb_lensing, pol.bb_tensor,
                                                 pol.bb_dust)]
        return ["ell", "EE_uK2", "TE_uK2", "BB_lensing", "BB_tensor", "BB_dust"], rows

    def _csv(self):
        rows = [[f"{ell:.0f}", f"{d:.3f}", f"{r:.3f}"]
                for ell, d, r in zip(self.spec.ell, self.spec.d_ell, self.reference.d_ell)]
        return ["ell", "D_ell_uK2", "planck_model_D_ell_uK2"], rows

    def state(self) -> dict:
        return {
            "engine": self.engine(),
            "omega_b": self.omega_b.value(),
            "omega_c": self.omega_c.value(),
            "omega_k": self.omega_k.value(),
            "h": self.h.value(),
            "first_peak": self.spec.peaks[0][0] if self.spec.peaks else float("nan"),
            "tau": self.tau.value(),
            "r": self.pol.r,
            "a_lens": self.pol.a_lens,
            "dust": self.dust.value(),
            "ee_peak": max(float(np.nanmax(self.pol.ee)), 0.0),
            "ee_first_peak": (cmb.find_peaks(self.pol.ell, self.pol.ee, limit=1) or [(float("nan"),)])[0][0],
            "bb_tensor_80": self.pol.at(self.pol.bb_tensor, 80),
            "bb_lensing_80": self.pol.at(self.pol.bb_lensing, 80),
            "bb_dust_80": self.pol.at(self.pol.bb_dust, 80),
            "tensor_above_foregrounds": (self.pol.at(self.pol.bb_tensor, 80)
                                         > self.pol.at(self.pol.bb_lensing, 80)
                                         + self.pol.at(self.pol.bb_dust, 80)),
        }

    def guide_extra(self) -> str:
        engines = (tr("Both engines are available: compare them with the **Engine** box.")
                   if camb_backend.available()
                   else tr("Only the teaching model is available here. `pip install camb` adds the exact "
                           "engine."))
        return (
            "### " + tr("Two engines") + f"\n\n{engines}\n\n"
            + "### " + tr("Reading the spectrum") + "\n\n"
            + tr("- **Left (ℓ < 50):** regions larger than the horizon at decoupling, the flat Sachs–Wolfe "
                 "plateau.\n"
                 "- **Peaks:** sound waves caught at maximum compression (1, 3, 5) or rarefaction (2, 4).\n"
                 "- **Right (ℓ > 1300):** photon diffusion erases the smallest ripples (Silk damping).")
        )
