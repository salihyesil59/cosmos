"""S2 — Expansion History Explorer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import ParameterSlider, PresetSelector, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology, Fate, no_big_bang_boundary, recollapse_boundary
from cosmos.physics.presets import PRESETS

OM_RANGE = (0.0, 3.0)
OL_RANGE = (-1.0, 3.0)
MAX_PINNED = 5


class ExpansionSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.pinned: list[tuple[str, object]] = []
        self.history = None

        model = QGroupBox(tr("Universe contents"))
        ml = QVBoxLayout(model)
        self.preset = PresetSelector()
        ml.addWidget(labelled_row(tr("Preset"), self.preset, (
            tr("Presets"), tr("Load a named model. Moving any slider switches back to custom values."))))
        self.om = ParameterSlider(
            tr("Ωm matter"), *OM_RANGE, 0.31, decimals=3, step=0.01,
            info=(tr("Matter density Ωm"), tr("Matter (ordinary + dark) slows the expansion. Above 1 without dark "
                      "energy, the universe recollapses.")),
        )
        self.ode = ParameterSlider(
            tr("ΩΛ dark energy"), *OL_RANGE, 0.69, decimals=3, step=0.01,
            info=(tr("Dark energy density ΩΛ"), tr("A positive cosmological constant accelerates the expansion. "
                      "Negative values act like extra attraction and cause recollapse.")),
        )
        self.h0 = ParameterSlider(
            tr("H0 (km/s/Mpc)"), 40, 100, 67.66, decimals=1,
            info=(tr("Hubble constant"), tr("Sets the time scale: a larger H0 makes every universe younger, "
                      "but does not change the shape of the curves.")),
        )
        self.radiation = QCheckBox(tr("Include radiation"))
        self.radiation.setToolTip(tr("Radiation only matters in the first ~100 000 years; the effect on this plot is tiny."))
        for w in (self.om, self.ode, self.h0, self.radiation):
            ml.addWidget(w)
        self.controls.addWidget(model)

        pins = QGroupBox(tr("Compare"))
        pl = QHBoxLayout(pins)
        pin = QPushButton(tr("📌 Pin curve"))
        pin.setToolTip(tr("Keep the current a(t) curve on the plot to compare with other models (up to 5)."))
        pin.clicked.connect(self._pin)
        clear = QPushButton(tr("Clear pins"))
        clear.clicked.connect(self._clear_pins)
        pl.addWidget(pin)
        pl.addWidget(clear)
        self.controls.addWidget(pins)

        summary = QGroupBox(tr("This universe"))
        sl = QVBoxLayout(summary)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        sl.addWidget(self.summary)
        self.controls.addWidget(summary)
        self.finish_controls()

        split = QSplitter(Qt.Vertical)
        self.a_plot = PlotWidget(self._draw_history, csv_provider=self._history_csv, export_name="scale_factor")
        self.plane = PlotWidget(self._draw_plane, export_name="omega_plane")
        self.plane.canvas.mpl_connect("button_press_event", self._plane_clicked)
        self.plane.canvas.setToolTip(tr("Click anywhere on this map to choose Ωm and ΩΛ."))
        split.addWidget(self.a_plot)
        split.addWidget(self.plane)
        split.setSizes([450, 400])
        self.display.addWidget(split, 1)

        self.preset.presetChosen.connect(self._load_preset)
        for w in (self.om, self.ode, self.h0):
            w.valueChanged.connect(self._custom_change)
        self.radiation.toggled.connect(self._custom_change)
        self._loading = False
        self.preset.set_key("planck18", emit=True)

    # --------------------------------------------------------------- model
    def _load_preset(self, key: str) -> None:
        c = PRESETS[key].cosmology
        self._loading = True
        self.om.setValue(min(c.Om0, OM_RANGE[1]), emit=False)
        self.ode.setValue(min(max(c.Ode0, OL_RANGE[0]), OL_RANGE[1]), emit=False)
        self.h0.setValue(c.H0, emit=False)
        self.radiation.setChecked(c.Tcmb0 > 0)
        self._loading = False
        self.recompute()

    def _custom_change(self, *_args) -> None:
        if self._loading:
            return
        self.preset.set_key("custom")
        self.schedule_update()

    def cosmology(self) -> Cosmology:
        return Cosmology(
            H0=self.h0.value(),
            Om0=self.om.value(),
            Ode0=self.ode.value(),
            Tcmb0=const.T_CMB if self.radiation.isChecked() else 0.0,
            name=f"Ωm={self.om.value():.2f}, ΩΛ={self.ode.value():.2f}",
        )

    def state(self) -> dict:
        c = self.cosmology()
        fate = c.fate()
        return {
            "om": self.om.value(),
            "ode": self.ode.value(),
            "h0": self.h0.value(),
            "fate": fate.name.replace("_", " ").lower(),
            "accelerating": float(c.deceleration_parameter(0)) < 0,
            "age_gyr": self.history.age if self.history and self.history.age else float("nan"),
            "geometry": c.geometry,
        }

    def recompute(self) -> None:
        c = self.cosmology()
        self.cosmo = c
        self.history = c.expansion_history(t_future=160.0, a_max=6.0)
        fate = c.fate()
        q0 = float(c.deceleration_parameter(0))
        p = theme().palette
        color = {Fate.ACCELERATES_FOREVER: p.accent, Fate.EXPANDS_FOREVER: p.success,
                 Fate.BIG_CRUNCH: p.danger, Fate.NO_BIG_BANG: p.warning}[fate]
        age = (tr("{years} billion years").format(years=f"{self.history.age:.2f}") if self.history.age
               else tr("undefined (no Big Bang)"))
        crunch = ""
        if self.history.crunch_time is not None:
            crunch = "<br>" + tr("Big Crunch in: <b>{years} billion years</b>").format(
                years=f"{self.history.crunch_time:.1f}")
        self.summary.setText(
            tr("Age: <b>{age}</b>{crunch}<br>"
               "Geometry: <b>{geometry}</b> (Ωk = {curvature})<br>"
               "Today: <b>{trend}</b> (q0 = {q0})<br>"
               "Hubble time 1/H0: {hubble} billion years<br><br>"
               "<span style='color:{colour}'><b>Fate: this universe {fate}.</b></span><br>{explanation}")
            .format(age=age, crunch=crunch, geometry=physics(c.geometry),
                    curvature=f"{0.0 if abs(c.Ok0) < 5e-4 else c.Ok0:+.3f}",
                    trend=tr("accelerating") if q0 < 0 else tr("decelerating"), q0=f"{q0:+.2f}",
                    hubble=f"{c.hubble_time:.2f}", colour=color,
                    fate=physics(fate.value), explanation=physics(fate.explanation))
        )
        self.a_plot.refresh()
        self.plane.refresh()

    # --------------------------------------------------------------- pins
    def _pin(self) -> None:
        if self.history is None:
            return
        if len(self.pinned) >= MAX_PINNED:
            self.pinned.pop(0)
        self.pinned.append((self.cosmo.name, self.history))
        self.a_plot.refresh()

    def _clear_pins(self) -> None:
        self.pinned.clear()
        self.a_plot.refresh()

    # -------------------------------------------------------------- plots
    def _draw_history(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        for i, (label, hist) in enumerate(self.pinned):
            ax.plot(hist.t, hist.a, color=p.series[(i + 1) % 6], linewidth=1.4, alpha=0.75, linestyle="--",
                    label=f"Pinned: {label}")
        h = self.history
        if h is not None:
            ax.plot(h.t, h.a, color=p.series[0], linewidth=2.6, label=f"Current: {self.cosmo.name}")
            if h.big_bang_time is not None:
                ax.scatter([h.big_bang_time], [0], color=p.accent2, zorder=4, s=40)
                ax.annotate("Big Bang", (h.big_bang_time, 0), textcoords="offset points", xytext=(4, 8),
                            color=p.accent2, fontsize=8)
            if h.crunch_time is not None:
                ax.scatter([h.crunch_time], [0], color=p.danger, zorder=4, s=40)
                ax.annotate("Big Crunch", (h.crunch_time, 0), textcoords="offset points", xytext=(-50, 8),
                            color=p.danger, fontsize=8)
        ax.axvline(0, color=p.muted, linestyle=":", linewidth=1)
        ax.axhline(1, color=p.muted, linestyle=":", linewidth=1)
        ax.annotate("today (a = 1)", (0, 1), textcoords="offset points", xytext=(5, -14), color=p.muted, fontsize=8)
        right = 40.0
        crunches = [hist.crunch_time for _l, hist in self.pinned] + ([h.crunch_time] if h else [])
        crunches = [t for t in crunches if t is not None]
        if crunches:
            right = min(160.0, max(right, max(crunches) + 5))
        ax.set_xlim(-30, right)
        ax.set_ylim(0, 4)
        ax.set_xlabel("Time from today (billion years)")
        ax.set_ylabel("Scale factor a(t)  —  size relative to today")
        ax.set_title("Expansion history", fontsize=10)
        ax.legend(loc="upper left", fontsize=8)

    def _draw_plane(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        om = np.linspace(*OM_RANGE, 300)
        top = np.full_like(om, OL_RANGE[1])
        nbb = np.clip(no_big_bang_boundary(om), None, OL_RANGE[1])
        rec = recollapse_boundary(om)
        ax.fill_between(om, nbb, top, color=p.warning, alpha=0.22, linewidth=0)
        ax.fill_between(om, OL_RANGE[0], rec, color=p.danger, alpha=0.18, linewidth=0)
        ax.plot(om, 1 - om, color=p.text, linewidth=1.2, label="Flat (Ωm + ΩΛ = 1)")
        ax.plot(om, om / 2, color=p.accent, linewidth=1.2, linestyle="--", label="Accelerating above this line")
        ax.text(0.15, 2.75, "No Big Bang", color=p.warning, fontsize=9, weight="bold")
        ax.text(1.9, -0.7, "Recollapse (Big Crunch)", color=p.danger, fontsize=9, weight="bold")
        ax.text(0.05, 1.55, "closed ↗", color=p.muted, fontsize=8)
        ax.text(0.05, 0.25, "open ↙", color=p.muted, fontsize=8)
        planck = PRESETS["planck18"].cosmology
        ax.scatter([planck.Om0], [planck.Ode0], marker="*", s=120, color=p.accent2, zorder=4, label="Our universe (Planck)")
        ax.scatter([self.om.value()], [self.ode.value()], s=70, color=p.series[0], edgecolor=p.text, zorder=5,
                   label="Your choice")
        ax.set_xlim(*OM_RANGE)
        ax.set_ylim(*OL_RANGE)
        ax.set_xlabel("Ωm (matter)")
        ax.set_ylabel("ΩΛ (dark energy)")
        ax.set_title("The Ωm–ΩΛ map: click to choose a universe", fontsize=10)
        ax.legend(loc="upper right", fontsize=8)

    def _plane_clicked(self, event) -> None:
        if event.inaxes is None or event.xdata is None:
            return
        self._loading = True
        self.om.setValue(float(np.clip(event.xdata, *OM_RANGE)), emit=False)
        self.ode.setValue(float(np.clip(event.ydata, *OL_RANGE)), emit=False)
        self._loading = False
        self.preset.set_key("custom")
        self.recompute()

    def _history_csv(self):
        h = self.history
        return ["time_from_today_Gyr", "scale_factor"], [[f"{t:.6g}", f"{a:.6g}"] for t, a in zip(h.t, h.a)]
