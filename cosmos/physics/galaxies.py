"""How galaxies fill their haloes (L5.8): the stellar-to-halo mass relation and cooling.

The stellar-to-halo mass relation is the abundance-matching fit of Moster, Naab &
White (2013) at z = 0: rank the galaxies by stellar mass and the haloes by mass,
pair them off, and the ratio comes out as a double power law that peaks at a few
per cent near 10¹² M☉ — the Milky Way's halo. Compared with the cosmic baryon
fraction Ωb/Ωm ≈ 0.16, even the most efficient haloes have turned only about a
fifth of their baryons into stars.
"""

from __future__ import annotations

import math

import numpy as np

from cosmos.physics import constants as const

BARYON_FRACTION = 0.0490 / 0.3097          # Ωb / Ωm, Planck 2018
# Moster, Naab & White (2013), z = 0 (masses in M☉, h = 0.704 absorbed).
M1, NORM, BETA, GAMMA = 10**11.59, 0.0351, 1.376, 0.608


def stellar_fraction(halo_mass_msun) -> np.ndarray:
    """m* / M_halo at z = 0."""
    x = np.asarray(halo_mass_msun, dtype=float) / M1
    return 2 * NORM / (x ** -BETA + x**GAMMA)


def stellar_mass(halo_mass_msun) -> np.ndarray:
    return stellar_fraction(halo_mass_msun) * np.asarray(halo_mass_msun, dtype=float)


def peak_halo_mass() -> float:
    """The halo mass at which star formation has been most efficient [M☉]."""
    # d/dx of x^-β + x^γ vanishes at x = (β/γ)^(1/(β+γ)).
    return M1 * (BETA / GAMMA) ** (1 / (BETA + GAMMA))


def star_formation_efficiency(halo_mass_msun) -> np.ndarray:
    """Fraction of the halo's baryons that are in stars today."""
    return stellar_fraction(halo_mass_msun) / BARYON_FRACTION


def virial_temperature(halo_mass_msun, z: float = 0.0, mu: float = 0.59) -> np.ndarray:
    """T_vir ≈ 3.6e5 K (M / 10¹¹ M☉)^(2/3) (1+z) in a matter-dominated approximation."""
    m = np.asarray(halo_mass_msun, dtype=float)
    return 3.6e5 * (mu / 0.59) * (m / 1e11) ** (2 / 3) * (1 + z)


def disk_scale_length(virial_radius_kpc: float, spin: float = 0.035) -> float:
    """Mo, Mao & White (1998): R_d ≈ λ R_vir / √2 for a disc that keeps its angular momentum."""
    return spin * virial_radius_kpc / math.sqrt(2)


def virial_radius_kpc(halo_mass_msun: float, delta: float = 200.0) -> float:
    """Radius enclosing 200 times the critical density today [kpc]."""
    h0 = const.hubble_to_si(67.66)
    rho_crit = 3 * h0**2 / (8 * math.pi * const.G)
    m = halo_mass_msun * const.M_SUN
    return (3 * m / (4 * math.pi * delta * rho_crit)) ** (1 / 3) / const.KPC
