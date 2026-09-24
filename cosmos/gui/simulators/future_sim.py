"""S26 — The Far Future."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QGroupBox, QLabel, QTabWidget, QVBoxLayout

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr, tr_noop
from cosmos.physics import constants as const
from cosmos.physics import future as fut
from cosmos.physics.cosmology import Cosmology, Fate

H0 = 67.66
# Presets: label, Ωm, ΩΛ, w.
PRESETS = {
    "ours": (tr_noop("Our universe: a cosmological constant"), 0.31, 0.69, -1.0),
    "phantom": (tr_noop("Phantom energy, w = −1.5"), 0.30, 0.70, -1.5),
    "mild": (tr_noop("Barely phantom, w = −1.05"), 0.31, 0.69, -1.05),
    "quintessence": (tr_noop("Quintessence, w = −0.8"), 0.31, 0.69, -0.8),
    "crunch": (tr_noop("Negative dark energy: a Big Crunch"), 0.31, -0.30, -1.0),
    "matter": (tr_noop("Matter only, no dark energy"), 1.00, 0.0, -1.0),
}
CUSTOM = "custom"
SECONDS_PER = ((const.GYR, tr_noop("billion years")), (1e6 * const.YEAR, tr_noop("million years")),
               (const.YEAR, tr_noop("years")), (86_400, tr_noop("days")), (3600, tr_noop("hours")),
               (60, tr_noop("minutes")), (1, tr_noop("seconds")))


def format_span(seconds: float) -> str:
    """A time span in the largest unit that keeps the number at one or more."""
    for size, unit in SECONDS_PER:
        if seconds >= size:
            return f"{seconds / size:.3g} {tr(unit)}"
    return f"{seconds:.1e} {tr('seconds')}"


class FutureSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.result: fut.Future | None = None
        self._applying = False

        pick = QGroupBox(tr("1 · Choose a universe"))
        pl = QVBoxLayout(pick)
        self.preset = QComboBox()
        for key, (label, *_values) in PRESETS.items():
            self.preset.addItem(tr(label), key)
        self.preset.addItem(tr("Your own settings"), CUSTOM)
        pl.addWidget(labelled_row(tr("Universe"), self.preset, (
            tr("Which future?"),
            tr("Today's measurements fit a cosmological constant, which never changes. But a small "
               "difference in w decides between a quiet heat death and a violent Big Rip, and the "
               "data cannot yet rule out either side of w = −1."))))
        self.controls.addWidget(pick)

        dials = QGroupBox(tr("2 · Adjust it"))
        dl = QVBoxLayout(dials)
        self.om = ParameterSlider(
            tr("Matter Ωm"), 0.05, 1.5, 0.31, decimals=2, step=0.01,
            info=(tr("Matter"), tr("Matter dilutes as the universe grows, so it matters less and less "
                                   "for the future — unless there is enough of it to stop the expansion.")))
        self.ol = ParameterSlider(
            tr("Dark energy ΩΛ"), -1.0, 1.5, 0.69, decimals=2, step=0.01,
            info=(tr("Dark energy"), tr("Negative values are allowed here on purpose: a negative vacuum "
                                        "energy pulls, and it always ends in a Big Crunch.")))
        self.w = ParameterSlider(
            tr("Equation of state w"), -2.0, -0.4, -1.0, decimals=2, step=0.01,
            info=(tr("How dark energy behaves"),
                  tr("w = −1 is a cosmological constant: its density never changes. Above −1 it thins "
                     "out slowly (quintessence); below −1 it grows as space expands (phantom energy), "
                     "and the expansion runs away in a finite time.")))
        for w in (self.om, self.ol, self.w):
            dl.addWidget(w)
        self.controls.addWidget(dials)

        results = QGroupBox(tr("What lies ahead"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("The expansion comes from the Friedmann equations. The astrophysical "
                                    "milestones are estimates good to an order of magnitude, which on "
                                    "this scale is what matters.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.scale_plot = PlotWidget(self._draw_scale, csv_provider=self._csv, export_name="future_expansion")
        self.timeline_plot = PlotWidget(self._draw_timeline, export_name="future_timeline")
        self.rip_plot = PlotWidget(self._draw_rip, export_name="big_rip_countdown")
        self.reach_plot = PlotWidget(self._draw_reach, export_name="reachable_universe")
        tabs.addTab(self.scale_plot, tr("Expansion"))
        tabs.addTab(self.timeline_plot, tr("The next 10¹⁰⁰ years"))
        tabs.addTab(self.rip_plot, tr("Big Rip countdown"))
        tabs.addTab(self.reach_plot, tr("Galaxies we can still reach"))
        self.display.addWidget(tabs, 1)

        self.preset.currentIndexChanged.connect(self._preset_changed)
        for w in (self.om, self.ol, self.w):
            w.valueChanged.connect(self._dial_moved)
        self.recompute()

    # ----------------------------------------------------------- controls
    def _preset_changed(self, *_args) -> None:
        key = self.preset.currentData()
        if key == CUSTOM:
            return
        _label, om, ol, w = PRESETS[key]
        self._applying = True
        try:
            self.om.setValue(om)
            self.ol.setValue(ol)
            self.w.setValue(w)
        finally:
            self._applying = False
        self.schedule_update()

    def _dial_moved(self, *_args) -> None:
        if not self._applying:
            self.preset.blockSignals(True)
            self.preset.setCurrentIndex(self.preset.findData(CUSTOM))
            self.preset.blockSignals(False)
        self.schedule_update()

    def cosmology(self) -> Cosmology:
        # Radiation is irrelevant to the future and would tip an Ωm = 1 universe into
        # a (very distant) recollapse, so it is left out here.
        return Cosmology(H0=H0, Om0=self.om.value(), Ode0=self.ol.value(), w0=self.w.value(), Tcmb0=0.0)

    # ----------------------------------------------------------- compute
    def recompute(self) -> None:
        cosmo = self.cosmology()
        f = fut.future(cosmo)
        self.result = f
        lines = [tr("Fate: this universe <b>{fate}</b>.").format(fate=physics(f.fate.value))]
        if f.fate is Fate.NO_BIG_BANG:
            lines.append(physics(f.fate.explanation))
        else:
            lines.append(tr("Age today: {age} billion years").format(age=f"{f.age_gyr:.1f}"))
            if f.ends:
                lines.append(tr("The end comes in <b>{time} billion years</b>").format(time=f"{f.end_gyr:.1f}"))
            else:
                lines.append(tr("There is no end: time goes on for ever"))
            if math.isfinite(f.efold_gyr):
                lines.append(tr("Distances grow by a factor e every {time} billion years")
                             .format(time=f"{f.efold_gyr:.1f}"))
            if len(f.reach):
                lines.append(tr("A signal sent today can still reach <b>{percent}</b> of the galaxies we see")
                             .format(percent=f"{f.reachable_now:.1%}"))
            times = f.destruction_times()
            if times:
                lines.append(tr("The Milky Way is torn apart {milky} before the end, the Earth {earth} before")
                             .format(milky=format_span(times["milky-way"]), earth=format_span(times["earth"])))
            happening = sum(f.happens(m) for m in fut.MILESTONES)
            lines.append(tr("{count} of the {total} milestones on the timeline happen")
                         .format(count=happening, total=len(fut.MILESTONES)))
        self.summary.setText("<br>".join(lines))

        if f.fate is Fate.BIG_RIP:
            self.banner.set_message(
                "danger",
                tr("<b>A Big Rip in {time} billion years.</b> Phantom energy grows denser as space expands. "
                   "Clusters go first, then galaxies, then planetary systems; in the last fraction of a "
                   "second, atoms.").format(time=f"{f.end_gyr:.0f}"))
        elif f.fate is Fate.BIG_CRUNCH:
            self.banner.set_message(
                "warning",
                tr("<b>A Big Crunch.</b> The expansion stops and reverses. The CMB heats up again, the "
                   "stars are cooked by the sky, and everything ends as it began, hot and dense."))
        elif f.fate is Fate.NO_BIG_BANG:
            self.banner.set_message("warning", physics(f.fate.explanation))
        else:
            self.banner.set_message(
                "info",
                tr("<b>A cold, dark, endless future.</b> Nothing dramatic happens: the lights simply go out, "
                   "one by one, over a stretch of time that makes the present age of the universe a "
                   "rounding error."))
        for plot in (self.scale_plot, self.timeline_plot, self.rip_plot, self.reach_plot):
            plot.refresh()

    # ------------------------------------------------------------- plots
    def _draw_scale(self, fig) -> None:
        p = theme().palette
        f = self.result
        ax = fig.add_subplot()
        if f.fate is Fate.NO_BIG_BANG or len(f.t) < 2:
            ax.text(0.5, 0.5, "This universe has no Big Bang to start from.", ha="center", va="center",
                    transform=ax.transAxes, color=p.muted)
            ax.set_axis_off()
            return
        ax.semilogy(f.t, np.maximum(f.a, 1e-3), color=p.series[0], linewidth=2.2, label="scale factor a(t)")
        ax.axvline(0, color=p.muted, linestyle=":", linewidth=1)
        ax.text(0, 1.2, " today", color=p.muted, fontsize=7.5)
        if f.ends:
            ax.axvline(f.end_gyr, color=p.danger, linestyle="--", linewidth=1.4,
                       label=("Big Rip" if f.fate is Fate.BIG_RIP else "Big Crunch") + f" in {f.end_gyr:.1f} Gyr")
        ax.set_xlabel("time from now (billion years)", fontsize=8)
        ax.set_ylabel("size of the universe relative to today", fontsize=8)
        ax.set_title("How big the universe will be", fontsize=9)
        ax.legend(fontsize=7.5, loc="upper left")
        ax.tick_params(labelsize=7)

    def _draw_timeline(self, fig) -> None:
        p = theme().palette
        f = self.result
        ax = fig.add_subplot()
        age_years = (f.age_gyr if math.isfinite(f.age_gyr) else 13.8) * 1e9
        ax.axvline(math.log10(age_years), color=p.accent2, linewidth=1.5)
        ax.text(math.log10(age_years), len(fut.MILESTONES) + 0.3, " today", color=p.accent2, fontsize=7.5,
                ha="left")
        for i, m in enumerate(fut.MILESTONES):
            x = math.log10(age_years + m.years_from_now)
            happens = f.happens(m)
            colour = p.series[0] if happens else p.muted
            ax.plot([x], [i], "o", color=colour, markersize=7, alpha=1.0 if happens else 0.4)
            text = m.label + ("" if happens else "  — never happens")
            # Labels of the late milestones go to the left of their dot to stay on the axis.
            right = x > 60
            ax.text(x - 1.2 if right else x + 1.2, i, text, va="center", ha="right" if right else "left",
                    fontsize=7.5, color=p.text if happens else p.muted)
        if f.ends:
            x_end = math.log10(age_years + f.end_gyr * 1e9)
            ax.axvspan(x_end, 112, color=p.danger, alpha=0.12)
            ax.axvline(x_end, color=p.danger, linewidth=1.5)
            ax.text(x_end, -0.9, " Big Rip" if f.fate is Fate.BIG_RIP else " Big Crunch", color=p.danger,
                    fontsize=8)
        ax.set_xlim(9.5, 112)
        ax.set_ylim(-1.3, len(fut.MILESTONES) + 0.8)
        ax.set_yticks([])
        ax.set_xlabel("log₁₀ (years since the Big Bang)", fontsize=8)
        ax.set_title("Every tick on this axis is ten times longer than the one before", fontsize=9)
        ax.tick_params(labelsize=7)

    def _draw_rip(self, fig) -> None:
        p = theme().palette
        f = self.result
        ax = fig.add_subplot()
        times = f.destruction_times()
        if not times:
            ax.text(0.5, 0.5, "No Big Rip in this universe.\nSet w below −1 to see the countdown.",
                    ha="center", va="center", transform=ax.transAxes, color=p.muted, fontsize=10)
            ax.set_axis_off()
            return
        labels = [s.label for s in fut.BOUND_SYSTEMS]
        values = [times[s.key] for s in fut.BOUND_SYSTEMS]
        y = np.arange(len(labels))[::-1]
        ax.barh(y, np.log10(values) + 30, left=-30, color=[p.series[i % len(p.series)] for i in range(len(y))],
                alpha=0.85)
        for yy, v in zip(y, values):
            ax.text(math.log10(v) + 0.4, yy, format_span(v) + " before", va="center", fontsize=7.5, color=p.text)
        ax.set_yticks(y)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlim(-30, math.log10(max(values)) + 16)
        ax.set_xlabel("log₁₀ (seconds before the Big Rip)", fontsize=8)
        ax.set_title(f"w = {f.cosmology.w0:.2f}: the Big Rip comes in {f.end_gyr:.1f} billion years", fontsize=9)
        ax.tick_params(labelsize=7)

    def _draw_reach(self, fig) -> None:
        p = theme().palette
        f = self.result
        ax = fig.add_subplot()
        if not len(f.reach):
            ax.text(0.5, 0.5, "Without accelerating expansion there is no event horizon:\n"
                    "given enough time, a signal reaches every galaxy.",
                    ha="center", va="center", transform=ax.transAxes, color=p.muted, fontsize=10)
            ax.set_axis_off()
            return
        galaxies = f.reach * fut.OBSERVABLE_GALAXIES
        ax.semilogy(f.reach_t, np.maximum(galaxies, 1e-3), color=p.series[2], linewidth=2.2)
        ax.axhline(50, color=p.muted, linestyle="--", linewidth=1)
        ax.text(f.reach_t[-1], 70, "the Local Group: about 50 galaxies ", ha="right", fontsize=7.5, color=p.muted)
        ax.set_xlabel("time from now (billion years)", fontsize=8)
        ax.set_ylabel("galaxies a light signal sent then could reach", fontsize=8)
        ax.set_title(f"Today we could still reach {f.reachable_now:.1%} of the "
                     f"{fut.OBSERVABLE_GALAXIES / 1e12:.0f} trillion galaxies we see", fontsize=9)
        ax.set_ylim(max(float(galaxies.min()), 1e-2) / 3, fut.OBSERVABLE_GALAXIES * 2)
        ax.tick_params(labelsize=7)

    def _csv(self):
        f = self.result
        step = max(len(f.t) // 400, 1)
        rows = [[f"{t:.4f}", f"{a:.6g}"] for t, a in zip(f.t[::step], f.a[::step])]
        return ["time_from_now_Gyr", "scale_factor"], rows

    # ------------------------------------------------------------- state
    def state(self) -> dict:
        f = self.result
        times = f.destruction_times()
        return {
            "preset": self.preset.currentData(),
            "om": self.om.value(),
            "ol": self.ol.value(),
            "w": self.w.value(),
            "fate": f.fate.value,
            "end_gyr": f.end_gyr if f.ends else 1e12,
            "reachable": f.reachable_now if len(f.reach) else 1.0,
            "earth_seconds": times.get("earth", math.inf),
            "milestones": sum(f.happens(m) for m in fut.MILESTONES),
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("Why w = −1 is a knife edge") + "\n\n"
            + tr("The density of dark energy changes as $a^{-3(1+w)}$. At exactly w = −1 it stays the same "
                 "for ever; a little above, it fades; a little below, it grows without limit and the "
                 "expansion rate becomes infinite in a finite time. Today's data put w within about ten "
                 "per cent of −1, so they cannot yet tell a heat death from a Big Rip — they only say "
                 "that a Big Rip, if it comes, is at least tens of billions of years away.")
        )
