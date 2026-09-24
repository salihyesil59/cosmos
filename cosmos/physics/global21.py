"""The sky-averaged 21-cm signal from the dark ages to reionisation (S28).

Neutral hydrogen absorbs or emits at 21 cm depending on its spin temperature T_S,
the excitation temperature of the hyperfine transition, compared with the radio
background it is seen against (the CMB, T_γ):

    δT_b ≈ 27 mK · x_HI · (1 − T_γ / T_S) · √[(1+z)/10 · 0.15/(Ωm h²)] · (Ωb h²/0.023)

T_S is a weighted mean of three temperatures, set by what couples the hyperfine
levels (Field 1958):

    1/T_S = (1/T_γ + x_c/T_K + x_α/T_K) / (1 + x_c + x_α)

* x_c, collisions between atoms — strong only while the gas is dense (z ≳ 30);
* x_α, the Wouthuysen–Field effect — Lyman-α photons from the first stars;
* T_K, the gas temperature, which is computed here rather than assumed: the few
  electrons left after recombination (from :mod:`cosmos.physics.recombination`)
  tie it to the CMB by Compton scattering until z ≈ 150, after which it cools
  adiabatically as (1+z)², until X-rays from the first galaxies heat it again.

So there are two absorption troughs — one in the dark ages at ν ≈ 15 MHz, set by
physics alone, and one at cosmic dawn, set by the first stars — and, if the gas is
heated enough before reionisation, a region of emission. The astrophysics (star
formation, X-ray heating, reionisation) enters through tanh histories, as in the
simple models used to interpret EDGES and SARAS-3.
"""

from __future__ import annotations

import functools
import math
from dataclasses import dataclass

import numpy as np
from scipy import integrate

from cosmos.physics import constants as const
from cosmos.physics import recombination
from cosmos.physics.reionization import ionized_fraction

NU_21 = 1420.405_751                  # MHz
T_STAR = 0.068                        # K, the energy of the transition over k_B
A_10 = 2.85e-15                       # 1/s, the spontaneous decay rate
OMEGA_B_H2, OMEGA_M_H2, H0 = 0.02237, 0.1424, 67.66
M_ELECTRON = 9.109_383_7015e-31
SIGMA_T = 6.652_458_7321e-29
F_HE = 0.079                          # helium nuclei per hydrogen nucleus

# EDGES (Bowman et al. 2018): a flattened Gaussian absorption profile.
EDGES = dict(amplitude=0.53, nu0=78.3, width=20.7, tau=6.5)


def frequency(z):
    return NU_21 / (1 + np.asarray(z, dtype=float))


def redshift(nu_mhz):
    return NU_21 / np.asarray(nu_mhz, dtype=float) - 1


def edges_profile(nu_mhz) -> np.ndarray:
    """The best-fit EDGES absorption profile, in mK."""
    nu = np.asarray(nu_mhz, dtype=float)
    a, nu0, w, tau = EDGES["amplitude"], EDGES["nu0"], EDGES["width"], EDGES["tau"]
    b = 4 * (nu - nu0) ** 2 / w**2 * math.log(-1 / tau * math.log((1 + math.exp(-tau)) / 2))
    return -a * (1 - np.exp(-tau * np.exp(b))) / (1 - math.exp(-tau)) * 1e3


def step(z, z_mid: float, width: float) -> np.ndarray:
    """0 at high redshift, rising to 1 as z falls through z_mid."""
    return 0.5 * (1 + np.tanh((z_mid - np.asarray(z, dtype=float)) / width))


def kappa_hh(t_k) -> np.ndarray:
    """Collision rate coefficient for H–H spin exchange [m³/s] (fit to Zygelman 2005)."""
    t = np.maximum(np.asarray(t_k, dtype=float), 1.0)
    return 3.1e-11 * t**0.357 * np.exp(-32.0 / t) * 1e-6


@functools.lru_cache(maxsize=4)
def _electron_history(omega_b_h2: float = OMEGA_B_H2):
    h = recombination.history(omega_b_h2=omega_b_h2, H0=H0, Om0=OMEGA_M_H2 / (H0 / 100) ** 2,
                              z_start=1600, z_end=4, n=3000)
    return h.z[::-1].copy(), h.x_peebles[::-1].copy()


def hubble(z) -> np.ndarray:
    """H(z) in 1/s for flat Planck 2018 (radiation included)."""
    z = np.asarray(z, dtype=float)
    h = H0 / 100
    om = OMEGA_M_H2 / h**2
    orad = 4.18e-5 / h**2
    e2 = om * (1 + z) ** 3 + orad * (1 + z) ** 4 + (1 - om - orad)
    return const.hubble_to_si(H0) * np.sqrt(e2)


@dataclass(frozen=True)
class Astrophysics:
    """When the first stars couple the spin temperature, heat the gas and reionise it."""

    z_alpha: float = 19.0          # Lyman-α coupling switches on
    z_heat: float = 12.0           # X-ray heating switches on
    heating: float = 1000.0        # K of heating the X-rays eventually deliver
    z_re: float = 7.7              # midpoint of reionisation (Planck)
    radio_excess: float = 0.0      # extra radio background, in units of the CMB at 78 MHz


@dataclass(frozen=True)
class Signal:
    z: np.ndarray                  # descending from the dark ages to reionisation
    t_gamma: np.ndarray            # the radio background: CMB (+ any excess)
    t_gas: np.ndarray
    t_spin: np.ndarray
    x_c: np.ndarray
    x_alpha: np.ndarray
    x_hi: np.ndarray
    delta_tb: np.ndarray           # mK

    @property
    def nu(self) -> np.ndarray:
        return frequency(self.z)

    def trough(self, z_min: float, z_max: float) -> tuple[float, float]:
        """(depth in mK, redshift) of the deepest absorption between z_min and z_max."""
        sel = (self.z >= z_min) & (self.z <= z_max)
        if not np.any(sel):
            return math.nan, math.nan
        i = int(np.argmin(np.where(sel, self.delta_tb, np.inf)))
        return float(self.delta_tb[i]), float(self.z[i])

    @property
    def dark_ages(self) -> tuple[float, float]:
        return self.trough(40.0, 200.0)

    @property
    def cosmic_dawn(self) -> tuple[float, float]:
        return self.trough(5.0, 40.0)

    @property
    def emission_peak(self) -> float:
        return float(max(self.delta_tb[self.z < 30].max(), 0.0))

    @property
    def heating_crossing(self) -> float:
        """Redshift at which X-rays heat the gas back above the background (nan if never)."""
        low = self.z < 40
        above = np.nonzero(low & (self.t_gas > self.t_gamma))[0]
        return float(self.z[above[0]]) if len(above) else math.nan


def gas_temperature(z_grid, astro: Astrophysics, omega_b_h2: float = OMEGA_B_H2) -> np.ndarray:
    """Kinetic temperature of the gas: Compton coupling, adiabatic cooling and X-ray heating."""
    z_e, x_e = _electron_history(omega_b_h2)
    a_rad = const.A_RAD

    def rhs(zz, y):
        t_k = y[0]
        t_g = const.T_CMB * (1 + zz)
        xe = float(np.interp(zz, z_e, x_e))
        rate = 8 * SIGMA_T * a_rad * t_g**4 * xe / (3 * M_ELECTRON * const.C * (1 + F_HE + xe))
        return [2 * t_k / (1 + zz) - rate * (t_g - t_k) / (float(hubble(zz)) * (1 + zz))]

    z_grid = np.asarray(z_grid, dtype=float)
    z0 = max(float(z_grid.max()), 800.0)
    sol = integrate.solve_ivp(rhs, (z0, float(z_grid.min())), [const.T_CMB * (1 + z0)],
                              t_eval=np.sort(z_grid)[::-1], method="LSODA", rtol=1e-6, atol=1e-6)
    t_ad = np.interp(z_grid, sol.t[::-1], sol.y[0][::-1])
    # X-ray heating: added on top, growing as the first galaxies form.
    return t_ad + astro.heating * step(z_grid, astro.z_heat, 2.0)


def signal(astro: Astrophysics = Astrophysics(), z=None, omega_b_h2: float = OMEGA_B_H2) -> Signal:
    z = np.geomspace(300, 5, 900) if z is None else np.asarray(z, dtype=float)
    t_cmb = const.T_CMB * (1 + z)
    # An excess radio background, like the one proposed for EDGES, falls as ν^-2.6
    # (Fialkov & Barkana 2019); A_r is its size relative to the CMB at 78 MHz.
    t_gamma = t_cmb * (1 + astro.radio_excess * (frequency(z) / 78.0) ** -2.6)
    t_k = gas_temperature(z, astro, omega_b_h2)
    x_hi = 1.0 - np.clip(ionized_fraction(z, z_re=astro.z_re, delta_z=0.5, z_he=0.0), 0.0, 1.0)
    n_h = recombination.hydrogen_density(z, omega_b_h2)
    x_c = T_STAR * n_h * kappa_hh(t_k) / (A_10 * t_gamma)
    # Lyman-α coupling switches on with the first stars; a brighter radio background
    # needs proportionally more of it.
    x_alpha = 200.0 * step(z, astro.z_alpha, 2.0) * t_cmb / t_gamma
    t_s = (1 + x_c + x_alpha) / (1 / t_gamma + (x_c + x_alpha) / t_k)
    prefactor = 27.0 * np.sqrt((1 + z) / 10 * 0.15 / OMEGA_M_H2) * (omega_b_h2 / 0.023)
    delta_tb = prefactor * x_hi * (1 - t_gamma / t_s)
    return Signal(z=z, t_gamma=t_gamma, t_gas=t_k, t_spin=t_s, x_c=x_c, x_alpha=x_alpha,
                  x_hi=x_hi, delta_tb=delta_tb)
