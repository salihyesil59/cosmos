"""Forecasting what a galaxy redshift survey will measure (S21, L7.4, L7.6).

The measurement is the baryon acoustic oscillation (BAO) scale: the volume-averaged
distance D_V(z) in units of the sound horizon r_d. How precisely a survey measures it
depends on two things only:

* **volume** — how many independent patches of the cosmic web it maps (sample variance);
* **density** — whether it has enough galaxies to trace each patch (shot noise).

Both are captured by the *effective volume* (Tegmark 1997; Seo & Eisenstein 2003)

    V_eff = V · [n̄P / (1 + n̄P)]²

evaluated at the BAO wavenumber k ≈ 0.14 h/Mpc. The distance error then scales as
V_eff^(−1/2). The normalisation is calibrated so that a BOSS-CMASS-like survey gives
the 1% it achieved after reconstruction. This is a teaching forecast, good to tens of
percent, not a Fisher-matrix code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np

from cosmos.physics.presets import PRESETS

C_KM_S = 299_792.458
SKY_DEG2 = 41_252.96
SOUND_HORIZON_MPC = 147.09                 # Planck 2018 r_d
P_BAO = 5000.0                             # matter power at k = 0.14 h/Mpc today, (Mpc/h)³
BIN_WIDTH = 0.1


@dataclass(frozen=True)
class Tracer:
    key: str
    label: str
    bias0: float                  # b(z) = b0 / D(z), so b(z)² D(z)² P is the same at every redshift
    density: float                # n̄ in (h/Mpc)³
    z_range: tuple[float, float]
    description: str


TRACERS = {
    "bgs": Tracer("bgs", "Bright galaxies (BGS)", 1.34, 1e-3, (0.05, 0.4),
                  "The brightest nearby galaxies: dense but only a small volume."),
    "lrg": Tracer("lrg", "Luminous red galaxies (LRG)", 1.7, 5e-4, (0.4, 1.1),
                  "Massive, old, strongly clustered galaxies: the classic BAO tracer."),
    "elg": Tracer("elg", "Emission-line galaxies (ELG)", 0.84, 5e-4, (0.6, 1.6),
                  "Star-forming galaxies with bright [O II] lines: numerous at high redshift, weakly clustered."),
    "qso": Tracer("qso", "Quasars (QSO)", 1.2, 2e-5, (0.8, 2.1),
                  "Rare but luminous: they reach far, but so few that shot noise dominates."),
    "halpha": Tracer("halpha", "Hα emitters (space infrared)", 1.4, 2e-4, (0.9, 1.8),
                     "Galaxies seen in Hα with a slitless spectrograph from space, as Euclid does."),
}


@dataclass(frozen=True)
class SurveySettings:
    tracer: str = "lrg"
    area_deg2: float = 14_000.0
    z_min: float = 0.4
    z_max: float = 1.1
    density: float = 5e-4                  # target density n̄, (h/Mpc)³
    fibres: int = 5000                     # spectra observed at once
    fields_per_night: float = 10.0
    nights_per_year: float = 250.0
    years: float = 5.0
    success_rate: float = 0.85             # spectra that yield a redshift
    systematic_floor: float = 0.0          # percent, added in quadrature to the combined error


PRESETS_SURVEY: dict[str, tuple[str, SurveySettings]] = {
    "boss": ("BOSS CMASS style (2014)", SurveySettings(
        tracer="lrg", area_deg2=9_300, z_min=0.43, z_max=0.7, density=3e-4, fibres=1000,
        fields_per_night=8, nights_per_year=150, years=5)),
    "desi_lrg": ("DESI luminous red galaxies (2021–26)", SurveySettings(
        tracer="lrg", area_deg2=14_000, z_min=0.4, z_max=1.1, density=5e-4)),
    "desi_qso": ("DESI quasars (2021–26)", SurveySettings(
        tracer="qso", area_deg2=14_000, z_min=0.8, z_max=2.1, density=2e-5)),
    "euclid": ("Euclid spectroscopic style (2023–29)", SurveySettings(
        tracer="halpha", area_deg2=14_000, z_min=0.9, z_max=1.8, density=2e-4, fibres=30_000,
        fields_per_night=3, nights_per_year=300, years=6, success_rate=0.6)),
    "pilot": ("A small pilot survey", SurveySettings(
        tracer="lrg", area_deg2=500, z_min=0.4, z_max=0.8, density=5e-4, fibres=1000,
        fields_per_night=6, nights_per_year=60, years=1)),
}


@dataclass
class Bin:
    z_low: float
    z_high: float
    z_mid: float
    volume: float                  # (Gpc/h)³
    n_p: float
    effective_volume: float        # (Gpc/h)³
    error_percent: float           # on D_V / r_d
    dv_over_rd: float


@dataclass
class Forecast:
    settings: SurveySettings
    bins: list[Bin] = field(default_factory=list)
    targets_needed: float = 0.0
    spectra_available: float = 0.0
    density_used: float = 0.0      # after dilution by the fibres available

    @property
    def diluted(self) -> bool:
        return self.spectra_available < self.targets_needed

    @property
    def volume(self) -> float:
        return sum(b.volume for b in self.bins)

    @property
    def effective_volume(self) -> float:
        return sum(b.effective_volume for b in self.bins)

    @property
    def n_p(self) -> float:
        return self.bins[0].n_p if self.bins else 0.0

    @property
    def statistical_percent(self) -> float:
        inverse = sum(1 / b.error_percent**2 for b in self.bins if b.error_percent > 0)
        return 1 / math.sqrt(inverse) if inverse else math.inf

    @property
    def total_percent(self) -> float:
        return math.hypot(self.statistical_percent, self.settings.systematic_floor)

    @property
    def galaxies(self) -> float:
        return min(self.targets_needed, self.spectra_available)


def _calibration() -> float:
    """Normalisation A in σ = A / √V_eff, fixed so that a BOSS-CMASS-like survey gives 1.0%."""
    settings = PRESETS_SURVEY["boss"][1]
    raw = _raw_forecast(settings, 1.0)
    return 1.0 / raw.statistical_percent


def _raw_forecast(s: SurveySettings, amplitude: float) -> Forecast:
    cosmo = PRESETS["planck18"].cosmology
    h = cosmo.h
    tracer = TRACERS[s.tracer]
    z_edges = np.arange(s.z_min, s.z_max + 1e-9, BIN_WIDTH)
    if len(z_edges) < 2 or z_edges[-1] < s.z_max - 1e-9:
        z_edges = np.append(z_edges, s.z_max)
    distance = np.asarray(cosmo.comoving_distance(z_edges), dtype=float) * h / 1e3      # Gpc/h
    fraction = s.area_deg2 / SKY_DEG2
    shells = fraction * 4 * math.pi / 3 * np.diff(distance**3)

    needed = s.density * float(np.sum(shells)) * 1e9                                  # galaxies
    available = s.fibres * s.fields_per_night * s.nights_per_year * s.years * s.success_rate
    density = s.density * min(1.0, available / needed) if needed > 0 else 0.0
    n_p = density * tracer.bias0**2 * P_BAO

    bins = []
    for z_low, z_high, volume in zip(z_edges[:-1], z_edges[1:], shells):
        z_mid = 0.5 * (z_low + z_high)
        effective = volume * (n_p / (1 + n_p)) ** 2
        error = amplitude / math.sqrt(effective) if effective > 0 else math.inf
        d_m = float(cosmo.transverse_comoving_distance(z_mid))
        hz = float(cosmo.H(z_mid))
        d_v = (z_mid * d_m**2 * C_KM_S / hz) ** (1 / 3)
        bins.append(Bin(float(z_low), float(z_high), z_mid, float(volume), n_p, float(effective), error,
                        d_v / SOUND_HORIZON_MPC))
    return Forecast(s, bins, needed, available, density)


_AMPLITUDE: float | None = None


def forecast(settings: SurveySettings) -> Forecast:
    global _AMPLITUDE
    if settings.z_max <= settings.z_min:
        raise ValueError("the redshift range is empty")
    if _AMPLITUDE is None:
        _AMPLITUDE = _calibration()
    return _raw_forecast(settings, _AMPLITUDE)


def area_tradeoff(settings: SurveySettings, areas=None) -> tuple[np.ndarray, np.ndarray]:
    """Combined error against area when the number of galaxies is fixed (density = galaxies / volume).

    With N galaxies spread over a volume V, n̄P = N b²P / V and V_eff = V (n̄P / (1 + n̄P))², which is
    largest where n̄P = 1: spread the galaxies until each patch is just traced.
    """
    areas = np.geomspace(30, SKY_DEG2, 45) if areas is None else np.asarray(areas)
    reference = forecast(settings)
    galaxies = reference.galaxies
    errors = []
    for area in areas:
        probe = replace(settings, area_deg2=float(area), density=1.0)
        volume = forecast(replace(probe, density=1e-9)).volume * 1e9
        density = galaxies / volume if volume > 0 else 0.0
        errors.append(forecast(replace(probe, density=density)).statistical_percent)
    return areas, np.array(errors)
