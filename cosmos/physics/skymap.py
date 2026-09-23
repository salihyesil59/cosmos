"""The real microwave sky, and what you do to it before you can measure anything (S24).

The bundled map is the **WMAP 9-year ILC**: nine years of observations in five
frequency bands, combined so that everything with a non-thermal spectrum — our own
Galaxy, mostly — cancels out and the cosmic microwave background is left. It comes
with the **KQ85 analysis mask**, the team's own judgement about where the Galaxy is
still too bright to trust, and no published analysis uses the map without it.

The file here is that map resampled from HEALPix onto a longitude–latitude grid in
galactic coordinates, which is why the app needs no HEALPix library. Resampling
costs nothing on the scales that matter: the pixels are about a fifth of a degree
and the features are about a degree across.

Two things follow from the grid that every function here has to respect:

* **Cells are not equal in area.** A cell near the pole covers far less sky than one
  at the equator, so every average is weighted by cos(latitude). Forget this and the
  poles count for far more than they should.
* **Longitude is compressed near the poles.** Smoothing by a fixed number of cells
  would smooth a much larger angle there, so the longitude kernel widens as
  1/cos(latitude).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent.parent / "data" / "external" / "wmap_ilc_9yr.npz"

# WMAP's own numbers for the map that is bundled, for the app to quote.
SOURCE = "WMAP 9-year ILC (NASA LAMBDA)"
BEAM_DEGREES = 1.0                 # the ILC map is smoothed to a 1° beam
SKY_KEPT = 0.748                   # fraction of the sky the KQ85 mask keeps


@dataclass(frozen=True)
class SkyMap:
    """A temperature map on a longitude–latitude grid, with its analysis mask."""

    temperature: np.ndarray        # µK, shape (lat, lon)
    mask: np.ndarray               # 1 where the data are trusted, 0 over the Galaxy
    source: str = SOURCE

    @property
    def shape(self) -> tuple[int, int]:
        return self.temperature.shape

    @property
    def latitudes(self) -> np.ndarray:
        """Cell centres in degrees, −90 at the bottom row."""
        rows = self.shape[0]
        return (np.arange(rows) + 0.5) / rows * 180.0 - 90.0

    @property
    def longitudes(self) -> np.ndarray:
        columns = self.shape[1]
        return (np.arange(columns) + 0.5) / columns * 360.0

    @property
    def weights(self) -> np.ndarray:
        """Solid angle of each cell, up to a constant: cos(latitude)."""
        return np.cos(np.radians(self.latitudes))[:, None] * np.ones((1, self.shape[1]))


@lru_cache(maxsize=1)
def load(path: str | None = None) -> SkyMap:
    """The bundled map. Cached, because it is two megabytes of float32."""
    target = Path(path) if path else DATA
    with np.load(target) as data:
        return SkyMap(temperature=np.asarray(data["temperature"], dtype=float),
                      mask=np.asarray(data["mask"], dtype=float))


def available() -> bool:
    """False in a source checkout where tools/fetch_sky_data.py has not been run."""
    return DATA.exists()


# ------------------------------------------------------------------ statistics
def weighted_stats(sky: SkyMap, values: np.ndarray, use_mask: bool = True) -> dict:
    """Mean, rms and extremes, weighted by how much sky each cell covers."""
    weights = sky.weights * (sky.mask if use_mask else 1.0)
    total = weights.sum()
    if total <= 0:
        return {"mean": 0.0, "rms": 0.0, "min": 0.0, "max": 0.0, "sky_fraction": 0.0}
    mean = float((values * weights).sum() / total)
    variance = float((weights * (values - mean) ** 2).sum() / total)
    visible = values[weights > 0]
    return {
        "mean": mean,
        "rms": math.sqrt(max(variance, 0.0)),
        "min": float(visible.min()),
        "max": float(visible.max()),
        "sky_fraction": float(total / sky.weights.sum()),
    }


def remove_monopole_and_dipole(sky: SkyMap, values: np.ndarray, use_mask: bool = True):
    """Fit and subtract the constant and the ±1 gradient across the sky.

    The monopole is the 2.725 K average, which says nothing about the ripples; the
    dipole is our own 370 km/s motion through the radiation, a 3 mK effect a hundred
    times larger than everything cosmological. Both are removed before anybody looks
    at a CMB map — WMAP's ILC already has them out, so what this removes here is only
    the small residual the masking and resampling leave behind.
    """
    lat = np.radians(sky.latitudes)[:, None]
    lon = np.radians(sky.longitudes)[None, :]
    basis = np.stack([
        np.ones_like(values),
        np.broadcast_to(np.cos(lat) * np.cos(lon), values.shape),
        np.broadcast_to(np.cos(lat) * np.sin(lon), values.shape),
        np.broadcast_to(np.sin(lat) * np.ones_like(lon), values.shape),
    ])
    weights = sky.weights * (sky.mask if use_mask else 1.0)
    flat_w = weights.ravel()
    design = basis.reshape(4, -1).T * flat_w[:, None]
    target = values.ravel() * flat_w
    coefficients, *_ = np.linalg.lstsq(design, target, rcond=None)
    model = np.tensordot(coefficients, basis, axes=(0, 0))
    return values - model, coefficients


# ------------------------------------------------------------------- filtering
def smooth(sky: SkyMap, values: np.ndarray, degrees: float) -> np.ndarray:
    """Blur the map with a Gaussian of the given width on the sky.

    Separable and approximate: a fixed kernel down the latitude axis, and a kernel
    that widens as 1/cos(latitude) across longitude, because a degree of longitude
    covers less sky the further from the equator you go.
    """
    if degrees <= 0:
        return values
    rows, columns = sky.shape
    per_row = 180.0 / rows
    sigma_rows = degrees / per_row
    result = _gaussian_axis(values, sigma_rows, axis=0, wrap=False)

    per_column = 360.0 / columns
    cos_lat = np.cos(np.radians(sky.latitudes))
    for row in range(rows):
        scale = max(cos_lat[row], 1e-3)
        sigma = degrees / (per_column * scale)
        if sigma < 0.3:
            continue
        result[row] = _gaussian_axis(result[row][None, :], sigma, axis=1, wrap=True)[0]
    return result


def _gaussian_axis(values: np.ndarray, sigma: float, axis: int, wrap: bool) -> np.ndarray:
    if sigma < 0.3:
        return values.copy()
    radius = max(int(math.ceil(3 * sigma)), 1)
    offsets = np.arange(-radius, radius + 1)
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    kernel /= kernel.sum()
    mode = "wrap" if wrap else "edge"
    padding = [(0, 0), (0, 0)]
    padding[axis] = (radius, radius)
    padded = np.pad(values, padding, mode=mode)
    out = np.zeros_like(values, dtype=float)
    for weight, offset in zip(kernel, offsets):
        index = offset + radius
        if axis == 0:
            out += weight * padded[index:index + values.shape[0], :]
        else:
            out += weight * padded[:, index:index + values.shape[1]]
    return out


def high_pass(sky: SkyMap, values: np.ndarray, degrees: float) -> np.ndarray:
    """Keep only what is smaller than ``degrees`` across, by subtracting the blur."""
    return values - smooth(sky, values, degrees)


# ------------------------------------------------- the angular correlation function
def correlation(sky: SkyMap, values: np.ndarray, use_mask: bool = True,
                bins: np.ndarray | None = None, samples: int = 4000,
                seed: int = 17) -> tuple[np.ndarray, np.ndarray]:
    """C(θ): how alike two points are, as a function of how far apart they lie.

    Measured by taking a random sample of trusted cells and averaging the product of
    their temperatures in bins of separation. This is the real two-point function of
    the CMB, and its first zero crossing near 1° is the acoustic scale showing up in
    real space rather than in a power spectrum.
    """
    bins = np.linspace(0.0, 20.0, 41) if bins is None else np.asarray(bins, dtype=float)
    weights = sky.weights * (sky.mask if use_mask else 1.0)
    rows, columns = sky.shape
    good = np.flatnonzero(weights.ravel() > 0)
    if good.size < 100:
        return 0.5 * (bins[:-1] + bins[1:]), np.full(len(bins) - 1, np.nan)

    rng = np.random.default_rng(seed)
    # Sample proportionally to solid angle, so the poles do not dominate.
    probability = weights.ravel()[good]
    probability = probability / probability.sum()
    picked = rng.choice(good, size=min(samples, good.size), replace=False, p=probability)

    lat = np.radians(sky.latitudes)[picked // columns]
    lon = np.radians(sky.longitudes)[picked % columns]
    temperature = values.ravel()[picked]
    vectors = np.stack([np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=1)

    upper = np.triu_indices(len(picked), k=1)
    cosines = np.clip(np.einsum("ij,kj->ik", vectors, vectors)[upper], -1.0, 1.0)
    separation = np.degrees(np.arccos(cosines))
    products = np.outer(temperature, temperature)[upper]

    index = np.digitize(separation, bins) - 1
    inside = (index >= 0) & (index < len(bins) - 1)
    total = np.bincount(index[inside], weights=products[inside], minlength=len(bins) - 1)
    count = np.bincount(index[inside], minlength=len(bins) - 1)
    with np.errstate(invalid="ignore", divide="ignore"):
        curve = np.where(count > 0, total / np.maximum(count, 1), np.nan)
    return 0.5 * (bins[:-1] + bins[1:]), curve


def correlation_half_width(theta: np.ndarray, curve: np.ndarray) -> float:
    """Where C(θ) has fallen to half its value at zero separation, in degrees.

    A blunt but honest measure of how big a typical spot is. Within 20° the CMB
    correlation function never crosses zero — it falls steeply and then flattens —
    so the half-width, not a zero crossing, is what these angles can measure.
    """
    finite = np.isfinite(curve)
    if not finite.any():
        return float("nan")
    theta, curve = theta[finite], curve[finite]
    half = curve[0] / 2.0
    below = np.flatnonzero(curve <= half)
    if below.size == 0:
        return float(theta[-1])
    first = below[0]
    if first == 0:
        return float(theta[0])
    # Linear interpolation between the last point above the half and the first below.
    x0, x1 = theta[first - 1], theta[first]
    y0, y1 = curve[first - 1], curve[first]
    if y0 == y1:
        return float(x1)
    return float(x0 + (half - y0) * (x1 - x0) / (y1 - y0))


def hottest_and_coldest(sky: SkyMap, values: np.ndarray, use_mask: bool = True):
    """Where the extremes are, as (latitude, longitude, temperature) in degrees and µK."""
    weights = sky.weights * (sky.mask if use_mask else 1.0)
    masked = np.where(weights > 0, values, np.nan)
    hot = np.unravel_index(np.nanargmax(masked), masked.shape)
    cold = np.unravel_index(np.nanargmin(masked), masked.shape)
    return tuple(
        (float(sky.latitudes[row]), float(sky.longitudes[column]), float(values[row, column]))
        for row, column in (hot, cold)
    )


def rms_against_smoothing(sky: SkyMap, scales: np.ndarray | None = None,
                          use_mask: bool = True) -> tuple[np.ndarray, np.ndarray]:
    """How much structure survives as the map is blurred — the acoustic scale, felt."""
    scales = np.array([0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 7.0, 10.0]) if scales is None \
        else np.asarray(scales, dtype=float)
    values = sky.temperature
    return scales, np.array([weighted_stats(sky, smooth(sky, values, s), use_mask)["rms"]
                             for s in scales])
