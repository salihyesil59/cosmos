"""The history of the universe as a function of cosmic time.

After about one second the Planck 2018 ΛCDM model is used directly. Earlier, the
standard radiation-era relation t = 2.42 g*^(-1/2) (MeV/T)² s is used with a
stepwise number of relativistic degrees of freedom g*, which is accurate to tens
of percent. Before about 10⁻¹² s the physics is unknown or speculative.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np
from scipy import optimize

from cosmos.physics import constants as const
from cosmos.physics.presets import PRESETS

SECOND = 1.0
YEAR_S = const.YEAR
T_PLANCK_S = 5.39e-44
T_MIN_S = 1e-45
T_MAX_S = 1e12 * YEAR_S
MEV_TO_K = 1e6 * const.EV / const.K_B


@dataclass(frozen=True)
class Epoch:
    name: str
    start_s: float
    end_s: float | None
    description: str
    status: str          # "speculative", "theory", "tested", "observed"
    lesson: str | None = None


EPOCHS: list[Epoch] = [
    Epoch("Planck era", T_MIN_S, 5.4e-44,
          "Quantum gravity is important; general relativity and quantum mechanics cannot be combined yet.",
          "speculative", "L6.8"),
    Epoch("Grand unification", 5.4e-44, 1e-36,
          "The strong, weak and electromagnetic forces may have been a single force.", "speculative", "L6.8"),
    Epoch("Inflation (hypothesis)", 1e-36, 1e-32,
          "A brief accelerated expansion stretches the universe flat and creates the seeds of structure.",
          "theory", "L6.3"),
    Epoch("Reheating", 1e-32, 1e-30,
          "The inflaton decays into hot particles: the hot Big Bang begins.", "theory", "L6.3"),
    Epoch("Baryogenesis", 1e-30, 1e-11,
          "An unknown process creates one extra quark per billion quark–antiquark pairs.", "speculative", "L4.6"),
    Epoch("Electroweak transition", 1e-12, 1e-11,
          "The Higgs field switches on and particles acquire mass (energies tested at the LHC).", "tested", "L4.1"),
    Epoch("Quark–hadron transition", 1e-5, 2e-5,
          "Quarks and gluons bind into protons and neutrons.", "tested", "L4.1"),
    Epoch("Neutrino decoupling", 1.0, None,
          "Neutrinos stop interacting and stream freely: the cosmic neutrino background.", "tested", "L4.5"),
    Epoch("Electron–positron annihilation", 3.0, 30.0,
          "Most electrons and positrons annihilate and heat the photons.", "tested", "L4.5"),
    Epoch("Big Bang nucleosynthesis", 60.0, 1200.0,
          "Deuterium, helium-3, helium-4 and a little lithium form.", "observed", "L4.3"),
    Epoch("Matter–radiation equality", 5.1e4 * YEAR_S, None,
          "Matter becomes the dominant component; structure begins to grow efficiently.", "observed", "L3.1"),
    Epoch("Recombination and the CMB", 3.7e5 * YEAR_S, None,
          "Neutral atoms form, the universe becomes transparent and the CMB is released.", "observed", "L4.4"),
    Epoch("Dark ages", 3.8e5 * YEAR_S, 1.5e8 * YEAR_S,
          "Neutral gas and dark matter, but no stars yet.", "observed", "L6.4"),
    Epoch("First stars (cosmic dawn)", 1.5e8 * YEAR_S, None,
          "Gas cools in small dark matter halos and the first stars ignite.", "theory", "L6.4"),
    Epoch("Reionisation", 3e8 * YEAR_S, 1e9 * YEAR_S,
          "Ultraviolet light from galaxies ionises the intergalactic hydrogen again.", "observed", "L6.4"),
    Epoch("Cosmic noon", 2.5e9 * YEAR_S, 4e9 * YEAR_S,
          "Star formation and black hole growth reach their peak.", "observed", "L1.4"),
    Epoch("Acceleration begins", 7.7e9 * YEAR_S, None,
          "Dark energy starts to dominate the dynamics; the expansion speeds up.", "observed", "L3.3"),
    Epoch("Sun and Earth form", 9.2e9 * YEAR_S, None,
          "A cloud of gas enriched by earlier generations of stars collapses into the Solar System.",
          "observed", None),
    Epoch("Today", 13.8e9 * YEAR_S, None, "You are here.", "observed", None),
    Epoch("The Sun becomes a red giant", 18.8e9 * YEAR_S, None,
          "About 5 billion years from now the Sun swells and later becomes a white dwarf.", "theory", None),
    Epoch("Other galaxies disappear from view", 1.5e11 * YEAR_S, None,
          "Accelerating expansion carries all galaxies beyond the merged Local Group out of sight.",
          "theory", "L2.6"),
]


# Relativistic degrees of freedom g*(T): smooth steps at the electroweak transition, the quark–hadron
# transition and electron–positron annihilation (temperature in MeV, change in g*, log width).
_G_STAR_STEPS = [(1e5, 45.0, 0.3), (150.0, 51.0, 0.3), (0.3, 7.39, 0.5)]
_G_STAR_LOW = 3.36


def g_star(temperature_mev: float) -> float:
    lt = math.log(temperature_mev)
    return _G_STAR_LOW + sum(dg * 0.5 * (1 + math.tanh((lt - math.log(tc)) / w)) for tc, dg, w in _G_STAR_STEPS)


def early_temperature_mev(time_s: float) -> float:
    """Radiation-era temperature from t = 2.42 g*^(-1/2) (MeV/T)² s."""
    t = max(time_s, T_MIN_S)
    target = math.log(2.42 / t)
    # g* grows with T, so the left-hand side increases monotonically with ln T.
    root = optimize.brentq(lambda lt: 0.5 * math.log(g_star(math.exp(lt))) + 2 * lt - target, -30.0, 80.0)
    return math.exp(root)


class Timeline:
    """Temperature, scale factor and composition at any cosmic time."""

    BLEND_START_S = 1.0
    BLEND_END_S = 30.0

    def __init__(self):
        c = self.cosmo = PRESETS["planck18"].cosmology
        # Tabulate t(a) and the comoving horizon from deep in the radiation era, integrating in ln a.
        a = np.logspace(-11, math.log10(200.0), 8000)
        h0 = c.H0_si
        e = np.sqrt(c.E2_of_a(a))
        lna = np.log(a)
        dt = 1 / (h0 * e)
        dchi = const.C / (a * h0 * e) / const.MPC
        t = np.concatenate([[0.0], np.cumsum(0.5 * (dt[1:] + dt[:-1]) * np.diff(lna))])
        chi = np.concatenate([[0.0], np.cumsum(0.5 * (dchi[1:] + dchi[:-1]) * np.diff(lna))])
        sqrt_or = math.sqrt(c.Or0)
        t += a[0] ** 2 / (2 * h0 * sqrt_or)                       # radiation-era start
        chi += const.C * a[0] / (h0 * sqrt_or) / const.MPC
        self._log_a = lna
        self._log_t = np.log(t)
        self._chi = chi
        self.age_s = float(c.age()) * 1e9 * YEAR_S
        self._h_lambda = c.H0_si * math.sqrt(c.Ode0)
        self._t_end = float(np.exp(self._log_t[-1]))

    # ------------------------------------------------------------ state
    def _model_scale_factor(self, time_s: float) -> float:
        if time_s > self._t_end:
            return float(np.exp(self._log_a[-1] + self._h_lambda * (time_s - self._t_end)))
        return float(np.exp(np.interp(math.log(time_s), self._log_t, self._log_a)))

    def scale_factor(self, time_s: float) -> float:
        return const.T_CMB / self.temperature_k(time_s)

    def temperature_k(self, time_s: float) -> float:
        """Temperature of the photons."""
        early = early_temperature_mev(time_s) * MEV_TO_K
        if time_s <= self.BLEND_START_S:
            return early
        late = const.T_CMB / self._model_scale_factor(time_s)
        if time_s >= self.BLEND_END_S:
            return late
        # Electron–positron annihilation: interpolate smoothly between the two regimes.
        w = math.log(time_s / self.BLEND_START_S) / math.log(self.BLEND_END_S / self.BLEND_START_S)
        return math.exp((1 - w) * math.log(early) + w * math.log(late))

    def particle_horizon_m(self, time_s: float) -> float:
        if time_s < 1.0:
            return 2 * const.C * time_s  # radiation era: d_p = 2ct
        if time_s > self._t_end:
            return math.inf
        chi = float(np.interp(math.log(time_s), self._log_t, self._chi))
        return chi * const.MPC * self.scale_factor(time_s)

    def composition(self, time_s: float) -> dict[str, float]:
        a = self.scale_factor(time_s)
        c = self.cosmo
        parts = {"radiation": c.Or0 * a**-4, "matter": c.Om0 * a**-3, "dark energy": c.Ode0}
        total = sum(parts.values())
        return {k: v / total for k, v in parts.items()}

    def dominant(self, time_s: float) -> str:
        comp = self.composition(time_s)
        return max(comp, key=comp.get)

    def density_kg_m3(self, time_s: float) -> float:
        """Total energy density divided by c² (the critical density in a flat universe)."""
        a = self.scale_factor(time_s)
        c = self.cosmo
        if time_s < 1.0:
            # ρ = 3/(32πG t²) during radiation domination.
            return 3 / (32 * math.pi * const.G * time_s**2)
        return float(c.critical_density0 * (c.Or0 * a**-4 + c.Om0 * a**-3 + c.Ode0))

    def epochs_at(self, time_s: float) -> list[Epoch]:
        """Epochs in progress at this time (or point events within a factor 1.5)."""
        active = []
        for ep in EPOCHS:
            if ep.end_s is None:
                if ep.start_s / 1.25 <= time_s <= ep.start_s * 1.25:
                    active.append(ep)
            elif ep.start_s <= time_s <= ep.end_s:
                active.append(ep)
        return active


_SUPERSCRIPT = str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹")


def format_time(time_s: float, unit: Callable[[str], str] = str) -> str:
    """A readable time span. ``unit`` translates the unit word for the interface."""
    if time_s < 1e-3:
        exponent = math.floor(math.log10(time_s))
        return f"{time_s / 10**exponent:.1f} × 10{str(exponent).translate(_SUPERSCRIPT)} {unit('s')}"
    if time_s < 120:
        return f"{time_s:.3g} {unit('s')}"
    if time_s < 2 * 3600:
        return f"{time_s / 60:.3g} {unit('minutes')}"
    if time_s < 2 * 86400:
        return f"{time_s / 3600:.3g} {unit('hours')}"
    years = time_s / YEAR_S
    if years < 1:
        return f"{time_s / 86400:.3g} {unit('days')}"
    if years < 1e6:
        return f"{years:,.0f}".replace(",", " ") + f" {unit('years')}"
    if years < 1e9:
        return f"{years / 1e6:.3g} {unit('million years')}"
    return f"{years / 1e9:.3g} {unit('billion years')}"
