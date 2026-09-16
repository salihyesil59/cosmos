"""S10 — Interactive Cosmic Timeline."""

from __future__ import annotations

import math

import numpy as np
from matplotlib.patches import Patch
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.physics import constants as const
from cosmos.physics.timeline import EPOCHS, T_MAX_S, T_MIN_S, YEAR_S, Timeline, format_time

LOG_T_MIN = math.log10(T_MIN_S)
LOG_T_MAX = math.log10(T_MAX_S)

STATUS_TEXT = {
    "speculative": "Speculative: no direct evidence yet",
    "theory": "Well-motivated theory, indirect evidence",
    "tested": "Physics tested in laboratories and accelerators",
    "observed": "Directly observed",
}

# Reference temperatures to give a feeling for the numbers (kelvin).
COMPARISONS = [
    (1e32, "the Planck temperature, where known physics ends"),
    (1e16, "collisions at the Large Hadron Collider"),
    (1e12, "heavy-ion collisions that melt protons into quarks"),
    (1e9, "the hottest nuclear fusion in massive stars"),
    (1.5e7, "the core of the Sun"),
    (5800, "the surface of the Sun"),
    (1500, "a candle flame"),
    (373, "boiling water"),
    (293, "a comfortable room"),
    (77, "liquid nitrogen"),
    (2.7, "deep space today"),
    (0.0, "colder than anything in the universe today"),
]

TICKS = [(-40, "10⁻⁴⁰ s"), (-30, "10⁻³⁰ s"), (-20, "10⁻²⁰ s"), (-10, "10⁻¹⁰ s"), (0, "1 s"),
         (math.log10(YEAR_S), "1 yr"), (math.log10(1e6 * YEAR_S), "1 Myr"),
         (math.log10(1e12 * YEAR_S), "1 Tyr")]


def format_energy(temperature_k: float) -> str:
    ev = temperature_k * const.K_B / const.EV
    for scale, unit in ((1e18, "EeV"), (1e15, "PeV"), (1e12, "TeV"), (1e9, "GeV"), (1e6, "MeV"),
                        (1e3, "keV"), (1.0, "eV"), (1e-3, "meV")):
        if ev >= scale:
            value = ev / scale
            return f"{value:.3g} {unit}" if value < 1000 else f"{ev:.2e} eV"
    return f"{ev:.2e} eV"


def format_length(metres: float) -> str:
    if math.isinf(metres):
        return "infinite"
    ly = metres / const.LIGHT_YEAR
    if metres < 1e3:
        return f"{metres:.3g} m"
    if metres < const.C:
        return f"{metres / 1e3:,.0f} km".replace(",", " ")
    if ly < 1:
        seconds = metres / const.C
        for scale, unit in ((86400, "light-days"), (3600, "light-hours"), (60, "light-minutes"), (1, "light-seconds")):
            if seconds >= scale:
                return f"{seconds / scale:.3g} {unit}"
    if ly < 1e6:
        return f"{ly:.3g} light-years"
    if ly < 1e9:
        return f"{ly / 1e6:.3g} million light-years"
    return f"{ly / 1e9:.3g} billion light-years"


def sci(value: float) -> str:
    if value == 0 or 1e-3 <= abs(value) < 1e5:
        return f"{value:.4g}"
    exponent = math.floor(math.log10(abs(value)))
    return f"{value / 10**exponent:.2f} × 10<sup>{exponent}</sup>"


class CosmicTimelineSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.timeline = Timeline()
        self._markers = []

        travel = QGroupBox("1 · Travel through time")
        tl = QVBoxLayout(travel)
        self.log_time = ParameterSlider(
            "log₁₀ of time since the Big Bang (seconds)", LOG_T_MIN, LOG_T_MAX,
            math.log10(self.timeline.age_s), decimals=2, step=0.1,
            info=("A logarithmic time axis",
                  "Each step of 1 multiplies the time by ten. A log scale is the only way to show 10⁻⁴³ seconds and "
                  "13.8 billion years on the same slider. 0 is one second, 7.5 is one year and 17.64 is today."),
        )
        tl.addWidget(self.log_time)
        self.time_label = QLabel()
        self.time_label.setProperty("role", "subtitle")
        tl.addWidget(self.time_label)
        self.epoch_box = QComboBox()
        self.epoch_box.addItem("Jump to an epoch…", None)
        for ep in EPOCHS:
            self.epoch_box.addItem(ep.name, ep.name)
        tl.addWidget(labelled_row("Epoch", self.epoch_box, (
            "Jump to an epoch", "Moves the time slider to the middle of the chosen epoch.")))
        row = QHBoxLayout()
        self.play = QPushButton("▶ Play history")
        self.play.setCheckable(True)
        self.play.setProperty("role", "primary")
        self.play.setToolTip("Sweep through cosmic history from the Planck era to the far future.")
        self.play.toggled.connect(self._toggle)
        today = QPushButton("Today")
        today.setToolTip("Jump back to the present day.")
        today.clicked.connect(lambda: self.log_time.setValue(math.log10(self.timeline.age_s)))
        row.addWidget(self.play)
        row.addWidget(today)
        tl.addLayout(row)
        self.controls.addWidget(travel)

        state = QGroupBox("The universe at this moment")
        sl = QVBoxLayout(state)
        self.readout = QLabel()
        self.readout.setWordWrap(True)
        self.readout.setTextFormat(Qt.RichText)
        sl.addWidget(self.readout)
        self.controls.addWidget(state)
        self.finish_controls()

        self.banner = Banner("info")
        self.display.addWidget(self.banner)
        self.plot = PlotWidget(self._draw, export_name="cosmic_timeline", csv_provider=self._csv)
        self.display.addWidget(self.plot, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self._grid = np.linspace(LOG_T_MIN, LOG_T_MAX, 500)
        self._temps = np.array([self.timeline.temperature_k(10**x) for x in self._grid])
        self._comp = np.array([list(self.timeline.composition(10**x).values()) for x in self._grid]).T

        self.log_time.valueChanged.connect(self._time_changed)
        self.epoch_box.activated.connect(self._jump)
        self.plot.refresh()
        self._time_changed()

    # ------------------------------------------------------------ state
    def time_s(self) -> float:
        return 10 ** self.log_time.value()

    def _jump(self, index: int) -> None:
        name = self.epoch_box.itemData(index)
        if name is None:
            return
        ep = next(e for e in EPOCHS if e.name == name)
        t = math.sqrt(ep.start_s * ep.end_s) if ep.end_s else ep.start_s
        self.log_time.setValue(math.log10(t))

    def _time_changed(self, *_args) -> None:
        tl, t = self.timeline, self.time_s()
        temp = tl.temperature_k(t)
        a = tl.scale_factor(t)
        comp = tl.composition(t)
        self.time_label.setText(format_time(t) + (" (the future)" if t > tl.age_s * 1.02 else ""))
        like = next(text for limit, text in COMPARISONS if temp >= limit * 0.5)
        horizon = tl.particle_horizon_m(t)
        self.readout.setText(
            f"Temperature: <b>{sci(temp)} K</b><br>"
            f"Typical particle energy kT: <b>{format_energy(temp)}</b><br>"
            f"About as hot as: {like}<br>"
            f"Scale factor a: <b>{sci(a)}</b> " + (
                "(today's size)" if abs(a - 1) < 0.02
                else f"(distances were {sci(1 / a)} times smaller than today)" if a < 1
                else f"(distances are {sci(a)} times larger than today)") + "<br>"
            + (f"Redshift of light emitted then: z = {sci(1 / a - 1)}<br>" if a < 0.98 else "")
            + f"Density: <b>{sci(tl.density_kg_m3(t))} kg/m³</b> (water: 1000)<br>"
            f"Particle horizon: <b>{format_length(horizon)}</b><br>"
            f"Energy budget: radiation {100 * comp['radiation']:.3g}%, matter {100 * comp['matter']:.3g}%, "
            f"dark energy {100 * comp['dark energy']:.3g}%"
        )
        epochs = tl.epochs_at(t)
        if epochs:
            kinds = {"speculative": "danger", "theory": "warning", "tested": "info", "observed": "success"}
            main = epochs[-1]
            text = "<br>".join(
                f"<b>{ep.name}.</b> {ep.description} <i>({STATUS_TEXT[ep.status]}"
                + (f"; lesson {ep.lesson}" if ep.lesson else "") + ")</i>"
                for ep in epochs
            )
            self.banner.set_message(kinds[main.status], text)
        else:
            nxt = next((e for e in EPOCHS if e.start_s > t), None)
            prev = [e for e in EPOCHS if e.start_s <= t]
            text = f"After <b>{prev[-1].name}</b>" if prev else "Before every known epoch"
            if nxt:
                text += f"; next: <b>{nxt.name}</b> at {format_time(nxt.start_s)}"
            if t < 1e-11:
                text += ". The physics of this period is not known: numbers are extrapolations."
            self.banner.set_message("info", text + ".")
        self._update_markers()

    def recompute(self) -> None:
        self.plot.refresh()
        self._time_changed()

    # ---------------------------------------------------------- animation
    def _toggle(self, on: bool) -> None:
        self.play.setText("⏸ Pause" if on else "▶ Play history")
        if on:
            if self.log_time.value() >= LOG_T_MAX - 0.05:
                self.log_time.setValue(LOG_T_MIN)
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        value = min(self.log_time.value() + 0.1, LOG_T_MAX)
        # Slow down near the well-observed epochs so there is time to read them.
        if value > 0:
            value = min(self.log_time.value() + 0.05, LOG_T_MAX)
        self.log_time.setValue(value)
        if value >= LOG_T_MAX:
            self.play.setChecked(False)

    def on_hidden(self) -> None:
        self.play.setChecked(False)

    def _update_markers(self) -> None:
        if not self._markers:
            return
        x = self.log_time.value()
        line_top, point, line_bottom = self._markers
        line_top.set_xdata([x, x])
        point.set_data([x], [math.log10(self.timeline.temperature_k(10**x))])
        line_bottom.set_xdata([x, x])
        self.plot.canvas.draw_idle()

    # ---------------------------------------------------------------- draw
    def _draw(self, fig) -> None:
        p = theme().palette
        colours = {"speculative": p.danger, "theory": p.warning, "tested": p.accent, "observed": p.success}
        ax, ax2 = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
        x = self.log_time.value()
        for ep in EPOCHS:
            lo = math.log10(ep.start_s)
            hi = math.log10(ep.end_s) if ep.end_s else lo
            if hi - lo < 0.25:
                lo, hi = (lo + hi) / 2 - 0.12, (lo + hi) / 2 + 0.12
            for axis in (ax, ax2):
                axis.axvspan(lo, hi, color=colours[ep.status], alpha=0.18, linewidth=0)
        ax.plot(self._grid, np.log10(self._temps), color=p.series[0], linewidth=2)
        age = math.log10(self.timeline.age_s)
        for axis in (ax, ax2):
            axis.axvline(age, color=p.muted, linestyle=":", linewidth=1)
        ax.text(age, 30, " today", color=p.muted, fontsize=7)
        line_top = ax.axvline(x, color=p.accent2, linewidth=1.5)
        point, = ax.plot([x], [math.log10(self.timeline.temperature_k(10**x))], "o", color=p.accent2, markersize=8)
        ax.set_ylabel("log₁₀ temperature (K)", fontsize=8)
        ax.set_title("Temperature; bands are epochs, coloured by how well we know them", fontsize=8)
        ax.legend(handles=[Patch(color=colours[k], alpha=0.4, label=k) for k in colours], loc="upper right",
                  fontsize=7, ncols=4)
        labels = ["radiation", "matter", "dark energy"]
        ax2.stackplot(self._grid, self._comp, colors=[p.series[3], p.series[1], p.series[2]], alpha=0.8, labels=labels)
        line_bottom = ax2.axvline(x, color=p.accent2, linewidth=1.5)
        ax2.set_ylim(0, 1)
        ax2.set_ylabel("Share of energy", fontsize=8)
        ax2.legend(loc="center left", fontsize=7)
        ax2.set_xticks([v for v, _ in TICKS], [label for _, label in TICKS])
        ax2.set_xlim(LOG_T_MIN, LOG_T_MAX)
        ax2.set_xlabel("Time since the Big Bang (logarithmic)", fontsize=8)
        for axis in (ax, ax2):
            axis.tick_params(labelsize=7)
        self._markers = [line_top, point, line_bottom]

    def _csv(self):
        rows = [[f"{10**x:.6g}", f"{t:.6g}", f"{c[0]:.6g}", f"{c[1]:.6g}", f"{c[2]:.6g}"]
                for x, t, c in zip(self._grid, self._temps, self._comp.T)]
        return ["time_s", "temperature_K", "radiation_fraction", "matter_fraction", "dark_energy_fraction"], rows

    def guide_extra(self) -> str:
        lines = ["### Epochs and their lessons", ""]
        for ep in EPOCHS:
            link = f" — [lesson {ep.lesson}](lesson:{ep.lesson})" if ep.lesson else ""
            lines.append(f"- **{ep.name}** ({format_time(ep.start_s)}){link}")
        lines += ["", "Before about 10⁻¹¹ s the temperatures are extrapolations of known physics. "
                  "After one second they come from the Planck 2018 ΛCDM model."]
        return "\n".join(lines)
