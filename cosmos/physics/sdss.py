"""The real cone diagram: an SDSS galaxy slice (E15, used by S23).

The bundled file is a spectroscopic sample from the Sloan Digital Sky Survey, DR18,
taken from the equatorial strip that produced the famous pictures of the cosmic web:
right ascension 120° to 250°, declination within 1.5° of the celestial equator,
redshifts between 0.005 and 0.15. Every row is a galaxy somebody pointed a fibre at.

Putting it beside the mock of :mod:`cosmos.physics.mock` is the whole point. The
mock is built from a known cosmology and observed on purpose; this is what the sky
actually returned. If the two look like each other, the simulation is doing its job —
and if they do not, the simulation is where the error is, because the sky is not
wrong.

The catalogue is converted into the same :class:`~cosmos.physics.mock.Catalogue` the
simulated slices use, so every measurement in the app — the cone, the radial
profile, the correlation function — runs on real galaxies without a line of special
casing. What is *not* known for a real galaxy is its true distance, so ``r_true`` is
set to the observed one and the truth-versus-observed comparison is meaningless here;
callers must not offer it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from cosmos.physics import mock

DATA = Path(__file__).resolve().parent.parent / "data" / "external" / "sdss_slice_dr18.csv"

SOURCE = "SDSS DR18 spectroscopic galaxies"
# The window the query asked for; the randoms in any clustering estimate need it.
RA_RANGE = (120.0, 250.0)
DEC_RANGE = (-1.5, 1.5)
Z_RANGE = (0.005, 0.15)
BAD_MAGNITUDE = -9000.0        # SkyServer writes -9999 when a magnitude is missing


@dataclass(frozen=True)
class Slice:
    """The raw columns, before anything cosmological is done to them."""

    ra: np.ndarray             # degrees
    dec: np.ndarray            # degrees
    z: np.ndarray
    magnitude: np.ndarray      # r-band Petrosian; NaN where SDSS had none

    def __len__(self) -> int:
        return int(self.z.size)


@lru_cache(maxsize=1)
def load(path: str | None = None) -> Slice:
    target = Path(path) if path else DATA
    table = np.genfromtxt(target, delimiter=",", names=True)
    magnitude = np.asarray(table["petroMag_r"], dtype=float)
    return Slice(
        ra=np.asarray(table["ra"], dtype=float),
        dec=np.asarray(table["dec"], dtype=float),
        z=np.asarray(table["z"], dtype=float),
        magnitude=np.where(magnitude > BAD_MAGNITUDE, magnitude, np.nan),
    )


def available() -> bool:
    """False in a checkout where tools/fetch_sky_data.py has not been run."""
    return DATA.exists()


def comoving_distance(z: np.ndarray) -> np.ndarray:
    """Comoving distance in Mpc/h for the fiducial cosmology, by interpolation."""
    from cosmos.physics.presets import PRESETS

    cosmo = PRESETS["planck18"].cosmology
    grid = np.linspace(0.0, max(float(np.max(z)) * 1.05, Z_RANGE[1]), 300)
    table = np.asarray(cosmo.comoving_distance(grid), dtype=float) * cosmo.h
    return np.interp(z, grid, table)


def settings(data: Slice | None = None) -> mock.MockSettings:
    """The geometry of the real slice, written as if it were a mock."""
    data = data or load()
    depth = float(np.max(comoving_distance(data.z)))
    return mock.MockSettings(
        wedge_deg=RA_RANGE[1] - RA_RANGE[0],
        thickness_deg=DEC_RANGE[1] - DEC_RANGE[0],
        r_max=depth,
        velocities=False,           # nothing here is simulated
        fingers_km_s=0.0,
        flux_limit=0.0,
        redshift_error=0.0,
    )


def catalogue(data: Slice | None = None) -> mock.Catalogue:
    """The slice as a :class:`~cosmos.physics.mock.Catalogue`, ready to measure.

    The wedge is re-centred so that the middle of the observed right-ascension range
    sits at angle zero, which is what the cone diagram expects and what makes the
    randoms in a clustering estimate cover the same patch of sky.
    """
    data = data or load()
    keep = np.isfinite(data.z) & (data.z > 0)
    ra, dec, z = data.ra[keep], data.dec[keep], data.z[keep]

    angle = np.radians(ra - 0.5 * (RA_RANGE[0] + RA_RANGE[1]))
    latitude = np.radians(dec)
    direction = np.stack([np.cos(latitude) * np.cos(angle),
                          np.cos(latitude) * np.sin(angle),
                          np.sin(latitude)], axis=1)
    distance = comoving_distance(z)
    zeros = np.zeros_like(distance)
    return mock.Catalogue(
        settings=settings(data),
        direction=direction,
        r_true=distance,            # unknown for a real galaxy; see the module docstring
        r_obs=distance,
        z_true=z,
        z_obs=z,
        velocity=zeros,
        overdensity=np.ones_like(distance),
        sigma_linear=float("nan"),
        growth_rate=float("nan"),
    )


def summary(data: Slice | None = None) -> dict:
    """The numbers the simulator reports beside the real cone."""
    data = data or load()
    distance = comoving_distance(data.z)
    solid_angle = (math.radians(RA_RANGE[1] - RA_RANGE[0])
                   * 2 * math.sin(math.radians(DEC_RANGE[1] - DEC_RANGE[0]) / 2))
    volume = solid_angle / 3 * float(np.max(distance)) ** 3
    magnitudes = data.magnitude[np.isfinite(data.magnitude)]
    return {
        "galaxies": len(data),
        "median_z": float(np.median(data.z)),
        "max_z": float(np.max(data.z)),
        "depth": float(np.max(distance)),
        "volume": volume,
        "density": len(data) / volume if volume > 0 else 0.0,
        "faintest": float(np.max(magnitudes)) if magnitudes.size else float("nan"),
        "brightest": float(np.min(magnitudes)) if magnitudes.size else float("nan"),
    }
