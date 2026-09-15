"""Gravitational waves from inspiralling compact binaries (leading post-Newtonian order)."""

from __future__ import annotations

import math

import numpy as np

from cosmos.physics import constants as const

T_SUN = const.G * const.M_SUN / const.C**3   # G M☉ / c³ ≈ 4.93 μs


def chirp_mass(m1: float, m2: float) -> float:
    """Chirp mass (m1 m2)^{3/5} / (m1 + m2)^{1/5} in the units of the inputs."""
    return (m1 * m2) ** 0.6 / (m1 + m2) ** 0.2


def time_to_merger(frequency_hz, mchirp_msun: float):
    """Time left until coalescence [s] when the wave frequency is f."""
    tc = mchirp_msun * T_SUN
    return 5.0 / 256.0 * (math.pi * np.asarray(frequency_hz, dtype=float)) ** (-8 / 3) * tc ** (-5 / 3)


def frequency_at(tau_s, mchirp_msun: float):
    """Gravitational-wave frequency [Hz] a time τ before merger."""
    tc = mchirp_msun * T_SUN
    tau = np.maximum(np.asarray(tau_s, dtype=float), 1e-6)
    return (5.0 / (256.0 * tau)) ** 0.375 * tc ** (-0.625) / math.pi


def strain_amplitude(frequency_hz, mchirp_msun: float, distance_mpc: float):
    """Amplitude h of an optimally oriented binary: 4/D (G M_c/c²)^{5/3} (π f / c)^{2/3}."""
    mc_len = mchirp_msun * T_SUN * const.C
    d = distance_mpc * const.MPC
    f = np.asarray(frequency_hz, dtype=float)
    return 4 / d * mc_len ** (5 / 3) * (math.pi * f / const.C) ** (2 / 3)


def chirp_waveform(mchirp_msun: float, distance_mpc: float, duration_s: float = 0.25, rate: int = 8192,
                   f_max: float | None = None):
    """Time series (t, h) of the inspiral, ending shortly before merger (t = 0)."""
    tc = mchirp_msun * T_SUN
    t = np.linspace(-duration_s, 0.0, int(duration_s * rate))
    tau = -t
    # Stop where the frequency approaches the innermost stable orbit.
    total_mass_s = 2 ** 1.2 * tc  # total mass of an equal-mass binary with this chirp mass
    f_stop = f_max or 1.0 / (6 ** 1.5 * math.pi * total_mass_s)  # innermost stable circular orbit
    freq = frequency_at(tau, mchirp_msun)
    phase = -2.0 * (np.maximum(tau, 1e-6) / (5 * tc)) ** 0.625
    h = strain_amplitude(freq, mchirp_msun, distance_mpc) * np.cos(phase)
    keep = freq < f_stop
    return t[keep], h[keep], freq[keep]


def siren_distance_from_amplitude(h: float, frequency_hz: float, mchirp_msun: float) -> float:
    """Luminosity distance [Mpc] inferred from amplitude, frequency and chirp mass."""
    return float(strain_amplitude(frequency_hz, mchirp_msun, 1.0)) / h


def siren_hubble_constant(velocity_km_s: float, distance_mpc: float) -> float:
    """H0 from a nearby standard siren with a known host-galaxy recession velocity."""
    return velocity_km_s / distance_mpc
