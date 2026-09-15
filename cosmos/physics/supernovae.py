"""Type Ia supernova cosmology: simulated samples and parameter fits.

The samples generated here are synthetic, not real observations. They mimic
the redshift coverage and scatter of the 1998 discovery samples and of modern
compilations such as Pantheon+, so learners can repeat the analysis.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from cosmos.physics.cosmology import Cosmology

C_KM_S = 299_792.458
M_CEPHEID = -19.253      # SH0ES absolute magnitude calibration (Riess et al. 2022)
M_INVERSE_LADDER = -19.40  # calibration implied by the CMB sound horizon and BAO
TRUE_H0 = 73.0           # H0 used to generate the synthetic samples with M_CEPHEID


@dataclass(frozen=True)
class SupernovaSample:
    key: str
    label: str
    description: str
    z: np.ndarray
    m: np.ndarray        # apparent peak magnitude (standardised)
    error: np.ndarray    # total magnitude uncertainty


def _generate(key, label, description, z, sigma, seed) -> SupernovaSample:
    truth = Cosmology.flat(H0=TRUE_H0, Om0=0.3, Tcmb0=0.0)
    mu = truth.distance_modulus(z)
    rng = np.random.default_rng(seed)
    err = np.full_like(z, sigma)
    m = mu + M_CEPHEID + rng.normal(0, sigma, z.size)
    order = np.argsort(z)
    return SupernovaSample(key, label, description, z[order], m[order], err[order])


def discovery_sample(seed: int = 2005) -> SupernovaSample:
    rng = np.random.default_rng(seed)
    z = np.concatenate([rng.uniform(0.01, 0.1, 18), rng.uniform(0.3, 0.85, 42)])
    return _generate(
        "discovery", "1998-like sample (60 supernovae)",
        "Simulated to resemble the discovery data: 18 nearby and 42 distant supernovae "
        "up to z ≈ 0.85, with 0.17 mag scatter. Not real measurements.",
        z, 0.17, seed + 1,
    )


def modern_sample(seed: int = 2022) -> SupernovaSample:
    rng = np.random.default_rng(seed)
    z = np.concatenate([
        rng.uniform(0.01, 0.1, 250), rng.uniform(0.1, 0.8, 450), rng.uniform(0.8, 1.5, 150),
        rng.uniform(1.5, 2.3, 30),
    ])
    return _generate(
        "modern", "Modern-like sample (880 supernovae)",
        "Simulated to resemble modern compilations such as Pantheon+: hundreds of supernovae up "
        "to z ≈ 2.3 with 0.14 mag scatter. Not real measurements.",
        z, 0.14, seed + 1,
    )


SAMPLES = {"discovery": discovery_sample, "modern": modern_sample}


def dimensionless_luminosity_distance(z, om, ol) -> np.ndarray:
    """H0 D_L / c for a grid of (Ωm, ΩΛ) models, no radiation.

    ``om`` and ``ol`` may be arrays of equal shape; the result has shape
    ``om.shape + z.shape``. Models without a Big Bang in the probed range give nan.
    """
    z = np.asarray(z, dtype=float)
    om = np.atleast_1d(np.asarray(om, dtype=float))
    ol = np.atleast_1d(np.asarray(ol, dtype=float))
    shape = om.shape
    om, ol = om.ravel()[:, None], ol.ravel()[:, None]
    ok = 1 - om - ol
    zmax = float(z.max())
    grid = np.linspace(0.0, zmax, max(400, int(zmax * 300)))
    zp = 1 + grid[None, :]
    e2 = om * zp**3 + ok * zp**2 + ol
    valid = np.all(e2 > 0, axis=1)
    inv_e = 1 / np.sqrt(np.where(e2 > 0, e2, np.nan))
    dz = np.diff(grid)
    chi = np.concatenate([np.zeros((inv_e.shape[0], 1)),
                          np.cumsum(0.5 * (inv_e[:, 1:] + inv_e[:, :-1]) * dz, axis=1)], axis=1)
    chi_z = np.array([np.interp(z, grid, row) for row in chi])
    sk = np.sqrt(np.abs(ok))
    with np.errstate(invalid="ignore", divide="ignore"):
        dm = np.where(ok > 1e-8, np.sinh(sk * chi_z) / np.where(sk > 0, sk, 1),
                      np.where(ok < -1e-8, np.sin(sk * chi_z) / np.where(sk > 0, sk, 1), chi_z))
    dl = (1 + z)[None, :] * dm
    dl[~valid] = np.nan
    return dl.reshape(shape + z.shape)


@dataclass(frozen=True)
class GridFit:
    om: np.ndarray
    ol: np.ndarray
    chi2: np.ndarray
    best_om: float
    best_ol: float
    chi2_min: float
    offset: float                  # fitted M + 5 log10(c/H0 / Mpc) + 25
    acceleration_sigma: float      # how strongly q0 < 0 is preferred
    dark_energy_sigma: float       # how strongly ΩΛ > 0 is preferred

    def hubble_constant(self, absolute_magnitude: float) -> float:
        """H0 [km/s/Mpc] implied by a calibration of the absolute magnitude M."""
        return C_KM_S / 10 ** ((self.offset - absolute_magnitude - 25) / 5)


def fit_grid(sample: SupernovaSample, n: int = 61, om_range=(0.0, 1.5), ol_range=(-0.5, 2.0)) -> GridFit:
    """χ² over a grid of (Ωm, ΩΛ), marginalising analytically over the magnitude offset."""
    om_axis = np.linspace(*om_range, n)
    ol_axis = np.linspace(*ol_range, n)
    om, ol = np.meshgrid(om_axis, ol_axis, indexing="ij")
    dl = dimensionless_luminosity_distance(sample.z, om, ol)
    with np.errstate(divide="ignore", invalid="ignore"):
        shape_mu = 5 * np.log10(dl)
    w = 1 / sample.error**2
    resid = sample.m[None, None, :] - shape_mu
    offset = np.sum(w * resid, axis=-1) / np.sum(w)
    chi2 = np.sum(w * (resid - offset[..., None]) ** 2, axis=-1)
    chi2 = np.where(np.isfinite(chi2), chi2, np.inf)
    i, j = np.unravel_index(np.argmin(chi2), chi2.shape)
    def preference(excluded) -> float:
        if not np.any(excluded) or not np.isfinite(chi2[i, j]):
            return 0.0
        return math.sqrt(max(float(np.min(chi2[excluded]) - chi2[i, j]), 0.0))

    return GridFit(
        om=om, ol=ol, chi2=chi2, best_om=float(om[i, j]), best_ol=float(ol[i, j]),
        chi2_min=float(chi2[i, j]), offset=float(offset[i, j]),
        acceleration_sigma=preference(ol <= om / 2),
        dark_energy_sigma=preference(ol <= 0),
    )


def distance_modulus_shape(z, om: float, ol: float) -> np.ndarray:
    """5 log10(H0 D_L / c) for a single model."""
    dl = dimensionless_luminosity_distance(z, om, ol)[0]
    with np.errstate(divide="ignore", invalid="ignore"):
        return 5 * np.log10(dl)


@dataclass(frozen=True)
class FlatFit:
    om: np.ndarray
    chi2: np.ndarray
    best_om: float
    acceleration_sigma: float   # preference for Ωm < 2/3, i.e. q0 < 0 in a flat universe

    @property
    def best_ol(self) -> float:
        return 1.0 - self.best_om


def fit_flat(sample: SupernovaSample, n: int = 301) -> FlatFit:
    """χ² along flat models ΩΛ = 1 − Ωm (a common extra assumption)."""
    om = np.linspace(0.0, 1.2, n)
    dl = dimensionless_luminosity_distance(sample.z, om, 1.0 - om)
    with np.errstate(divide="ignore", invalid="ignore"):
        shape_mu = 5 * np.log10(dl)
    w = 1 / sample.error**2
    resid = sample.m[None, :] - shape_mu
    offset = np.sum(w * resid, axis=-1) / np.sum(w)
    chi2 = np.sum(w * (resid - offset[:, None]) ** 2, axis=-1)
    chi2 = np.where(np.isfinite(chi2), chi2, np.inf)
    i = int(np.argmin(chi2))
    decelerating = om >= 2 / 3
    delta = float(np.min(chi2[decelerating]) - chi2[i])
    return FlatFit(om=om, chi2=chi2, best_om=float(om[i]), acceleration_sigma=math.sqrt(max(delta, 0.0)))
