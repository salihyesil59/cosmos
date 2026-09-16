"""Olbers' paradox: why is the night sky dark?

In an infinite, static, eternal universe filled uniformly with stars, every line
of sight ends on the surface of a star. A line of sight of length D hits a star
with probability 1 − exp(−D/λ), where the mean free path is λ = 1/(n π R²) for
stars of radius R and number density n.

Three things make the real sky dark:

* the universe has a finite age, so we only see stars within the light-travel
  distance (the sky is a finite "forest" of stars);
* stars shine for a limited time, which lowers the density of shining stars;
* expansion redshifts distant light, dimming surface brightness as (1 + z)⁻⁴.

The sky-patch generator draws stars as discs for a teaching universe measured in
units of the stellar radius; stars too far away to draw as discs are handled line
of sight by line of sight with the exact exponential statistics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from cosmos.physics import constants as const

MAX_DRAWN_STARS = 40_000
DRAW_DEPTH = 400.0            # stars closer than this (in stellar radii) are drawn as discs
FIELD_RAD = 0.35              # side of the square sky patch (about 20°)
R_MIN = 1.5                   # the observer is not inside a star


def mean_free_path(density: float, radius: float = 1.0) -> float:
    """Average distance a line of sight travels before hitting a star."""
    return 1.0 / (density * math.pi * radius**2)


def sky_coverage(depth: float, mfp: float) -> float:
    """Fraction of the sky covered by star discs out to distance ``depth``."""
    if math.isinf(depth):
        return 1.0
    return 1.0 - math.exp(-depth / mfp)


def redshift_factor(distance, hubble_length: float | None):
    """1 + z for light that travelled ``distance`` at constant expansion rate (de Sitter)."""
    d = np.asarray(distance, dtype=float)
    if hubble_length is None or math.isinf(hubble_length):
        return np.ones_like(d)
    return np.exp(d / hubble_length)


def sky_brightness(depth: float, mfp: float, hubble_length: float | None = None) -> float:
    """Average sky surface brightness as a fraction of a star's surface.

    Integrates the first-hit probability e^(−x/λ) dx/λ weighted by the (1 + z)⁻⁴
    dimming with 1 + z = e^(x/L).
    """
    if hubble_length is None or math.isinf(hubble_length):
        return sky_coverage(depth, mfp)
    inv = 1 / mfp + 4 / hubble_length
    if math.isinf(depth):
        return (1 / mfp) / inv
    return (1 / mfp) / inv * (1 - math.exp(-depth * inv))


@dataclass(frozen=True)
class SkyPatch:
    image: np.ndarray        # brightness per pixel, 0 … 1 (fraction of a star's surface)
    distance: np.ndarray     # distance to the star seen in each pixel (inf for dark pixels)
    n_drawn: int             # stars drawn as discs
    truncated: bool          # True if MAX_DRAWN_STARS was reached
    coverage: float          # fraction of pixels showing a star
    brightness: float        # mean brightness


def generate_sky(
    density: float,
    depth: float,
    *,
    hubble_length: float | None = None,
    pixels: int = 280,
    seed: int = 1,
) -> SkyPatch:
    """Monte Carlo view of a square patch of sky in a universe of stars of radius 1."""
    rng = np.random.default_rng(seed)
    pix = FIELD_RAD / pixels
    image = np.zeros((pixels, pixels))
    dist = np.full((pixels, pixels), np.inf)
    near = max(min(depth, DRAW_DEPTH), R_MIN)

    # Stars within the drawing depth. A star at distance r has angular radius 1/r, so it overlaps the patch
    # if its centre lies within f/2 + 1/r of the middle: the number per unit distance is n (f r + 2)².
    f = FIELD_RAD
    lo, hi = (f * R_MIN + 2) ** 3, (f * near + 2) ** 3
    expected = density * (hi - lo) / (3 * f)
    n = int(rng.poisson(expected)) if expected < 1e7 else MAX_DRAWN_STARS + 1
    truncated = n > MAX_DRAWN_STARS
    n = min(n, MAX_DRAWN_STARS)
    r = ((lo + rng.random(n) * (hi - lo)) ** (1 / 3) - 2) / f
    r = np.sort(r)[::-1]
    half = f / 2 + 1 / r
    x = rng.uniform(-half, half)
    y = rng.uniform(-half, half)
    ang_r = 1.0 / r
    bright = redshift_factor(r, hubble_length) ** -4.0
    for xi, yi, ai, di, bi in zip(x, y, ang_r, r, bright):
        cx = (xi + FIELD_RAD / 2) / pix
        cy = (yi + FIELD_RAD / 2) / pix
        rad = ai / pix
        if rad < 0.5:
            # Sub-pixel star: it covers the pixel it falls in with probability equal to its area.
            ix, iy = int(cx), int(cy)
            if 0 <= ix < pixels and 0 <= iy < pixels and rng.random() < math.pi * rad * rad:
                image[iy, ix] = bi
                dist[iy, ix] = di
            continue
        x0, x1 = max(int(cx - rad), 0), min(int(cx + rad) + 1, pixels)
        y0, y1 = max(int(cy - rad), 0), min(int(cy + rad) + 1, pixels)
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        mask = (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= rad * rad
        image[y0:y1, x0:x1][mask] = bi
        dist[y0:y1, x0:x1][mask] = di

    # Beyond the drawing depth: each empty line of sight hits a star after an exponential distance.
    if depth > near:
        mfp = mean_free_path(density)
        empty = np.isinf(dist)
        hit = near + rng.exponential(mfp, size=empty.sum())
        seen = hit < depth
        vals = np.zeros_like(hit)
        vals[seen] = redshift_factor(hit[seen], hubble_length) ** -4.0
        image[empty] = vals
        d = np.full_like(hit, np.inf)
        d[seen] = hit[seen]
        dist[empty] = d

    return SkyPatch(image, dist, n, truncated, float(np.isfinite(dist).mean()), float(image.mean()))


# ---------------------------------------------------------------- real universe
@dataclass(frozen=True)
class RealUniverse:
    star_density_m3: float
    mean_free_path_ly: float
    visible_depth_ly: float
    coverage: float
    filling_time_yr: float
    sun_lifetime_yr: float
    daylight_factor: float


def real_universe() -> RealUniverse:
    """Order-of-magnitude numbers for our universe.

    Stellar mass density Ω* ≈ 0.003 of the critical density with an average star of
    half a solar mass and the Sun's radius.
    """
    rho_crit = 3 * (67.7e3 / const.MPC) ** 2 / (8 * math.pi * const.G)
    n = 0.003 * rho_crit / (0.5 * 1.989e30)
    radius = 6.96e8
    mfp_m = 1 / (n * math.pi * radius**2)
    ly = const.C * const.YEAR
    depth_ly = 13.8e9                        # light-travel distance: what a finite age allows
    coverage = -math.expm1(-depth_ly / (mfp_m / ly))
    # The Sun's disc covers 6.8e-5 sr; a sky made of solar surface (seen over a hemisphere, weighted
    # by cos θ) gives π / 6.8e-5 times the sunlight on a surface facing the Sun.
    sun_solid_angle = math.pi * (radius / 1.496e11) ** 2
    return RealUniverse(n, mfp_m / ly, depth_ly, coverage, mfp_m / ly, 1e10, math.pi / sun_solid_angle)
