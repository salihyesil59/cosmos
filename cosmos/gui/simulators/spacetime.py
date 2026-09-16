"""S9 — Spacetime / Horizon Diagram."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QLabel, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, PresetSelector, labelled_row
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr, tr_noop
from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology, Fate
from cosmos.physics.presets import PRESETS

MPC_TO_GLY = const.MPC / const.LIGHT_YEAR / 1e9
COORDINATES = {
    "proper": tr_noop("Proper distance vs cosmic time"),
    "comoving": tr_noop("Comoving distance vs cosmic time"),
    "conformal": tr_noop("Comoving distance vs conformal time (light at 45°)"),
}
GALAXY_COMOVING_GLY = (4, 10, 20, 30, 40, 60)


class SpacetimeSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.data = None

        model = QGroupBox(tr("1 · Universe"))
        ml = QVBoxLayout(model)
        self.preset = PresetSelector()
        ml.addWidget(labelled_row(tr("Preset"), self.preset))
        self.om = ParameterSlider(tr("Ωm matter"), 0.05, 1.0, 0.3097, decimals=3, step=0.01)
        self.ode = ParameterSlider(tr("ΩΛ dark energy"), 0.0, 1.5, 0.6889, decimals=3, step=0.01)
        ml.addWidget(self.om)
        ml.addWidget(self.ode)
        self.controls.addWidget(model)

        view = QGroupBox(tr("2 · Diagram"))
        vl = QVBoxLayout(view)
        self.coords = QComboBox()
        for key, label in COORDINATES.items():
            self.coords.addItem(tr(label), key)
        vl.addWidget(labelled_row(tr("Coordinates"), self.coords, (
            tr("Coordinates"),
            tr("Proper distance is the real distance at each moment. Comoving distance removes the expansion, "
                "so galaxies stay at fixed positions. In conformal time light always travels at 45°."))))
        self.observe = ParameterSlider(
            tr("Observer's scale factor a"), 0.1, 2.5, 1.0, decimals=2, step=0.05,
            info=(tr("Observation time"), tr("Move the observer through cosmic history: a = 1 is today, a = 0.5 when the "
                      "universe was half its present size, a = 2 in the future.")),
        )
        vl.addWidget(self.observe)
        self.toggles = {}
        for key, label, default in [
            ("past", tr("Past light cone (what you see)"), True),
            ("future", tr("Future light cone (where your light goes)"), False),
            ("particle", tr("Particle horizon"), True),
            ("event", tr("Event horizon"), True),
            ("hubble", tr("Hubble sphere"), True),
            ("galaxies", tr("Galaxy worldlines"), True),
        ]:
            box = QCheckBox(label)
            box.setChecked(default)
            box.toggled.connect(self.schedule_update)
            vl.addWidget(box)
            self.toggles[key] = box
        self.controls.addWidget(view)

        results = QGroupBox(tr("At the observer's time"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("warning")
        self.banner.hide()
        self.display.addWidget(self.banner)
        self.plot = PlotWidget(self._draw, export_name="spacetime_diagram")
        self.display.addWidget(self.plot, 1)

        self.preset.presetChosen.connect(self._load_preset)
        for w in (self.om, self.ode):
            w.valueChanged.connect(lambda _v: (self.preset.set_key("custom"), self.schedule_update()))
        self.observe.valueChanged.connect(self.schedule_update)
        self.coords.currentIndexChanged.connect(self.schedule_update)
        self.preset.set_key("planck18")
        self.recompute()

    def _load_preset(self, key: str) -> None:
        c = PRESETS[key].cosmology
        self.om.setValue(min(max(c.Om0, 0.05), 1.0), emit=False)
        self.ode.setValue(min(max(c.Ode0, 0.0), 1.5), emit=False)
        self.recompute()

    def cosmology(self) -> Cosmology:
        return Cosmology(H0=67.66, Om0=self.om.value(), Ode0=self.ode.value(), Tcmb0=2.7255)

    # ------------------------------------------------------------ compute
    def recompute(self) -> None:
        c = self.cosmology()
        fate = c.fate()
        if fate in (Fate.BIG_CRUNCH, Fate.NO_BIG_BANG):
            self.banner.set_message("warning", f"This universe <b>{fate.value}</b>. The diagram needs a universe "
                                    "with a Big Bang that keeps expanding: lower Ωm or ΩΛ.")
            self.banner.show()
            self.data = None
            self.plot.refresh()
            return
        self.banner.hide()
        a_max = max(4.0, 1.6 * self.observe.value())
        a, t, chi = c.conformal_history(a_max=a_max, n=2500)
        if math.isfinite(c.event_horizon()):
            chi_inf = chi[-1] + c._conformal_integral(a_max, math.inf) * c.hubble_distance
        else:
            chi_inf = math.inf
        a_obs = self.observe.value()
        t_obs = float(np.interp(math.log(a_obs), np.log(a), t))
        chi_obs = float(np.interp(math.log(a_obs), np.log(a), chi))
        hubble = const.C / 1e3 / (c.H0 * np.sqrt(c.E2_of_a(a)))   # proper Mpc
        self.data = dict(c=c, a=a, t=t, chi=chi, chi_inf=chi_inf, a_obs=a_obs, t_obs=t_obs, chi_obs=chi_obs,
                         hubble=hubble)

        past = a <= a_obs
        cone = a[past] * (chi_obs - chi[past])
        i_max = int(np.argmax(cone))
        z_obs = 1 / a_obs - 1
        epoch = f"redshift {z_obs:.2f}" if a_obs < 0.995 else ("today" if a_obs < 1.005 else "future")
        event_now = (chi_inf - chi_obs) * a_obs if math.isfinite(chi_inf) else math.inf
        g = MPC_TO_GLY
        self.summary.setText(
            f"Scale factor a = <b>{a_obs:.2f}</b> ({epoch})<br>"
            f"Age of the universe: <b>{t_obs:.2f} Gyr</b><br>"
            f"Particle horizon: <b>{chi_obs * a_obs * g:.1f} billion ly</b> (proper)<br>"
            f"Event horizon: <b>{'none' if math.isinf(event_now) else format(event_now * g, '.1f') + ' billion ly'}</b><br>"
            f"Hubble sphere: <b>{float(np.interp(math.log(a_obs), np.log(a), hubble)) * g:.1f} billion ly</b><br>"
            f"Past light cone is widest at <b>{cone[i_max] * g:.1f} billion ly</b>, "
            f"when the universe was {t[past][i_max]:.1f} Gyr old (a = {a[past][i_max]:.2f})"
        )
        self.plot.refresh()

    # --------------------------------------------------------------- draw
    def _draw(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        d = self.data
        if d is None:
            ax.text(0.5, 0.5, "No diagram for this universe", ha="center", transform=ax.transAxes, color=p.text)
            return
        g = MPC_TO_GLY
        mode = self.coords.currentData()
        a, t, chi = d["a"], d["t"], d["chi"]
        if mode == "conformal":
            y = chi * g  # conformal time × c: billions of light-years travelled = billions of years
            ylabel = "Conformal time (billion years)"
        else:
            y = t
            ylabel = "Cosmic time (billion years)"

        def x_of(comoving):
            return (a * comoving if mode == "proper" else comoving) * g

        y_obs = d["chi_obs"] * g if mode == "conformal" else d["t_obs"]
        past = a <= d["a_obs"]
        future = a >= d["a_obs"]
        if self.toggles["galaxies"].isChecked():
            for gly in GALAXY_COMOVING_GLY:
                comoving = gly / g
                for sign in (1, -1):
                    ax.plot(sign * x_of(np.full_like(a, comoving)), y, color=p.border, linewidth=0.8)
        if self.toggles["hubble"].isChecked():
            hs = d["hubble"] if mode == "proper" else d["hubble"] / a
            for sign in (1, -1):
                ax.plot(sign * hs * g, y, color=p.series[2], linestyle="--", linewidth=1.6,
                        label="Hubble sphere" if sign > 0 else None)
        if self.toggles["particle"].isChecked():
            for sign in (1, -1):
                ax.plot(sign * x_of(chi), y, color=p.series[0], linewidth=1.8,
                        label="Particle horizon" if sign > 0 else None)
        if self.toggles["event"].isChecked() and math.isfinite(d["chi_inf"]):
            for sign in (1, -1):
                ax.plot(sign * x_of(d["chi_inf"] - chi), y, color=p.danger, linewidth=1.8,
                        label="Event horizon" if sign > 0 else None)
        if self.toggles["past"].isChecked():
            cone = d["chi_obs"] - chi[past]
            xs = (a[past] * cone if mode == "proper" else cone) * g
            ax.fill_betweenx(y[past], -xs, xs, color=p.accent2, alpha=0.15, linewidth=0)
            for sign in (1, -1):
                ax.plot(sign * xs, y[past], color=p.accent2, linewidth=2.2, label="Past light cone" if sign > 0 else None)
        if self.toggles["future"].isChecked():
            cone = chi[future] - d["chi_obs"]
            xs = (a[future] * cone if mode == "proper" else cone) * g
            for sign in (1, -1):
                ax.plot(sign * xs, y[future], color=p.series[4], linewidth=1.8,
                        label="Future light cone" if sign > 0 else None)
        ax.axhline(y_obs, color=p.muted, linestyle=":", linewidth=1)
        ax.scatter([0], [y_obs], color=p.success, zorder=5, s=40, label="Observer")
        top = y_obs * 2.2 if mode != "conformal" else y_obs * 1.8
        ax.set_ylim(0, min(top, float(y[-1])))
        visible = y <= ax.get_ylim()[1]
        span = float(np.max(x_of(chi)[visible])) if np.any(visible) else 50.0
        ax.set_xlim(-min(span, 80), min(span, 80))
        ax.set_xlabel(("Proper" if mode == "proper" else "Comoving") + " distance (billion light-years)")
        ax.set_ylabel(ylabel)
        ax.legend(loc="upper left", fontsize=8)
