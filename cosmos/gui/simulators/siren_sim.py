"""S22 — Standard Siren Explorer."""

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
from cosmos.physics import gravitational_waves as gw
from cosmos.physics import ladder, sirens

BAND_LOW_HZ = 20.0      # where a ground-based detector starts to hear a binary


class SirenSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.result: sirens.SirenMeasurement | None = None
        self._loading = False

        start = QGroupBox(tr("0 · Start from"))
        sl = QVBoxLayout(start)
        self.preset = QComboBox()
        self.preset.addItem(tr("Custom"), "custom")
        for key, (label, _settings) in sirens.PRESETS_SIREN.items():
            self.preset.addItem(physics(label), key)
        sl.addWidget(labelled_row(tr("Event"), self.preset, (
            tr("Real and imagined mergers"),
            tr("GW170817 is the only standard siren so far with an identified host galaxy. The others show "
               "what happens without one, and what the next generation of detectors will do."))))
        self.controls.addWidget(start)

        source = QGroupBox(tr("1 · The merger"))
        so = QVBoxLayout(source)
        self.m1 = ParameterSlider(
            tr("First mass (M☉)"), 1.0, 60.0, 1.46, decimals=2, log=True,
            info=(tr("Chirp mass"),
                  tr("The wave depends on the two masses almost only through the combination "
                     "M_c = (m₁m₂)^(3/5)/(m₁+m₂)^(1/5). Heavier binaries radiate more, so they are heard "
                     "further away — but they merge at a lower frequency and last a shorter time in band.")),
        )
        self.m2 = ParameterSlider(tr("Second mass (M☉)"), 1.0, 60.0, 1.27, decimals=2, log=True)
        self.distance = ParameterSlider(tr("True distance (Mpc)"), 10, 3000, 40, decimals=0, log=True)
        self.inclination = ParameterSlider(
            tr("Inclination ι (°)"), 0, 90, 30, decimals=0, step=5,
            info=(tr("Face-on or edge-on"),
                  tr("The angle between the orbital axis and our line of sight. A face-on binary is almost "
                     "three times louder than an edge-on one, so a distant face-on merger and a nearby "
                     "edge-on one make nearly the same signal. This is the degeneracy that limits every "
                     "siren.")),
        )
        for w in (self.m1, self.m2, self.distance, self.inclination):
            so.addWidget(w)
        self.controls.addWidget(source)

        instrument = QGroupBox(tr("2 · Who is listening"))
        il = QVBoxLayout(instrument)
        self.network = QComboBox()
        for key, net in sirens.NETWORKS.items():
            self.network.addItem(physics(net.label), key)
            self.network.setItemData(self.network.count() - 1, physics(net.description), Qt.ToolTipRole)
        il.addWidget(labelled_row(tr("Detector network"), self.network, (
            tr("Why the number of sites matters"),
            tr("Sensitivity sets how far a merger can be heard. The number of widely separated sites sets "
               "how well it can be <b>located</b>: the sky position comes from the difference in arrival "
               "times, so two detectors give a ring and three give a patch."))))
        self.controls.addWidget(instrument)

        host = QGroupBox(tr("3 · Finding the redshift"))
        hl = QVBoxLayout(host)
        self.host_known = QCheckBox(tr("A counterpart was seen: the host galaxy is known"))
        self.host_known.setChecked(True)
        hl.addWidget(self.host_known)
        self.velocity = ParameterSlider(
            tr("Uncertainty on the host's velocity (km/s)"), 0, 500, 150, decimals=0, step=10,
            info=(tr("Peculiar velocity"),
                  tr("A galaxy's redshift is the expansion plus its own motion through its group or cluster, "
                     "which is a few hundred km/s. Nearby, that is the dominant error: at 40 Mpc it is 5% of "
                     "the recession velocity.")),
        )
        self.events = ParameterSlider(
            tr("Number of events like this one"), 1, 1000, 1, decimals=0, log=True,
            info=(tr("One siren is not enough"),
                  tr("Each event gives an independent measurement, so the error falls as 1/√N. The question "
                     "every forecast asks is how many events it takes to say something the Hubble tension "
                     "has to answer to.")),
        )
        for w in (self.velocity, self.events):
            hl.addWidget(w)
        self.controls.addWidget(host)

        results = QGroupBox(tr("The measurement"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Teaching model, calibrated on GW170817. Localisation areas and dark-siren "
                                    "penalties are good to a factor of a few.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.wave_plot = PlotWidget(self._draw_wave, csv_provider=self._csv, export_name="siren_chirp")
        self.degeneracy_plot = PlotWidget(self._draw_degeneracy, export_name="distance_inclination")
        self.h0_plot = PlotWidget(self._draw_h0, export_name="siren_hubble_constant")
        self.events_plot = PlotWidget(self._draw_events, export_name="sirens_needed")
        tabs.addTab(self.wave_plot, tr("The chirp"))
        tabs.addTab(self.degeneracy_plot, tr("Distance vs inclination"))
        tabs.addTab(self.h0_plot, tr("H₀ from this event"))
        tabs.addTab(self.events_plot, tr("How many sirens?"))
        self.display.addWidget(tabs, 1)

        self.inputs = (self.m1, self.m2, self.distance, self.inclination, self.velocity, self.events)
        for w in self.inputs:
            w.valueChanged.connect(self._changed)
        self.host_known.toggled.connect(self._changed)
        self.network.currentIndexChanged.connect(self._changed)
        self.preset.currentIndexChanged.connect(self._load_preset)
        self.preset.setCurrentIndex(self.preset.findData("gw170817"))

    # ------------------------------------------------------------ inputs
    def settings(self) -> sirens.SirenSettings:
        return sirens.SirenSettings(
            m1=self.m1.value(),
            m2=self.m2.value(),
            distance_mpc=self.distance.value(),
            inclination_deg=self.inclination.value(),
            network=self.network.currentData(),
            host_known=self.host_known.isChecked(),
            peculiar_velocity_km_s=self.velocity.value(),
            events=int(round(self.events.value())),
        )

    def _load_preset(self, *_args) -> None:
        key = self.preset.currentData()
        if key not in sirens.PRESETS_SIREN:
            return
        s = sirens.PRESETS_SIREN[key][1]
        self._loading = True
        # The stored inclination can exceed 90°; the physics only depends on |cos ι|.
        inclination = min(s.inclination_deg, 180.0 - s.inclination_deg)
        for widget, value in ((self.m1, s.m1), (self.m2, s.m2), (self.distance, s.distance_mpc),
                              (self.inclination, inclination),
                              (self.velocity, s.peculiar_velocity_km_s), (self.events, s.events)):
            widget.setValue(value, emit=False)
        self.network.blockSignals(True)
        self.network.setCurrentIndex(self.network.findData(s.network))
        self.network.blockSignals(False)
        self.host_known.blockSignals(True)
        self.host_known.setChecked(s.host_known)
        self.host_known.blockSignals(False)
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
        s = self.settings()
        self.velocity.setEnabled(self.host_known.isChecked())
        m = self.result = sirens.measure(s)

        lines = [
            tr("Signal-to-noise <b>{snr}</b>, chirp mass {mchirp} M☉, horizon {horizon} Mpc")
            .format(snr=f"{m.snr:.1f}", mchirp=f"{gw.chirp_mass(s.m1, s.m2):.2f}",
                    horizon=f"{sirens.horizon_distance(s):,.0f}".replace(",", " ")),
            tr("In the detector band for {seconds} s before merging")
            .format(seconds=f"{self.time_in_band():,.0f}".replace(",", " ")),
            tr("Distance <b>{distance}</b> (+{high} / −{low}) Mpc, that is {percent}%")
            .format(distance=f"{m.distance:.0f}", high=f"{m.distance_high - m.distance:.0f}",
                    low=f"{m.distance - m.distance_low:.0f}", percent=f"{m.distance_percent:.0f}"),
            tr("Localised to {area} deg², {candidates} candidate host galaxies")
            .format(area=f"{m.sky_area_deg2:,.0f}".replace(",", " "),
                    candidates=f"{m.host_candidates:,}".replace(",", " ")),
            tr("H₀ = <b>{h0} ± {error}</b> km/s/Mpc from {events} event(s), that is {percent}%")
            .format(h0=f"{m.h0:.1f}", error=f"{m.h0 * m.h0_percent / 100:.1f}", events=s.events,
                    percent=f"{m.h0_percent:.1f}"),
        ]
        self.summary.setText("<br>".join(lines))

        if not m.detected:
            self.banner.set_message(
                "danger",
                tr("<b>Too quiet to claim.</b> A signal-to-noise ratio of {snr} is below the threshold of 8: "
                   "this merger would be lost in the noise. Move it closer, make it heavier, or wait for a "
                   "better network.").format(snr=f"{m.snr:.1f}"))
        elif not s.host_known:
            self.banner.set_message(
                "warning",
                tr("<b>A dark siren.</b> With no counterpart, all {candidates} galaxies in the localisation "
                   "volume are candidates. The right one still counts, but one event is {factor} times weaker "
                   "than it would be with a known host.")
                .format(candidates=f"{m.host_candidates:,}".replace(",", " "),
                        factor=f"{sirens.dark_penalty(m.host_candidates):.1f}"))
        elif m.h0_percent < 2.0:
            self.banner.set_message(
                "success",
                tr("<b>Better than two percent.</b> At {percent}% this measurement is sharp enough to say "
                   "which side of the Hubble tension it falls on — with no distance ladder at all.")
                .format(percent=f"{m.h0_percent:.1f}"))
        else:
            needed = sirens.events_needed(s, 2.0)
            self.banner.set_message(
                "info",
                tr("<b>H₀ to {percent}% from gravitational waves alone.</b> It would take about {needed} "
                   "events like this one to reach 2%, the precision the Hubble tension calls for.")
                .format(percent=f"{m.h0_percent:.1f}", needed=f"{needed:,}".replace(",", " ")))
        for plot in (self.wave_plot, self.degeneracy_plot, self.h0_plot, self.events_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _waveform(self):
        """The last few cycles, where the individual oscillations can still be drawn."""
        s = self.result.settings
        mchirp = gw.chirp_mass(s.m1, s.m2)
        duration = min(1.2, max(0.05, 0.35 * (1.219 / mchirp) ** (5 / 3)))
        return gw.chirp_waveform(mchirp, s.distance_mpc, duration_s=duration)

    def time_in_band(self) -> float:
        """Seconds between entering the detector band at 20 Hz and merging."""
        s = self.result.settings
        return float(gw.time_to_merger(BAND_LOW_HZ, gw.chirp_mass(s.m1, s.m2)))

    def _draw_wave(self, fig) -> None:
        p = theme().palette
        s = self.result.settings
        top, bottom = fig.subplots(2, 1, gridspec_kw={"height_ratios": [2, 1], "hspace": 0.55})
        t, h, freq = self._waveform()
        scale = float(sirens.orientation(s.inclination_deg))
        top.plot(t, h * scale * 1e21, color=p.series[0], linewidth=0.9)
        top.set_xlabel("time before merger (s)", fontsize=8)
        top.set_ylabel("strain h × 10²¹", fontsize=8)
        top.set_title(f"The last {-t[0]:.2f} s: the amplitude gives the distance, the chirp the masses",
                      fontsize=9)

        # The whole time in band, which is where the masses are actually measured from.
        span = self.time_in_band()
        tau = np.geomspace(max(span, 1e-3), 1e-3, 400)
        bottom.plot(tau, gw.frequency_at(tau, gw.chirp_mass(s.m1, s.m2)), color=p.series[1], linewidth=1.8)
        bottom.set_xscale("log")
        bottom.set_yscale("log")
        bottom.invert_xaxis()
        bottom.xaxis.set_minor_formatter(NullFormatter())
        bottom.yaxis.set_major_formatter(ScalarFormatter())
        bottom.yaxis.set_minor_formatter(NullFormatter())
        ticks = [t for t in (1000, 100, 10, 1, 0.1, 0.01) if 1e-3 <= t <= max(span, 1e-3)]
        bottom.set_xticks(ticks, [f"{t:g}" for t in ticks])
        bottom.set_yticks([20, 50, 100, 300, 1000])
        bottom.set_xlabel(f"time before merger (s) — {span:,.0f} s in band from {BAND_LOW_HZ:.0f} Hz"
                          .replace(",", " "), fontsize=8)
        bottom.set_ylabel("frequency (Hz)", fontsize=8)
        for axis in (top, bottom):
            axis.tick_params(labelsize=7)

    def _draw_degeneracy(self, fig) -> None:
        p = theme().palette
        m = self.result
        s = m.settings
        left, right = fig.subplots(1, 2, gridspec_kw={"width_ratios": [3, 2]})
        distances, inclinations, joint = sirens.degeneracy_grid(s)
        left.contourf(inclinations, distances, joint, levels=12, cmap="magma")
        left.contour(inclinations, distances, joint, levels=[0.05, 0.32], colors=[p.text], linewidths=0.9)
        left.plot([min(s.inclination_deg, 180 - s.inclination_deg)], [s.distance_mpc], "*",
                  color=p.accent2, markersize=13)
        left.set_xlabel("inclination ι (°)", fontsize=8)
        left.set_ylabel("luminosity distance (Mpc)", fontsize=8)
        left.set_title("The banana: louder can mean nearer or more face-on", fontsize=9)

        right.plot(m.density, m.distances, color=p.series[0], linewidth=2)
        right.fill_betweenx(m.distances, 0, m.density,
                            where=(m.distances >= m.distance_low) & (m.distances <= m.distance_high),
                            color=p.series[0], alpha=0.3, label="68%")
        right.axhline(s.distance_mpc, color=p.accent2, linestyle="--", linewidth=1.3, label="true distance")
        right.set_xlabel("p(D)", fontsize=8)
        right.set_title("marginal distance", fontsize=9)
        right.set_xticks([])
        right.legend(fontsize=7.5)
        for axis in (left, right):
            axis.set_ylim(m.distances[0], m.distances[-1])
            axis.tick_params(labelsize=7)

    def _draw_h0(self, fig) -> None:
        p = theme().palette
        m = self.result
        ax = fig.add_subplot()
        width = max(m.h0 * m.h0_percent / 100, 0.2)
        grid = np.linspace(40, 110, 500)
        combined = np.exp(-0.5 * ((grid - m.h0) / width) ** 2)
        ax.plot(grid, combined, color=p.series[0], linewidth=2.2,
                label=f"sirens: {m.h0:.1f} ± {width:.1f} ({m.settings.events} event(s))")
        if m.settings.events > 1:
            single = max(m.h0 * m.h0_single_percent / 100, 0.2)
            ax.plot(grid, np.exp(-0.5 * ((grid - m.h0) / single) ** 2), color=p.series[0],
                    linewidth=1.1, linestyle=":", label="one event")
        for (value, error), colour, name in ((ladder.PLANCK_H0, p.series[1], "Planck CMB"),
                                             (ladder.SHOES_H0, p.danger, "SH0ES ladder")):
            ax.plot(grid, np.exp(-0.5 * ((grid - value) / error) ** 2), color=colour, linewidth=1.6,
                    label=f"{name}: {value:.1f} ± {error:.1f}")
        ax.set_xlabel("H₀ (km/s/Mpc)", fontsize=8)
        ax.set_ylabel("relative probability", fontsize=8)
        ax.set_yticks([])
        ax.set_title("A measurement of H₀ that uses no distance ladder at all", fontsize=9)
        ax.legend(fontsize=7.5, loc="upper right")
        ax.tick_params(labelsize=7)

    def _draw_events(self, fig) -> None:
        p = theme().palette
        m = self.result
        ax = fig.add_subplot()
        counts = np.geomspace(1, 3000, 160)
        ax.plot(counts, m.h0_single_percent / np.sqrt(counts), color=p.series[0], linewidth=2,
                label=f"events like this one ({m.h0_single_percent:.0f}% each)")
        bright = sirens.measure(sirens.SirenSettings(**{**m.settings.__dict__, "host_known": True,
                                                       "events": 1}))
        if not m.settings.host_known:
            ax.plot(counts, bright.h0_single_percent / np.sqrt(counts), color=p.muted, linewidth=1.4,
                    linestyle="--", label=f"if the host were known ({bright.h0_single_percent:.0f}% each)")
        tension = 100 * (ladder.SHOES_H0[0] - ladder.PLANCK_H0[0]) / ladder.PLANCK_H0[0]
        ax.axhline(tension, color=p.danger, linestyle=":", linewidth=1.4,
                   label=f"the size of the Hubble tension ({tension:.1f}%)")
        ax.axhline(2.0, color=p.success, linestyle="--", linewidth=1.3, label="2% target")
        ax.plot([m.settings.events], [m.h0_percent], "o", color=p.accent2, markersize=8, label="your setting")
        ax.set_xscale("log")
        ax.set_yscale("log")
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_formatter(ScalarFormatter())
            axis.set_minor_formatter(NullFormatter())
        ax.set_ylim(0.2, 200)
        ax.set_xlabel("number of events", fontsize=8)
        ax.set_ylabel("error on H₀ (%)", fontsize=8)
        ax.set_title("The error falls as 1/√N — the only question is how fast events arrive", fontsize=9)
        ax.legend(fontsize=7.5, loc="lower left")
        ax.tick_params(labelsize=7)

    def _csv(self):
        t, h, freq = self._waveform()
        scale = float(sirens.orientation(self.result.settings.inclination_deg))
        rows = [[f"{ti:.6f}", f"{hi * scale:.6e}", f"{fi:.3f}"] for ti, hi, fi in zip(t, h, freq)]
        return ["time_s", "strain", "frequency_hz"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        m = self.result
        s = m.settings
        return {
            "preset": self.preset.currentData(),
            "network": s.network,
            "m1": s.m1,
            "m2": s.m2,
            "chirp_mass": gw.chirp_mass(s.m1, s.m2),
            "distance": s.distance_mpc,
            "inclination": s.inclination_deg,
            "host_known": s.host_known,
            "events": s.events,
            "snr": m.snr,
            "detected": m.detected,
            "distance_percent": m.distance_percent,
            "sky_area": m.sky_area_deg2,
            "candidates": m.host_candidates,
            "redshift": m.redshift,
            "h0_percent": m.h0_percent,
            "h0_single_percent": m.h0_single_percent,
            "horizon": sirens.horizon_distance(s),
            "time_in_band": self.time_in_band(),
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("Why a siren needs no ladder") + "\n\n"
            + tr("General relativity fixes the amplitude of the wave a binary radiates, so the strain that "
                 "arrives here gives the luminosity distance outright:\n\n"
                 "$$h \\propto \\frac{1}{D_L}\\,(\\mathcal{M}_c)^{5/3} f^{2/3}.$$\n\n"
                 "Nothing in that expression was calibrated on anything. The chirp gives $\\mathcal{M}_c$, "
                 "the amplitude then gives $D_L$, and a host galaxy gives $z$ — which is the whole "
                 "measurement of $H_0$, in one event, with no rung below it to go wrong.")
        )
