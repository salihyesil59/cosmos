"""S1 — Cosmology Calculator."""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QGroupBox,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
)

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, InfoButton, ParameterSlider, PresetSelector, labelled_row
from cosmos.gui.widgets.plot import PlotWidget, write_csv
from cosmos.i18n import tr, tr_noop
from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology, Fate
from cosmos.physics.presets import PRESETS
from cosmos.physics.thermal import RELIC_NEUTRINO_RATIO

MPC_TO_GLY = const.MPC / const.LIGHT_YEAR / 1e9
C_KM_S = const.C / 1e3

EXPLANATIONS = {
    "age0": (
        tr_noop("Age of the universe today"),
        tr_noop("Time since the Big Bang until now, from integrating dt = da/(aH) over the whole expansion history."),
    ),
    "agez": (
        tr_noop("Age at redshift z"),
        tr_noop("How old the universe was when the light we see now left the object."),
    ),
    "lookback": (
        tr_noop("Lookback time"),
        tr_noop("How long the light has been travelling. Age today minus age at z."),
    ),
    "dc": (
        tr_noop("Comoving distance"),
        tr_noop("The distance to the object today, measured along the expanding grid. It is larger than the "
                "light-travel distance because space kept expanding while the light was on its way."),
    ),
    "dlt": (
        tr_noop("Light-travel distance"),
        tr_noop("Speed of light × lookback time. Often quoted in news reports, but it is not the object's actual "
                "distance at any single moment."),
    ),
    "dl": (
        tr_noop("Luminosity distance"),
        tr_noop("The distance you would infer from the object's brightness using the inverse-square law. It is "
                "(1 + z) times the comoving distance in a flat universe."),
    ),
    "da": (
        tr_noop("Angular diameter distance"),
        tr_noop("The distance you would infer from the object's apparent size. It is the comoving distance divided "
                "by (1 + z), and it shrinks again for very distant objects."),
    ),
    "vnow": (
        tr_noop("Recession velocity today"),
        tr_noop("How fast the distance to the object grows today, H0 × comoving distance, in units of the speed of "
                "light. Values above 1 are allowed: this is the stretching of space, not motion through space."),
    ),
    "vemit": (
        tr_noop("Recession velocity at emission"),
        tr_noop("How fast the distance was growing when the light was emitted: H(z) × proper distance at that time."),
    ),
    "ph": (
        tr_noop("Particle horizon today"),
        tr_noop("Radius of the observable universe: the comoving distance light has covered since the Big Bang."),
    ),
    "eh": (
        tr_noop("Event horizon today"),
        tr_noop("Light emitted today from beyond this distance will never reach us. Only accelerating universes have "
                "one."),
    ),
    "mu": (
        tr_noop("Distance modulus"),
        tr_noop("m − M = 5 log10(D_L / 10 pc): how many magnitudes fainter the object appears than it would at 10 pc."),
    ),
    "scale": (
        tr_noop("Scale at the object"),
        tr_noop("The physical size that covers one arcsecond on the sky at this redshift."),
    ),
    "hz": (
        tr_noop("Hubble parameter H(z)"),
        tr_noop("The expansion rate of the universe at the moment the light was emitted."),
    ),
    "a": (
        tr_noop("Scale factor a"),
        tr_noop("a = 1/(1 + z): the size of the universe at emission relative to today."),
    ),
    "tcmb": (
        tr_noop("CMB temperature at z"),
        tr_noop("T = T0 (1 + z): the temperature of the background radiation when the light was emitted."),
    ),
    "tnu": (
        tr_noop("Neutrino background temperature at z"),
        tr_noop("T_ν = (4/11)^(1/3) × T_CMB: relic neutrinos are colder because electron–positron annihilation heated "
                "only the photons."),
    ),
    "ok": (
        tr_noop("Curvature Ωk"),
        tr_noop("Ωk = 1 − Ωr − Ωm − ΩΛ. Zero means flat space, positive open, negative closed."),
    ),
    "rhoc": (
        tr_noop("Critical density today"),
        tr_noop("The density a flat universe needs for the chosen H0, shown also as hydrogen atoms per cubic metre."),
    ),
    "q0": (
        tr_noop("Deceleration parameter q0"),
        tr_noop("q0 < 0 means the expansion is accelerating today; q0 > 0 means it is slowing down."),
    ),
    "fate": (tr_noop("Fate of this universe"),
             tr_noop("Long-term behaviour determined from the Friedmann equation.")),
}


def fmt(value: float, digits: int = 4) -> str:
    """Format a number with ``digits`` significant figures and thin thousands separators."""
    if value is None or not math.isfinite(value):
        return "—"
    if value == 0:
        return "0"
    mag = abs(value)
    if mag >= 1e7 or mag < 1e-3:
        return f"{value:.{digits - 1}e}"
    decimals = max(0, digits - 1 - math.floor(math.log10(mag)))
    return f"{value:,.{decimals}f}".replace(",", " ")


class CalculatorSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.results: list[tuple[str, str, str]] = []

        # ------------------------------------------------------ controls
        model = QGroupBox(tr("1 · Cosmological model"))
        ml = QVBoxLayout(model)
        self.preset = PresetSelector()
        ml.addWidget(
            labelled_row(
                tr("Preset"),
                self.preset,
                (tr("Presets"), tr("Well-known sets of parameters. Planck 2018 is the current reference model.")),
            )
        )
        self.h0 = ParameterSlider(
            tr("H0 (km/s/Mpc)"), 40, 100, 67.66, decimals=2,
            info=(tr("Hubble constant"), tr("Today's expansion rate. Measurements give 67–73 km/s/Mpc.")),
        )
        self.om = ParameterSlider(
            tr("Ωm matter"), 0.0, 2.0, 0.3097, decimals=4, step=0.01,
            info=(tr("Matter density"), tr("Ordinary plus dark matter, as a fraction of the critical density.")),
        )
        self.ode = ParameterSlider(
            tr("ΩΛ dark energy"), -0.5, 2.0, 0.6889, decimals=4, step=0.01,
            info=(tr("Dark energy density"),
                  tr("Cosmological constant density as a fraction of the critical density.")),
        )
        self.flat = QCheckBox(tr("Keep space flat (sets ΩΛ automatically)"))
        self.flat.setToolTip(tr("When checked, ΩΛ is adjusted automatically so that space stays flat."))
        self.radiation = QCheckBox(tr("Include radiation (photons, neutrinos)"))
        self.radiation.setToolTip(tr("Radiation matters at very high redshift (z > 1000). Uncheck to see its effect."))
        for w in (self.h0, self.om, self.ode, self.flat, self.radiation):
            ml.addWidget(w)
        self.controls.addWidget(model)

        target = QGroupBox(tr("2 · Object"))
        tl = QVBoxLayout(target)
        self.z = ParameterSlider(
            tr("Redshift z"), 0.001, 1500, 1.0, decimals=3, log=True,
            info=(
                tr("Redshift"),
                tr("How much the light has been stretched. z ≈ 0.02 nearby galaxies, z ≈ 1–3 distant galaxies, "
                        "z ≈ 10 the first galaxies, z ≈ 1090 the CMB."),
            ),
        )
        tl.addWidget(self.z)
        quick = QVBoxLayout()
        for label, value in [
            (tr("Virgo cluster (z = 0.004)"), 0.004),
            (tr("Distant galaxy (z = 1)"), 1.0),
            (tr("Galaxy at cosmic noon (z = 2)"), 2.0),
            (tr("First galaxies (z = 10)"), 10.0),
            (tr("CMB (z = 1090)"), 1090.0),
        ]:
            btn = QPushButton(label)
            btn.setToolTip(tr("Set z = {z}").format(z=value))
            btn.clicked.connect(lambda _=False, v=value: self.z.setValue(v))
            quick.addWidget(btn)
        tl.addLayout(quick)
        self.controls.addWidget(target)

        export = QPushButton(tr("Export results (CSV)…"))
        export.clicked.connect(self._export_results)
        self.controls.addWidget(export)
        self.finish_controls()

        # ------------------------------------------------------- display
        self.banner = Banner("warning")
        self.banner.hide()
        self.display.addWidget(self.banner)
        split = QSplitter(Qt.Vertical)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Quantity", "Value"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.itemSelectionChanged.connect(self._explain_row)
        top = QTabWidget()
        top.addTab(self.table, tr("Results"))
        split.addWidget(top)
        self.explain = QLabel(tr("Click a row to see what the quantity means."))
        self.explain.setWordWrap(True)
        self.explain.setProperty("role", "muted")
        self.explain.setMinimumHeight(48)
        explain_box = QGroupBox(tr("What does this mean?"))
        el = QVBoxLayout(explain_box)
        el.addWidget(self.explain)
        el.addWidget(InfoButton(tr("Many distances"), (
            tr("In an expanding universe 'distance' is ambiguous: the object was closer when the light left, "
                    "and farther when it arrives. Astronomers therefore use several distance measures, each tied "
                    "to a way of observing.")
        )), 0, Qt.AlignRight)
        split.addWidget(explain_box)
        plots = QTabWidget()
        self.distance_plot = PlotWidget(self._draw_distances, csv_provider=self._curve_csv,
                                        export_name="distances_vs_z")
        self.age_plot = PlotWidget(self._draw_ages, csv_provider=self._curve_csv, export_name="age_vs_z")
        plots.addTab(self.distance_plot, tr("Distances vs redshift"))
        # "&" alone would become a keyboard accelerator and vanish from the tab.
        plots.addTab(self.age_plot, tr("Age & lookback time").replace("&", "&&"))
        split.addWidget(plots)
        split.setSizes([330, 90, 380])
        self.display.addWidget(split, 1)

        # ------------------------------------------------------- signals
        self.preset.presetChosen.connect(self._load_preset)
        self.h0.valueChanged.connect(self._params_changed)
        self.om.valueChanged.connect(self._params_changed)
        self.ode.valueChanged.connect(self._params_changed)
        self.flat.toggled.connect(self._params_changed)
        self.radiation.toggled.connect(self._params_changed)
        self.z.valueChanged.connect(self.schedule_update)

        self._loading = False
        self.preset.set_key("planck18", emit=True)
        self.cosmo = self._build()
        self.recompute()

    # -------------------------------------------------------------- model
    def _load_preset(self, key: str) -> None:
        c = PRESETS[key].cosmology
        self._loading = True
        self.h0.setValue(c.H0, emit=False)
        self.om.setValue(c.Om0, emit=False)
        self.ode.setValue(c.Ode0, emit=False)
        self.radiation.setChecked(c.Tcmb0 > 0)
        self.flat.setChecked(abs(c.Ok0) < 1e-6)
        self._loading = False
        self._preset_cosmo = c
        self._params_changed(from_preset=True)

    def _params_changed(self, *_args, from_preset: bool = False) -> None:
        if self._loading:
            return
        if not from_preset:
            self.preset.set_key("custom")
        self.ode.setEnabled(not self.flat.isChecked())
        if self.flat.isChecked():
            probe = self._build(ode=0.0)
            self.ode.setValue(1.0 - probe.Om0 - probe.Or0, emit=False)
        self.schedule_update()

    def _build(self, ode: float | None = None) -> Cosmology:
        base = PRESETS["planck18"].cosmology
        return Cosmology(
            H0=self.h0.value(),
            Om0=self.om.value(),
            Ode0=self.ode.value() if ode is None else ode,
            Ob0=min(base.Ob0, self.om.value()),
            Tcmb0=const.T_CMB if self.radiation.isChecked() else 0.0,
            name="Calculator",
        )

    # ------------------------------------------------------------ compute
    def state(self) -> dict:
        c = self.cosmo
        z = self.z.value()
        return {
            "z": z,
            "preset": self.preset.currentData(),
            "om": c.Om0,
            "ode": c.Ode0,
            "h0": c.H0,
            "age_gyr": float(c.age(0)) if c.has_big_bang() else float("nan"),
            "age_at_z_gyr": float(c.age(z)) if c.has_big_bang() else float("nan"),
        }

    def recompute(self) -> None:
        self.cosmo = c = self._build()
        z = self.z.value()
        big_bang = c.has_big_bang()
        if not big_bang:
            self.banner.set_message(
                "warning",
                tr("<b>This universe has no Big Bang.</b> Going back in time it never reaches zero size, so ages "
                       "are undefined. Reduce ΩΛ or increase Ωm."),
            )
            self.banner.show()
        else:
            self.banner.hide()

        age0 = c.age(0) if big_bang else math.nan
        agez = c.age(z) if big_bang else math.nan
        try:
            lookback = c.lookback_time(z)
            dc = c.comoving_distance(z)
            dm = c.transverse_comoving_distance(z)
        except Exception:  # integration through a forbidden region
            lookback = dc = dm = math.nan
        dl, da = (1 + z) * dm, dm / (1 + z)
        dlt = lookback * const.GYR * const.C / const.MPC
        rhoc = c.critical_density0
        q0 = float(c.deceleration_parameter(0))
        trend = tr("accelerating") if q0 < 0 else tr("decelerating")
        rows = [
            ("age0", tr("Age of the universe today"), self._time(age0)),
            ("agez", tr("Age at z = {z}").format(z=f"{z:g}"), self._time(agez)),
            ("lookback", tr("Lookback time"), self._time(lookback)),
            ("dc", tr("Comoving distance"), self._dist(dc)),
            ("dlt", tr("Light-travel distance"), self._dist(dlt)),
            ("dl", tr("Luminosity distance"), self._dist(dl)),
            ("da", tr("Angular diameter distance"), self._dist(da)),
            ("vnow", tr("Recession velocity today"), self._speed(c.H0 * dc / C_KM_S)),
            ("vemit", tr("Recession velocity at emission"), self._speed(float(c.H(z)) * dc / (1 + z) / C_KM_S)),
            ("mu", tr("Distance modulus m − M"),
             f"{fmt(5 * math.log10(dl) + 25 if dl > 0 else math.nan)} " + tr("mag")),
            ("scale", tr("Scale: 1 arcsec corresponds to"), f"{fmt(da * 1e3 * math.pi / 648000)} kpc"),
            ("hz", tr("Hubble parameter H(z)"), f"{fmt(float(c.H(z)))} km/s/Mpc"),
            ("a", tr("Scale factor a = 1/(1+z)"), fmt(1 / (1 + z))),
            ("tcmb", tr("CMB temperature at z"), f"{fmt(const.T_CMB * (1 + z))} K"),
            ("tnu", tr("Neutrino background temperature at z"),
             f"{fmt(RELIC_NEUTRINO_RATIO * const.T_CMB * (1 + z))} K"),
            ("ok", tr("Curvature Ωk"), f"{fmt(c.Ok0)}  ({physics(c.geometry)})"),
            ("ph", tr("Particle horizon today"), self._dist(c.particle_horizon())),
            ("eh", tr("Event horizon today"), self._dist(c.event_horizon()) if c.fate() is not Fate.BIG_CRUNCH
             else tr("not computed for recollapsing universes")),
            ("rhoc", tr("Critical density today"),
             tr("{density} kg/m³  (≈ {atoms} H atoms/m³)").format(
                 density=fmt(rhoc), atoms=f"{rhoc / const.M_PROTON:.2f}")),
            ("q0", tr("Deceleration parameter q0"), f"{fmt(q0)}  ({trend})"),
            ("fate", tr("Fate"), physics(c.fate().value)),
        ]
        self.results = rows
        selected = self.table.currentRow()
        self.table.setRowCount(len(rows))
        for i, (key, name, value) in enumerate(rows):
            name_item = QTableWidgetItem(name)
            name_item.setToolTip(tr(EXPLANATIONS[key][1]))
            name_item.setData(Qt.UserRole, key)
            value_item = QTableWidgetItem(value)
            value_item.setToolTip(tr(EXPLANATIONS[key][1]))
            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, value_item)
        if selected >= 0:
            self.table.selectRow(selected)
        self.distance_plot.refresh()
        self.age_plot.refresh()

    @staticmethod
    def _time(gyr: float) -> str:
        if not math.isfinite(gyr):
            return "—"
        if gyr < 1e-3:
            return f"{fmt(gyr * 1e9)} " + tr("years")
        if gyr < 1:
            return f"{fmt(gyr * 1e3)} " + tr("million years")
        return f"{fmt(gyr)} " + tr("billion years")

    @staticmethod
    def _speed(v_over_c: float) -> str:
        if not math.isfinite(v_over_c):
            return "—"
        note = tr("faster than light") if v_over_c > 1 else tr("slower than light")
        return f"{v_over_c:.3f} c  ({note})"

    @staticmethod
    def _dist(mpc: float) -> str:
        if math.isinf(mpc):
            return tr("infinite")
        if not math.isfinite(mpc):
            return "—"
        return tr("{mpc} Mpc  ({gly} billion ly)").format(mpc=fmt(mpc), gly=fmt(mpc * MPC_TO_GLY))

    def _explain_row(self) -> None:
        row = self.table.currentRow()
        if row < 0:
            return
        key = self.table.item(row, 0).data(Qt.UserRole)
        title, text = EXPLANATIONS[key]
        if key == "fate":
            text = self.cosmo.fate().explanation
        self.explain.setText(f"<b>{tr(title)}.</b> {physics(text) if key == 'fate' else tr(text)}")

    # -------------------------------------------------------------- plots
    def _z_grid(self):
        zmax = max(10.0, self.z.value() * 1.5)
        return np.logspace(-3, np.log10(zmax), 160)

    def _draw_distances(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        c, zg = self.cosmo, self._z_grid()
        try:
            dm = c.transverse_comoving_distance(zg)
        except Exception:
            ax.text(0.5, 0.5, "Distances undefined for this model", transform=ax.transAxes, ha="center", color=p.text)
            return
        ax.loglog(zg, dm * (1 + zg), color=p.series[1], label="Luminosity distance")
        ax.loglog(zg, c.comoving_distance(zg), color=p.series[0], label="Comoving distance")
        ax.loglog(zg, dm / (1 + zg), color=p.series[2], label="Angular diameter distance")
        ax.axvline(self.z.value(), color=p.muted, linestyle="--", linewidth=1)
        ax.set_xlabel("Redshift z")
        ax.set_ylabel("Distance (Mpc)")
        ax.legend(loc="upper left", fontsize=8)

    def _draw_ages(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        c, zg = self.cosmo, self._z_grid()
        ax.semilogx(zg, c.lookback_time(zg), color=p.series[0], label="Lookback time")
        if c.has_big_bang():
            ax.semilogx(zg, c.age(zg), color=p.series[1], label="Age of the universe at z")
            ax.axhline(c.age(0), color=p.muted, linestyle=":", linewidth=1)
        ax.axvline(self.z.value(), color=p.muted, linestyle="--", linewidth=1)
        ax.set_xlabel("Redshift z")
        ax.set_ylabel("Time (billion years)")
        ax.legend(loc="center right", fontsize=8)

    def _curve_csv(self):
        c, zg = self.cosmo, self._z_grid()
        dc = c.comoving_distance(zg)
        dm = c.transverse_comoving_distance(zg)
        age = c.age(zg) if c.has_big_bang() else np.full_like(zg, np.nan)
        rows = zip(zg, dc, dm * (1 + zg), dm / (1 + zg), c.lookback_time(zg), age)
        headers = ["z", "comoving_Mpc", "luminosity_Mpc", "angular_diameter_Mpc", "lookback_Gyr", "age_Gyr"]
        return headers, [[f"{v:.6g}" for v in r] for r in rows]

    def _export_results(self) -> None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self, "Export results", "cosmology_calculator.csv", "CSV file (*.csv)")
        if not path:
            return
        c = self.cosmo
        header_rows = [
            ["H0", c.H0], ["Om0", c.Om0], ["Ode0", c.Ode0], ["Or0", c.Or0], ["z", self.z.value()], [],
        ]
        write_csv(path, ["quantity", "value"], header_rows + [[name, value] for _k, name, value in self.results])
