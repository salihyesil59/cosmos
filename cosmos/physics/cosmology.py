"""Friedmann–Lemaître–Robertson–Walker (FLRW) cosmological models.

The :class:`Cosmology` class describes a homogeneous, isotropic universe filled
with radiation (photons + massless neutrinos), matter (baryons + cold dark
matter) and dark energy with the equation of state ``w(a) = w0 + wa (1 - a)``
(Chevallier–Polarski–Linder; ``wa = 0`` is a constant ``w``). Spatial
curvature follows from the closure relation ``Ok0 = 1 - Or0 - Om0 - Ode0``.

Conventions
-----------
* ``H0`` is given in km/s/Mpc.
* Distances are returned in megaparsecs (Mpc), times in gigayears (Gyr).
* Functions accept scalars or numpy arrays for redshift ``z``.
"""

from __future__ import annotations

import enum
import math
from dataclasses import dataclass, replace

import numpy as np
from scipy import integrate

from cosmos.physics import constants as const


class Fate(enum.Enum):
    """Qualitative long-term behaviour of a universe."""

    ACCELERATES_FOREVER = "accelerates forever"
    EXPANDS_FOREVER = "expands forever"
    BIG_CRUNCH = "recollapses in a Big Crunch"
    BIG_RIP = "ends in a Big Rip"
    NO_BIG_BANG = "has no Big Bang"

    @property
    def explanation(self) -> str:
        return _FATE_EXPLANATIONS[self]


_FATE_EXPLANATIONS = {
    Fate.ACCELERATES_FOREVER: (
        "Dark energy eventually dominates. The expansion speeds up forever and "
        "distant galaxies disappear beyond our horizon."
    ),
    Fate.EXPANDS_FOREVER: (
        "Gravity slows the expansion but never stops it. The universe keeps "
        "growing, ever more slowly."
    ),
    Fate.BIG_CRUNCH: (
        "Gravity wins: the expansion stops, reverses, and the universe collapses "
        "back into a hot, dense state."
    ),
    Fate.BIG_RIP: (
        "Phantom dark energy (w < −1) grows denser as space expands. The expansion rate "
        "diverges in a finite time and tears apart galaxies, stars and finally atoms."
    ),
    Fate.NO_BIG_BANG: (
        "Going back in time the universe never shrinks to zero size: dark energy "
        "is so dominant that it either 'bounces' at a minimum size or has been "
        "expanding forever. Such models contradict observations of "
        "high-redshift objects and the CMB."
    ),
}

# Radiation density per photon temperature: Omega_gamma * h^2 for T = 1 K.
_RHO_CRIT_H1 = 3 * (100 * const.KM_S_MPC_TO_SI) ** 2 / (8 * math.pi * const.G)
_NEUTRINO_FACTOR = 7 / 8 * (4 / 11) ** (4 / 3)  # ≈ 0.2271 per species


@dataclass(frozen=True)
class Cosmology:
    """A simple FLRW universe.

    Parameters
    ----------
    H0:
        Hubble constant today [km/s/Mpc].
    Om0:
        Matter density parameter today (baryons + dark matter).
    Ode0:
        Dark-energy density parameter today.
    Ob0:
        Baryon density parameter today (informational; included in ``Om0``).
    Tcmb0:
        CMB temperature today [K]. ``0`` switches radiation off.
    Neff:
        Effective number of massless neutrino species.
    w0:
        Dark-energy equation of state today, ``p = w rho c^2``.
    wa:
        Rate of change of the equation of state: ``w(a) = w0 + wa (1 - a)``.
    name:
        Human readable label.
    """

    H0: float = 67.66
    Om0: float = 0.3097
    Ode0: float = 0.6889
    Ob0: float = 0.0490
    Tcmb0: float = const.T_CMB
    Neff: float = const.NEFF
    w0: float = -1.0
    wa: float = 0.0
    name: str = "Custom"

    # ------------------------------------------------------------------ build
    @classmethod
    def flat(cls, H0: float = 67.66, Om0: float = 0.3097, **kwargs) -> "Cosmology":
        """Create a spatially flat model; ``Ode0`` absorbs the remainder."""
        probe = cls(H0=H0, Om0=Om0, Ode0=0.0, **kwargs)
        return replace(probe, Ode0=1.0 - Om0 - probe.Or0)

    def with_params(self, **changes) -> "Cosmology":
        """Return a copy with some parameters changed."""
        return replace(self, **changes)

    # ------------------------------------------------------------- parameters
    @property
    def h(self) -> float:
        """Dimensionless Hubble parameter ``H0 / (100 km/s/Mpc)``."""
        return self.H0 / 100.0

    @property
    def Ogamma0(self) -> float:
        """Photon density parameter today."""
        if self.Tcmb0 <= 0:
            return 0.0
        rho_gamma = const.A_RAD * self.Tcmb0**4 / const.C**2
        return rho_gamma / (_RHO_CRIT_H1 * self.h**2)

    @property
    def Onu0(self) -> float:
        """Massless-neutrino density parameter today."""
        return self.Ogamma0 * _NEUTRINO_FACTOR * self.Neff

    @property
    def Or0(self) -> float:
        """Total radiation density parameter today."""
        return self.Ogamma0 + self.Onu0

    @property
    def Ok0(self) -> float:
        """Curvature density parameter today (``> 0`` open, ``< 0`` closed)."""
        return 1.0 - self.Or0 - self.Om0 - self.Ode0

    @property
    def Otot0(self) -> float:
        """Total density parameter (everything except curvature)."""
        return self.Or0 + self.Om0 + self.Ode0

    @property
    def geometry(self) -> str:
        """'flat', 'open' or 'closed' (with a small tolerance)."""
        if abs(self.Ok0) < 1e-3:
            return "flat"
        return "open" if self.Ok0 > 0 else "closed"

    @property
    def H0_si(self) -> float:
        """Hubble constant in 1/s."""
        return const.hubble_to_si(self.H0)

    @property
    def hubble_time(self) -> float:
        """Hubble time ``1/H0`` [Gyr]."""
        return 1.0 / self.H0_si / const.GYR

    @property
    def hubble_distance(self) -> float:
        """Hubble distance ``c/H0`` [Mpc]."""
        return const.C / self.H0_si / const.MPC

    @property
    def critical_density0(self) -> float:
        """Critical density today [kg/m^3]."""
        return self.critical_density(0.0)

    # -------------------------------------------------------- expansion rate
    def w_of_a(self, a):
        """Dark-energy equation of state at scale factor ``a``."""
        return self.w0 + self.wa * (1.0 - np.asarray(a, dtype=float))

    def de_density_ratio(self, a):
        """Dark-energy density relative to today, ρ_de(a)/ρ_de,0."""
        a = np.asarray(a, dtype=float)
        with np.errstate(over="ignore", divide="ignore"):
            ratio = a ** (-3.0 * (1.0 + self.w0 + self.wa))
            if self.wa:
                ratio = ratio * np.exp(-3.0 * self.wa * (1.0 - a))
        return ratio

    def E2_of_a(self, a):
        """Squared normalised expansion rate ``(H/H0)^2`` as a function of ``a``."""
        a = np.asarray(a, dtype=float)
        return (
            self.Or0 * a**-4
            + self.Om0 * a**-3
            + self.Ok0 * a**-2
            + self.Ode0 * self.de_density_ratio(a)
        )

    def efunc(self, z):
        """Normalised expansion rate ``E(z) = H(z)/H0``."""
        a = 1.0 / (1.0 + np.asarray(z, dtype=float))
        return np.sqrt(self.E2_of_a(a))

    def H(self, z):
        """Hubble parameter at redshift ``z`` [km/s/Mpc]."""
        return self.H0 * self.efunc(z)

    def critical_density(self, z):
        """Critical density ``3 H^2 / (8 pi G)`` at redshift ``z`` [kg/m^3]."""
        h_si = const.hubble_to_si(self.H(z))
        return 3 * h_si**2 / (8 * math.pi * const.G)

    def Om(self, z):
        """Matter density parameter at redshift ``z``."""
        zp1 = 1.0 + np.asarray(z, dtype=float)
        return self.Om0 * zp1**3 / self.efunc(z) ** 2

    def Or(self, z):
        """Radiation density parameter at redshift ``z``."""
        zp1 = 1.0 + np.asarray(z, dtype=float)
        return self.Or0 * zp1**4 / self.efunc(z) ** 2

    def Ode(self, z):
        """Dark-energy density parameter at redshift ``z``."""
        a = 1.0 / (1.0 + np.asarray(z, dtype=float))
        return self.Ode0 * self.de_density_ratio(a) / self.efunc(z) ** 2

    def deceleration_parameter(self, z=0.0):
        """Deceleration parameter ``q = -a a'' / a'^2`` (negative = accelerating)."""
        a = 1.0 / (1.0 + np.asarray(z, dtype=float))
        return self.Or(z) + 0.5 * self.Om(z) + 0.5 * (1 + 3 * self.w_of_a(a)) * self.Ode(z)

    def Tcmb(self, z):
        """CMB temperature at redshift ``z`` [K]."""
        return self.Tcmb0 * (1.0 + np.asarray(z, dtype=float))

    @property
    def z_equality(self) -> float:
        """Redshift of matter–radiation equality (``inf`` without radiation)."""
        if self.Or0 <= 0:
            return math.inf
        return self.Om0 / self.Or0 - 1.0

    # --------------------------------------------------------- qualitative
    def has_big_bang(self) -> bool:
        """True if ``a -> 0`` is reached in the past (no bounce)."""
        a = np.logspace(-8, 0, 4000)
        if not np.all(self.E2_of_a(a) > 0):
            return False  # a bounce: the expansion rate vanishes in the past
        # The age integral must converge as a -> 0. A universe containing only
        # a cosmological constant has been expanding exponentially forever.
        tiny = 1e-12
        return (
            self.Or0 > tiny
            or self.Om0 > tiny
            or self.Ok0 > tiny
            or (self.Ode0 > tiny and self.w0 + self.wa > -1.0)
        )

    def recollapses(self) -> bool:
        """True if the expansion halts and reverses in the future."""
        a = np.logspace(0, 6, 6000)
        with np.errstate(over="ignore", invalid="ignore"):
            return bool(np.any(self.E2_of_a(a) < 0))

    def _late_time_w(self) -> float:
        """Equation of state of dark energy in the far future."""
        if self.wa == 0:
            return self.w0
        return -math.inf if self.wa > 0 else math.inf

    def fate(self) -> Fate:
        """Classify the universe's history and future."""
        if not self.has_big_bang():
            return Fate.NO_BIG_BANG
        if self.recollapses():
            return Fate.BIG_CRUNCH
        if self.Ode0 > 0:
            w_late = self._late_time_w()
            if w_late < -1.0:
                return Fate.BIG_RIP
            if w_late < -1.0 / 3.0:
                # Far in the future dark energy with positive density dominates.
                return Fate.ACCELERATES_FOREVER
        return Fate.EXPANDS_FOREVER

    def big_rip_time(self) -> float:
        """Time from today until the Big Rip [Gyr] (``inf`` if there is none)."""
        if self.fate() is not Fate.BIG_RIP:
            return math.inf
        return self._time_integral(1.0, math.inf) * self.hubble_time

    # ------------------------------------------------------------------ times
    def _time_integral(self, a_lo: float, a_hi: float) -> float:
        """Integral of ``da / (a E(a))`` in units of the Hubble time."""

        def integrand(a):
            val = a * a * self.E2_of_a(a)
            return 1.0 / math.sqrt(val) if val > 0 else math.inf

        result, _ = integrate.quad(integrand, a_lo, a_hi, limit=200, epsabs=0, epsrel=1e-8)
        return result

    def age(self, z=0.0):
        """Age of the universe at redshift ``z`` [Gyr] (``nan`` without a Big Bang)."""
        if not self.has_big_bang():
            return np.full(np.shape(z), np.nan) if np.ndim(z) else math.nan

        def one(zz: float) -> float:
            return self._time_integral(0.0, 1.0 / (1.0 + zz)) * self.hubble_time

        return _vectorise(one, z)

    def lookback_time(self, z):
        """Time elapsed since light left an object at redshift ``z`` [Gyr]."""

        def one(zz: float) -> float:
            return self._time_integral(1.0 / (1.0 + zz), 1.0) * self.hubble_time

        return _vectorise(one, z)

    # -------------------------------------------------------------- distances
    def comoving_distance(self, z):
        """Line-of-sight comoving distance [Mpc]."""

        def one(zz: float) -> float:
            val, _ = integrate.quad(lambda x: 1.0 / self.efunc(x), 0.0, zz, limit=200)
            return val * self.hubble_distance

        return _vectorise(one, z)

    def transverse_comoving_distance(self, z):
        """Transverse comoving distance, including the effect of curvature [Mpc]."""
        dc = np.asarray(self.comoving_distance(z), dtype=float)
        dh = self.hubble_distance
        ok = self.Ok0
        if abs(ok) < 1e-8:
            result = dc
        elif ok > 0:
            s = math.sqrt(ok)
            result = dh / s * np.sinh(s * dc / dh)
        else:
            s = math.sqrt(-ok)
            result = dh / s * np.sin(s * dc / dh)
        return result if np.ndim(z) else float(result)

    def luminosity_distance(self, z):
        """Luminosity distance ``(1+z) D_M`` [Mpc]."""
        return (1.0 + np.asarray(z)) * self.transverse_comoving_distance(z)

    def angular_diameter_distance(self, z):
        """Angular diameter distance ``D_M / (1+z)`` [Mpc]."""
        return self.transverse_comoving_distance(z) / (1.0 + np.asarray(z))

    def distance_modulus(self, z):
        """Distance modulus ``m - M = 5 log10(D_L / 10 pc)``."""
        return 5.0 * np.log10(self.luminosity_distance(z)) + 25.0

    def kpc_per_arcsec(self, z):
        """Proper transverse size corresponding to one arcsecond [kpc]."""
        return self.angular_diameter_distance(z) * 1e3 * math.pi / 648_000

    def light_travel_distance(self, z):
        """Speed of light times lookback time [Mpc]."""
        return np.asarray(self.lookback_time(z)) * const.GYR * const.C / const.MPC

    def angular_diameter_distance_peak(self) -> tuple[float, float]:
        """Redshift and value [Mpc] where the angular diameter distance is largest."""
        from scipy import optimize

        res = optimize.minimize_scalar(
            lambda lz: -self.angular_diameter_distance(10**lz), bounds=(-2, 2), method="bounded"
        )
        return float(10**res.x), float(-res.fun)

    # ------------------------------------------------------------- horizons
    def _conformal_integral(self, a_lo: float, a_hi: float) -> float:
        """Integral of ``da / (a^2 E(a))``, a comoving distance in Hubble distances."""

        def integrand(a):
            val = a**4 * self.E2_of_a(a) if a > 0 else self.Or0
            if val <= 0:
                return math.inf if a > 0 else 0.0
            return 1.0 / math.sqrt(val)

        result, _ = integrate.quad(integrand, a_lo, a_hi, limit=400, epsabs=0, epsrel=1e-8)
        return result

    def particle_horizon(self, z=0.0) -> float:
        """Comoving distance light has travelled since the Big Bang [Mpc].

        Equal to today's proper radius of the observable universe for ``z = 0``.
        """
        if not self.has_big_bang():
            return math.inf
        return self._conformal_integral(0.0, 1.0 / (1.0 + z)) * self.hubble_distance

    def event_horizon(self, z=0.0) -> float:
        """Comoving distance light emitted at ``z`` can ever travel in the future [Mpc].

        Infinite when the expansion does not accelerate forever, ``nan`` for
        recollapsing universes (not modelled here).
        """
        if self.recollapses():
            return math.nan
        if not (self.Ode0 > 0 and self._late_time_w() < -1.0 / 3.0):
            return math.inf
        return self._conformal_integral(1.0 / (1.0 + z), math.inf) * self.hubble_distance

    def conformal_history(self, a_max: float = 6.0, n: int = 3000) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Tabulate cosmic time and comoving light distance since the Big Bang.

        Returns ``(a, t, chi)`` with ``t`` in Gyr since the Big Bang and ``chi`` the
        comoving distance [Mpc] light has travelled by then (the particle horizon).
        Only defined for universes with a Big Bang that do not recollapse before
        ``a_max``.
        """
        a0 = 1e-6
        a = np.logspace(math.log10(a0), math.log10(a_max), n)
        e = np.sqrt(self.E2_of_a(a))
        # Integrate in ln a: dt = dln(a) / H, dchi = c dln(a) / (a H).
        dt = 1.0 / e
        dchi = 1.0 / (a * e)
        lna = np.log(a)
        t = np.concatenate([[0.0], np.cumsum(0.5 * (dt[1:] + dt[:-1]) * np.diff(lna))])
        chi = np.concatenate([[0.0], np.cumsum(0.5 * (dchi[1:] + dchi[:-1]) * np.diff(lna))])
        t += self._time_integral(0.0, a0)
        chi += self._conformal_integral(0.0, a0)
        return a, t * self.hubble_time, chi * self.hubble_distance

    def hubble_radius(self, z=0.0):
        """Radius of the Hubble sphere ``c/H(z)`` [proper Mpc]."""
        return const.C / 1e3 / self.H(z)

    def recession_velocity(self, z, at_emission: bool = False):
        """Recession velocity of an object at redshift ``z`` in units of c.

        Today: ``H0 D_C / c``. At emission: ``H(z) D_C / ((1+z) c)``.
        """
        dc = np.asarray(self.comoving_distance(z))
        if at_emission:
            return self.H(z) * dc / (1.0 + np.asarray(z)) / (const.C / 1e3)
        return self.H0 * dc / (const.C / 1e3)

    # -------------------------------------------------------- time evolution
    def expansion_history(self, t_future: float = 40.0, a_max: float = 30.0) -> "ExpansionHistory":
        """Integrate the scale factor ``a(t)`` backwards and forwards from today.

        The acceleration equation is used, so turning points (recollapse,
        bounces) are handled naturally. Time is measured relative to today
        (``t = 0``) in Gyr.
        """
        return _integrate_history(self, t_future, a_max)


@dataclass(frozen=True)
class ExpansionHistory:
    """Result of :meth:`Cosmology.expansion_history`."""

    t: np.ndarray             # time relative to today [Gyr], ascending
    a: np.ndarray             # scale factor
    big_bang_time: float | None   # time of a -> 0 relative to today [Gyr]
    crunch_time: float | None     # time of the Big Crunch relative to today [Gyr]

    @property
    def age(self) -> float | None:
        return None if self.big_bang_time is None else -self.big_bang_time


def _vectorise(func, z):
    if np.ndim(z) == 0:
        return float(func(float(z)))
    arr = np.asarray(z, dtype=float)
    return np.array([func(float(v)) for v in arr.ravel()]).reshape(arr.shape)


_A_MIN = 1e-3


def _integrate_history(cosmo: Cosmology, t_future: float, a_max: float) -> ExpansionHistory:
    th = cosmo.hubble_time

    def rhs(_tau, y):
        a, adot = y
        a = max(a, 1e-9)
        w = float(cosmo.w_of_a(a))
        addot = a * (
            -cosmo.Or0 * a**-4
            - 0.5 * cosmo.Om0 * a**-3
            - 0.5 * (1 + 3 * w) * cosmo.Ode0 * float(cosmo.de_density_ratio(a))
        )
        return [adot, addot]

    def hit_zero(_tau, y):
        return y[0] - _A_MIN

    hit_zero.terminal = True
    hit_zero.direction = -1

    def hit_max(_tau, y):
        return y[0] - a_max

    hit_max.terminal = True
    hit_max.direction = 1

    y0 = [1.0, 1.0]  # a(today) = 1 and da/dtau = E(1) = 1
    opts = dict(rtol=1e-9, atol=1e-12, max_step=0.01, events=(hit_zero, hit_max))

    # Past: a big-bang universe reaches a -> 0 within a few Hubble times,
    # a bouncing one is followed for a limited time only.
    past = integrate.solve_ivp(rhs, (0.0, -3.0), y0, **opts)
    future = integrate.solve_ivp(rhs, (0.0, t_future / th), y0, **opts)

    big_bang = None
    if past.t_events[0].size and cosmo.has_big_bang():
        # Use the exact age integral rather than the truncated ODE.
        big_bang = -float(cosmo.age(0.0))
    crunch = None
    if future.t_events[0].size:
        crunch = float(future.t_events[0][0]) * th

    t = np.concatenate([past.t[::-1], future.t[1:]]) * th
    a = np.concatenate([past.y[0][::-1], future.y[0][1:]])
    if big_bang is not None:
        t = np.concatenate([[big_bang], t])
        a = np.concatenate([[0.0], a])
    if crunch is not None:
        t = np.concatenate([t, [crunch]])
        a = np.concatenate([a, [0.0]])
    return ExpansionHistory(t=t, a=np.clip(a, 0.0, None), big_bang_time=big_bang, crunch_time=crunch)


# ---------------------------------------------------------------- boundaries
def recollapse_boundary(om: np.ndarray) -> np.ndarray:
    """Minimum ΩΛ that avoids recollapse for matter + Λ universes (no radiation)."""
    om = np.asarray(om, dtype=float)
    out = np.zeros_like(om)
    big = om > 1
    x = om[big]
    out[big] = 4 * x * np.cos((np.arccos((1 - x) / x) + 4 * np.pi) / 3) ** 3
    return out


def no_big_bang_boundary(om: np.ndarray) -> np.ndarray:
    """Minimum ΩΛ that gives a bouncing universe (no Big Bang), no radiation."""
    om = np.asarray(om, dtype=float)
    out = np.empty_like(om)
    small = om < 0.5
    x = np.clip(om[small], 1e-9, None)
    out[small] = 4 * x * np.cosh(np.arccosh((1 - x) / x) / 3) ** 3
    x = om[~small]
    out[~small] = 4 * x * np.cos(np.arccos((1 - x) / x) / 3) ** 3
    return out
