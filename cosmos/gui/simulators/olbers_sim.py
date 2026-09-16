"""S17 — Olbers' Paradox Simulator."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QLabel, QPushButton, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.physics import olbers

# name: (density, finite age, age, limited lifetimes, shining fraction, expanding, Hubble length)
SCENARIOS = {
    "olbers": ("Olbers' universe: infinite, static and eternal", (4e-4, False, 300.0, False, 1.0, False, 1000.0)),
    "age": ("A universe with a finite age", (4e-4, True, 200.0, False, 1.0, False, 1000.0)),
    "lifetimes": ("Finite age and stars that burn out", (4e-4, True, 200.0, True, 0.2, False, 1000.0)),
    "expanding": ("Infinitely old but expanding (steady state)", (4e-4, False, 300.0, False, 1.0, True, 300.0)),
    "custom": ("Custom", None),
}


class OlbersSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.seed = 1
        self.sky = None
        self._loading = False

        universe = QGroupBox("1 · Choose a universe")
        ul = QVBoxLayout(universe)
        self.scenario = QComboBox()
        for key, (label, _) in SCENARIOS.items():
            self.scenario.addItem(label, key)
        ul.addWidget(labelled_row("Scenario", self.scenario, (
            "Scenarios", "Each scenario switches on one of the ways out of the paradox. Change any control to "
            "build your own.")))
        self.density = ParameterSlider(
            "Star density (stars per unit volume)", 2e-5, 2e-2, 4e-4, decimals=5, log=True,
            info=("Units", "Distances are measured in stellar radii: a star has radius 1. The mean free path "
                  "λ = 1/(nπ) is how far a line of sight goes, on average, before it hits a star."),
        )
        ul.addWidget(self.density)
        self.controls.addWidget(universe)

        ways = QGroupBox("2 · Ways out of the paradox")
        wl = QVBoxLayout(ways)
        self.finite_age = QCheckBox("The universe has a finite age")
        self.finite_age.setToolTip("Light from stars farther than the light-travel distance has not reached us yet.")
        wl.addWidget(self.finite_age)
        self.age = ParameterSlider(
            "Light-travel distance (age × c)", 10.0, 1e4, 300.0, decimals=0, log=True,
            info=("Finite age", "If the universe (or its stars) began a time t ago, we see only stars within a "
                  "distance ct. In our universe ct is 13.8 billion light-years, far shorter than the mean free "
                  "path of about 10²⁴ light-years."),
        )
        wl.addWidget(self.age)
        self.lifetimes = QCheckBox("Stars shine for a limited time")
        wl.addWidget(self.lifetimes)
        self.fraction = ParameterSlider(
            "Fraction of stars shining at once", 0.01, 1.0, 0.2, decimals=3, log=True,
            info=("Stellar lifetimes", "A star shines for a limited time, so only part of the stars along a line "
                  "of sight are shining when their light leaves. This lowers the effective density of stars."),
        )
        wl.addWidget(self.fraction)
        self.expanding = QCheckBox("The universe expands")
        wl.addWidget(self.expanding)
        self.hubble = ParameterSlider(
            "Hubble length c/H", 20.0, 1e4, 150.0, decimals=0, log=True,
            info=("Redshift dimming", "Light from a distance d arrives with 1 + z = e^(d/L) in a universe expanding "
                  "at a constant rate. Its surface brightness falls as (1 + z)⁻⁴: fewer photons per second, each "
                  "with less energy, and two factors from the stretching of the image."),
        )
        wl.addWidget(self.hubble)
        new_sky = QPushButton("New random sky")
        new_sky.setToolTip("Place the stars at new random positions.")
        new_sky.clicked.connect(self._new_sky)
        wl.addWidget(new_sky)
        self.controls.addWidget(ways)

        results = QGroupBox("Results")
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        self.controls.addWidget(results)

        real = QGroupBox("Our universe")
        ol = QVBoxLayout(real)
        r = olbers.real_universe()
        text = QLabel(
            f"Stars per cubic metre: about {r.star_density_m3:.1e}<br>"
            f"Mean free path: about <b>{r.mean_free_path_ly:.0e} light-years</b><br>"
            f"We see out to about {r.visible_depth_ly / 1e9:.1f} billion light-years<br>"
            f"Sky covered by stars: about <b>{r.coverage:.0e}</b><br>"
            f"To fill the sky, stars would have to shine for {r.filling_time_yr:.0e} years; "
            f"the Sun lasts {r.sun_lifetime_yr:.0e}.<br>"
            f"A sky covered by stars would give about {r.daylight_factor:,.0f} times the heat of sunlight."
        )
        text.setWordWrap(True)
        text.setTextFormat(Qt.RichText)
        ol.addWidget(text)
        self.controls.addWidget(real)
        self.finish_controls()

        self.banner = Banner("info")
        self.display.addWidget(self.banner)
        self.plot = PlotWidget(self._draw, export_name="olbers", csv_provider=self._csv)
        self.display.addWidget(self.plot, 1)

        self.scenario.currentIndexChanged.connect(self._scenario_changed)
        for w in (self.density, self.age, self.fraction, self.hubble):
            w.valueChanged.connect(self._custom)
        for box in (self.finite_age, self.lifetimes, self.expanding):
            box.toggled.connect(self._custom)
        self._scenario_changed()

    # ------------------------------------------------------------ state
    def _scenario_changed(self, *_args) -> None:
        values = SCENARIOS[self.scenario.currentData()][1]
        if values is None:
            return
        self._loading = True
        density, finite, age, limited, fraction, expanding, hubble = values
        self.density.setValue(density, emit=False)
        self.finite_age.setChecked(finite)
        self.age.setValue(age, emit=False)
        self.lifetimes.setChecked(limited)
        self.fraction.setValue(fraction, emit=False)
        self.expanding.setChecked(expanding)
        self.hubble.setValue(hubble, emit=False)
        self._loading = False
        self._sync_enabled()
        self.recompute()

    def _custom(self, *_args) -> None:
        if self._loading:
            return
        self._sync_enabled()
        index = self.scenario.findData("custom")
        if self.scenario.currentIndex() != index:
            self.scenario.blockSignals(True)
            self.scenario.setCurrentIndex(index)
            self.scenario.blockSignals(False)
        self.schedule_update()

    def _sync_enabled(self) -> None:
        self.age.setEnabled(self.finite_age.isChecked())
        self.fraction.setEnabled(self.lifetimes.isChecked())
        self.hubble.setEnabled(self.expanding.isChecked())

    def _new_sky(self) -> None:
        self.seed += 1
        self.recompute()

    def parameters(self) -> tuple[float, float, float | None]:
        """Effective density of shining stars, visible depth and Hubble length."""
        density = self.density.value() * (self.fraction.value() if self.lifetimes.isChecked() else 1.0)
        depth = self.age.value() if self.finite_age.isChecked() else math.inf
        hubble = self.hubble.value() if self.expanding.isChecked() else None
        return density, depth, hubble

    def recompute(self) -> None:
        density, depth, hubble = self.parameters()
        mfp = olbers.mean_free_path(density)
        self.sky = olbers.generate_sky(density, depth, hubble_length=hubble, seed=self.seed)
        coverage = olbers.sky_coverage(depth, mfp)
        brightness = olbers.sky_brightness(depth, mfp, hubble)
        depth_text = "infinite" if math.isinf(depth) else f"{depth:.0f}"
        self.summary.setText(
            f"Mean free path λ: <b>{mfp:.0f}</b> stellar radii<br>"
            f"Visible depth: <b>{depth_text}</b>"
            + ("" if math.isinf(depth) else f" = {depth / mfp:.2f} λ")
            + "<br>"
            f"Sky covered by stars: <b>{100 * coverage:.1f}%</b> (this patch {100 * self.sky.coverage:.1f}%)<br>"
            f"Sky brightness: <b>{100 * brightness:.1f}%</b> of a star's surface "
            f"(this patch {100 * self.sky.brightness:.1f}%)<br>"
            f"Stars drawn as discs: {self.sky.n_drawn:,}" + (" (limit reached)" if self.sky.truncated else "")
        )
        if brightness > 0.9:
            self.banner.set_message(
                "danger", "<b>The paradox:</b> every line of sight ends on a star, so the whole sky blazes like the "
                "surface of the Sun, day and night.")
        elif brightness > 0.3:
            self.banner.set_message(
                "warning", f"<b>Still a bright sky</b> ({100 * brightness:.0f}% of a star's surface). Try a younger "
                "universe, shorter-lived stars or faster expansion.")
        else:
            reasons = [name for name, on in (("the finite age", self.finite_age.isChecked()),
                                             ("limited stellar lifetimes", self.lifetimes.isChecked()),
                                             ("redshift dimming", self.expanding.isChecked())) if on]
            self.banner.set_message(
                "success", f"<b>A dark night sky</b> ({100 * brightness:.0f}% of a star's surface), thanks to "
                + (" and ".join(reasons) if reasons else "the low density of stars") + ".")
        self.plot.refresh()

    # ---------------------------------------------------------------- draw
    def _draw(self, fig) -> None:
        if self.sky is None:
            return
        p = theme().palette
        density, depth, hubble = self.parameters()
        mfp = olbers.mean_free_path(density)
        gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1])

        ax = fig.add_subplot(gs[:, 0])
        deg = math.degrees(olbers.FIELD_RAD)
        ax.imshow(self.sky.image, cmap="afmhot", vmin=0, vmax=1, extent=(0, deg, 0, deg), origin="lower",
                  interpolation="nearest")
        ax.set_title(f"A {deg:.0f}° × {deg:.0f}° patch of sky (simulated)", fontsize=9)
        ax.set_xlabel("degrees", fontsize=8)
        ax.tick_params(labelsize=7)

        ax = fig.add_subplot(gs[0, 1])
        d_max = max(5 * mfp, 1.3 * depth if math.isfinite(depth) else 0)
        distances = np.linspace(0, d_max, 300)
        static = [olbers.sky_brightness(d, mfp) for d in distances]
        ax.plot(distances / mfp, static, color=p.series[0], linewidth=2, label="static universe")
        if hubble:
            expanding = [olbers.sky_brightness(d, mfp, hubble) for d in distances]
            ax.plot(distances / mfp, expanding, color=p.series[3], linewidth=2, label="expanding")
        if math.isfinite(depth):
            ax.axvline(depth / mfp, color=p.accent2, linestyle="--", linewidth=1.2, label="light-travel limit")
        ax.axhline(olbers.sky_brightness(depth, mfp, hubble), color=p.text, linestyle=":", linewidth=1)
        ax.set_ylim(0, 1.05)
        ax.set_xlim(0, d_max / mfp)
        ax.set_xlabel("how far we can see (in λ)", fontsize=8)
        ax.set_ylabel("sky brightness", fontsize=8)
        ax.set_title("Sky brightness vs depth", fontsize=8)
        ax.legend(loc="lower right", fontsize=6.5)
        ax.tick_params(labelsize=7)

        ax = fig.add_subplot(gs[1, 1])
        shell = np.ones_like(distances)
        ax.plot(distances / mfp, shell, color=p.muted, linestyle="--", linewidth=1.2, label="each shell alone")
        seen = np.exp(-distances / mfp) * olbers.redshift_factor(distances, hubble) ** -4.0
        if math.isfinite(depth):
            seen = np.where(distances <= depth, seen, 0.0)
        ax.fill_between(distances / mfp, 0, seen, color=p.series[1], alpha=0.35, linewidth=0)
        ax.plot(distances / mfp, seen, color=p.series[1], linewidth=2, label="light that reaches us")
        ax.set_ylim(0, 1.15)
        ax.set_xlim(0, d_max / mfp)
        ax.set_xlabel("distance of the shell (in λ)", fontsize=8)
        ax.set_ylabel("light per shell", fontsize=8)
        ax.set_title("The shell argument", fontsize=8)
        ax.legend(loc="upper right", fontsize=6.5)
        ax.tick_params(labelsize=7)

    def _csv(self):
        density, depth, hubble = self.parameters()
        mfp = olbers.mean_free_path(density)
        rows = []
        for d in np.linspace(0, 6 * mfp, 200):
            rows.append([f"{d:.2f}", f"{d / mfp:.4f}", f"{olbers.sky_coverage(d, mfp):.5f}",
                         f"{olbers.sky_brightness(d, mfp, hubble):.5f}"])
        return ["depth_stellar_radii", "depth_mean_free_paths", "coverage", "brightness"], rows

    def guide_extra(self) -> str:
        return (
            "### About the simulation\n\n"
            "Stars are placed at random in a teaching universe measured in stellar radii. Nearby stars are drawn "
            "as discs; beyond 400 stellar radii each empty pixel is followed along its line of sight with the "
            "exact probability of hitting a star. The sky is **simulated**, not an image of the real sky."
        )
