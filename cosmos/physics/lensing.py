"""Gravitational lensing by point masses and isothermal spheres.

Angles are in arcseconds unless stated otherwise.
"""

from __future__ import annotations

import math

import numpy as np

from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology

RAD_TO_ARCSEC = 648_000 / math.pi


def lens_distances(c: Cosmology, z_lens: float, z_source: float) -> tuple[float, float, float]:
    """Angular diameter distances D_l, D_s, D_ls [Mpc] (valid for flat or curved space)."""
    if z_source <= z_lens:
        raise ValueError("the source must be behind the lens")
    dm_l = float(c.transverse_comoving_distance(z_lens))
    dm_s = float(c.transverse_comoving_distance(z_source))
    ok, dh = c.Ok0, c.hubble_distance
    # Generalised distance between two redshifts (Hogg 1999, eq. 19).
    dm_ls = dm_s * math.sqrt(1 + ok * dm_l**2 / dh**2) - dm_l * math.sqrt(1 + ok * dm_s**2 / dh**2)
    return dm_l / (1 + z_lens), dm_s / (1 + z_source), dm_ls / (1 + z_source)


def einstein_radius_point(c: Cosmology, mass_msun: float, z_lens: float, z_source: float) -> float:
    """Einstein radius of a point mass [arcsec]: θ_E² = 4GM/c² · D_ls/(D_l D_s)."""
    d_l, d_s, d_ls = lens_distances(c, z_lens, z_source)
    theta2 = 4 * const.G * mass_msun * const.M_SUN / const.C**2 * d_ls / (d_l * d_s * const.MPC)
    return math.sqrt(theta2) * RAD_TO_ARCSEC


def einstein_radius_sis(c: Cosmology, sigma_km_s: float, z_lens: float, z_source: float) -> float:
    """Einstein radius of a singular isothermal sphere [arcsec]: 4π (σ/c)² D_ls/D_s."""
    _d_l, d_s, d_ls = lens_distances(c, z_lens, z_source)
    return 4 * math.pi * (sigma_km_s * 1e3 / const.C) ** 2 * d_ls / d_s * RAD_TO_ARCSEC


def mass_inside_einstein_radius(c: Cosmology, theta_e_arcsec: float, z_lens: float, z_source: float) -> float:
    """Projected mass [M☉] enclosed by an Einstein ring of the given radius."""
    d_l, d_s, d_ls = lens_distances(c, z_lens, z_source)
    theta = theta_e_arcsec / RAD_TO_ARCSEC
    return theta**2 * const.C**2 / (4 * const.G) * d_l * d_s / d_ls * const.MPC / const.M_SUN


def deflection(theta_x, theta_y, lenses):
    """Total deflection (α_x, α_y) [arcsec] from a list of lenses.

    Each lens is ``(kind, x0, y0, theta_e)`` with kind ``"point"`` or ``"sis"``.
    """
    ax = np.zeros_like(theta_x, dtype=float)
    ay = np.zeros_like(theta_y, dtype=float)
    for kind, x0, y0, te in lenses:
        dx, dy = theta_x - x0, theta_y - y0
        r2 = np.maximum(dx * dx + dy * dy, 1e-6)
        if kind == "point":
            factor = te * te / r2
        elif kind == "sis":
            factor = te / np.sqrt(r2)
        else:
            raise ValueError(f"unknown lens kind {kind!r}")
        ax += factor * dx
        ay += factor * dy
    return ax, ay


def point_lens_image_positions(beta: float, theta_e: float) -> tuple[float, float]:
    """Positions of the two images of a point lens along the source direction [same units]."""
    root = math.sqrt(beta * beta + 4 * theta_e * theta_e)
    return 0.5 * (beta + root), 0.5 * (beta - root)


def point_lens_magnification(beta: float, theta_e: float) -> float:
    """Total magnification of both images: μ = (u² + 2) / (u √(u² + 4)), u = β/θ_E."""
    u = max(abs(beta) / theta_e, 1e-9)
    return (u * u + 2) / (u * math.sqrt(u * u + 4))


def background_sky(n: int = 400, field_arcsec: float = 20.0, seed: int = 5, n_galaxies: int = 70):
    """Procedural image of background galaxies (RGB float array, values 0..1)."""
    rng = np.random.default_rng(seed)
    coords = (np.arange(n) + 0.5) / n * field_arcsec - field_arcsec / 2
    x, y = np.meshgrid(coords, coords)
    image = np.zeros((n, n, 3))
    colours = np.array([[0.55, 0.7, 1.0], [1.0, 0.85, 0.6], [0.9, 0.6, 0.9], [0.7, 1.0, 0.85]])
    for _ in range(n_galaxies):
        cx, cy = rng.uniform(-field_arcsec / 2, field_arcsec / 2, 2)
        size = rng.uniform(0.008, 0.025) * field_arcsec
        q = rng.uniform(0.35, 1.0)
        ang = rng.uniform(0, math.pi)
        dx, dy = x - cx, y - cy
        u = dx * math.cos(ang) + dy * math.sin(ang)
        v = -dx * math.sin(ang) + dy * math.cos(ang)
        profile = np.exp(-(u * u + (v / q) ** 2) / (2 * size * size))
        image += profile[..., None] * colours[rng.integers(len(colours))] * rng.uniform(0.5, 1.0)
    return np.clip(image, 0, 1)


def source_galaxy(x, y, cx: float, cy: float, size: float = 0.5):
    """Brightness of a single round source galaxy at positions (x, y)."""
    return np.exp(-((x - cx) ** 2 + (y - cy) ** 2) / (2 * size * size))
