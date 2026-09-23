"""The cosmic distance ladder, rung by rung, with its error budget (S20, L7.3).

A toy version of how the local Hubble constant is measured (the SH0ES approach):

1. **Parallax.** Milky Way Cepheids with measured parallaxes calibrate the zero
   point of the Leavitt law, M = a + b (log P − 1).
2. **Calibrators.** Galaxies close enough to resolve Cepheids that also hosted a
   type Ia supernova: their Cepheids give the distance, and the supernova's
   apparent brightness then gives the supernova absolute magnitude M_B.
3. **Hubble flow.** Distant supernovae with redshifts: their apparent magnitudes
   and M_B give distances, and distance against redshift gives H0.

Everything here is **simulated**: the "true" H0 of the toy universe is an input.
The point is not the value but the bookkeeping — how each rung's uncertainty
propagates into H0, and how a systematic error survives any amount of data.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

C_KM_S = 299_792.458
LN10 = math.log(10)

LEAVITT_SLOPE = -3.26            # mag per dex of period (near-infrared Wesenheit magnitudes)
LEAVITT_ZERO_POINT = -5.93       # absolute magnitude of a 10-day Cepheid
SN_ABSOLUTE_MAGNITUDE = -19.25   # peak M_B of a standardised type Ia supernova
Q0, J0 = -0.55, 1.0              # low-redshift expansion history used for the Hubble flow
PECULIAR_VELOCITY_KM_S = 250.0

PLANCK_H0 = (67.4, 0.5)
SHOES_H0 = (73.04, 1.04)

RUNGS = ("parallax", "calibrators", "flow")
RUNG_LABELS = {
    "parallax": "Parallaxes → Leavitt law",
    "calibrators": "Cepheid hosts → supernova M_B",
    "flow": "Hubble-flow supernovae → H0",
}


@dataclass(frozen=True)
class LadderSettings:
    true_h0: float = 73.0
    # rung 1
    n_parallax: int = 20
    parallax_error_uas: float = 30.0
    parallax_offset_uas: float = 0.0        # systematic: a zero-point error in every parallax
    # rung 2
    n_hosts: int = 20
    cepheids_per_host: int = 40
    cepheid_scatter: float = 0.15           # mag, intrinsic scatter of the Leavitt law
    crowding_bias: float = 0.0              # systematic: host Cepheids look brighter by this (mag)
    # rung 3
    n_flow: int = 100
    sn_scatter: float = 0.13                # mag, after standardisation
    z_range: tuple[float, float] = (0.023, 0.15)
    seed: int = 1


PRESETS: dict[str, tuple[str, LadderSettings]] = {
    "key_project": ("Hubble Key Project style (2001)", LadderSettings(
        n_parallax=10, parallax_error_uas=120.0, n_hosts=6, cepheids_per_host=20, cepheid_scatter=0.25,
        n_flow=36, sn_scatter=0.18)),
    "shoes": ("SH0ES style (2022)", LadderSettings(
        n_parallax=40, parallax_error_uas=20.0, n_hosts=40, cepheids_per_host=80, cepheid_scatter=0.15,
        n_flow=300, sn_scatter=0.13)),
    "gaia": ("A future Gaia-era ladder", LadderSettings(
        n_parallax=150, parallax_error_uas=10.0, n_hosts=60, cepheids_per_host=100, cepheid_scatter=0.12,
        n_flow=1000, sn_scatter=0.11)),
}


@dataclass
class Rung1:
    log_period: np.ndarray
    parallax_uas: np.ndarray
    parallax_error_uas: np.ndarray
    apparent_mag: np.ndarray
    zero_point: float
    zero_point_error: float


@dataclass
class Rung2:
    true_modulus: np.ndarray
    modulus: np.ndarray
    modulus_error: np.ndarray
    sn_mag: np.ndarray
    cepheid_log_period: list[np.ndarray]
    cepheid_mag: list[np.ndarray]
    sn_absolute: float
    sn_absolute_error: float          # from the hosts alone, without the rung-1 zero point


@dataclass
class Rung3:
    z: np.ndarray
    mag: np.ndarray
    intercept: float                  # a_B = ⟨log10(cz f(z)) − 0.2 m⟩
    intercept_error: float


@dataclass
class LadderResult:
    settings: LadderSettings
    rung1: Rung1
    rung2: Rung2
    rung3: Rung3
    h0: float
    budget_percent: dict[str, float] = field(default_factory=dict)

    @property
    def error_percent(self) -> float:
        return math.sqrt(sum(v**2 for v in self.budget_percent.values()))

    @property
    def h0_error(self) -> float:
        return self.h0 * self.error_percent / 100

    @property
    def dominant(self) -> str:
        return max(self.budget_percent, key=self.budget_percent.get)

    def tension_with(self, reference: tuple[float, float] = PLANCK_H0) -> float:
        value, error = reference
        return (self.h0 - value) / math.hypot(self.h0_error, error)


# --------------------------------------------------------------------- helpers
def leavitt_magnitude(log_period, zero_point: float = LEAVITT_ZERO_POINT) -> np.ndarray:
    return zero_point + LEAVITT_SLOPE * (np.asarray(log_period) - 1.0)


def distance_modulus(distance_pc) -> np.ndarray:
    return 5 * np.log10(np.asarray(distance_pc)) - 5


def expansion_factor(z) -> np.ndarray:
    """cz f(z) ≈ H0 d_L to third order in z (Riess et al. 2016, eq. 5)."""
    z = np.asarray(z)
    return 1 + 0.5 * (1 - Q0) * z - (1 - Q0 - 3 * Q0**2 + J0) * z**2 / 6


def h0_from(sn_absolute: float, intercept: float) -> float:
    """log10 H0 = 0.2 M_B + a_B + 5."""
    return 10 ** (0.2 * sn_absolute + intercept + 5)


# --------------------------------------------------------------------- the ladder
def build(settings: LadderSettings, noise: bool = True) -> LadderResult:
    """Simulate one set of observations and climb the ladder."""
    s = settings
    rng = np.random.default_rng(s.seed)
    k = 1.0 if noise else 0.0

    # Rung 1 — Milky Way Cepheids between 0.5 and 3 kpc.
    n1 = max(int(s.n_parallax), 2)
    distance_pc = rng.uniform(500, 3000, n1)
    log_p1 = rng.uniform(0.4, 1.6, n1)
    true_parallax = 1e6 / distance_pc
    parallax = true_parallax + s.parallax_offset_uas + k * rng.normal(0, s.parallax_error_uas, n1)
    parallax = np.maximum(parallax, 1.0)
    m1 = leavitt_magnitude(log_p1) + distance_modulus(distance_pc) + k * rng.normal(0, s.cepheid_scatter, n1)
    mu1 = distance_modulus(1e6 / parallax)
    sigma_mu1 = 5 / LN10 * s.parallax_error_uas / parallax
    total1 = np.sqrt(sigma_mu1**2 + s.cepheid_scatter**2)
    w1 = 1 / total1**2
    zero_points = m1 - LEAVITT_SLOPE * (log_p1 - 1) - mu1
    a_hat = float(np.sum(w1 * zero_points) / np.sum(w1))
    a_err = float(1 / math.sqrt(np.sum(w1)))
    rung1 = Rung1(log_p1, parallax, np.full(n1, s.parallax_error_uas), m1, a_hat, a_err)

    # Rung 2 — calibrator galaxies between 7 and 40 Mpc.
    n2 = max(int(s.n_hosts), 1)
    per_host = max(int(s.cepheids_per_host), 2)
    host_mu = distance_modulus(rng.uniform(7e6, 4e7, n2))
    mu_hat, mu_err, sn_mag, logs, mags = [], [], [], [], []
    for mu in host_mu:
        log_p = rng.uniform(0.8, 2.0, per_host)
        m = (leavitt_magnitude(log_p) + mu - s.crowding_bias
             + k * rng.normal(0, s.cepheid_scatter, per_host))
        estimate = float(np.mean(m - LEAVITT_SLOPE * (log_p - 1) - a_hat))
        mu_hat.append(estimate)
        mu_err.append(s.cepheid_scatter / math.sqrt(per_host))
        sn_mag.append(SN_ABSOLUTE_MAGNITUDE + mu + k * rng.normal(0, s.sn_scatter))
        logs.append(log_p)
        mags.append(m)
    mu_hat, mu_err, sn_mag = np.array(mu_hat), np.array(mu_err), np.array(sn_mag)
    per_host_error = np.sqrt(s.sn_scatter**2 + mu_err**2)
    w2 = 1 / per_host_error**2
    mb_hat = float(np.sum(w2 * (sn_mag - mu_hat)) / np.sum(w2))
    mb_err = float(1 / math.sqrt(np.sum(w2)))
    rung2 = Rung2(host_mu, mu_hat, mu_err, sn_mag, logs, mags, mb_hat, mb_err)

    # Rung 3 — supernovae in the smooth Hubble flow.
    n3 = max(int(s.n_flow), 2)
    z = rng.uniform(*s.z_range, n3)
    luminosity_distance = C_KM_S * z * expansion_factor(z) / s.true_h0
    z_obs = z + k * rng.normal(0, PECULIAR_VELOCITY_KM_S / C_KM_S, n3)
    m3 = (SN_ABSOLUTE_MAGNITUDE + distance_modulus(luminosity_distance * 1e6)
          + k * rng.normal(0, s.sn_scatter, n3))
    x = np.log10(C_KM_S * z_obs * expansion_factor(z_obs)) - 0.2 * m3
    # scatter in x: 0.2 × magnitude scatter plus the peculiar-velocity term, which fades with distance
    sigma_x = np.sqrt((0.2 * s.sn_scatter) ** 2 + (PECULIAR_VELOCITY_KM_S / (C_KM_S * z_obs * LN10)) ** 2)
    w3 = 1 / sigma_x**2
    a_b = float(np.sum(w3 * x) / np.sum(w3))
    a_b_err = float(1 / math.sqrt(np.sum(w3)))
    rung3 = Rung3(z_obs, m3, a_b, a_b_err)

    h0 = h0_from(mb_hat, a_b)
    # M_B inherits the rung-1 zero point one to one, so the three terms are independent.
    budget = {
        "parallax": 100 * LN10 * 0.2 * a_err,
        "calibrators": 100 * LN10 * 0.2 * mb_err,
        "flow": 100 * LN10 * a_b_err,
    }
    return LadderResult(s, rung1, rung2, rung3, h0, budget)


def systematic_shift(settings: LadderSettings) -> float:
    """How far H0 moves because of the systematics alone (km/s/Mpc), free of any noise."""
    biased = build(settings, noise=False).h0
    clean = build(replace(settings, parallax_offset_uas=0.0, crowding_bias=0.0), noise=False).h0
    return biased - clean


def monte_carlo(settings: LadderSettings, runs: int = 300) -> np.ndarray:
    """H0 from many independent realisations of the same observing programme."""
    return np.array([build(replace(settings, seed=settings.seed * 1000 + i)).h0 for i in range(runs)])
