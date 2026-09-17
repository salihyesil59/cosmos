"""Neutrino mass and cosmology (L4.7).

Oscillation experiments measure differences of squared masses, which set a floor
on the sum of the three masses. Cosmology measures the sum itself, because relic
neutrinos that became non-relativistic add to the matter density but refuse to
cluster on small scales. Both sides are collected here.

Numbers: NuFIT 5.2 (2022) for the mass splittings; Planck 2018 and DESI for the
cosmological bounds; KATRIN (2024) for the direct laboratory limit.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

DM21_SQ = 7.41e-5          # eV², solar splitting
DM3L_SQ_NORMAL = 2.511e-3  # eV², Δm²31 in the normal ordering
DM3L_SQ_INVERTED = 2.498e-3  # eV², |Δm²32| in the inverted ordering

EV_PER_OMEGA_H2 = 93.14    # Σmν / (Ων h²), for the standard relic temperature
NUMBER_DENSITY_PER_FLAVOUR_CM3 = 112.0   # neutrinos plus antineutrinos
TEMPERATURE_K = 1.945      # (4/11)^(1/3) × T_CMB


@dataclass(frozen=True)
class Bound:
    name: str
    year: int
    kind: str                # "floor", "cosmology" or "laboratory"
    value_ev: float          # a lower limit for floors, an upper limit on Σmν otherwise
    note: str


BOUNDS = [
    Bound("Oscillations, normal ordering", 2022, "floor", 0.0587,
          "Two measured mass splittings with the lightest neutrino massless."),
    Bound("Oscillations, inverted ordering", 2022, "floor", 0.0992,
          "The same splittings with the order of the states reversed."),
    Bound("KATRIN (tritium decay)", 2024, "laboratory", 3 * 0.45,
          "mβ < 0.45 eV at 90% CL, shown as three equal masses."),
    Bound("Planck 2018 CMB + BAO", 2018, "cosmology", 0.12, "95% upper limit."),
    Bound("DESI 2024 BAO + CMB", 2024, "cosmology", 0.072, "95% upper limit."),
    Bound("DESI 2025 BAO + CMB", 2025, "cosmology", 0.064, "95% upper limit."),
]


def masses(lightest_ev: float, ordering: str = "normal") -> tuple[float, float, float]:
    """The three masses (m1, m2, m3) in eV for a given lightest mass."""
    m0 = max(lightest_ev, 0.0)
    if ordering == "normal":
        m1 = m0
        m2 = math.sqrt(m0**2 + DM21_SQ)
        m3 = math.sqrt(m0**2 + DM3L_SQ_NORMAL)
    elif ordering == "inverted":
        m3 = m0
        m2 = math.sqrt(m0**2 + DM3L_SQ_INVERTED)
        m1 = math.sqrt(m2**2 - DM21_SQ)
    else:
        raise ValueError(f"unknown ordering {ordering!r}")
    return m1, m2, m3


def minimum_sum(ordering: str = "normal") -> float:
    return sum(masses(0.0, ordering))


def omega_nu_h2(sum_ev: float) -> float:
    return sum_ev / EV_PER_OMEGA_H2


def omega_nu(sum_ev: float, h: float) -> float:
    return omega_nu_h2(sum_ev) / h**2


def neutrino_fraction(sum_ev: float, omega_m: float, h: float) -> float:
    """fν = Ων / Ωm, the share of the matter that does not cluster on small scales."""
    return omega_nu(sum_ev, h) / omega_m


def nonrelativistic_redshift(mass_ev: float) -> float:
    """Roughly when a neutrino of this mass stopped being relativistic (⟨p⟩ = 3.15 T = m)."""
    return 1890.0 * mass_ev - 1.0


def free_streaming_wavenumber(mass_ev: float, omega_m: float) -> float:
    """k_nr ≈ 0.018 Ωm^½ (m/1 eV)^½ h/Mpc: smaller scales are smoothed out."""
    return 0.018 * math.sqrt(omega_m) * math.sqrt(max(mass_ev, 1e-6))


def power_suppression(k, sum_ev: float, omega_m: float = 0.31, h: float = 0.674) -> np.ndarray:
    """P(k) with massive neutrinos divided by P(k) without, a smooth teaching approximation.

    Large scales are untouched; well below the free-streaming length the power is
    reduced by the classic factor ΔP/P ≈ −8 fν.
    """
    k = np.asarray(k, dtype=float)
    if sum_ev <= 0:
        return np.ones_like(k)
    fraction = neutrino_fraction(sum_ev, omega_m, h)
    k_nr = free_streaming_wavenumber(sum_ev / 3, omega_m)
    x = (k / k_nr) ** 2
    return 1 - 8 * fraction * x / (1 + x)


def is_allowed(sum_ev: float, ordering: str = "normal", cosmology_limit: float = 0.12) -> bool:
    return minimum_sum(ordering) <= sum_ev <= cosmology_limit
