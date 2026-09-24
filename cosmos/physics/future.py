"""The far future of the universe (S26, L6.10).

Three kinds of numbers live here:

* **Astrophysical milestones** that do not depend on the cosmological model: the
  Sun's red-giant phase, the end of star formation, Hawking evaporation. Their
  times come from Adams & Laughlin (1997) and later work, and are good to an order
  of magnitude at best — which, on a scale running to 10¹⁰⁰ years, is the point.
* **The end** of a given universe: a Big Rip or a Big Crunch, from the Friedmann
  equations in :mod:`cosmos.physics.cosmology`.
* **The Big Rip countdown** of Caldwell, Kamionkowski & Weinberg (2003): a system
  bound with orbital period P comes apart a time P √(2|1 + 3w|) / (6π|1 + w|)
  before the rip, when the phantom energy inside it overwhelms the binding.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import integrate

from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology, Fate

OBSERVABLE_GALAXIES = 2e12          # galaxies in today's observable universe (Conselice et al. 2016)


@dataclass(frozen=True)
class Milestone:
    key: str
    label: str
    years_from_now: float
    description: str
    needs_acceleration: bool = False    # only happens if the expansion keeps accelerating


def hawking_lifetime_years(mass_msun: float) -> float:
    """Time for a black hole to evaporate by Hawking radiation: 5120 π G² M³ / (ħ c⁴)."""
    m = mass_msun * const.M_SUN
    return 5120 * math.pi * const.G**2 * m**3 / (const.HBAR * const.C**4) / const.YEAR


MILESTONES: list[Milestone] = [
    Milestone("sun", "The Sun becomes a red giant", 5e9,
              "The Sun runs out of hydrogen in its core, swells and swallows the inner planets."),
    Milestone("andromeda", "The Milky Way and Andromeda probably merge", 5e9,
              "The two large galaxies of the Local Group fall together. Gaia data now make it roughly "
              "even odds within ten billion years."),
    Milestone("alone", "Only the Local Group is left in view", 1.5e11,
              "Every galaxy outside our gravitationally bound group has been carried beyond the event "
              "horizon. An astronomer then would see one galaxy and nothing else.", True),
    Milestone("cmb", "The CMB can no longer be detected", 1e12,
              "Its wavelength has been stretched beyond the size of the Local Group's gas and beyond any "
              "telescope. The evidence for the Big Bang is gone.", True),
    Milestone("stars", "Star formation ends; the last red dwarfs fade", 1e14,
              "The gas has all been used up. The smallest stars, which burn for ten trillion years, go out "
              "one by one. The stelliferous era is over."),
    Milestone("evaporate", "Galaxies evaporate", 1e19,
              "Close encounters fling dead stars out of their galaxies, and what remains falls into the "
              "central black holes."),
    Milestone("protons", "Protons decay, if they decay at all", 1e35,
              "Grand unified theories predict it; experiments show it takes longer than 2.4 × 10³⁴ years. "
              "If it happens, white dwarfs and neutron stars dissolve."),
    Milestone("stellar-bh", "Stellar black holes evaporate", hawking_lifetime_years(10.0),
              "A 10 M☉ black hole slowly radiates itself away by Hawking radiation."),
    Milestone("smbh", "The largest black holes evaporate", hawking_lifetime_years(1e11),
              "Even a 10¹¹ M☉ black hole is gone. What remains is a thin, cold gas of photons, "
              "neutrinos and electrons: the heat death."),
]


@dataclass(frozen=True)
class BoundSystem:
    key: str
    label: str
    period_s: float                    # a characteristic orbital period


BOUND_SYSTEMS: list[BoundSystem] = [
    BoundSystem("clusters", "Galaxy clusters", 3.5e9 * const.YEAR),
    BoundSystem("milky-way", "The Milky Way", 2.3e8 * const.YEAR),
    BoundSystem("solar-system", "The Solar System", const.YEAR),
    BoundSystem("moon", "The Earth–Moon system", 27.32 * 86_400),
    BoundSystem("earth", "The Earth itself", 2 * math.pi * math.sqrt(6.371e6**3 / 3.986e14)),
    BoundSystem("atom", "Atoms (order of magnitude)", 1.52e-16),
]


def rip_lead_time(period_s, w: float):
    """How long before the Big Rip a system with orbital period ``period_s`` comes apart [s]."""
    if w >= -1:
        return math.inf
    return np.asarray(period_s) * math.sqrt(2 * abs(1 + 3 * w)) / (6 * math.pi * abs(1 + w))


def rip_estimate_gyr(w: float, Om0: float, H0: float) -> float:
    """Caldwell's closed-form time to the Big Rip, (2/3) |1 + w|⁻¹ H0⁻¹ (1 − Ωm)^(−1/2) [Gyr]."""
    if w >= -1 or Om0 >= 1:
        return math.inf
    hubble_time = 1 / const.hubble_to_si(H0) / const.GYR
    return 2 / 3 / abs(1 + w) * hubble_time / math.sqrt(1 - Om0)


@dataclass(frozen=True)
class Future:
    """What lies ahead for one universe."""

    cosmology: Cosmology
    fate: Fate
    age_gyr: float
    end_gyr: float                     # time from now to a Rip or Crunch; inf if neither
    t: np.ndarray                      # time from now [Gyr]
    a: np.ndarray                      # scale factor
    reach_t: np.ndarray                # time from now [Gyr] for the reachable fraction
    reach: np.ndarray                  # fraction of today's observable galaxies still reachable
    efold_gyr: float                   # time for distances to grow by e at late times; inf if none

    @property
    def reachable_now(self) -> float:
        return float(self.reach[0]) if len(self.reach) else 1.0

    @property
    def ends(self) -> bool:
        return math.isfinite(self.end_gyr)

    def happens(self, milestone: Milestone) -> bool:
        """True if the universe lasts long enough (and accelerates, if that is required)."""
        if milestone.years_from_now / 1e9 >= self.end_gyr:
            return False
        if milestone.needs_acceleration:
            return self.fate in (Fate.ACCELERATES_FOREVER, Fate.BIG_RIP)
        return True

    def destruction_times(self) -> dict[str, float]:
        """Seconds before the Big Rip at which each bound system comes apart."""
        if self.fate is not Fate.BIG_RIP:
            return {}
        return {s.key: float(rip_lead_time(s.period_s, self.cosmology.w0)) for s in BOUND_SYSTEMS}


def future(cosmo: Cosmology, horizon_gyr: float = 200.0) -> Future:
    """Integrate a universe forward and work out what it has in store."""
    fate = cosmo.fate()
    age = float(cosmo.age(0.0)) if cosmo.has_big_bang() else math.nan
    end = math.inf
    if fate is Fate.BIG_RIP:
        end = cosmo.big_rip_time()
    history = cosmo.expansion_history(t_future=min(horizon_gyr, end * 0.999) if math.isfinite(end)
                                      else horizon_gyr, a_max=1e4)
    if history.crunch_time is not None:
        end = history.crunch_time
    keep = history.t >= 0
    t, a = history.t[keep], history.a[keep]

    # With a cosmological constant the expansion ends up exponential, a ∝ exp(t H0 √ΩΛ).
    efold = math.inf
    if cosmo.w0 == -1 and cosmo.wa == 0 and fate is Fate.ACCELERATES_FOREVER:
        efold = cosmo.hubble_time / math.sqrt(cosmo.Ode0)

    reach_t, reach = _reachable(cosmo, fate, t, a)
    return Future(cosmology=cosmo, fate=fate, age_gyr=age, end_gyr=end, t=t, a=a,
                  reach_t=reach_t, reach=reach, efold_gyr=efold)


def _reachable(cosmo: Cosmology, fate: Fate, t: np.ndarray, a: np.ndarray):
    """Fraction of today's observable galaxies that a light signal sent at time t can reach.

    Galaxies keep their comoving positions, so the count is today's number times
    (comoving event horizon at t / today's particle horizon)³.
    """
    if fate not in (Fate.ACCELERATES_FOREVER, Fate.BIG_RIP) or not cosmo.has_big_bang():
        return np.array([]), np.array([])
    chi_now = cosmo.particle_horizon(0.0) / cosmo.hubble_distance

    def remaining(a0: float) -> float:
        def integrand(x):
            val = x**4 * float(cosmo.E2_of_a(x))
            return 1 / math.sqrt(val) if val > 0 else 0.0

        value, _err = integrate.quad(integrand, a0, math.inf, limit=400)
        return value

    growing = np.concatenate([[True], np.diff(a) > 0])
    sample = np.unique(np.linspace(0, len(t) - 1, 80).astype(int))
    sample = sample[growing[sample]]
    ts, frac = [], []
    for i in sample:
        chi_e = remaining(float(a[i]))
        ts.append(float(t[i]))
        frac.append(min((chi_e / chi_now) ** 3, 1.0))
    return np.array(ts), np.array(frac)
