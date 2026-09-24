"""Dark matter haloes: how many there are of each mass, and when (S27, L4.8).

The halo mass function answers the question "how many objects of mass M are there
per unit volume at redshift z?". It comes from the linear density field alone:

* smooth the field over a sphere holding mass M; its rms is σ(M, z)
* a region collapses into a halo once its linear overdensity passes δc ≈ 1.686
* so the rarity of a halo is measured by the peak height ν = δc / σ(M, z)

Press & Schechter (1974) turned that into a formula; Sheth & Tormen (1999)
corrected it for ellipsoidal collapse, and fit N-body simulations to about 10%.
Because the abundance falls as exp(−ν²/2), the most massive clusters are
exponentially sensitive to σ8 — which is why counting them measures it.

Units follow the literature: masses in M☉/h, lengths in Mpc/h, number densities
in (h/Mpc)³.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import integrate

from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology
from cosmos.physics.structure import DELTA_C, LinearPowerSpectrum, growth_factor

RHO_CRIT_H2 = 2.775e11                  # critical density today, (M☉/h) / (Mpc/h)³
MODELS = ("sheth-tormen", "press-schechter")
ATOMIC_COOLING_MASS = 1e8               # M☉/h: the smallest haloes whose gas cools by atomic hydrogen


def multiplicity(nu, model: str = "sheth-tormen"):
    """f(ν): the fraction of mass in haloes per unit ln ν."""
    nu = np.asarray(nu, dtype=float)
    if model == "press-schechter":
        return math.sqrt(2 / math.pi) * nu * np.exp(-nu * nu / 2)
    a, p, amp = 0.707, 0.3, 0.3222
    x = math.sqrt(a) * nu
    return amp * math.sqrt(2 / math.pi) * x * (1 + x ** (-2 * p)) * np.exp(-x * x / 2)


@dataclass
class HaloModel:
    """σ(M) for one cosmology, with the mass function at any redshift."""

    cosmology: Cosmology
    sigma8: float = 0.811
    n_s: float = 0.9665
    masses: np.ndarray | None = None

    def __post_init__(self):
        if self.masses is None:
            self.masses = np.logspace(5, 16, 111)
        spectrum = LinearPowerSpectrum(self.cosmology, n_s=self.n_s, sigma8=self.sigma8)
        self.rho_m = RHO_CRIT_H2 * self.cosmology.Om0
        radii = spectrum.radius_of_mass(self.masses)
        self.sigma0 = np.asarray(spectrum.sigma_r(radii))
        self.dlnsigma_dlnm = np.gradient(np.log(self.sigma0), np.log(self.masses))
        self._growth: dict[float, float] = {}

    def growth(self, z: float) -> float:
        z = round(float(z), 6)
        if z not in self._growth:
            self._growth[z] = 1.0 if z == 0 else float(growth_factor(self.cosmology, 1 / (1 + z)))
        return self._growth[z]

    def sigma(self, z: float = 0.0) -> np.ndarray:
        return self.sigma0 * self.growth(z)

    def nu(self, z: float = 0.0) -> np.ndarray:
        return DELTA_C / self.sigma(z)

    def dn_dlnm(self, z: float = 0.0, model: str = "sheth-tormen") -> np.ndarray:
        """dn/dlnM [(h/Mpc)³] on the model's mass grid."""
        nu = self.nu(z)
        return self.rho_m / self.masses * multiplicity(nu, model) * np.abs(self.dlnsigma_dlnm)

    def n_above(self, z: float = 0.0, model: str = "sheth-tormen") -> np.ndarray:
        """Cumulative n(>M) [(h/Mpc)³] on the mass grid."""
        dn = self.dn_dlnm(z, model)
        lnm = np.log(self.masses)
        # Integrate from the top of the grid downwards.
        tail = integrate.cumulative_trapezoid(dn[::-1], -lnm[::-1], initial=0.0)
        return tail[::-1]

    def n_above_mass(self, mass: float, z: float = 0.0, model: str = "sheth-tormen") -> float:
        cumulative = self.n_above(z, model)
        return float(np.exp(np.interp(math.log(mass), np.log(self.masses), np.log(np.maximum(cumulative, 1e-300)))))

    def nonlinear_mass(self, z: float = 0.0) -> float:
        """M*: the mass whose σ equals δc — the typical halo collapsing at z [M☉/h], or nan."""
        s = self.sigma(z)
        if s[-1] >= DELTA_C or s[0] <= DELTA_C:
            return math.nan                     # off the mass grid (below 10⁵ M☉/h at z ≳ 5)
        return float(np.exp(np.interp(-DELTA_C, -s, np.log(self.masses))))

    def growth_many(self, zs) -> np.ndarray:
        """D(z) for many redshifts with one integration, cached like :meth:`growth`."""
        zs = np.asarray(zs, dtype=float)
        missing = [z for z in zs if round(float(z), 6) not in self._growth]
        if missing:
            values = np.atleast_1d(growth_factor(self.cosmology, 1 / (1 + np.asarray(missing))))
            for z, d in zip(missing, values):
                self._growth[round(float(z), 6)] = float(d)
        return np.array([self._growth[round(float(z), 6)] for z in zs])

    def all_sky_curve(self, z_max: float = 1.0, model: str = "sheth-tormen", n_z: int = 40) -> np.ndarray:
        """N(>M) on the whole sky out to ``z_max``, on the mass grid."""
        c = self.cosmology
        h = c.h
        dz = z_max / n_z
        zs = (np.arange(n_z) + 0.5) * dz
        self.growth_many(zs)
        total = np.zeros_like(self.masses)
        for z in zs:
            dm = float(c.transverse_comoving_distance(z)) * h        # Mpc/h
            hz = float(c.H(z)) / h                                    # 100 E(z): H in km/s per Mpc/h
            dv_dz = 4 * math.pi * dm**2 * (const.C / 1e3) / hz          # (Mpc/h)³ per unit z
            total += self.n_above(z, model) * dv_dz * dz
        return total

    def all_sky_counts(self, mass: float, z_max: float = 1.0, model: str = "sheth-tormen") -> float:
        """Haloes heavier than ``mass`` on the whole sky out to ``z_max``."""
        curve = self.all_sky_curve(z_max, model)
        return float(np.exp(np.interp(math.log(mass), np.log(self.masses), np.log(np.maximum(curve, 1e-300)))))

    def redshift_of_density(self, mass: float, density: float, model: str = "sheth-tormen",
                            z_max: float = 40.0) -> float:
        """The highest redshift at which haloes above ``mass`` reach ``density`` [(h/Mpc)³]."""
        lo, hi = 0.0, z_max
        if self.n_above_mass(mass, lo, model) < density:
            return math.nan
        if self.n_above_mass(mass, hi, model) >= density:
            return hi
        for _ in range(40):
            mid = 0.5 * (lo + hi)
            if self.n_above_mass(mass, mid, model) >= density:
                lo = mid
            else:
                hi = mid
        return 0.5 * (lo + hi)
