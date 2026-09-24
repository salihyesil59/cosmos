"""Hydrogen recombination: the Saha equation and Peebles' three-level atom (S25).

The universe became transparent when its free electrons were captured by protons.
Two descriptions are compared here:

* **Saha equilibrium** — ionisation and recombination balance at every instant. It
  says how many atoms *should* be neutral at a given temperature, and puts the
  moment of recombination too early.
* **Peebles (1968)** — a hydrogen atom with a ground state, the n = 2 level and the
  continuum. A recombination straight to the ground state emits a photon that
  ionises the next atom, so electrons must get down through n = 2, where they are
  either kicked out again or escape by the slow two-photon decay or the redshifting
  of Lyman-α photons. This bottleneck delays recombination and leaves a residual
  ionisation of a few 10⁻⁴ that never recombines: the "freeze-out".

Helium is left out (it recombines earlier and changes x_e by about 10 %), so the
electron fraction ``x`` is measured per hydrogen nucleus and never exceeds 1. With
Planck 2018 parameters the visibility function peaks at z ≈ 1090, within a few per
cent of RECFAST and CAMB.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import integrate

from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology

M_ELECTRON = 9.109_383_7015e-31          # [kg]
SIGMA_THOMSON = 6.652_458_7321e-29       # [m^2]
B_HYDROGEN = 13.605_693 * const.EV       # ionisation energy of hydrogen [J]
E_LYMAN_ALPHA = 0.75 * B_HYDROGEN        # 1s -> 2p [J]
E_N2 = 0.25 * B_HYDROGEN                 # binding energy of n = 2 [J]
LAMBDA_2S1S = 8.2245809                  # two-photon decay rate of 2s [1/s]
LAMBDA_LYMAN_ALPHA = const.H_PLANCK * const.C / E_LYMAN_ALPHA   # 121.6 nm
Y_HELIUM = 0.245                         # primordial helium mass fraction
FUDGE = 1.14                             # RECFAST's correction to the case-B coefficient
ZETA3 = 1.202_056_903


@dataclass(frozen=True)
class RecombinationHistory:
    """The ionisation history on a grid of redshifts (descending)."""

    z: np.ndarray
    x_saha: np.ndarray             # free electrons per hydrogen nucleus, in equilibrium
    x_peebles: np.ndarray          # the same with the n = 2 bottleneck
    tau: np.ndarray                # Thomson optical depth from today back to z
    visibility: np.ndarray         # g(z) = -dτ/dz e^{-τ}, per unit redshift
    omega_b_h2: float
    t_cmb: float

    def z_half(self, which: str = "peebles") -> float:
        """Redshift at which half of the hydrogen is neutral."""
        x = self.x_saha if which == "saha" else self.x_peebles
        return _crossing(self.z, x, 0.5)

    @property
    def x_freeze(self) -> float:
        """The residual ionisation left at the end of the grid (z ≈ 200)."""
        return float(self.x_peebles[-1])

    @property
    def z_peak(self) -> float:
        """Redshift where the visibility function peaks: the last-scattering surface."""
        return float(self.z[int(np.argmax(self.visibility))])

    @property
    def width(self) -> float:
        """Full width at half maximum of the visibility function, in redshift."""
        g = self.visibility
        half = g.max() / 2
        above = self.z[g >= half]
        return float(above.max() - above.min())

    def temperature(self, z) -> np.ndarray:
        return self.t_cmb * (1 + np.asarray(z, dtype=float))


def _crossing(z: np.ndarray, x: np.ndarray, level: float) -> float:
    """First redshift (from high z downwards) where x falls below ``level``."""
    below = np.nonzero(x < level)[0]
    if len(below) == 0:
        return math.nan
    i = below[0]
    if i == 0:
        return float(z[0])
    # Linear interpolation between the two grid points around the crossing.
    z0, z1, x0, x1 = z[i - 1], z[i], x[i - 1], x[i]
    return float(z0 + (level - x0) * (z1 - z0) / (x1 - x0))


def hydrogen_density(z, omega_b_h2: float) -> np.ndarray:
    """Number density of hydrogen nuclei (neutral or not) [1/m^3]."""
    rho_crit_h1 = 3 * (100 * const.KM_S_MPC_TO_SI) ** 2 / (8 * math.pi * const.G)
    n_h0 = (1 - Y_HELIUM) * omega_b_h2 * rho_crit_h1 / const.M_PROTON
    return n_h0 * (1 + np.asarray(z, dtype=float)) ** 3


def _thermal_factor(t_k) -> np.ndarray:
    """(m_e k T / 2π ħ²)^{3/2}: the number of quantum states per volume [1/m^3]."""
    return (M_ELECTRON * const.K_B * np.asarray(t_k, dtype=float)
            / (2 * math.pi * const.HBAR**2)) ** 1.5


def saha_fraction(z, omega_b_h2: float = 0.02237, t_cmb: float = const.T_CMB) -> np.ndarray:
    """Ionised fraction of hydrogen in equilibrium: x² / (1 − x) = S."""
    z = np.asarray(z, dtype=float)
    t = t_cmb * (1 + z)
    with np.errstate(over="ignore", under="ignore"):
        s = _thermal_factor(t) * np.exp(-B_HYDROGEN / (const.K_B * t)) / hydrogen_density(z, omega_b_h2)
    # x = (−S + √(S² + 4S)) / 2, written to stay accurate when S is huge or tiny.
    return np.where(s > 1e8, 1.0, 2 / (1 + np.sqrt(1 + 4 / np.maximum(s, 1e-300))))


def case_b_coefficient(t_k) -> np.ndarray:
    """Recombination rate to excited levels, α_B [m^3/s] (Péquignot et al. 1991, fudged)."""
    t4 = np.asarray(t_k, dtype=float) / 1e4
    return FUDGE * 1e-19 * 4.309 * t4 ** -0.6166 / (1 + 0.6703 * t4 ** 0.5300)


def photons_above(energy_j: float, t_k: float) -> float:
    """Photons per m³ of a blackbody at ``t_k`` with energy above ``energy_j``.

    The integrand x²/(eˣ − 1) is integrated numerically; for energies far above kT
    it is the Wien tail, which is why a few ionising photons survive at 3000 K.
    """
    x0 = energy_j / (const.K_B * t_k)
    tail, _err = integrate.quad(lambda x: x * x / math.expm1(x), x0, x0 + 200, limit=200)
    scale = (const.K_B * t_k / (const.HBAR * const.C)) ** 3 / math.pi**2
    return tail * scale


def ionising_photons_per_baryon(t_k: float, omega_b_h2: float = 0.02237,
                                t_cmb: float = const.T_CMB) -> float:
    """How many photons above 13.6 eV there are for every hydrogen nucleus at ``t_k``."""
    z = t_k / t_cmb - 1
    return photons_above(B_HYDROGEN, t_k) / float(hydrogen_density(z, omega_b_h2))


def photons_equal_atoms_temperature(omega_b_h2: float = 0.02237, t_cmb: float = const.T_CMB) -> float:
    """Temperature [K] below which ionising photons become rarer than hydrogen atoms.

    This is the textbook estimate kT ≈ B / ln(1/η): it is several thousand kelvin, far
    below the 158 000 K that 13.6 eV corresponds to. Full recombination needs the
    universe to cool somewhat further still.
    """
    from scipy import optimize

    def excess(t):
        return math.log(ionising_photons_per_baryon(t, omega_b_h2, t_cmb))

    return float(optimize.brentq(excess, 2000.0, 30000.0, xtol=1.0))


def photon_to_baryon_ratio(omega_b_h2: float = 0.02237, t_cmb: float = const.T_CMB) -> float:
    """1/η: photons per baryon, a number that never changes after e⁺e⁻ annihilation."""
    n_gamma = 2 * ZETA3 / math.pi**2 * (const.K_B * t_cmb / (const.HBAR * const.C)) ** 3
    n_b = float(hydrogen_density(0, omega_b_h2)) / (1 - Y_HELIUM)
    return n_gamma / n_b


def history(omega_b_h2: float = 0.02237, H0: float = 67.66, Om0: float = 0.3111,
            t_cmb: float = const.T_CMB, z_start: float = 1800.0, z_end: float = 200.0,
            n: int = 1601) -> RecombinationHistory:
    """Solve for the ionisation history from ``z_start`` down to ``z_end``."""
    cosmo = Cosmology.flat(H0=H0, Om0=Om0, Tcmb0=t_cmb, Ob0=omega_b_h2 / (H0 / 100) ** 2)
    z = np.linspace(z_start, z_end, n)
    x_saha = saha_fraction(z, omega_b_h2, t_cmb)
    kb = const.K_B

    def rhs(zz, y):
        x = min(max(y[0], 1e-12), 1.0)
        t = t_cmb * (1 + zz)
        n_h = float(hydrogen_density(zz, omega_b_h2))
        alpha = float(case_b_coefficient(t))
        beta = alpha * float(_thermal_factor(t)) * math.exp(-E_N2 / (kb * t))
        hubble = float(cosmo.H(zz)) * const.KM_S_MPC_TO_SI
        # Peebles' C: the chance that an atom in n = 2 reaches the ground state
        # before a photon ionises it again.
        k = LAMBDA_LYMAN_ALPHA**3 / (8 * math.pi * hubble)
        down = k * LAMBDA_2S1S * n_h * (1 - x)
        c_factor = (1 + down) / (1 + down + k * beta * n_h * (1 - x))
        rate = c_factor * (alpha * n_h * x * x
                           - beta * (1 - x) * math.exp(-E_LYMAN_ALPHA / (kb * t)))
        return [rate / (hubble * (1 + zz))]          # dx/dz = −(dx/dt) / (H (1 + z)) with dt<0

    x0 = float(x_saha[0])
    sol = integrate.solve_ivp(rhs, (z_start, z_end), [x0], t_eval=z, method="LSODA",
                              rtol=1e-6, atol=1e-10)
    x_peebles = np.clip(sol.y[0], 0.0, 1.0)

    # Optical depth from today: dτ = n_e σ_T c dt = n_e σ_T c dz / ((1 + z) H).
    hubble = cosmo.H(z) * const.KM_S_MPC_TO_SI
    dtau_dz = x_peebles * hydrogen_density(z, omega_b_h2) * SIGMA_THOMSON * const.C / ((1 + z) * hubble)
    # z is descending, so integrate from the low end upwards and flip back.
    tau_up = integrate.cumulative_trapezoid(dtau_dz[::-1], z[::-1], initial=0.0)
    # Below z_end the frozen-out electrons still add a little depth; count it.
    z_low = np.linspace(0, z_end, 400)
    h_low = cosmo.H(z_low) * const.KM_S_MPC_TO_SI
    low = np.trapezoid(x_peebles[-1] * hydrogen_density(z_low, omega_b_h2) * SIGMA_THOMSON * const.C
                       / ((1 + z_low) * h_low), z_low)
    tau = (tau_up + low)[::-1]
    visibility = dtau_dz * np.exp(-tau)
    return RecombinationHistory(z=z, x_saha=x_saha, x_peebles=x_peebles, tau=tau,
                                visibility=visibility, omega_b_h2=omega_b_h2, t_cmb=t_cmb)
