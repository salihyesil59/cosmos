"""S5 — Hubble Diagram Fitter."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QPushButton, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import ParameterSlider, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import constants as const
from cosmos.physics import datasets, hubble


class HubbleFitSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.sets = datasets.hubble_datasets()
        self.fit: hubble.HubbleFit | None = None

        data_box = QGroupBox(tr("1 · Data set"))
        dl = QVBoxLayout(data_box)
        self.selector = QComboBox()
        for key, ds in self.sets.items():
            self.selector.addItem(ds.label, key)
        self.selector.setToolTip(tr("Choose which galaxies to plot."))
        dl.addWidget(self.selector)
        self.description = muted_label("")
        dl.addWidget(self.description)
        self.controls.addWidget(data_box)

        fit_box = QGroupBox(tr("2 · Fit the line v = H0 × d"))
        fl = QVBoxLayout(fit_box)
        self.h0 = ParameterSlider(
            tr("Your H0 (km/s/Mpc)"), 0, 700, 300, decimals=1, step=5,
            info=(tr("Slope of the line"), tr("Move this until the line runs through the middle of the points. The "
                      "residual sum below gets smaller as the fit improves.")),
        )
        fl.addWidget(self.h0)
        self.residual = QLabel()
        self.residual.setTextFormat(Qt.RichText)
        self.residual.setWordWrap(True)
        fl.addWidget(self.residual)
        best = QPushButton(tr("Find best fit (least squares)"))
        best.setProperty("role", "primary")
        best.setToolTip(tr("Compute the slope that minimises the sum of squared residuals."))
        best.clicked.connect(self._best_fit)
        fl.addWidget(best)
        self.controls.addWidget(fit_box)

        result_box = QGroupBox(tr("Result"))
        rl = QVBoxLayout(result_box)
        self.result = QLabel(tr("Press <b>Find best fit</b> to compute H0 and the Hubble time."))
        self.result.setWordWrap(True)
        self.result.setTextFormat(Qt.RichText)
        rl.addWidget(self.result)
        self.controls.addWidget(result_box)
        self.finish_controls()

        self.plot = PlotWidget(self._draw, csv_provider=self._csv, export_name="hubble_diagram")
        self.display.addWidget(self.plot, 1)

        self.selector.currentIndexChanged.connect(self._dataset_changed)
        self.h0.valueChanged.connect(self.schedule_update)
        self._dataset_changed()

    @property
    def data(self) -> datasets.HubbleDataset:
        return self.sets[self.selector.currentData()]

    def _dataset_changed(self, *_args) -> None:
        ds = self.data
        tag = tr("⚠ Simulated data.") if ds.simulated else tr("Real historical data.")
        self.description.setText(tag + " " + ds.description)
        self.fit = None
        self.result.setText(tr("Press <b>Find best fit</b> to compute H0 and the Hubble time."))
        self.h0.setValue(300 if ds.key == "hubble1929" else 40)

    def recompute(self) -> None:
        ds = self.data
        ssr = hubble.sum_squared_residuals(ds.distance_mpc, ds.velocity_km_s, self.h0.value())
        rms = np.sqrt(ssr / len(ds.distance_mpc))
        tH = 1 / const.hubble_to_si(self.h0.value()) / const.GYR if self.h0.value() > 0 else float("inf")
        self.residual.setText(
            tr("Typical miss (RMS residual): <b>{rms} km/s</b><br>"
               "Hubble time for your slope: <b>{hubble_time} billion years</b>")
            .format(rms=f"{rms:,.0f}".replace(",", " "), hubble_time=f"{tH:.2f}")
        )
        self.plot.refresh()

    def _best_fit(self) -> None:
        ds = self.data
        self.fit = hubble.fit_through_origin(ds.distance_mpc, ds.velocity_km_s)
        f = self.fit
        self.h0.setValue(f.H0)
        comment = (
            tr("Hubble's value is about seven times larger than today's because his distances were too small. "
               "His Hubble time of {years} billion years was shorter than geologists' estimates of the age of "
               "the Earth, a real puzzle at the time.").format(years=f"{f.hubble_time_gyr:.1f}")
            if ds.key == "hubble1929"
            else tr("Close to modern measurements (67–73 km/s/Mpc). The Hubble time is close to the true age "
                    "of 13.8 billion years.")
        )
        self.result.setText(
            tr("H0 = <b>{h0} ± {error} km/s/Mpc</b><br>"
               "Hubble time 1/H0 = <b>{hubble_time} billion years</b><br>"
               "Points: {points}<br><br>{comment}")
            .format(h0=f"{f.H0:.1f}", error=f"{f.H0_error:.1f}", hubble_time=f"{f.hubble_time_gyr:.2f}",
                    points=f.n_points, comment=comment)
        )

    def _draw(self, fig) -> None:
        p = theme().palette
        ds = self.data
        grid = fig.add_gridspec(2, 1, height_ratios=[3, 1])
        ax = fig.add_subplot(grid[0])
        ax_res = fig.add_subplot(grid[1], sharex=ax)
        ax.scatter(ds.distance_mpc, ds.velocity_km_s, color=p.series[0], zorder=3, s=26, label=ds.label)
        dmax = float(ds.distance_mpc.max()) * 1.1
        d = np.linspace(0, dmax, 50)
        ax.plot(d, self.h0.value() * d, color=p.series[1], linewidth=2, label=f"Your line: H0 = {self.h0.value():.1f}")
        if self.fit is not None and abs(self.fit.H0 - self.h0.value()) > 0.05:
            ax.plot(d, self.fit.H0 * d, color=p.series[2], linestyle="--", label=f"Best fit: {self.fit.H0:.1f}")
        ax.axhline(0, color=p.muted, linewidth=0.8)
        ax.set_ylabel("Velocity (km/s)")
        ax.set_title("Hubble diagram", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)
        residuals = ds.velocity_km_s - self.h0.value() * ds.distance_mpc
        ax_res.axhline(0, color=p.series[1], linewidth=1)
        ax_res.scatter(ds.distance_mpc, residuals, color=p.series[0], s=14)
        ax_res.set_xlabel("Distance (Mpc)")
        ax_res.set_ylabel("Residual")
        ax_res.set_xlim(0, dmax)

    def _csv(self):
        ds = self.data
        rows = [[n, f"{d:.4g}", f"{v:.4g}"] for n, d, v in zip(ds.names, ds.distance_mpc, ds.velocity_km_s)]
        return ["object", "distance_Mpc", "velocity_km_s"], rows
