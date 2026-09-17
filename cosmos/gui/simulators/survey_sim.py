"""S21 — Survey Designer."""

from __future__ import annotations

import numpy as np
from matplotlib.ticker import NullFormatter, ScalarFormatter
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QTabWidget, QVBoxLayout

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import survey
from cosmos.physics.presets import PRESETS


class SurveySimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.result: survey.Forecast | None = None
        self._loading = False

        programme = QGroupBox(tr("0 · Start from"))
        pl = QVBoxLayout(programme)
        self.preset = QComboBox()
        self.preset.addItem(tr("Custom"), "custom")
        for key, (label, _settings) in survey.PRESETS_SURVEY.items():
            self.preset.addItem(physics(label), key)
        pl.addWidget(labelled_row(tr("Programme"), self.preset, (
            tr("Programmes"),
            tr("Survey designs in the style of real projects. The forecasts are approximate and use one "
               "tracer at a time; real surveys observe several at once."))))
        self.controls.addWidget(programme)

        target = QGroupBox(tr("1 · What to observe"))
        tl = QVBoxLayout(target)
        self.tracer = QComboBox()
        for key, tracer in survey.TRACERS.items():
            self.tracer.addItem(physics(tracer.label), key)
            self.tracer.setItemData(self.tracer.count() - 1, physics(tracer.description), Qt.ToolTipRole)
        tl.addWidget(labelled_row(tr("Tracer"), self.tracer, (
            tr("Tracers"),
            tr("Different kinds of galaxy trace the same cosmic web with a different bias: strongly clustered "
               "ones give a stronger signal per galaxy."))))
        self.z_min = ParameterSlider(tr("Lowest redshift"), 0.05, 3.0, 0.4, decimals=2, step=0.05)
        self.z_max = ParameterSlider(tr("Highest redshift"), 0.1, 3.5, 1.1, decimals=2, step=0.05)
        self.density = ParameterSlider(
            tr("Target density n̄ (h/Mpc)³"), 1e-6, 3e-3, 5e-4, decimals=6, log=True,
            info=(tr("Shot noise"),
                  tr("With too few galaxies you cannot trace the web: the measurement is limited by shot noise. "
                     "The product n̄P tells you which regime you are in — below 1 shot noise dominates, well "
                     "above 1 extra galaxies barely help.")),
        )
        for w in (self.z_min, self.z_max, self.density):
            tl.addWidget(w)
        self.controls.addWidget(target)

        where = QGroupBox(tr("2 · Where and for how long"))
        wl = QVBoxLayout(where)
        self.area = ParameterSlider(
            tr("Sky area (deg²)"), 100, 20_000, 14_000, decimals=0, log=True,
            info=(tr("Sample variance"),
                  tr("A survey can only average over the patches of the universe it covers. More area means more "
                     "independent patches: the whole sky is about 41 000 deg², and a ground telescope sees "
                     "roughly half of it.")),
        )
        self.fibres = ParameterSlider(
            tr("Spectra per field (fibres)"), 100, 30_000, 5000, decimals=0, log=True,
            info=(tr("Multiplexing"),
                  tr("DESI's 5000 robotic fibres take 5000 spectra at once; BOSS had 1000. A space slitless "
                     "spectrograph records everything in its field.")),
        )
        self.fields = ParameterSlider(tr("Fields per night"), 1, 20, 10, decimals=0, step=1)
        self.nights = ParameterSlider(tr("Usable nights per year"), 20, 330, 250, decimals=0, step=5)
        self.years = ParameterSlider(tr("Years"), 0.5, 10, 5, decimals=1, step=0.5)
        for w in (self.area, self.fibres, self.fields, self.nights, self.years):
            wl.addWidget(w)
        self.controls.addWidget(where)

        errors = QGroupBox(tr("3 · Systematics"))
        el = QVBoxLayout(errors)
        self.floor = ParameterSlider(
            tr("Systematic floor (%)"), 0.0, 1.0, 0.0, decimals=2, step=0.05,
            info=(tr("An error that does not average away"),
                  tr("Imaging calibration, redshift failures or the modelling of non-linear physics set a minimum "
                     "error. It is added in quadrature and does not shrink with more galaxies.")),
        )
        el.addWidget(self.floor)
        self.controls.addWidget(errors)

        results = QGroupBox(tr("The forecast"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Teaching forecast: BAO distance errors from the effective volume, calibrated "
                                    "on BOSS. Good to tens of percent.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.distance_plot = PlotWidget(self._draw_distances, csv_provider=self._csv, export_name="bao_forecast")
        self.tradeoff_plot = PlotWidget(self._draw_tradeoff, export_name="survey_area_tradeoff")
        tabs.addTab(self.distance_plot, tr("BAO distances"))
        tabs.addTab(self.tradeoff_plot, tr("Wide or deep?"))
        self.display.addWidget(tabs, 1)

        self.inputs = (self.z_min, self.z_max, self.density, self.area, self.fibres, self.fields, self.nights,
                       self.years, self.floor)
        for w in self.inputs:
            w.valueChanged.connect(self._changed)
        self.tracer.currentIndexChanged.connect(self._tracer_changed)
        self.preset.currentIndexChanged.connect(self._load_preset)
        self.preset.setCurrentIndex(self.preset.findData("desi_lrg"))

    # ------------------------------------------------------------ inputs
    def settings(self) -> survey.SurveySettings:
        z_low, z_high = sorted((self.z_min.value(), self.z_max.value()))
        if z_high - z_low < 0.05:
            z_high = z_low + 0.05
        return survey.SurveySettings(
            tracer=self.tracer.currentData(), area_deg2=self.area.value(), z_min=z_low, z_max=z_high,
            density=self.density.value(), fibres=int(round(self.fibres.value())),
            fields_per_night=self.fields.value(), nights_per_year=self.nights.value(), years=self.years.value(),
            systematic_floor=self.floor.value(),
        )

    def _load_preset(self, *_args) -> None:
        key = self.preset.currentData()
        if key not in survey.PRESETS_SURVEY:
            return
        s = survey.PRESETS_SURVEY[key][1]
        self._loading = True
        self.tracer.setCurrentIndex(self.tracer.findData(s.tracer))
        for widget, value in ((self.z_min, s.z_min), (self.z_max, s.z_max), (self.density, s.density),
                              (self.area, s.area_deg2), (self.fibres, s.fibres), (self.fields, s.fields_per_night),
                              (self.nights, s.nights_per_year), (self.years, s.years), (self.floor, 0.0)):
            widget.setValue(value, emit=False)
        self._loading = False
        self.recompute()

    def _tracer_changed(self, *_args) -> None:
        if self._loading:
            return
        tracer = survey.TRACERS[self.tracer.currentData()]
        self._loading = True
        self.z_min.setValue(tracer.z_range[0], emit=False)
        self.z_max.setValue(tracer.z_range[1], emit=False)
        self.density.setValue(tracer.density, emit=False)
        self._loading = False
        self._changed()

    def _changed(self, *_args) -> None:
        if self._loading:
            return
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(0)
        self.preset.blockSignals(False)
        self.schedule_update()

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        f = self.result = survey.forecast(self.settings())
        n_p = f.n_p
        regime = (tr("shot-noise limited") if n_p < 1 else
                  tr("sample-variance limited") if n_p > 3 else tr("balanced"))
        lines = [
            tr("BAO distance precision: <b>{stat}%</b> statistical, <b>{total}%</b> with systematics")
            .format(stat=f"{f.statistical_percent:.2f}", total=f"{f.total_percent:.2f}"),
            tr("Volume {volume} (Gpc/h)³, effective volume {effective} (Gpc/h)³")
            .format(volume=f"{f.volume:.1f}", effective=f"{f.effective_volume:.1f}"),
            tr("n̄P = <b>{np}</b>: {regime}").format(np=f"{n_p:.2f}", regime=regime),
            tr("Galaxies needed {needed} million, spectra available {available} million")
            .format(needed=f"{f.targets_needed / 1e6:.1f}", available=f"{f.spectra_available / 1e6:.1f}"),
        ]
        self.summary.setText("<br>".join(lines))
        if f.diluted:
            self.banner.set_message(
                "warning",
                tr("<b>Not enough telescope time.</b> The programme can take only {fraction} of the spectra it "
                   "needs, so the density drops to {density} (h/Mpc)³. Observe longer, use more fibres, or cover "
                   "less sky.").format(fraction=f"{f.spectra_available / f.targets_needed:.0%}",
                                       density=f"{f.density_used:.1e}"))
        elif self.floor.value() > 0 and f.statistical_percent < self.floor.value():
            self.banner.set_message(
                "danger",
                tr("<b>The systematic floor dominates.</b> The statistical error ({stat}%) is already below the "
                   "floor ({floor}%): more galaxies or more years would not improve the result.")
                .format(stat=f"{f.statistical_percent:.2f}", floor=f"{self.floor.value():.2f}"))
        else:
            self.banner.set_message(
                "info",
                tr("<b>Forecast.</b> {galaxies} million redshifts over {area} deg² measure the expansion history "
                   "to {total}% in {bins} redshift slices.")
                .format(galaxies=f"{f.galaxies / 1e6:.1f}", area=f"{f.settings.area_deg2:,.0f}".replace(",", " "),
                        total=f"{f.total_percent:.2f}", bins=len(f.bins)))
        self.distance_plot.refresh()
        self.tradeoff_plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_distances(self, fig) -> None:
        p = theme().palette
        f = self.result
        cosmo = PRESETS["planck18"].cosmology
        top, bottom = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [2, 1]})
        z = np.linspace(0.05, max(3.0, f.settings.z_max + 0.2), 120)
        d_m = np.asarray(cosmo.transverse_comoving_distance(z), dtype=float)
        d_v = (z * d_m**2 * survey.C_KM_S / np.asarray(cosmo.H(z), dtype=float)) ** (1 / 3)
        top.plot(z, d_v / survey.SOUND_HORIZON_MPC / np.sqrt(z), color=p.muted, linewidth=1.5,
                 label="Planck 2018 model")
        zs = np.array([b.z_mid for b in f.bins])
        values = np.array([b.dv_over_rd for b in f.bins]) / np.sqrt(zs)
        errors = values * np.hypot([b.error_percent for b in f.bins], f.settings.systematic_floor) / 100
        top.errorbar(zs, values, yerr=errors, fmt="o", color=p.series[0], capsize=3, markersize=5,
                     label="your survey (1σ)")
        top.set_ylabel("D_V / (r_d √z)", fontsize=8)
        top.legend(fontsize=7.5, loc="lower right")
        top.set_title("Forecast BAO measurements, one point per Δz = 0.1 slice", fontsize=9)

        stat = np.array([b.error_percent for b in f.bins])
        bottom.bar(zs, stat, width=0.08, color=p.series[0], alpha=0.8, label="statistical")
        if f.settings.systematic_floor > 0:
            bottom.axhline(f.settings.systematic_floor, color=p.danger, linestyle="--", linewidth=1.2,
                           label="systematic floor")
        bottom.set_ylabel("error per slice (%)", fontsize=8)
        bottom.set_xlabel("redshift z", fontsize=8)
        bottom.set_ylim(0, max(float(stat.max()) * 1.25, f.settings.systematic_floor * 1.3, 0.5))
        bottom.legend(fontsize=7, loc="upper right")
        for axis in (top, bottom):
            axis.tick_params(labelsize=7)

    def _draw_tradeoff(self, fig) -> None:
        p = theme().palette
        f = self.result
        ax = fig.add_subplot()
        areas, errors = survey.area_tradeoff(f.settings)
        ax.plot(areas, errors, color=p.series[0], linewidth=2,
                label=f"same {f.galaxies / 1e6:.1f} million galaxies spread over more or less sky")
        best = int(np.argmin(errors))
        ax.plot([areas[best]], [errors[best]], "*", color=p.accent2, markersize=13, label="best area")
        ax.plot([f.settings.area_deg2], [f.statistical_percent], "o", color=p.text, markersize=7,
                label="your design")
        ax.axvline(survey.SKY_DEG2 / 2, color=p.border, linestyle=":", linewidth=1)
        ax.text(survey.SKY_DEG2 / 2, errors.max(), " half the sky", color=p.muted, fontsize=7, va="top")
        ax.set_xscale("log")
        ax.set_yscale("log")
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_formatter(ScalarFormatter())
            axis.set_minor_formatter(NullFormatter())
        ax.set_xlabel("sky area (deg²)")
        ax.set_ylabel("statistical BAO error (%)")
        ax.set_title("Narrow and deep, or wide and shallow? The optimum is where n̄P = 1", fontsize=9)
        ax.legend(fontsize=7.5, loc="upper right")

    def _csv(self):
        f = self.result
        rows = [[f"{b.z_low:.2f}", f"{b.z_high:.2f}", f"{b.volume:.4f}", f"{b.effective_volume:.4f}",
                 f"{b.n_p:.3f}", f"{b.dv_over_rd:.3f}", f"{b.error_percent:.3f}"] for b in f.bins]
        return ["z_low", "z_high", "volume_gpc3_h-3", "effective_volume", "nP", "DV_over_rd", "error_percent"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        f = self.result
        s = f.settings
        return {
            "preset": self.preset.currentData(),
            "tracer": s.tracer,
            "area": s.area_deg2,
            "z_min": s.z_min,
            "z_max": s.z_max,
            "density": s.density,
            "years": s.years,
            "n_p": f.n_p,
            "diluted": f.diluted,
            "stat_percent": f.statistical_percent,
            "total_percent": f.total_percent,
            "floor": s.systematic_floor,
            "stat_below_floor": s.systematic_floor > 0 and f.statistical_percent < s.systematic_floor,
            "galaxies_millions": f.galaxies / 1e6,
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("The two numbers that decide a survey") + "\n\n"
            + tr("- **Volume** sets how many independent patches of the cosmic web you average over.\n"
                 "- **n̄P**, the galaxy density times the clustering power, says whether you have enough galaxies "
                 "to see each patch.\n\n"
                 "Together they give the effective volume, $V_\\mathrm{eff} = V\\,[\\bar nP/(1+\\bar nP)]^2$, and "
                 "the distance error falls as $1/\\sqrt{V_\\mathrm{eff}}$.")
        )
