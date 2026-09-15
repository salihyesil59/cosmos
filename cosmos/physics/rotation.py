"""Galaxy rotation curves: visible components and a dark-matter halo.

All radii are in kiloparsecs (kpc), masses in solar masses and velocities in
km/s.
"""

from __future__ import annotations

import math

import numpy as np
from scipy import special

from cosmos.physics import constants as const

# G in kpc (km/s)^2 / M_sun
G_KPC = const.G * const.M_SUN / (const.KPC * 1e6)


def disk_velocity(r_kpc, mass: float, scale_length: float):
    """Circular velocity of a thin exponential disk (Freeman 1970)."""
    r = np.asarray(r_kpc, dtype=float)
    if mass <= 0:
        return np.zeros_like(r)
    sigma0 = mass / (2 * math.pi * scale_length**2)
    y = np.clip(r / (2 * scale_length), 1e-9, None)
    bessel = special.i0(y) * special.k0(y) - special.i1(y) * special.k1(y)
    v2 = 4 * math.pi * G_KPC * sigma0 * scale_length * y**2 * bessel
    return np.sqrt(np.clip(v2, 0, None))


def bulge_velocity(r_kpc, mass: float, scale_radius: float = 0.5):
    """Circular velocity of a spherical Hernquist bulge."""
    r = np.asarray(r_kpc, dtype=float)
    if mass <= 0:
        return np.zeros_like(r)
    v2 = G_KPC * mass * r / (r + scale_radius) ** 2
    return np.sqrt(v2)


def nfw_velocity(r_kpc, virial_mass: float, concentration: float = 10.0, h: float = 0.7):
    """Circular velocity of a Navarro–Frenk–White dark-matter halo.

    ``virial_mass`` is M200: the mass inside the radius where the mean density is
    200 times the critical density.
    """
    r = np.clip(np.asarray(r_kpc, dtype=float), 1e-6, None)
    if virial_mass <= 0:
        return np.zeros_like(r)
    rho_crit = 3 * (100 * h * const.KM_S_MPC_TO_SI) ** 2 / (8 * math.pi * const.G)
    rho_crit_msun_kpc3 = rho_crit * const.KPC**3 / const.M_SUN
    r200 = (3 * virial_mass / (4 * math.pi * 200 * rho_crit_msun_kpc3)) ** (1 / 3)
    rs = r200 / concentration

    def m_of(x):
        return np.log1p(x) - x / (1 + x)

    enclosed = virial_mass * m_of(r / rs) / m_of(concentration)
    return np.sqrt(G_KPC * enclosed / r)


def total_velocity(*components):
    """Components add in quadrature: ``v^2 = sum(v_i^2)``."""
    return np.sqrt(sum(np.asarray(v) ** 2 for v in components))


def enclosed_mass(r_kpc, velocity_km_s):
    """Mass required inside ``r`` for circular speed ``v`` (spherical estimate)."""
    return np.asarray(velocity_km_s) ** 2 * np.asarray(r_kpc) / G_KPC


def keplerian_velocity(r_kpc, mass: float):
    """Speed of an orbit around a point mass: falls off as ``1/sqrt(r)``."""
    r = np.clip(np.asarray(r_kpc, dtype=float), 1e-6, None)
    return np.sqrt(G_KPC * mass / r)


A0_MOND = 1.2e-10  # Milgrom's acceleration scale [m/s²]


def mond_velocity(r_kpc, newtonian_velocity_km_s, a0: float = A0_MOND):
    """Rotation speed in Modified Newtonian Dynamics (MOND).

    The Newtonian acceleration g_N = v_N²/r of the visible matter is boosted with
    the "simple" interpolating function g = g_N (1 + √(1 + 4a0/g_N)) / 2. Far from
    the centre g ≈ √(g_N a0), which gives a flat curve with v⁴ = G M a0.
    """
    r_m = np.clip(np.asarray(r_kpc, dtype=float), 1e-6, None) * const.KPC
    v_n = np.asarray(newtonian_velocity_km_s, dtype=float) * 1e3
    g_n = np.clip(v_n * v_n / r_m, 1e-30, None)
    g = g_n * 0.5 * (1 + np.sqrt(1 + 4 * a0 / g_n))
    return np.sqrt(g * r_m) / 1e3
