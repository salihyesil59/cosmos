"""Direct detection of WIMP dark matter (S29, L3.6).

A WIMP from the Galaxy's halo occasionally bounces off an atomic nucleus in a
detector deep underground, and the nucleus recoils with a few keV to a few tens
of keV. The expected rate follows from four ingredients:

* how much dark matter passes through: the local density ρχ = 0.3 GeV/cm³ and the
  Standard Halo Model, a Maxwellian of dispersion v0 = 220 km/s seen from an Earth
  moving at vE ≈ 232 km/s, cut off at the escape speed of 544 km/s;
* how strongly it scatters: a spin-independent cross-section per nucleon σn, which
  adds coherently over the nucleus, σA = σn (μA/μn)² A²;
* how the nucleus looks at that momentum transfer: the Helm form factor;
* how big and how quiet the detector is: exposure, energy threshold, background.

Rates follow Lewin & Smith (1996). The speed integral η(vmin) is the analytic
Standard Halo Model result with a sharp cut at vesc + vE, which is accurate to a few
per cent except for light WIMPs near the kinematic edge.

An experiment that sees nothing excludes, at 90% confidence, every cross-section
that would have given it more than ~2.3 events. Drawing that limit mass by mass
gives the exclusion curve that every direct-detection paper shows.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy import optimize, special, stats

C_KM_S = 299_792.458
GEV_PER_AMU = 0.931_494
M_NUCLEON = 0.939                         # GeV
RHO_DM = 0.3                              # GeV / cm³
V0, V_EARTH, V_ESC = 220.0, 232.0, 544.0  # km/s
V_MODULATION = 15.0                       # km/s: half the swing of the Earth's orbital speed along the halo wind
PEAK_DAY = 152                            # 2 June
HBARC_MEV_FM = 197.327
SECONDS_PER_DAY = 86_400.0
KG_DAYS_PER_TONNE_YEAR = 1000 * 365.25


@dataclass(frozen=True)
class Target:
    key: str
    label: str
    mass_number: float


TARGETS = {
    t.key: t for t in [
        Target("xenon", "Xenon (A = 131)", 131.29),
        Target("argon", "Argon (A = 40)", 39.95),
        Target("germanium", "Germanium (A = 73)", 72.63),
        Target("silicon", "Silicon (A = 28)", 28.09),
    ]
}


@dataclass(frozen=True)
class Experiment:
    key: str
    label: str
    target: str
    exposure: float          # tonne-years
    threshold: float         # keV nuclear recoil
    e_max: float             # keV: top of the search window
    background: float        # expected background events in the window


EXPERIMENTS = {
    e.key: e for e in [
        Experiment("lz", "A large xenon detector (like LZ, 2024)", "xenon", 4.2, 5.0, 50.0, 1.0),
        Experiment("argon", "A large argon detector (like DarkSide-20k)", "argon", 100.0, 30.0, 200.0, 0.1),
        Experiment("germanium", "A cryogenic germanium detector (like SuperCDMS)", "germanium", 0.05, 0.5, 30.0, 5.0),
        Experiment("silicon", "A small, very low threshold silicon detector", "silicon", 0.001, 0.1, 10.0, 2.0),
    ]
}


def reduced_mass(m1: float, m2: float) -> float:
    return m1 * m2 / (m1 + m2)


def nucleus_mass(mass_number: float) -> float:
    return mass_number * GEV_PER_AMU


def helm_form_factor_sq(e_kev, mass_number: float) -> np.ndarray:
    """|F(q)|² for a nucleus, Lewin & Smith's Helm parametrisation."""
    e = np.asarray(e_kev, dtype=float)
    m_a = nucleus_mass(mass_number) * 1e3                 # MeV
    q = np.sqrt(2 * m_a * e * 1e-3) / HBARC_MEV_FM        # 1/fm
    s, a = 0.9, 0.52
    c = 1.23 * mass_number ** (1 / 3) - 0.6
    rn = math.sqrt(c * c + 7 / 3 * math.pi**2 * a * a - 5 * s * s)
    qr = np.maximum(q * rn, 1e-9)
    j1 = np.sin(qr) / qr**2 - np.cos(qr) / qr
    f = 3 * j1 / qr * np.exp(-((q * s) ** 2) / 2)
    return np.where(q * rn < 1e-6, 1.0, f * f)


def eta(v_min, v_earth: float = V_EARTH) -> np.ndarray:
    """Mean inverse speed ∫ f(v)/v d³v above v_min, in s/km."""
    v = np.asarray(v_min, dtype=float)
    val = (special.erf((v + v_earth) / V0) - special.erf((v - v_earth) / V0)) / (2 * v_earth)
    # The escape-speed cut, in the sharp approximation.
    n_esc = special.erf(V_ESC / V0) - 2 / math.sqrt(math.pi) * V_ESC / V0 * math.exp(-(V_ESC / V0) ** 2)
    return np.where(v < V_ESC + v_earth, np.maximum(val, 0.0), 0.0) / n_esc


def v_min(e_kev, m_chi: float, mass_number: float) -> np.ndarray:
    """Smallest WIMP speed that can give a nuclear recoil energy E [km/s]."""
    m_a = nucleus_mass(mass_number)
    mu = reduced_mass(m_chi, m_a)
    e_gev = np.asarray(e_kev, dtype=float) * 1e-6
    return np.sqrt(m_a * e_gev / (2 * mu * mu)) * C_KM_S


def differential_rate(e_kev, m_chi: float, sigma_n_cm2: float, target: str = "xenon",
                      v_earth: float = V_EARTH) -> np.ndarray:
    """dR/dE in events per kg per day per keV."""
    a = TARGETS[target].mass_number
    m_a = nucleus_mass(a)
    mu_a, mu_n = reduced_mass(m_chi, m_a), reduced_mass(m_chi, M_NUCLEON)
    sigma_a = sigma_n_cm2 * (mu_a / mu_n) ** 2 * a * a                       # cm²
    # Rate per target nucleus, then per kg:
    #   dR/dE = (ρχ / mχ) · σA / (2 μA²) · mA · F² · η  (natural units → per keV per day).
    n_per_kg = 1000.0 / (a * 1.660_539e-24)                                  # nuclei per kg
    eta_cm = eta(v_min(e_kev, m_chi, a), v_earth) / 1e5                      # s/cm
    prefactor = RHO_DM / m_chi * sigma_a * m_a / (2 * mu_a * mu_a)           # 1/(cm·s) per GeV … × c²
    c2 = (C_KM_S * 1e5) ** 2                                                 # (cm/s)²
    per_gev = prefactor * c2 * eta_cm * helm_form_factor_sq(e_kev, a)        # 1/(s · GeV) per nucleus
    return per_gev * 1e-6 * SECONDS_PER_DAY * n_per_kg                        # per keV per day per kg


def expected_events(m_chi: float, sigma_n_cm2: float, target: str, exposure_tonne_years: float,
                    threshold_kev: float, e_max_kev: float, v_earth: float = V_EARTH) -> float:
    """Signal events in the energy window for a given exposure."""
    e = np.geomspace(max(threshold_kev, 1e-3), max(e_max_kev, threshold_kev * 1.001), 400)
    rate = differential_rate(e, m_chi, sigma_n_cm2, target, v_earth)
    per_kg_day = float(np.trapezoid(rate, e))
    return per_kg_day * exposure_tonne_years * KG_DAYS_PER_TONNE_YEAR


def upper_limit(background: float, confidence: float = 0.9) -> float:
    """90% upper limit on the signal when the expected background is observed (rounded down)."""
    observed = math.floor(background)
    target = 1 - confidence

    def f(s):
        return stats.poisson.cdf(observed, s + background) - target

    return float(optimize.brentq(f, 0.0, 200.0 + 10 * background))


def discovery_significance(signal: float, background: float) -> float:
    """Gaussian-equivalent significance of seeing signal + background when only background is expected."""
    n = signal + background
    if signal <= 0:
        return 0.0
    if background <= 0:
        return math.inf if n >= 1 else 0.0
    p = stats.poisson.sf(math.ceil(n) - 1, background)
    return float(stats.norm.isf(max(p, 1e-300)))


def exclusion_curve(masses, experiment: Experiment | None = None, *, target: str | None = None,
                    exposure: float | None = None, threshold: float | None = None,
                    e_max: float | None = None, background: float | None = None) -> np.ndarray:
    """90% exclusion limit on σn [cm²] for each WIMP mass [GeV]."""
    e = experiment
    target = target or e.target
    exposure = exposure if exposure is not None else e.exposure
    threshold = threshold if threshold is not None else e.threshold
    e_max = e_max if e_max is not None else e.e_max
    background = background if background is not None else e.background
    limit = upper_limit(background)
    reference = 1e-45
    out = []
    for m in np.atleast_1d(masses):
        n = expected_events(float(m), reference, target, exposure, threshold, e_max)
        out.append(reference * limit / n if n > 0 else math.inf)
    return np.array(out)


def modulation(m_chi: float, sigma_n_cm2: float, target: str, exposure_tonne_years: float,
               threshold_kev: float, e_max_kev: float, days=None):
    """Expected events per day of the year: the Earth's orbit adds and subtracts from the halo wind."""
    days = np.arange(0, 365, 5) if days is None else np.asarray(days)
    v = V_EARTH + V_MODULATION * np.cos(2 * math.pi * (days - PEAK_DAY) / 365.25)
    counts = np.array([expected_events(m_chi, sigma_n_cm2, target, exposure_tonne_years,
                                       threshold_kev, e_max_kev, float(vv)) for vv in v])
    return days, counts
