"""S24 — CMB Sky Viewer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QLabel, QTabWidget, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import skymap

PROJECTIONS = (("mollweide", "Mollweide (the whole sky)"), ("rectilinear", "Longitude and latitude"))


class SkySimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.sky = skymap.load()
        self.values = self.sky.temperature
        self.report: dict = {}
        self._correlation = None

        what = QGroupBox(tr("1 · What you are looking at"))
        wl = QVBoxLayout(what)
        wl.addWidget(muted_label(
            tr("The WMAP 9-year ILC map: nine years in five frequency bands, combined so that "
               "everything without a thermal spectrum cancels and the microwave background is left. "
               "Temperatures are in microkelvin about the 2.725 K average.")))
        self.controls.addWidget(what)

        clean = QGroupBox(tr("2 · Cleaning it up"))
        cl = QVBoxLayout(clean)
        self.use_mask = QCheckBox(tr("Apply the KQ85 analysis mask"))
        self.use_mask.setChecked(True)
        self.use_mask.setToolTip(tr("WMAP's own judgement about where the Galaxy is still too bright "
                                    "to trust. No published analysis uses the map without it."))
        cl.addWidget(self.use_mask)
        self.remove_dipole = QCheckBox(tr("Remove the monopole and dipole"))
        self.remove_dipole.setToolTip(tr("The 2.725 K average and our own 370 km/s motion through the "
                                         "radiation. The ILC map already has them out, so what this "
                                         "removes is the small residual left by masking."))
        cl.addWidget(self.remove_dipole)
        self.controls.addWidget(clean)

        filters = QGroupBox(tr("3 · Filtering"))
        fl = QVBoxLayout(filters)
        self.smoothing = ParameterSlider(
            tr("Smooth by (°)"), 0.0, 10.0, 0.0, decimals=2, step=0.25,
            info=(tr("Blurring on purpose"),
                  tr("Averaging over a patch of sky throws away everything smaller than it. Watch the "
                     "rms fall: most of the structure lives near one degree, which is the size the "
                     "sound waves had reached when the light was released.")),
        )
        self.high_pass = QCheckBox(tr("Keep only what is smaller than that"))
        self.high_pass.setToolTip(tr("Subtract the blurred map from the original, leaving the fine "
                                     "detail. This is how the large-scale foregrounds are suppressed."))
        for w in (self.smoothing, self.high_pass):
            fl.addWidget(w)
        self.controls.addWidget(filters)

        view = QGroupBox(tr("4 · Display"))
        vl = QVBoxLayout(view)
        self.projection = QComboBox()
        for key, label in PROJECTIONS:
            self.projection.addItem(tr(label), key)
        vl.addWidget(labelled_row(tr("Projection"), self.projection, (
            tr("Drawing a sphere flat"),
            tr("Mollweide keeps areas honest, which is what matters when you are judging how much sky "
               "something covers. The rectangular view is easier to read coordinates off, and badly "
               "exaggerates the poles."))))
        self.scale = ParameterSlider(tr("Colour range (± µK)"), 50, 400, 250, decimals=0, step=10)
        vl.addWidget(self.scale)
        self.controls.addWidget(view)

        results = QGroupBox(tr("What the map says"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Real data, unmodified apart from being resampled from HEALPix onto "
                                    "a grid. Smoothing here is a separable approximation to a spherical "
                                    "one.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.sky_plot = PlotWidget(self._draw_sky, csv_provider=self._csv, export_name="cmb_sky")
        self.correlation_plot = PlotWidget(self._draw_correlation, export_name="cmb_correlation")
        self.scales_plot = PlotWidget(self._draw_scales, export_name="cmb_smoothing")
        self.histogram_plot = PlotWidget(self._draw_histogram, export_name="cmb_histogram")
        tabs.addTab(self.sky_plot, tr("The sky"))
        tabs.addTab(self.correlation_plot, tr("Correlation function"))
        tabs.addTab(self.scales_plot, tr("How much survives blurring"))
        tabs.addTab(self.histogram_plot, tr("Are the ripples Gaussian?"))
        self.display.addWidget(tabs, 1)

        for w in (self.smoothing, self.scale):
            w.valueChanged.connect(self.schedule_update)
        for w in (self.use_mask, self.remove_dipole, self.high_pass):
            w.toggled.connect(self.schedule_update)
        self.projection.currentIndexChanged.connect(self.schedule_update)
        self.recompute()

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        sky = self.sky
        values = sky.temperature
        if self.remove_dipole.isChecked():
            values, _coefficients = skymap.remove_monopole_and_dipole(
                sky, values, self.use_mask.isChecked())
        width = self.smoothing.value()
        if width > 0:
            values = (skymap.high_pass(sky, values, width) if self.high_pass.isChecked()
                      else skymap.smooth(sky, values, width))
        self.values = values
        self.high_pass.setEnabled(width > 0)
        self._correlation = None

        stats = skymap.weighted_stats(sky, values, self.use_mask.isChecked())
        self.report = stats
        hot, cold = skymap.hottest_and_coldest(sky, values, self.use_mask.isChecked())
        lines = [
            tr("Fluctuations: <b>{rms} µK</b> rms, from {low} to {high} µK")
            .format(rms=f"{stats['rms']:.1f}", low=f"{stats['min']:.0f}", high=f"{stats['max']:.0f}"),
            tr("That is <b>{ratio}</b> of the 2.725 K average — one part in {inverse}")
            .format(ratio=f"{stats['rms'] / 2.725e6:.1e}", inverse=f"{2.725e6 / max(stats['rms'], 1e-9):,.0f}"
                    .replace(",", " ")),
            tr("Sky used: <b>{percent}</b>").format(percent=f"{stats['sky_fraction']:.1%}"),
            tr("Typical spot size: <b>{size}°</b> across")
            .format(size=f"{skymap.correlation_half_width(*self.correlation()):.1f}"),
            tr("Hottest at ℓ={hot_lon}°, b={hot_lat}°; coldest at ℓ={cold_lon}°, b={cold_lat}°")
            .format(hot_lon=f"{hot[1]:.0f}", hot_lat=f"{hot[0]:+.0f}",
                    cold_lon=f"{cold[1]:.0f}", cold_lat=f"{cold[0]:+.0f}"),
        ]
        self.summary.setText("<br>".join(lines))

        if not self.use_mask.isChecked():
            self.banner.set_message(
                "warning",
                tr("<b>The Galaxy is in the picture.</b> The bright band across the middle is our own "
                   "galaxy, not the early universe. Every published measurement masks it first — the "
                   "extremes you see now are foreground, not cosmology."))
        elif self.high_pass.isChecked() and width > 0:
            self.banner.set_message(
                "info",
                tr("<b>Only the fine detail.</b> Everything larger than {width}° has been subtracted, "
                   "which is how the smooth foregrounds are suppressed and the degree-scale spots "
                   "stand out.").format(width=f"{width:.2f}"))
        elif width >= 3:
            self.banner.set_message(
                "info",
                tr("<b>Blurred past the signal.</b> At {width}° the acoustic spots have been averaged "
                   "away and the rms has fallen to {rms} µK from about 67.")
                .format(width=f"{width:.1f}", rms=f"{stats['rms']:.0f}"))
        else:
            self.banner.set_message(
                "success",
                tr("<b>The oldest light there is.</b> These ripples are a few parts in a hundred thousand of "
                   "the average temperature, released 380 000 years after the Big Bang, and every "
                   "structure in the universe grew from them."))
        for plot in (self.sky_plot, self.correlation_plot, self.scales_plot, self.histogram_plot):
            plot.refresh()

    def _masked(self) -> np.ndarray:
        if not self.use_mask.isChecked():
            return self.values
        return np.where(self.sky.mask > 0, self.values, np.nan)

    def correlation(self):
        if self._correlation is None:
            self._correlation = skymap.correlation(self.sky, self.values, self.use_mask.isChecked())
        return self._correlation

    # ------------------------------------------------------------- plots
    def _draw_sky(self, fig) -> None:
        p = theme().palette
        limit = self.scale.value()
        data = self._masked()
        projection = self.projection.currentData()
        ax = fig.add_subplot(projection=projection if projection == "mollweide" else None)
        if projection == "mollweide":
            # Mollweide wants radians, longitude from −π to π and increasing to the left,
            # which is how every CMB map in the literature is drawn.
            lon = np.radians(self.sky.longitudes - 180.0)[::-1]
            lat = np.radians(self.sky.latitudes)
            mesh = ax.pcolormesh(lon, lat, data[:, ::-1], cmap="RdBu_r", vmin=-limit, vmax=limit,
                                 shading="auto", rasterized=True)
            ax.grid(True, color=p.border, linewidth=0.4)
            ax.set_xticklabels([])
        else:
            mesh = ax.imshow(data, origin="lower", cmap="RdBu_r", vmin=-limit, vmax=limit,
                             extent=(360, 0, -90, 90), aspect="auto", interpolation="nearest")
            ax.set_xlabel("galactic longitude ℓ (°)", fontsize=8)
            ax.set_ylabel("galactic latitude b (°)", fontsize=8)
        bar = fig.colorbar(mesh, ax=ax, orientation="horizontal", pad=0.06, shrink=0.7, aspect=40)
        bar.set_label("temperature relative to 2.725 K (µK)", fontsize=8)
        bar.ax.tick_params(labelsize=7)
        ax.set_title(f"{skymap.SOURCE} — {self.report['rms']:.0f} µK rms", fontsize=9)

    def _draw_correlation(self, fig) -> None:
        p = theme().palette
        theta, curve = self.correlation()
        ax = fig.add_subplot()
        ax.axhline(0, color=p.border, linewidth=1)
        ax.plot(theta, curve, "o-", color=p.series[0], markersize=4)
        half = skymap.correlation_half_width(theta, curve)
        ax.axvline(1.0, color=p.accent2, linestyle="--", linewidth=1.2)
        ax.text(1.0, ax.get_ylim()[1], " one degree: the sound horizon", color=p.accent2,
                fontsize=7.5, va="top")
        if np.isfinite(half):
            finite = np.isfinite(curve)
            ax.axhline(curve[finite][0] / 2, color=p.muted, linestyle=":", linewidth=1)
            ax.plot([half], [curve[finite][0] / 2], "o", color=p.danger, markersize=8,
                    label=f"half of C(0) at {half:.1f}°")
            ax.legend(fontsize=7.5)
        ax.set_xlabel("separation on the sky (°)", fontsize=8)
        ax.set_ylabel("C(θ)  (µK²)", fontsize=8)
        ax.set_title("How alike two points are, against how far apart they lie", fontsize=9)
        ax.tick_params(labelsize=7)

    def _draw_scales(self, fig) -> None:
        p = theme().palette
        scales, rms = skymap.rms_against_smoothing(self.sky, use_mask=self.use_mask.isChecked())
        ax = fig.add_subplot()
        ax.plot(scales, rms, "o-", color=p.series[0], markersize=5)
        ax.axvline(self.smoothing.value(), color=p.accent2, linestyle="--", linewidth=1.3,
                   label="your setting")
        ax.axvline(skymap.BEAM_DEGREES, color=p.muted, linestyle=":", linewidth=1.2,
                   label="the 1° beam of the map itself")
        ax.set_xlabel("smoothing scale (°)", fontsize=8)
        ax.set_ylabel("rms fluctuation (µK)", fontsize=8)
        ax.set_ylim(0, max(float(rms.max()) * 1.15, 1.0))
        ax.set_title("Blur the sky and the structure goes: most of it is about a degree across",
                     fontsize=9)
        ax.legend(fontsize=7.5)
        ax.tick_params(labelsize=7)

    def _draw_histogram(self, fig) -> None:
        p = theme().palette
        values = self._masked()
        good = values[np.isfinite(values)]
        ax = fig.add_subplot()
        counts, edges, _patches = ax.hist(good, bins=90, color=p.series[0], alpha=0.85, density=True)
        centres = 0.5 * (edges[:-1] + edges[1:])
        sigma = max(self.report["rms"], 1e-6)
        mean = self.report["mean"]
        gaussian = np.exp(-0.5 * ((centres - mean) / sigma) ** 2) / (sigma * np.sqrt(2 * np.pi))
        ax.plot(centres, gaussian, color=p.danger, linewidth=2,
                label=f"Gaussian, σ = {sigma:.0f} µK")
        ax.set_xlabel("temperature (µK)", fontsize=8)
        ax.set_ylabel("fraction of the sky", fontsize=8)
        ax.set_title("Inflation predicts a Gaussian distribution, and this is one", fontsize=9)
        ax.legend(fontsize=7.5)
        ax.tick_params(labelsize=7)

    def _csv(self):
        """Every twentieth cell, so the file stays a sensible size."""
        step = 20
        rows = []
        for row in range(0, self.sky.shape[0], step):
            for column in range(0, self.sky.shape[1], step):
                rows.append([f"{self.sky.latitudes[row]:.3f}", f"{self.sky.longitudes[column]:.3f}",
                             f"{self.values[row, column]:.2f}", f"{self.sky.mask[row, column]:.0f}"])
        return ["galactic_latitude_deg", "galactic_longitude_deg", "temperature_uK", "mask"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        theta, curve = self.correlation()
        return {
            "masked": self.use_mask.isChecked(),
            "dipole_removed": self.remove_dipole.isChecked(),
            "smoothing": self.smoothing.value(),
            "high_pass": self.high_pass.isChecked() and self.smoothing.value() > 0,
            "projection": self.projection.currentData(),
            "rms": self.report["rms"],
            "min": self.report["min"],
            "max": self.report["max"],
            "sky_fraction": self.report["sky_fraction"],
            "relative": self.report["rms"] / 2.725e6,
            "spot_size": skymap.correlation_half_width(theta, curve),
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("One part in a hundred thousand") + "\n\n"
            + tr("The whole map spans about ±250 µK around 2.725 K. That is a contrast of $10^{-5}$ — "
                 "and it is the largest contrast the universe had at that moment. Everything you have "
                 "ever seen, every galaxy and every star, grew out of ripples this small by nothing but "
                 "gravity pulling for 13.8 billion years.")
        )
