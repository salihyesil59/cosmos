"""Reference page (G9): formula sheet, constants, units and model parameters."""

from __future__ import annotations

import math

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from cosmos.content.loader import load_formulas
from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.widgets.common import ParameterSlider, labelled_row, muted_label, placeholder, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.physics import constants as const
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Reference

Everything the course uses, collected in one place, so you never have to hunt
through the lessons for a formula or a number.

- **Formulas** — every important equation, grouped by topic, with the meaning of
  each symbol and a link to the lesson where it is derived. Use the search box
  to filter by name, symbol or topic.
- **Constants & units** — the physical constants of the engine and a converter
  between the units astronomers use.
- **Models** — the cosmological parameters of every preset in the app.
- **Data & methods** — which plots are real measurements and which the app
  generates itself, where every file came from, and how the physics is checked.

The same page is the fastest way to remind yourself what a symbol means while
you work in a simulator.
""")

CONSTANTS = [
    ("Speed of light", "c", const.C, "m/s"),
    ("Gravitational constant", "G", const.G, "m³ kg⁻¹ s⁻²"),
    ("Planck constant", "h", const.H_PLANCK, "J s"),
    ("Reduced Planck constant", "ħ", const.HBAR, "J s"),
    ("Boltzmann constant", "k_B", const.K_B, "J/K"),
    ("Stefan–Boltzmann constant", "σ", const.SIGMA_SB, "W m⁻² K⁻⁴"),
    ("Radiation constant", "a = 4σ/c", const.A_RAD, "J m⁻³ K⁻⁴"),
    ("Proton mass", "m_p", const.M_PROTON, "kg"),
    ("Electron volt", "eV", const.EV, "J"),
    ("Solar mass", "M_☉", const.M_SUN, "kg"),
    ("Astronomical unit", "AU", const.AU, "m"),
    ("Light-year", "ly", const.LIGHT_YEAR, "m"),
    ("Parsec", "pc", const.PARSEC, "m"),
    ("Megaparsec", "Mpc", const.MPC, "m"),
    ("Julian year", "yr", const.YEAR, "s"),
    ("CMB temperature today", "T₀", const.T_CMB, "K"),
    ("Effective neutrino species", "N_eff", const.NEFF, "—"),
    ("1 km/s/Mpc in SI", "—", const.KM_S_MPC_TO_SI, "1/s"),
]

# name: (unit, value of one unit in the base unit)
UNIT_FAMILIES = {
    "Length": ("m", [("metres", 1.0), ("kilometres", 1e3), ("Earth radii", 6.371e6),
                     ("astronomical units", const.AU), ("light-years", const.LIGHT_YEAR),
                     ("parsecs", const.PARSEC), ("kiloparsecs", const.KPC),
                     ("megaparsecs", const.MPC), ("gigaparsecs", const.GPC)]),
    "Time": ("s", [("seconds", 1.0), ("hours", 3600.0), ("days", 86400.0), ("years", const.YEAR),
                   ("million years", 1e6 * const.YEAR), ("billion years", const.GYR)]),
    "Mass": ("kg", [("kilograms", 1.0), ("Earth masses", 5.9722e24), ("solar masses", const.M_SUN),
                    ("Milky Ways (10¹² M☉)", 1e12 * const.M_SUN)]),
    "Energy": ("J", [("joules", 1.0), ("electron volts", const.EV), ("keV", 1e3 * const.EV),
                     ("MeV", 1e6 * const.EV), ("GeV", 1e9 * const.EV), ("TeV", 1e12 * const.EV),
                     ("kelvin (kT)", const.K_B)]),
    "Speed": ("m/s", [("metres per second", 1.0), ("kilometres per second", 1e3),
                      ("fractions of c", const.C)]),
    "Density": ("kg/m³", [("kilograms per m³", 1.0), ("protons per m³", const.M_PROTON),
                          ("solar masses per Mpc³", const.M_SUN / const.MPC**3),
                          ("critical densities today", 8.5e-27)]),
}


def _sci(value: float, digits: int = 6) -> str:
    if value == 0:
        return "0"
    if 1e-3 <= abs(value) < 1e5:
        return f"{value:.{digits}g}"
    exponent = math.floor(math.log10(abs(value)))
    return f"{value / 10**exponent:.{digits - 2}f} × 10<sup>{exponent}</sup>"


class UnitConverter(QGroupBox):
    """Type a number in one unit and read it in all the others."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Unit converter", parent)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.family = QComboBox()
        self.family.addItems(list(UNIT_FAMILIES))
        self.family.currentTextChanged.connect(self._family_changed)
        row.addWidget(labelled_row(tr("Quantity"), self.family, (
            "Quantity", "Choose what you are converting: a length, a time, a mass, an energy, a speed "
            "or a density.")), 1)
        self.unit = QComboBox()
        self.unit.currentIndexChanged.connect(self._update)
        row.addWidget(labelled_row(tr("Unit"), self.unit), 1)
        layout.addLayout(row)
        self.amount = ParameterSlider(
            "Amount", 1e-6, 1e6, 1.0, decimals=6, log=True,
            info=("Amount", "The slider is logarithmic; type an exact value in the box if you prefer."),
        )
        self.amount.valueChanged.connect(self._update)
        layout.addWidget(self.amount)
        self.result = QLabel()
        self.result.setTextFormat(Qt.RichText)
        self.result.setWordWrap(True)
        layout.addWidget(self.result)
        self._family_changed(self.family.currentText())

    def _family_changed(self, name: str) -> None:
        self.unit.blockSignals(True)
        self.unit.clear()
        self.unit.addItems([u for u, _ in UNIT_FAMILIES[name][1]])
        self.unit.blockSignals(False)
        self._update()

    def _update(self, *_args) -> None:
        base_unit, units = UNIT_FAMILIES[self.family.currentText()]
        index = max(self.unit.currentIndex(), 0)
        base = self.amount.value() * units[index][1]
        rows = "".join(
            f"<tr><td align='right'><b>{_sci(base / factor)}</b>&nbsp;</td><td>{name}</td></tr>"
            for name, factor in units
        )
        self.result.setText(f"<table>{rows}</table><br>"
                            + tr("In base units: {value} {unit}").format(value=_sci(base), unit=base_unit))


class ReferencePage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.formulas = load_formulas()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.addWidget(title_label(tr("Reference")))
        root.addWidget(muted_label(
            tr("{formulas} formulas, {constants} constants, unit conversions, the parameters of every model "
               "in the app, and where all of its data comes from.")
            .format(formulas=len(self.formulas), constants=len(CONSTANTS))))

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        # --- formulas
        formulas_tab = QWidget()
        fl = QVBoxLayout(formulas_tab)
        fl.setContentsMargins(0, 8, 0, 0)
        self.search = QLineEdit()
        placeholder(self.search, tr("Filter formulas…  (e.g. redshift, Friedmann, horizon, L4.3)"))
        self.search.setClearButtonEnabled(True)
        self.search.setToolTip(tr("Show only the formulas whose name, topic, symbols or lesson match."))
        self.search.textChanged.connect(self._render_formulas)
        fl.addWidget(self.search)
        self.formula_view = self._browser()
        fl.addWidget(self.formula_view, 1)
        self.tabs.addTab(formulas_tab, tr("Formulas"))

        # --- constants and units
        units_tab = QWidget()
        ul = QVBoxLayout(units_tab)
        ul.setContentsMargins(0, 8, 0, 0)
        self.converter = UnitConverter()
        self.converter.setMaximumWidth(640)
        ul.addWidget(self.converter, 0, Qt.AlignLeft)
        self.constants_view = self._browser()
        ul.addWidget(self.constants_view, 1)
        # "&" in a tab label would turn into a keyboard mnemonic.
        self.tabs.addTab(units_tab, tr("Constants && units"))

        # --- models
        self.models_view = self._browser()
        self.tabs.addTab(self.models_view, tr("Models"))

        # --- data and methods (V1)
        self.data_view = self._browser()
        self.tabs.addTab(self.data_view, tr("Data && methods"))

        # Drawn icons rather than symbols in the label: a sigma and a pair of scales
        # come out of whatever font is to hand, and the galaxy came out as a colour
        # emoji (D3). The names are left on the tab widget, so a theme change can
        # redraw them in its own colours.
        nav_icons.set_tab_glyphs(self.tabs, ("reference", "constants", "models", "data"))

        # Filled on the first visit (E12): rendering these needs matplotlib and the
        # physics engine, and nothing on the home page wants either.
        self._filled = False

    def refresh(self) -> None:
        """Render the sheet. Cheap after the first call."""
        if self._filled:
            return
        self._filled = True
        self.constants_view.set_markdown_content(self._constants_markdown())
        self.models_view.set_markdown_content(self._models_markdown())
        self.data_view.set_markdown_content(self._data_markdown())
        self._render_formulas()

    def _browser(self) -> RichBrowser:
        view = RichBrowser(font_pt=11.0)
        view.glossaryRequested.connect(self.ctx.signals.glossaryRequested)
        view.lessonRequested.connect(lambda i: self.ctx.navigate(f"lesson:{i}"))
        view.simulatorRequested.connect(lambda s: self.ctx.navigate(f"sim:{s}"))
        view.routeRequested.connect(self.ctx.navigate)
        return view

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    def open_target(self, target: str) -> None:
        """Handle the part after ``reference:`` — a tab name, or a formula to show."""
        if target == "data":
            self.tabs.setCurrentWidget(self.data_view)
            return
        self.show_formula(target)

    def show_data(self) -> None:
        self.tabs.setCurrentWidget(self.data_view)

    def show_formula(self, formula_id: str) -> None:
        """Open the Formulas tab filtered down to one entry (used by search results)."""
        match = next((f for f in self.formulas if f.id == formula_id), None)
        if match is None:
            return
        self.tabs.setCurrentIndex(0)
        self.search.setText(match.title)

    # ------------------------------------------------------------ content
    def matching_formulas(self, needle: str = "") -> list:
        needle = needle.strip().lower()
        if not needle:
            return list(self.formulas)
        return [
            f for f in self.formulas
            if needle in " ".join([f.title, f.group, f.symbols, f.description, f.formula,
                                   f.lesson or ""]).lower()
        ]

    def _render_formulas(self, *_args) -> None:
        found = self.matching_formulas(self.search.text())
        lines = ["# Formula sheet", ""]
        if not found:
            lines += ["No formula matches your search. Try a shorter word, or a lesson id such as `L2.3`."]
        current_group = None
        lessons = self.ctx.curriculum.lessons
        for f in found:
            if f.group != current_group:
                current_group = f.group
                lines += ["", f"## {f.group}", ""]
            lines += [f"### {f.title}", "", f"$${f.formula}$$", ""]
            if f.symbols:
                lines += [f"{f.symbols}", ""]
            if f.description:
                lines += [f"{f.description}", ""]
            if f.lesson in lessons:
                lines += [f"→ [{f.lesson} {lessons[f.lesson].title}](lesson:{f.lesson})", ""]
        self.formula_view.set_markdown_content("\n".join(lines))

    def _constants_markdown(self) -> str:
        lines = ["# Constants", "",
                 "The values used by the physics engine (CODATA 2018 and IAU resolutions).", "",
                 "| Quantity | Symbol | Value | Unit |", "|---|---|---|---|"]
        for name, symbol, value, unit in CONSTANTS:
            lines.append(f"| {name} | {symbol} | {_sci(value)} | {unit} |")
        lines += [
            "", "## Handy conversions", "",
            "| From | To |", "|---|---|",
            f"| 1 parsec | {const.PARSEC / const.LIGHT_YEAR:.3f} light-years |",
            f"| 1 megaparsec | {const.MPC / const.LIGHT_YEAR / 1e6:.3f} million light-years |",
            f"| 1 light-year | {const.LIGHT_YEAR:.4g} m |",
            "| 1 km/s/Mpc | 1 / (978 billion years) |",
            f"| kT = 1 eV | {const.EV / const.K_B:.4g} K |",
            f"| kT = 1 MeV | {1e6 * const.EV / const.K_B:.4g} K |",
            f"| 1 solar mass | {const.M_SUN:.4g} kg |",
            "| 1 Jansky | 10⁻²⁶ W m⁻² Hz⁻¹ |",
            "", "## Rules of thumb", "",
            "- The Hubble time 1/H₀ ≈ 14 billion years, close to the true age of 13.8.",
            "- The Hubble length c/H₀ ≈ 4 300 Mpc ≈ 14 billion light-years; the observable "
            "universe reaches about 46 billion light-years.",
            "- The critical density is about five hydrogen atoms per cubic metre.",
            "- A temperature in kelvin becomes an energy in eV when divided by 11 600.",
            "- The CMB was released at z ≈ 1090, when the universe was 380 000 years old.",
        ]
        return "\n".join(lines)

    def _models_markdown(self) -> str:
        lines = ["# Cosmological models", "",
                 "Every preset available in the simulators. Ωk = 1 − Ωm − ΩΛ; a negative Ωk means "
                 "a closed universe.", "",
                 "| Model | H₀ | Ωm | ΩΛ | Ωb | Ωk | w₀, wa | Age (Gyr) |", "|---|---|---|---|---|---|---|---|"]
        from cosmos.physics.presets import PRESETS   # E12: numpy and scipy, on demand

        for preset in PRESETS.values():
            c = preset.cosmology
            omega_k = 1 - c.Om0 - c.Ode0
            w = f"{c.w0:g}, {c.wa:g}" if (c.w0 != -1 or c.wa != 0) else "−1, 0"
            try:
                age = f"{c.age():.2f}"
            except (ValueError, ZeroDivisionError):
                age = "—"
            lines.append(f"| {preset.label} | {c.H0:g} | {c.Om0:g} | {c.Ode0:g} | {c.Ob0:g} | "
                         f"{omega_k:+.3f} | {w} | {age} |")
        lines += ["", "## What the presets mean", ""]
        from cosmos.physics.presets import PRESETS   # E12: numpy and scipy, on demand

        for preset in PRESETS.values():
            lines.append(f"- **{preset.label}** — {preset.description}")
        lines += ["", "Open the [Cosmology Calculator](sim:S1) or "
                  "[Build Your Own Universe](sim:S18) to experiment with these numbers."]
        return "\n".join(lines)

    def _validation_markdown(self) -> list[str]:
        """V4: the engine's report card, with the numbers rather than the claim."""
        from cosmos import validation

        # The numbers are read, not recomputed. Running the checks here cost 2.8
        # seconds every time this page was opened for the first time, and bought
        # nothing: the astropy half cannot run in a packaged build at all, and a
        # test compares the record with a fresh run on every change.
        record = validation.read_record()
        if record is None:
            return ["## How the physics is checked", "",
                    "The checks have not been recorded in this copy. Run "
                    "`python tools/record_validation.py` to fill them in.", ""]
        rows_by_kind: dict[str, list[str]] = {}
        for check in validation.CHECKS:
            worst = record["worst"].get(check.id)
            shown = check.format(worst) if worst is not None else "not recorded"
            rows_by_kind.setdefault(check.against, []).append(
                f"| {check.quantity} | {check.reference} | {shown} | "
                f"{check.format(check.tolerance)} |")

        lines = [
            "## How the physics is checked", "",
            "The engine is not trusted because it looks right. Every quantity below is "
            "computed twice — once here, once by something that had nothing to do with "
            "this app — and the third column is the largest disagreement found anywhere "
            "in the range tested. The fourth is the most that would be accepted before "
            "the test suite fails, on Linux and on Windows, on every change.", "",
        ]
        headings = {
            validation.AGAINST_ASTROPY:
                ("Against another implementation",
                 "[astropy](https://www.astropy.org/) is the standard astronomy library "
                 "for Python, written by other people from the same equations. Agreement "
                 "at this level means the two codes are doing the same arithmetic."),
            validation.AGAINST_CLOSED_FORM:
                ("Against mathematics",
                 "Some universes can be solved with a pen. Those solutions are exact, so "
                 "any disagreement is the numerical method's own error and nothing else."),
            validation.AGAINST_PUBLISHED:
                ("Against published measurements",
                 "Here the tolerance is the published uncertainty rather than the "
                 "engine's: the app is being asked to land on a number the field agrees "
                 "on, not to reproduce it exactly."),
        }
        for kind, (title, blurb) in headings.items():
            lines += [f"### {title}", "", blurb, "",
                      "| Quantity | Compared with | Worst disagreement | Allowed |",
                      "|---|---|---|---|", *rows_by_kind.get(kind, []), ""]

        lines += [
            f"Measured on {record['measured']} and shipped with the app. The comparisons "
            "against astropy cannot be repeated inside a packaged build — astropy is a "
            "development dependency and is not included — so they are run where it is "
            "installed and the results travel with the app. A test repeats every one of "
            "them against a fresh run on every change, so what you see here cannot "
            "quietly go stale. `python tools/record_validation.py` repeats them for "
            "yourself.", "",
        ]
        lines += [
            "Alongside these, the suite opens every page, every lesson and every "
            "simulator, checks that this data list still matches the files in "
            "`cosmos/data`, and checks that no figure drawing invented data forgets to "
            "say so. A packaged build runs its own `--selftest` before it is published.", "",
        ]
        return lines

    def _data_markdown(self) -> str:
        """V1: every source the app plots, real and invented, in one place."""
        from cosmos import provenance
        from cosmos.gui.simulators.registry import SIMULATORS

        def links(ids: tuple[str, ...]) -> str:
            named = [f"[{i} {tr(SIMULATORS[i].title)}](sim:{i})" for i in ids if i in SIMULATORS]
            return ", ".join(named)

        real, made = provenance.MEASUREMENTS, provenance.GENERATED
        lines = [
            "# Data and methods", "",
            f"The app plots two different kinds of thing. **{len(real)} files of real "
            f"measurements** are bundled with it, so that the course works without a "
            f"network; everything else it works out or invents as you go. Each plot says "
            f"which it is showing. This page says where each one came from.", "",
            "## Real measurements", "",
            "These are other people's work, redistributed so the course runs offline. If "
            "you use them for anything beyond learning, cite the papers, not this app.", "",
        ]
        for m in real:
            # A list rather than a table: a two-column table needs a header row, and an
            # empty one draws a blank band across the page.
            lines += [f"### {m.title}", "", f"`cosmos/data/{m.file}`", "", m.holds, "",
                      f"- **Source** — [{m.archive}]({m.url})",
                      f"- **Retrieved** — {m.retrieved}",
                      f"- **Cite** — {m.cite}",
                      f"- **Terms** — {m.terms}", ""]
            if m.prepared:
                lines += [f"**Prepared for the app.** {m.prepared}", ""]
            if m.caveat:
                lines += [f"**What it does not claim.** {m.caveat}", ""]
            where = links(m.used_by)
            if m.figures:
                where = f"{where} · {m.figures}" if where else m.figures
            if where:
                lines += [f"Used by {where}", ""]

        lines += [
            "## Data the app generates", "",
            "None of the following was measured by anyone. It is drawn, simulated or "
            "modelled inside the app to show how a measurement behaves, and it says so "
            "where it is shown — in the title of the figure, in the note beside the "
            "control that produced it, and in anything you export.", "",
        ]
        for g in made:
            lines += [f"### {g.title}", "", g.holds, "", g.how, ""]
            where = links(g.shown_in)
            if g.figures:
                where = f"{where} · {g.figures}" if where else g.figures
            if where:
                lines += [f"Shown in {where}", ""]
            lines += [f"Generated by `{g.module}`.", ""]

        lines += [
            *self._validation_markdown(),
            "## What leaves with a file", "",
            "Save a plot and the picture carries a caption under it: the app and its "
            "version, which simulator drew it, whether what you are looking at was "
            "measured or generated, the sample or the model behind it, and the date. The "
            "same text goes into the image's metadata, where a program can read it. "
            "Export a table and it sits above the numbers as comment lines, which a "
            "spreadsheet ignores and a reader does not. A figure that ends up in someone "
            "else's slide deck should not need this page to be understood.", "",
            "## Where this list lives", "",
            "`cosmos/provenance.py` in the source, beside the code that loads the files, "
            "so the two cannot drift apart. The licence terms are in `NOTICE`, and "
            "`cosmos/data/external/README.md` carries the same record with the data "
            "itself, for anyone who takes the files without the app.", "",
        ]
        return "\n".join(lines)
