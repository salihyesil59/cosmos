"""Spectral lines, Doppler shifts and cosmological redshift."""

from __future__ import annotations

import math
from dataclasses import dataclass

from cosmos.physics.constants import C

VISIBLE_MIN_NM = 380.0
VISIBLE_MAX_NM = 750.0


@dataclass(frozen=True)
class SpectralLine:
    name: str
    wavelength_nm: float  # rest-frame wavelength in air/vacuum approximations
    element: str
    note: str


# Prominent absorption lines seen in galaxy and stellar spectra.
SPECTRAL_LINES: tuple[SpectralLine, ...] = (
    SpectralLine("Ca II K", 393.37, "Calcium", "Strong line in old stellar populations."),
    SpectralLine("Ca II H", 396.85, "Calcium", "Pairs with Ca II K; easy to spot."),
    SpectralLine("Hδ", 410.17, "Hydrogen", "Balmer series (n = 6 → 2)."),
    SpectralLine("Hγ", 434.05, "Hydrogen", "Balmer series (n = 5 → 2)."),
    SpectralLine("Hβ", 486.13, "Hydrogen", "Balmer series (n = 4 → 2)."),
    SpectralLine("Mg b", 517.27, "Magnesium", "Triplet blended into one feature here."),
    SpectralLine("Na D", 589.29, "Sodium", "The famous sodium doublet (blended)."),
    SpectralLine("Hα", 656.28, "Hydrogen", "Balmer series (n = 3 → 2); the red hydrogen line."),
)


def observed_wavelength(rest_nm: float, z: float) -> float:
    """Wavelength observed for light emitted at ``rest_nm`` with redshift ``z``."""
    return rest_nm * (1.0 + z)


def redshift_from_wavelengths(rest_nm: float, observed_nm: float) -> float:
    """``z = (λ_obs - λ_rest) / λ_rest``."""
    return (observed_nm - rest_nm) / rest_nm


def classical_doppler_z(velocity_km_s: float) -> float:
    """Non-relativistic Doppler redshift ``z = v/c`` (positive = receding)."""
    return velocity_km_s * 1e3 / C


def relativistic_doppler_z(velocity_km_s: float) -> float:
    """Special-relativistic Doppler redshift for radial motion."""
    beta = velocity_km_s * 1e3 / C
    if abs(beta) >= 1:
        raise ValueError("speed must be below the speed of light")
    return math.sqrt((1 + beta) / (1 - beta)) - 1


def velocity_from_relativistic_z(z: float) -> float:
    """Radial velocity [km/s] that would produce redshift ``z`` by Doppler motion."""
    s = (1 + z) ** 2
    return (s - 1) / (s + 1) * C / 1e3


def wavelength_to_rgb(wavelength_nm: float, gamma: float = 0.8) -> tuple[int, int, int]:
    """Approximate perceived colour of monochromatic light.

    Outside the visible band the colour fades to black. Based on the widely used
    piecewise approximation by Dan Bruton.
    """
    w = wavelength_nm
    if w < 380 or w > 750:
        return (0, 0, 0)
    if w < 440:
        r, g, b = -(w - 440) / (440 - 380), 0.0, 1.0
    elif w < 490:
        r, g, b = 0.0, (w - 440) / (490 - 440), 1.0
    elif w < 510:
        r, g, b = 0.0, 1.0, -(w - 510) / (510 - 490)
    elif w < 580:
        r, g, b = (w - 510) / (580 - 510), 1.0, 0.0
    elif w < 645:
        r, g, b = 1.0, -(w - 645) / (645 - 580), 0.0
    else:
        r, g, b = 1.0, 0.0, 0.0
    # Intensity falls off near the limits of vision.
    if w < 420:
        factor = 0.3 + 0.7 * (w - 380) / (420 - 380)
    elif w > 700:
        factor = 0.3 + 0.7 * (750 - w) / (750 - 700)
    else:
        factor = 1.0
    return tuple(int(round(255 * (c * factor) ** gamma)) if c > 0 else 0 for c in (r, g, b))


def band_name(wavelength_nm: float) -> str:
    """Name of the electromagnetic band containing ``wavelength_nm``."""
    w = wavelength_nm
    if w < 0.01:
        return "gamma rays"
    if w < 10:
        return "X-rays"
    if w < VISIBLE_MIN_NM:
        return "ultraviolet"
    if w <= VISIBLE_MAX_NM:
        return "visible light"
    if w < 1e6:
        return "infrared"
    if w < 1e9:
        return "microwaves"
    return "radio waves"
