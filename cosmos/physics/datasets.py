"""Bundled observational data sets and clearly labelled simulated samples."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from cosmos.physics import rotation
from cosmos.physics.constants import C

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@dataclass(frozen=True)
class HubbleDataset:
    key: str
    label: str
    description: str
    names: list[str]
    distance_mpc: np.ndarray
    velocity_km_s: np.ndarray
    simulated: bool


def load_hubble_1929() -> HubbleDataset:
    names, dist, vel = [], [], []
    with open(DATA_DIR / "hubble1929.csv", encoding="utf-8") as fh:
        rows = (line for line in fh if not line.startswith("#"))
        for row in csv.DictReader(rows):
            names.append(row["object"])
            dist.append(float(row["distance_mpc"]))
            vel.append(float(row["velocity_km_s"]))
    return HubbleDataset(
        key="hubble1929",
        label="Hubble (1929) — original data",
        description=(
            "The 24 galaxies Edwin Hubble used in 1929. His distances were "
            "systematically too small (Cepheid calibration errors), so the fitted "
            "slope comes out near 400–500 km/s/Mpc instead of today's ~70."
        ),
        names=names,
        distance_mpc=np.array(dist),
        velocity_km_s=np.array(vel),
        simulated=False,
    )


def simulated_modern_sample(h0: float = 70.0, n: int = 40, seed: int = 1998) -> HubbleDataset:
    """A synthetic sample resembling modern measurements (NOT real data).

    Galaxies between 10 and 400 Mpc receive a random peculiar velocity
    (σ = 300 km/s) and a 7% distance error, typical of modern standard candles.
    """
    rng = np.random.default_rng(seed)
    true_d = np.sort(rng.uniform(10, 400, n))
    velocity = h0 * true_d + rng.normal(0, 300, n)
    # Keep the low-redshift regime where v ≈ cz is a good approximation.
    velocity = np.clip(velocity, 0, 0.1 * C / 1e3)
    measured_d = true_d * (1 + rng.normal(0, 0.07, n))
    return HubbleDataset(
        key="simulated_modern",
        label="Simulated modern sample",
        description=(
            f"A synthetic data set generated inside the app with H0 = {h0:g} km/s/Mpc, "
            "realistic peculiar velocities and 7% distance errors. It illustrates "
            "what modern surveys look like; it is not real measurements."
        ),
        names=[f"Galaxy {i + 1}" for i in range(n)],
        distance_mpc=measured_d,
        velocity_km_s=velocity,
        simulated=True,
    )


def hubble_datasets() -> dict[str, HubbleDataset]:
    sets = [load_hubble_1929(), simulated_modern_sample()]
    return {s.key: s for s in sets}


@dataclass(frozen=True)
class RotationSample:
    radius_kpc: np.ndarray
    velocity_km_s: np.ndarray
    error_km_s: np.ndarray


def illustrative_rotation_data(seed: int = 3198) -> RotationSample:
    """Synthetic 'observed' rotation curve of a Milky-Way-like spiral (NOT real data).

    Generated from a disk + bulge + NFW halo model with measurement noise, it has
    the flat outer shape seen in real galaxies such as NGC 3198.
    """
    rng = np.random.default_rng(seed)
    r = np.linspace(1.0, 30.0, 24)
    v = rotation.total_velocity(
        rotation.disk_velocity(r, 5.0e10, 3.0),
        rotation.bulge_velocity(r, 1.0e10, 0.5),
        rotation.nfw_velocity(r, 1.0e12, 10.0),
    )
    err = np.full_like(r, 8.0)
    return RotationSample(r, v + rng.normal(0, 6.0, r.size), err)
