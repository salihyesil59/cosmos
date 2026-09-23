"""Reionisation history, CMB optical depth and a schematic 21-cm global signal."""

from __future__ import annotations

import math

import numpy as np
from scipy import integrate, optimize

from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology

SIGMA_THOMSON = 6.6524587e-29   # m²
Y_HELIUM = 0.245
F_HELIUM = Y_HELIUM / (4 * (1 - Y_HELIUM))
NU_21CM_MHZ = 1420.405751


def ionized_fraction(z, z_re: float = 7.7, delta_z: float = 0.5, z_he: float = 3.5):
    """Free electrons per hydrogen atom, x_e(z), in the tanh model used by Planck.

    Hydrogen and singly ionised helium reionise together around ``z_re``; helium is
    fully ionised around ``z_he``. Recombination-era electrons are ignored.
    """
    z = np.asarray(z, dtype=float)
    y = (1 + z) ** 1.5
    y_re = (1 + z_re) ** 1.5
    dy = 1.5 * math.sqrt(1 + z_re) * delta_z
    x = (1 + F_HELIUM) / 2 * (1 + np.tanh((y_re - y) / dy))
    x += F_HELIUM / 2 * (1 + np.tanh((z_he - z) / 0.5))
    return x


def neutral_hydrogen_fraction(z, z_re: float = 7.7, delta_z: float = 0.5):
    return 1 - np.clip(ionized_fraction(z, z_re, delta_z, z_he=-10) / (1 + F_HELIUM), 0, 1)


def hydrogen_density_today(c: Cosmology) -> float:
    """Number density of hydrogen nuclei today [1/m³]."""
    return c.critical_density0 * c.Ob0 * (1 - Y_HELIUM) / const.M_PROTON


def optical_depth(c: Cosmology, z_re: float = 7.7, delta_z: float = 0.5, z_max: float = 50.0) -> float:
    """Thomson optical depth to reionisation, τ = σ_T c ∫ n_e dt."""
    n_h0 = hydrogen_density_today(c)
    h0_si = c.H0_si

    def integrand(z):
        return float(ionized_fraction(z, z_re, delta_z)) * (1 + z) ** 2 / float(c.efunc(z))

    val, _ = integrate.quad(integrand, 0, z_max, limit=300, points=[3.5, z_re])
    return SIGMA_THOMSON * const.C * n_h0 / h0_si * val


def reionization_redshift(c: Cosmology, tau: float) -> float:
    """Midpoint redshift of reionisation that gives the optical depth ``tau``."""
    return float(optimize.brentq(lambda zr: optical_depth(c, zr) - tau, 4.0, 30.0))


def frequency_mhz(z):
    """Observed frequency of the 21-cm line emitted at redshift z."""
    return NU_21CM_MHZ / (1 + np.asarray(z, dtype=float))


def global_21cm_signal(c: Cosmology, z, z_re: float = 7.7, heating_z: float = 12.0, coupling_z: float = 22.0):
    """Schematic sky-averaged 21-cm brightness temperature δT_b [mK].

    A simplified model for teaching: the gas decouples from the CMB near z ≈ 150
    and cools adiabatically, collisions couple the spin temperature at high z, Lyman-α
    photons from the first stars couple it again below ``coupling_z``, X-rays heat
    the gas below ``heating_z``, and reionisation removes the neutral hydrogen.
    """
    z = np.asarray(z, dtype=float)
    t_cmb = c.Tcmb0 * (1 + z)
    z_dec = 150.0
    t_adiabatic = np.where(z > z_dec, t_cmb, c.Tcmb0 * (1 + z_dec) * ((1 + z) / (1 + z_dec)) ** 2)
    t_heat = 3000.0 / (1 + np.exp((z - heating_z) / 1.2))
    t_gas = t_adiabatic + t_heat
    x_coll = 0.45 * ((1 + z) / 50.0) ** 3.0
    x_lya = 8.0 / (1 + np.exp((z - coupling_z) / 1.5))
    x_tot = x_coll + x_lya
    t_spin = (1 + x_tot) / (1 / t_cmb + x_tot / t_gas)
    omega_m_h2 = c.Om0 * c.h**2
    omega_b_h2 = c.Ob0 * c.h**2
    x_hi = neutral_hydrogen_fraction(z, z_re)
    return (27.0 * x_hi * (1 - t_cmb / t_spin) * np.sqrt((1 + z) / 10 * 0.15 / omega_m_h2)
            * (omega_b_h2 / 0.023))
