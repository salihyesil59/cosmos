"""S23 — Redshift Survey Slice."""

from __future__ import annotations

import numpy as np
from matplotlib.ticker import NullFormatter, ScalarFormatter
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QLabel, QTabWidget, QVBoxLayout

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import mock, sdss


class SliceSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.catalogue: mock.Catalogue | None = None
        self.report: dict = {}
        self._xi_cache: tuple | None = None
        self._real = None            # the SDSS slice, loaded on first use
        self._real_xi = None
        self._loading = False

        start = QGroupBox(tr("0 · Start from"))
        sl = QVBoxLayout(start)
        self.preset = QComboBox()
        self.preset.addItem(tr("Custom"), "custom")
        for key, (label, _settings) in mock.PRESETS_MOCK.items():
            self.preset.addItem(physics(label), key)
        sl.addWidget(labelled_row(tr("Survey"), self.preset, (
            tr("Mock catalogues"),
            tr("Each choice observes the same simulated universe in a different way. Compare any of them with "
               "<b>the true universe</b> to see what the observing did."))))
        self.controls.addWidget(start)

        universe = QGroupBox(tr("1 · The simulated universe"))
        ul = QVBoxLayout(universe)
        self.seed = ParameterSlider(
            tr("Random seed"), 1, 40, 7, decimals=0, step=1,
            info=(tr("One universe out of many"),
                  tr("The initial conditions are a random draw. Change the seed and you get a different universe "
                     "with exactly the same statistics — which is why a measurement made in one of them has an "
                     "error bar at all.")),
        )
        self.bias = ParameterSlider(
            tr("Galaxy bias b"), 0.6, 3.0, 1.3, decimals=2, step=0.05,
            info=(tr("Galaxies are not matter"),
                  tr("Galaxies form in the densest places, so they clump harder than the matter does: "
                     "1 + δ_galaxies = (1 + δ_matter)^b, roughly. Red massive galaxies have b ≈ 2, blue "
                     "star-forming ones b ≈ 1.")),
        )
        self.density = ParameterSlider(
            tr("Galaxies per (Mpc/h)³"), 1e-3, 1.5e-1, 3e-3, decimals=4, log=True)
        for w in (self.seed, self.bias, self.density):
            ul.addWidget(w)
        self.controls.addWidget(universe)

        geometry = QGroupBox(tr("2 · The slice you observe"))
        gl = QVBoxLayout(geometry)
        self.wedge = ParameterSlider(tr("Opening angle (°)"), 20, 180, 120, decimals=0, step=5)
        self.thickness = ParameterSlider(
            tr("Slice thickness (°)"), 1, 12, 4, decimals=1, step=0.5,
            info=(tr("Why a slice?"),
                  tr("A three-dimensional map cannot be drawn on paper. Taking a thin wedge of the sky and "
                     "plotting distance against angle gives the cone diagram in which the cosmic web was first "
                     "seen, in 1986.")),
        )
        self.depth = ParameterSlider(tr("Depth (Mpc/h)"), 80, 330, 300, decimals=0, step=10)
        for w in (self.wedge, self.thickness, self.depth):
            gl.addWidget(w)
        self.controls.addWidget(geometry)

        observing = QGroupBox(tr("3 · What observing does to it"))
        ol = QVBoxLayout(observing)
        self.velocities = QCheckBox(tr("Peculiar velocities (redshift-space distortions)"))
        self.velocities.setChecked(True)
        ol.addWidget(self.velocities)
        self.fingers = ParameterSlider(
            tr("Cluster velocity dispersion (km/s)"), 0, 1200, 500, decimals=0, step=50,
            info=(tr("Fingers of God"),
                  tr("Galaxies inside a cluster orbit at hundreds of km/s. A redshift cannot tell that motion "
                     "from distance, so the cluster is smeared into a spike pointing straight at us.")),
        )
        self.magnitude = ParameterSlider(
            tr("Apparent magnitude limit (0 = none)"), 0, 20, 0, decimals=2, step=0.25,
            info=(tr("A flux-limited catalogue"),
                  tr("A telescope sees down to a fixed brightness, so far away only the rare luminous galaxies "
                     "make the list. The catalogue thins out with distance — and the galaxies left in it are "
                     "not a fair sample.")),
        )
        self.photo_z = ParameterSlider(
            tr("Redshift error σ_z / (1+z)"), 0.0, 0.04, 0.0, decimals=4, step=0.002,
            info=(tr("Spectra or colours?"),
                  tr("A spectrum gives a redshift to one part in ten thousand. Estimating it from a few filters "
                     "is far cheaper but uncertain by a few percent, which smears the map along the line of "
                     "sight far more than any peculiar velocity.")),
        )
        for w in (self.fingers, self.magnitude, self.photo_z):
            ol.addWidget(w)
        self.controls.addWidget(observing)

        results = QGroupBox(tr("The catalogue"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Teaching mock: a lognormal density field, not an N-body simulation. Below "
                                    "the cell size of about 4 Mpc/h it has no structure at all.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.cone_plot = PlotWidget(self._draw_cone, csv_provider=self._csv, export_name="redshift_slice")
        self.compare_plot = PlotWidget(self._draw_compare, export_name="redshift_space_distortions")
        self.profile_plot = PlotWidget(self._draw_profile, export_name="survey_selection")
        self.xi_plot = PlotWidget(self._draw_xi, export_name="correlation_function")
        self.real_plot = PlotWidget(self._draw_real, export_name="sdss_slice")
        tabs.addTab(self.cone_plot, tr("Cone diagram"))
        tabs.addTab(self.compare_plot, tr("Truth vs observed"))
        tabs.addTab(self.profile_plot, tr("Selection"))
        tabs.addTab(self.xi_plot, tr("Correlation function"))
        if sdss.available():
            tabs.addTab(self.real_plot, tr("The real sky (SDSS)"))
        self.display.addWidget(tabs, 1)

        self.inputs = (self.seed, self.bias, self.density, self.wedge, self.thickness, self.depth,
                       self.fingers, self.magnitude, self.photo_z)
        for w in self.inputs:
            w.valueChanged.connect(self._changed)
        self.velocities.toggled.connect(self._changed)
        self.preset.currentIndexChanged.connect(self._load_preset)
        self.preset.setCurrentIndex(self.preset.findData("sdss"))

    # ------------------------------------------------------------ inputs
    def settings(self) -> mock.MockSettings:
        return mock.MockSettings(
            seed=int(round(self.seed.value())),
            bias=self.bias.value(),
            density=self.density.value(),
            wedge_deg=self.wedge.value(),
            thickness_deg=self.thickness.value(),
            r_max=self.depth.value(),
            velocities=self.velocities.isChecked(),
            fingers_km_s=self.fingers.value(),
            flux_limit=self.magnitude.value(),
            redshift_error=self.photo_z.value(),
        )

    def _load_preset(self, *_args) -> None:
        key = self.preset.currentData()
        if key not in mock.PRESETS_MOCK:
            return
        s = mock.PRESETS_MOCK[key][1]
        self._loading = True
        for widget, value in ((self.bias, s.bias), (self.density, s.density), (self.wedge, s.wedge_deg),
                              (self.thickness, s.thickness_deg), (self.depth, s.r_max),
                              (self.fingers, s.fingers_km_s), (self.magnitude, s.flux_limit),
                              (self.photo_z, s.redshift_error)):
            widget.setValue(value, emit=False)
        self.velocities.blockSignals(True)
        self.velocities.setChecked(s.velocities)
        self.velocities.blockSignals(False)
        self._loading = False
        self.recompute()

    def _changed(self, *_args) -> None:
        if self._loading:
            return
        self.preset.blockSignals(True)
        self.preset.setCurrentIndex(0)
        self.preset.blockSignals(False)
        self.schedule_update()

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        settings = self.settings()
        self._xi_cache = None
        try:
            self.catalogue = mock.build(settings)
        except ValueError as error:
            self.banner.set_message("danger", str(error))
            return
        cat = self.catalogue
        self.report = mock.summary(cat)
        r = self.report

        lines = [
            tr("<b>{galaxies}</b> galaxies, median redshift <b>{z}</b>")
            .format(galaxies=f"{r['galaxies']:,}".replace(",", " "), z=f"{r['median_z']:.4f}"),
            tr("Line-of-sight velocities: {rms} km/s rms, which move a galaxy by {shift} Mpc/h")
            .format(rms=f"{r['rms_velocity']:.0f}", shift=f"{r['median_shift']:.1f}"),
            tr("Radial stretch in the densest regions: <b>{finger} Mpc/h</b>")
            .format(finger=f"{r['finger_length']:.1f}"),
            tr("Completeness {complete}, growth rate f = {f}")
            .format(complete=f"{r['completeness']:.1%}", f=f"{cat.growth_rate:.2f}"),
        ]
        self.summary.setText("<br>".join(lines))

        if r["galaxies"] < 120:
            self.banner.set_message(
                "warning",
                tr("<b>Only {galaxies} galaxies.</b> The slice is too sparse to see the cosmic web. Raise the "
                   "density, widen the slice, or relax the magnitude limit.")
                .format(galaxies=r["galaxies"]))
        elif settings.redshift_error >= 0.005:
            self.banner.set_message(
                "warning",
                tr("<b>The redshifts are blurred.</b> An error of {sigma} in z moves a galaxy by about "
                   "{blur} Mpc/h — far more than any peculiar velocity, and enough to wash the filaments out.")
                .format(sigma=f"{settings.redshift_error:.3f}",
                        blur=f"{settings.redshift_error * mock.C_KM_S / 100:.0f}"))
        elif settings.flux_limit > 0 and r["density_drop"] < 0.1:
            self.banner.set_message(
                "info",
                tr("<b>A flux-limited catalogue.</b> At the far edge only {drop} of the galaxies are bright "
                   "enough to be seen, so the thinning out there is the telescope, not the universe.")
                .format(drop=f"{r['density_drop']:.1%}"))
        elif not settings.velocities and settings.fingers_km_s == 0:
            self.banner.set_message(
                "success",
                tr("<b>The true universe.</b> No velocities, no selection: this is where the galaxies really "
                   "are. Every other setting shows what a telescope would have made of it."))
        else:
            self.banner.set_message(
                "info",
                tr("<b>Redshift space.</b> Each galaxy is drawn at the distance its redshift implies, so "
                   "infall squashes the filaments and cluster orbits stretch them towards us."))
        for plot in (self.cone_plot, self.compare_plot, self.profile_plot, self.xi_plot):
            plot.refresh()
        if sdss.available():
            self.real_plot.refresh()

    # ------------------------------------------------------ the real thing
    def real_catalogue(self):
        """The SDSS slice, loaded once (E15)."""
        if self._real is None:
            self._real = sdss.catalogue()
        return self._real

    def real_correlation(self):
        if self._real_xi is None:
            self._real_xi = mock.correlation_function(self.real_catalogue(), observed=True)
        return self._real_xi

    def _correlations(self):
        if self._xi_cache is None:
            s, xi_obs = mock.correlation_function(self.catalogue, observed=True)
            _s, xi_true = mock.correlation_function(self.catalogue, observed=False)
            self._xi_cache = (s, xi_true, xi_obs)
        return self._xi_cache

    # ------------------------------------------------------------- plots
    def _cone(self, ax, observed: bool, color: str, size: float = 2.0, label: str | None = None) -> None:
        cat = self.catalogue
        x, y = cat.xy(observed)
        ax.scatter(y, x, s=size, c=color, alpha=0.75, linewidths=0, label=label)
        ax.set_aspect("equal")
        ax.set_xlabel("Mpc/h", fontsize=8)
        ax.tick_params(labelsize=7)

    def _draw_cone(self, fig) -> None:
        p = theme().palette
        cat = self.catalogue
        ax = fig.add_subplot()
        self._cone(ax, True, p.series[0], size=2.4)
        ax.plot([0], [0], "*", color=p.accent2, markersize=12)
        ax.annotate(tr("us"), (0, 0), textcoords="offset points", xytext=(6, -12),
                    color=p.muted, fontsize=8)
        ax.set_ylabel("distance from the redshift (Mpc/h)", fontsize=8)
        ax.set_title(
            f"{len(cat)} galaxies in a {cat.settings.wedge_deg:.0f}° × {cat.settings.thickness_deg:.1f}° slice",
            fontsize=9)

    def _draw_compare(self, fig) -> None:
        p = theme().palette
        left, right = fig.subplots(1, 2, sharex=True, sharey=True)
        self._cone(left, False, p.muted, size=2.0)
        left.set_title(tr("Where the galaxies really are"), fontsize=9)
        left.set_ylabel("Mpc/h", fontsize=8)
        self._cone(right, True, p.series[0], size=2.0)
        right.set_title(tr("Where their redshifts put them"), fontsize=9)

    def _draw_profile(self, fig) -> None:
        p = theme().palette
        cat = self.catalogue
        top, bottom = fig.subplots(2, 1, gridspec_kw={"height_ratios": [2, 1]})
        centres, measured, expected = mock.radial_profile(cat)
        top.plot(centres, measured, "o-", color=p.series[0], markersize=4, label="measured density")
        top.plot(centres, expected, "--", color=p.danger, linewidth=1.4, label="expected from the flux limit")
        top.set_yscale("log")
        top.set_xlabel("comoving distance (Mpc/h)", fontsize=8)
        top.set_ylabel("galaxies per (Mpc/h)³", fontsize=8)
        top.set_title(tr("How the catalogue thins out with distance"), fontsize=9)
        top.legend(fontsize=7.5)

        bottom.hist(cat.z_obs, bins=40, color=p.series[1], alpha=0.85)
        bottom.set_xlabel("observed redshift z", fontsize=8)
        bottom.set_ylabel("galaxies", fontsize=8)
        for axis in (top, bottom):
            axis.tick_params(labelsize=7)

    def _draw_xi(self, fig) -> None:
        p = theme().palette
        s, xi_true, xi_obs = self._correlations()
        ax = fig.add_subplot()
        # On a log scale only the positive measurements can be drawn; ξ turns noisy and
        # crosses zero once the pairs at that separation run out.
        for values, colour, label in ((xi_true, p.muted, "real space ξ(r)"),
                                      (xi_obs, p.series[0], "redshift space ξ(s)")):
            drawn = np.where(values > 0, values, np.nan)
            ax.plot(s, drawn, "o-", color=colour, markersize=4, label=label)
        ax.plot(s, (s / 5.0) ** -1.8, ":", color=p.danger, linewidth=1.3, label=r"$(r/5)^{-1.8}$")
        cell = self.catalogue.settings.box_mpc / self.catalogue.settings.grid
        ax.axvline(cell, color=p.border, linestyle="--", linewidth=1)
        ax.text(cell, 12, " one grid cell", color=p.muted, fontsize=7, va="top")
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(1e-2, 20)
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_minor_formatter(NullFormatter())
        ax.xaxis.set_major_formatter(ScalarFormatter())
        ax.set_xticks([2, 5, 10, 20, 50])
        ax.set_xlabel("separation (Mpc/h)", fontsize=8)
        ax.set_ylabel("ξ", fontsize=8)
        ax.set_title(tr("Clustering measured from the mock, by counting pairs"), fontsize=9)
        ax.legend(fontsize=7.5)
        ax.tick_params(labelsize=7)

    def _draw_real(self, fig) -> None:
        """The sky's own answer, next to the one the mock gives."""
        p = theme().palette
        real = self.real_catalogue()
        report = sdss.summary()
        left, right = fig.subplots(1, 2, gridspec_kw={"width_ratios": [3, 2]})

        x, y = real.xy(True)
        left.scatter(y, x, s=0.8, c=p.series[1], alpha=0.75, linewidths=0)
        left.set_aspect("equal")
        left.plot([0], [0], "*", color=p.accent2, markersize=11)
        left.set_xlabel("Mpc/h", fontsize=8)
        left.set_ylabel("distance from the redshift (Mpc/h)", fontsize=8)
        left.set_title(f"{report['galaxies']:,} real galaxies, SDSS DR18".replace(",", " "), fontsize=9)
        left.tick_params(labelsize=7)

        s_real, xi_real = self.real_correlation()
        s_mock, _xi_true, xi_mock = self._correlations()
        for values, x_values, colour, label in ((xi_real, s_real, p.series[1], "SDSS galaxies"),
                                                (xi_mock, s_mock, p.series[0], "your mock")):
            drawn = np.where(values > 0, values, np.nan)
            right.plot(x_values, drawn, "o-", color=colour, markersize=3.5, label=label)
        right.plot(s_real, (s_real / 5.0) ** -1.8, ":", color=p.danger, linewidth=1.2,
                   label=r"$(r/5)^{-1.8}$")
        right.set_xscale("log")
        right.set_yscale("log")
        right.set_ylim(1e-2, 20)
        right.xaxis.set_major_formatter(ScalarFormatter())
        right.xaxis.set_minor_formatter(NullFormatter())
        right.set_xticks([2, 5, 10, 20, 50])
        right.set_xlabel("separation (Mpc/h)", fontsize=8)
        right.set_ylabel("ξ(s), redshift space", fontsize=8)
        right.set_title("Does the mock cluster like the sky?", fontsize=9)
        right.legend(fontsize=7)
        right.tick_params(labelsize=7)

    def _csv(self):
        cat = self.catalogue
        angle = np.degrees(cat.angle)
        rows = [[f"{a:.4f}", f"{rt:.3f}", f"{ro:.3f}", f"{zt:.6f}", f"{zo:.6f}", f"{v:.1f}"]
                for a, rt, ro, zt, zo, v in zip(angle, cat.r_true, cat.r_obs, cat.z_true, cat.z_obs, cat.velocity)]
        return ["angle_deg", "r_true_mpc_h", "r_observed_mpc_h", "z_true", "z_observed", "velocity_km_s"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        settings = self.settings()
        s, xi_true, xi_obs = self._correlations()
        small = s < 6
        large = (s > 8) & (s < 25)
        return {
            "preset": self.preset.currentData(),
            "galaxies": self.report["galaxies"],
            "bias": settings.bias,
            "density": settings.density,
            "wedge": settings.wedge_deg,
            "depth": settings.r_max,
            "velocities": settings.velocities,
            "fingers": settings.fingers_km_s,
            "magnitude_limit": settings.flux_limit,
            "redshift_error": settings.redshift_error,
            "finger_length": self.report["finger_length"],
            "completeness": self.report["completeness"],
            "density_drop": self.report["density_drop"],
            "median_z": self.report["median_z"],
            "rms_velocity": self.report["rms_velocity"],
            # Redshift-space distortions: squashed on large scales, stretched on small ones.
            "squashing": float(np.nanmean(xi_obs[large]) / np.nanmean(xi_true[large])),
            "smearing": float(np.nanmean(xi_obs[small]) / np.nanmean(xi_true[small])),
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("Two spaces, one universe") + "\n\n"
            + tr("A redshift is not a distance. What a survey plots is\n\n"
                 "$$s = r + \\frac{(1+z)\\,v_\\parallel}{H(z)},$$\n\n"
                 "the true distance plus whatever the galaxy's own motion adds. Coherent infall towards a "
                 "wall squashes it along the line of sight; the random orbits inside a cluster stretch it into "
                 "a finger pointing at us. Both are signal, not noise: the size of the squashing measures how "
                 "fast structure is growing.")
        )
