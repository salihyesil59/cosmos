"""Big Bang nucleosynthesis: light-element abundances as a function of the baryon density.

A full nucleosynthesis calculation solves a network of nuclear reactions. Here we
use published fitting formulas (Steigman 2007, 2012) that reproduce such
calculations near the observed baryon density, extended smoothly so that the
classic "Schramm plot" can be explored over a wider range. The helium fit is
written logarithmically and the lithium fit combines the two production
channels (⁷Li directly at low density, ⁷Be at high density), which gives the
characteristic lithium dip. Accuracy: a few percent near η₁₀ ≈ 6, qualitative
further away.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import optimize, special

B_DEUTERIUM_MEV = 2.224566
M_NUCLEON_MEV = 938.918
NEUTRON_LIFETIME_S = 878.4
NEUTRON_PROTON_MASS_DIFF_MEV = 1.293
FREEZE_OUT_T_MEV = 0.80          # weak interactions freeze out (lesson L4.2)
ETA10_PER_OMEGA_B_H2 = 273.9     # η₁₀ = 273.9 Ω_b h²

# Observed primordial abundances (approximate current values).
OBSERVED = {
    "Yp": (0.245, 0.003),            # helium-4 mass fraction (H II regions)
    "D/H": (2.53e-5, 0.03e-5),       # deuterium (quasar absorption systems, Cooke et al. 2018)
    "He3/H": (1.1e-5, 0.2e-5),       # helium-3 (Galactic H II regions, an upper-limit-like estimate)
    "Li7/H": (1.6e-10, 0.3e-10),     # lithium-7 (Spite plateau in old halo stars)
}

# Uncertainty of the predictions (nuclear reaction rates), relative except for Yp.
THEORY_ERRORS = {"Yp": 0.0006, "D/H": 0.03, "He3/H": 0.08, "Li7/H": 0.15}
PLANCK_OMEGA_B_H2 = (0.02237, 0.00015)


def eta10_from_omega_b_h2(omega_b_h2):
    return ETA10_PER_OMEGA_B_H2 * np.asarray(omega_b_h2, dtype=float)


def omega_b_h2_from_eta10(eta10):
    return np.asarray(eta10, dtype=float) / ETA10_PER_OMEGA_B_H2


def speedup_factor(delta_neff: float) -> float:
    """Expansion-rate factor S = H'/H from extra relativistic species during BBN."""
    return math.sqrt(1 + 7 * delta_neff / 43)


@dataclass(frozen=True)
class Abundances:
    eta10: np.ndarray
    yp: np.ndarray       # helium-4 mass fraction
    d_h: np.ndarray      # deuterium to hydrogen by number
    he3_h: np.ndarray    # helium-3 to hydrogen
    li7_h: np.ndarray    # lithium-7 to hydrogen


def abundances(eta10, delta_neff: float = 0.0, neutron_lifetime: float = NEUTRON_LIFETIME_S) -> Abundances:
    """Primordial abundances for baryon-to-photon ratio η = η₁₀ × 10⁻¹⁰."""
    eta = np.clip(np.asarray(eta10, dtype=float), 0.1, None)
    s = speedup_factor(delta_neff)
    # Helium: more baryons → earlier deuterium formation → more surviving neutrons.
    # Faster expansion → earlier freeze-out → more neutrons. Longer lifetime → fewer decay.
    yp = (0.2485 + 0.0091 * np.log(eta / 6.0) + 0.16 * (s - 1)
          + 2.0e-4 * (neutron_lifetime - NEUTRON_LIFETIME_S))
    d_h = 2.55e-5 * (6.0 / np.clip(eta - 6 * (s - 1), 0.05, None)) ** 1.6
    he3_h = 1.02e-5 * (6.0 / np.clip(eta - 5 * (s - 1), 0.05, None)) ** 0.59
    eta_li = np.clip(eta - 3 * (s - 1), 0.05, None)
    li7_h = 5.0e-10 * eta_li ** -2.3 + 4.82e-10 * (eta_li / 6.0) ** 2
    return Abundances(eta, yp, d_h, he3_h, li7_h)


def eta10_from_deuterium(d_h: float, delta_neff: float = 0.0) -> float:
    """Invert the deuterium fit: the baryon density measured by deuterium."""
    s = speedup_factor(delta_neff)
    return 6.0 * (2.55e-5 / d_h) ** (1 / 1.6) + 6 * (s - 1)


def deuterium_bottleneck_temperature(eta: float) -> float:
    """Temperature [MeV] at which deuterium survives photodisintegration.

    From the Saha condition X_D ≈ X_n X_p, i.e.
    (12 ζ(3)/√π) η (T/m_N)^{3/2} e^{B_D/T} ≈ 1.
    """
    def condition(t):
        return (math.log(12 * special.zeta(3) / math.sqrt(math.pi) * eta * (t / M_NUCLEON_MEV) ** 1.5)
                + B_DEUTERIUM_MEV / t)

    return float(optimize.brentq(condition, 0.01, 1.0))


def time_at_temperature(t_mev):
    """Cosmic time [s] after electron–positron annihilation, t ≈ 1.32 s (MeV/T)²."""
    return 1.32 / np.asarray(t_mev, dtype=float) ** 2


def neutron_fraction(time_s, neutron_lifetime: float = NEUTRON_LIFETIME_S, delta_neff: float = 0.0):
    """Neutrons per nucleon after weak freeze-out, decaying with the neutron lifetime."""
    # Faster expansion (S > 1) means weak reactions freeze out earlier, at a higher temperature.
    t_freeze = FREEZE_OUT_T_MEV * speedup_factor(delta_neff) ** (1 / 3)
    ratio = math.exp(-NEUTRON_PROTON_MASS_DIFF_MEV / t_freeze)      # n/p at freeze-out
    x_freeze = ratio / (1 + ratio)
    t = np.asarray(time_s, dtype=float)
    return x_freeze * np.exp(-np.clip(t - 1.0, 0, None) / neutron_lifetime)


def simple_helium_estimate(eta: float, neutron_lifetime: float = NEUTRON_LIFETIME_S, delta_neff: float = 0.0):
    """Y_p ≈ 2 X_n(t_nuc): all neutrons left at the bottleneck end up in helium."""
    t_nuc = float(time_at_temperature(deuterium_bottleneck_temperature(eta)))
    return 2 * float(neutron_fraction(t_nuc, neutron_lifetime, delta_neff)), t_nuc


def predicted(ab: Abundances) -> dict[str, float]:
    return {"Yp": float(ab.yp), "D/H": float(ab.d_h), "He3/H": float(ab.he3_h), "Li7/H": float(ab.li7_h)}


def tensions(ab: Abundances) -> dict[str, float]:
    """Difference between prediction and observation in combined standard deviations."""
    out = {}
    for key, value in predicted(ab).items():
        obs, err = OBSERVED[key]
        theory = THEORY_ERRORS[key] if key == "Yp" else THEORY_ERRORS[key] * value
        out[key] = (value - obs) / math.hypot(err, theory)
    return out
