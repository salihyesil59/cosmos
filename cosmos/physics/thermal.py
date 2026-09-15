"""Thermal history of the early universe: neutrinos, e± annihilation, relic abundances.

Temperatures are given as energies ``k_B T`` in MeV unless stated otherwise
(natural units: 1 MeV ≈ 1.16 × 10¹⁰ K).
"""

from __future__ import annotations

import math

import numpy as np
from scipy import integrate, special

from cosmos.physics import constants as const

M_ELECTRON_MEV = 0.51099895
M_NUCLEON_MEV = 938.9          # mean of proton and neutron masses
G_FERMI_GEV2 = 1.1663787e-5    # Fermi constant [GeV^-2]
M_PLANCK_GEV = 1.220890e19     # Planck mass [GeV]
ZETA3 = special.zeta(3)
MEV_TO_K = 1e6 * const.EV / const.K_B

# Entropy integral of one relativistic fermionic degree of freedom (u = p/T).
_S_REL = 4.0 / 3.0 * 7.0 * math.pi**4 / 120.0


def kelvin_from_mev(t_mev):
    return np.asarray(t_mev) * MEV_TO_K


def fermion_entropy_fraction(x: float) -> float:
    """Entropy of a fermion gas with mass ``m`` relative to the massless case.

    ``x = m / T``. Equals 1 for ``x -> 0`` and falls to 0 when the particles
    become non-relativistic and annihilate.
    """
    if x > 60:
        return 0.0

    def integrand(u):
        e = math.sqrt(u * u + x * x)
        return (e + u * u / (3 * e)) * u * u / (math.exp(e) + 1.0)

    val, _ = integrate.quad(integrand, 0, 80, limit=200)
    return val / _S_REL


def neutrino_to_photon_temperature(t_gamma_mev) -> np.ndarray:
    """Ratio T_ν / T_γ during and after electron–positron annihilation.

    Neutrinos have decoupled, so their temperature falls as 1/a. The entropy of
    the annihilating e± pairs goes into the photons:
    ``(T_γ/T_ν)^3 = (2 + 7/2) / (2 + 7/2 · I(m_e/T_γ))``.
    """
    t = np.atleast_1d(np.asarray(t_gamma_mev, dtype=float))
    frac = np.array([fermion_entropy_fraction(M_ELECTRON_MEV / ti) for ti in t])
    ratio = ((2.0 + 3.5 * frac) / 5.5) ** (1.0 / 3.0)
    return ratio if np.ndim(t_gamma_mev) else float(ratio[0])


RELIC_NEUTRINO_RATIO = (4.0 / 11.0) ** (1.0 / 3.0)


def neutrino_temperature_today() -> float:
    """Temperature of the cosmic neutrino background today [K]."""
    return RELIC_NEUTRINO_RATIO * const.T_CMB


def photon_number_density(t_kelvin: float = const.T_CMB) -> float:
    """Number density of blackbody photons [per cm^3]."""
    kt = const.K_B * t_kelvin
    n_m3 = 2 * ZETA3 / math.pi**2 * (kt / (const.HBAR * const.C)) ** 3
    return n_m3 / 1e6


def neutrino_number_density_per_species() -> float:
    """Relic neutrinos plus antineutrinos of one flavour today [per cm^3]."""
    return 3.0 / 11.0 * photon_number_density()


def weak_rate_over_hubble(t_mev, g_star: float = 10.75):
    """Order-of-magnitude ratio of the weak interaction rate to the expansion rate.

    ``Γ ≈ G_F² T⁵`` and ``H = 1.66 √g* T² / M_Pl``. Reactions freeze out when the
    ratio drops below one, which happens at ``T ≈ 1–2 MeV``.
    """
    t_gev = np.asarray(t_mev, dtype=float) * 1e-3
    rate = G_FERMI_GEV2**2 * t_gev**5
    hubble = 1.66 * math.sqrt(g_star) * t_gev**2 / M_PLANCK_GEV
    return rate / hubble


def neutrino_decoupling_temperature(g_star: float = 10.75) -> float:
    """Temperature [MeV] where ``Γ/H = 1`` in the simple estimate above."""
    # Γ/H ∝ T³, so solve analytically from the value at 1 MeV.
    return float(weak_rate_over_hubble(1.0, g_star)) ** (-1.0 / 3.0)


def nucleon_equilibrium_ratio(t_mev) -> np.ndarray:
    """Equilibrium number of nucleons (or antinucleons) per photon.

    Non-relativistic Maxwell–Boltzmann gas with 4 internal states (p, n with two
    spin states each): ``n = g (m T / 2π)^{3/2} e^{-m/T}``.
    """
    t = np.asarray(t_mev, dtype=float)
    g = 4.0
    n_nucleon = g * (M_NUCLEON_MEV * t / (2 * math.pi)) ** 1.5 * np.exp(-M_NUCLEON_MEV / t)
    n_gamma = 2 * ZETA3 / math.pi**2 * t**3
    return n_nucleon / n_gamma


def baryon_to_photon_ratio(omega_b_h2: float) -> float:
    """η = n_b / n_γ from the physical baryon density Ω_b h²."""
    rho_crit_h1 = 3 * (100 * const.KM_S_MPC_TO_SI) ** 2 / (8 * math.pi * const.G)
    n_b = omega_b_h2 * rho_crit_h1 / const.M_PROTON / 1e6  # per cm^3 (approx. proton mass)
    return n_b / photon_number_density()
