"""Fitting the Hubble–Lemaître law ``v = H0 d``."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from cosmos.physics import constants as const


@dataclass(frozen=True)
class HubbleFit:
    H0: float           # km/s/Mpc
    H0_error: float     # 1-sigma statistical error [km/s/Mpc]
    rms_residual: float  # km/s
    n_points: int

    @property
    def hubble_time_gyr(self) -> float:
        """``1/H0`` in Gyr: a first estimate of the age of the universe."""
        return 1.0 / const.hubble_to_si(self.H0) / const.GYR


def fit_through_origin(distance_mpc, velocity_km_s) -> HubbleFit:
    """Least-squares fit of ``v = H0 d`` with the line forced through the origin."""
    d = np.asarray(distance_mpc, dtype=float)
    v = np.asarray(velocity_km_s, dtype=float)
    n = d.size
    if n < 2:
        raise ValueError("need at least two data points")
    sdd = float(np.sum(d * d))
    h0 = float(np.sum(d * v) / sdd)
    residuals = v - h0 * d
    dof = max(n - 1, 1)
    sigma2 = float(np.sum(residuals**2) / dof)
    return HubbleFit(
        H0=h0,
        H0_error=math.sqrt(sigma2 / sdd),
        rms_residual=math.sqrt(float(np.mean(residuals**2))),
        n_points=n,
    )


def sum_squared_residuals(distance_mpc, velocity_km_s, h0: float) -> float:
    d = np.asarray(distance_mpc, dtype=float)
    v = np.asarray(velocity_km_s, dtype=float)
    return float(np.sum((v - h0 * d) ** 2))
