"""Single-field slow-roll inflation.

Units: reduced Planck mass M_Pl = (8πG)^(-1/2) = 1, so the field φ is measured in
units of M_Pl ≈ 2.435 × 10¹⁸ GeV and energy densities in M_Pl⁴.

Slow-roll parameters (potential form):

    ε = ½ (V'/V)²,   η = V''/V,   N = ∫ V/V' dφ

Predictions at the moment the observed scales left the horizon, N* e-folds
before the end of inflation:

    n_s = 1 − 6ε + 2η,   r = 16ε,   A_s = V / (24π² ε)
"""

from __future__ import annotations

import functools
import math
import warnings
from dataclasses import dataclass

import numpy as np
from scipy import integrate, optimize

M_PLANCK_GEV = 2.435e18
A_S_PLANCK = 2.1e-9

# Observational constraints (Planck 2018 + BICEP/Keck 2021).
N_S_MEASURED = 0.9649
N_S_ERROR = 0.0042
R_UPPER_LIMIT = 0.036


@dataclass(frozen=True)
class Potential:
    key: str
    label: str
    description: str
    parameter_label: str = ""
    parameter_default: float = 0.0
    parameter_range: tuple[float, float] = (0.0, 1.0)

    # Shape functions with unit amplitude; the amplitude is fixed by A_s.
    def v(self, phi, p):
        return _SHAPES[self.key][0](np.asarray(phi, dtype=float), p)

    def dv(self, phi, p):
        return _SHAPES[self.key][1](np.asarray(phi, dtype=float), p)

    def d2v(self, phi, p):
        return _SHAPES[self.key][2](np.asarray(phi, dtype=float), p)


_B = math.sqrt(2.0 / 3.0)


_SHAPES = {
    "quadratic": (lambda f, p: 0.5 * f * f, lambda f, p: f, lambda f, p: np.ones_like(f)),
    "quartic": (lambda f, p: 0.25 * f**4, lambda f, p: f**3, lambda f, p: 3 * f * f),
    "starobinsky": (
        lambda f, p: (1 - np.exp(-_B * f)) ** 2,
        lambda f, p: 2 * _B * np.exp(-_B * f) * (1 - np.exp(-_B * f)),
        lambda f, p: 2 * _B * _B * np.exp(-_B * f) * (2 * np.exp(-_B * f) - 1),
    ),
    "natural": (
        lambda f, p: 1 + np.cos(f / p),
        lambda f, p: -np.sin(f / p) / p,
        lambda f, p: -np.cos(f / p) / (p * p),
    ),
    "hilltop": (
        lambda f, p: 1 - (f / p) ** 4,
        lambda f, p: -4 * f**3 / p**4,
        lambda f, p: -12 * f * f / p**4,
    ),
}

POTENTIALS: dict[str, Potential] = {
    pot.key: pot
    for pot in [
        Potential("quadratic", "Quadratic  V ∝ φ²",
                  "The simplest model: a massive field rolling down a parabola. Predicts too many "
                  "gravitational waves and is now ruled out."),
        Potential("quartic", "Quartic  V ∝ φ⁴",
                  "A self-interacting field. Predicts even larger gravitational waves and a too-red "
                  "spectrum; ruled out."),
        Potential("starobinsky", "Starobinsky (R²)  V ∝ (1 − e^(−√(2/3) φ))²",
                  "Proposed by Alexei Starobinsky in 1980 as a modification of gravity. A long, flat "
                  "plateau gives n_s ≈ 0.965 and tiny r: an excellent fit to the data."),
        Potential("natural", "Natural inflation  V ∝ 1 + cos(φ/f)",
                  "An axion-like field with a periodic potential. The decay constant f sets how flat "
                  "the top is.", "Decay constant f (M_Pl)", 7.0, (2.0, 20.0)),
        Potential("hilltop", "Hilltop  V ∝ 1 − (φ/μ)⁴",
                  "The field starts near the top of a hill and rolls away. The scale μ controls the "
                  "predictions.", "Scale μ (M_Pl)", 15.0, (5.0, 40.0)),
    ]
}


@dataclass(frozen=True)
class SlowRollResult:
    phi_star: float
    phi_end: float
    epsilon: float
    eta: float
    n_s: float
    r: float
    amplitude: float           # V0 such that A_s matches Planck
    energy_scale_gev: float    # V*^(1/4)
    hubble_gev: float          # H during inflation at φ*

    @property
    def consistent(self) -> bool:
        return abs(self.n_s - N_S_MEASURED) < 2 * N_S_ERROR and self.r < R_UPPER_LIMIT


def _field_range(pot: Potential, p: float) -> tuple[float, float, int]:
    """Return (φ at the potential minimum side, far field value, rolling direction)."""
    if pot.key == "natural":
        return math.pi * p, 1e-4 * p, +1   # rolls from near the top (φ ≈ 0) towards φ = πf
    if pot.key == "hilltop":
        return p, 1e-6 * p, +1             # rolls away from the top at φ = 0
    return 0.0, 60.0, -1                  # large-field models roll towards φ = 0


def epsilon(pot: Potential, phi, p: float):
    with np.errstate(divide="ignore", invalid="ignore"):
        return 0.5 * (pot.dv(phi, p) / pot.v(phi, p)) ** 2


def eta(pot: Potential, phi, p: float):
    with np.errstate(divide="ignore", invalid="ignore"):
        return pot.d2v(phi, p) / pot.v(phi, p)


def end_of_inflation(pot: Potential, p: float = 0.0) -> float:
    """Field value where ε = 1."""
    bottom, far, direction = _field_range(pot, p)
    if pot.key == "quadratic":
        return math.sqrt(2.0)
    if pot.key == "quartic":
        return math.sqrt(8.0)
    grid = np.linspace(far, bottom, 20000) if direction > 0 else np.linspace(far, bottom + 1e-6, 20000)
    eps = epsilon(pot, grid, p)
    idx = np.argmax(eps >= 1.0)
    if eps[idx] < 1.0:
        return float(grid[-1])
    lo, hi = grid[max(idx - 1, 0)], grid[idx]
    return float(optimize.brentq(lambda f: float(epsilon(pot, f, p)) - 1.0, lo, hi))


def efolds(pot: Potential, phi: float, p: float = 0.0) -> float:
    """Number of e-folds from φ to the end of inflation (slow-roll approximation)."""
    phi_end = end_of_inflation(pot, p)
    with warnings.catch_warnings():
        # Near a hilltop V/V' diverges; the root finder only needs a rough value there.
        warnings.simplefilter("ignore", integrate.IntegrationWarning)
        val, _ = integrate.quad(lambda f: float(pot.v(f, p) / pot.dv(f, p)), phi_end, phi, limit=200)
    return abs(val)


def field_at_efolds(pot: Potential, n_star: float, p: float = 0.0) -> float:
    phi_end = end_of_inflation(pot, p)
    bottom, far, direction = _field_range(pot, p)
    if direction < 0:
        return float(optimize.brentq(lambda f: efolds(pot, f, p) - n_star, phi_end + 1e-6, far))
    return float(optimize.brentq(lambda f: efolds(pot, f, p) - n_star, far, phi_end - 1e-9))


@functools.lru_cache(maxsize=256)
def predictions(pot: Potential, n_star: float = 55.0, p: float | None = None) -> SlowRollResult:
    p = pot.parameter_default if p is None else p
    phi_star = field_at_efolds(pot, n_star, p)
    eps = float(epsilon(pot, phi_star, p))
    et = float(eta(pot, phi_star, p))
    shape = float(pot.v(phi_star, p))
    # A_s = V / (24 π² ε) with V = V0 · shape.
    v0 = A_S_PLANCK * 24 * math.pi**2 * eps / shape
    v_star = v0 * shape
    return SlowRollResult(
        phi_star=phi_star,
        phi_end=end_of_inflation(pot, p),
        epsilon=eps,
        eta=et,
        n_s=1 - 6 * eps + 2 * et,
        r=16 * eps,
        amplitude=v0,
        energy_scale_gev=v_star**0.25 * M_PLANCK_GEV,
        hubble_gev=math.sqrt(v_star / 3) * M_PLANCK_GEV,
    )


@dataclass(frozen=True)
class Trajectory:
    efolds: np.ndarray     # ln a since the start
    phi: np.ndarray
    phi_dot: np.ndarray
    hubble: np.ndarray
    epsilon_h: np.ndarray  # −Ḣ/H², inflation while < 1
    end_efold: float       # N at which inflation ends (ε_H = 1)


def evolve(pot: Potential, p: float | None = None, n_before: float = 65.0, extra: float = 3.0) -> Trajectory:
    """Solve the full field equation φ̈ + 3Hφ̇ + V' = 0 with ln a as the time variable.

    Starts ``n_before`` slow-roll e-folds before the end and continues ``extra``
    e-folds into the oscillation (reheating) phase.
    """
    p = pot.parameter_default if p is None else p
    res = predictions(pot, 55.0, p)
    v0 = res.amplitude
    phi0 = field_at_efolds(pot, n_before, p)

    def v(f):
        return v0 * float(pot.v(f, p))

    def dv(f):
        return v0 * float(pot.dv(f, p))

    # Slow-roll initial velocity dφ/dN = −V'/V.
    y0 = [phi0, -dv(phi0) / v(phi0)]

    def rhs(n, y):
        f, df = y                      # df = dφ/dN
        eps_h = min(0.5 * df * df, 3 - 1e-9)
        h2 = v(f) / (3 - eps_h)
        return [df, -(3 - eps_h) * df - dv(f) / h2]

    def below_zero(_n, y):
        # Hilltop potentials are unbounded below; stop once V turns negative.
        return v(y[0])

    below_zero.terminal = True
    below_zero.direction = -1

    sol = integrate.solve_ivp(rhs, (0, n_before + extra), y0, rtol=1e-8, atol=1e-10, max_step=0.02,
                              events=below_zero)
    f, df = sol.y
    eps_h = np.minimum(0.5 * df * df, 3 - 1e-9)
    h = np.sqrt(np.array([v(x) for x in f]) / (3 - eps_h))
    above = np.nonzero(eps_h >= 1.0)[0]
    end = float(sol.t[above[0]]) if above.size else float(sol.t[-1])
    return Trajectory(sol.t, f, df * h, h, eps_h, end)


def comoving_hubble_radius_history(n_inflation: float = 60.0, log_a_end: float = -28.0):
    """Comoving Hubble radius c/(aH) in units of today's Hubble distance, versus a.

    After inflation the Planck 2018 expansion history is used (radiation, matter,
    Λ). During inflation H is constant, so c/(aH) shrinks as 1/a. Returns
    (log10 a, log10 c/(aH H0⁻¹)) and the index where inflation ends.
    """
    from cosmos.physics.presets import PRESETS

    c = PRESETS["planck18"].cosmology
    log_start = log_a_end - n_inflation / math.log(10)
    x = np.linspace(log_start, 0.5, 2000)
    a = 10.0**x
    a_end = 10.0**log_a_end
    e_end = math.sqrt(float(c.E2_of_a(a_end)))
    e = np.where(a < a_end, e_end, np.sqrt(c.E2_of_a(np.maximum(a, a_end))))
    y = -np.log10(a * e)
    return x, y, int(np.argmax(a >= a_end))
