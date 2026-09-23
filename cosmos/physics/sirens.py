"""Measuring H0 from a gravitational-wave merger: standard sirens (S22, L6.9).

A merging pair of compact objects is a **standard siren**. General relativity fixes
the amplitude of the wave it radiates, so the strain measured on Earth gives the
luminosity distance directly — no ladder, no calibration, no Cepheids. If the
redshift of the host galaxy is known as well, one event gives

    H0 = c z / D_L      (at low redshift).

Two things spoil the simplicity, and both are modelled here.

* **The inclination degeneracy.** The amplitude depends on the angle between the
  orbital axis and the line of sight almost as strongly as on the distance, so a
  face-on binary far away looks like an edge-on one nearby. Marginalising over the
  unknown inclination is what makes the distance error asymmetric and large: the
  posterior of GW170817 was 40 (+8 / −14) Mpc from a signal of SNR 32.
* **Finding the host.** With a kilonova the host is identified and the redshift is
  exact. Without one — a "dark siren" — every galaxy in the localisation volume is a
  candidate, and a single event says very little.

The loudness is calibrated on GW170817 (SNR 32.4) and the localisation on GW170817
for a three-site network (28 deg²) and GW190425 for a two-site one (8400 deg²).
Everything here is good to a factor of order one, not better.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np

from cosmos.physics import gravitational_waves as gw
from cosmos.physics.presets import PRESETS

C_KM_S = 299_792.458
SKY_DEG2 = 41_252.96
DEG2_PER_SR = SKY_DEG2 / (4 * math.pi)

BNS_CHIRP_MASS = 1.219            # chirp mass of a 1.4 + 1.4 M☉ binary
HORIZON_OVER_RANGE = 2.26         # optimally oriented and placed, versus the quoted BNS range
GALAXY_DENSITY = 0.1              # galaxies per Mpc³ that a catalogue such as GLADE lists


@dataclass(frozen=True)
class Network:
    key: str
    label: str
    detectors: int
    range_mpc: float              # the quoted BNS range: sky- and orientation-averaged
    description: str


NETWORKS: dict[str, Network] = {
    "two": Network("two", "Two detectors only", 2, 130.0,
                   "With sites on one continent a merger can be found but barely located: "
                   "GW190425 landed in a patch of 8400 deg²."),
    "o2": Network("o2", "LIGO–Virgo, 2017 (O2)", 3, 100.0,
                  "The network that detected GW170817, with Virgo only just sensitive enough."),
    "o4": Network("o4", "LIGO–Virgo–KAGRA, 2023 (O4)", 4, 160.0,
                  "Today's network: two LIGO detectors, Virgo and KAGRA."),
    "design": Network("design", "Advanced detectors at design sensitivity", 4, 190.0,
                      "What the current instruments were built to reach."),
    "aplus": Network("aplus", "A+ upgrade (late 2020s)", 5, 330.0,
                     "Upgraded mirrors and squeezed light, with LIGO-India joining."),
    "et": Network("et", "Einstein Telescope (2030s)", 3, 1800.0,
                  "A ten-kilometre underground triangle: thousands of events a year, out to high redshift."),
}


@dataclass(frozen=True)
class SirenSettings:
    m1: float = 1.4                   # component masses, M☉
    m2: float = 1.4
    distance_mpc: float = 40.0        # the true luminosity distance
    inclination_deg: float = 30.0     # angle between the orbital axis and the line of sight
    network: str = "o2"
    host_known: bool = True           # a kilonova pins the host; otherwise it is a dark siren
    peculiar_velocity_km_s: float = 150.0    # uncertainty on the host's recession velocity
    events: int = 1                   # how many similar events are combined
    seed: int = 3


PRESETS_SIREN: dict[str, tuple[str, SirenSettings]] = {
    "gw170817": ("GW170817: the first standard siren (2017)", SirenSettings(
        m1=1.46, m2=1.27, distance_mpc=40.0, inclination_deg=150.0, network="o2", host_known=True)),
    "gw190425": ("GW190425: no counterpart, no host (2019)", SirenSettings(
        m1=2.0, m2=1.4, distance_mpc=159.0, inclination_deg=30.0, network="two", host_known=False)),
    "dark": ("A dark siren: black holes, no light", SirenSettings(
        m1=30.0, m2=25.0, distance_mpc=800.0, inclination_deg=45.0, network="o4", host_known=False)),
    "fifty": ("Fifty bright sirens from one observing run", SirenSettings(
        m1=1.4, m2=1.4, distance_mpc=120.0, inclination_deg=40.0, network="design", host_known=True,
        events=50)),
    "et": ("Einstein Telescope: a siren catalogue", SirenSettings(
        m1=1.4, m2=1.4, distance_mpc=1500.0, inclination_deg=40.0, network="et", host_known=True,
        events=500)),
}


# ------------------------------------------------------------------ amplitudes
def orientation(inclination_deg) -> np.ndarray:
    """How loud a binary is at inclination ι, relative to face-on.

    The two polarisations carry (1 + cos²ι)/2 and cos ι, so a face-on binary (ι = 0)
    is 2.83 times louder in power than an edge-on one and the amplitude alone cannot
    tell a nearby edge-on merger from a distant face-on one.
    """
    c = np.cos(np.radians(np.asarray(inclination_deg, dtype=float)))
    return np.sqrt(((1 + c * c) / 2) ** 2 + c * c) / math.sqrt(2)


def _snr_normalisation() -> float:
    """Fixed so that GW170817 comes out at the SNR 32.4 that was actually measured."""
    s = PRESETS_SIREN["gw170817"][1]
    return 32.4 / _raw_snr(s, 1.0)


def _raw_snr(s: SirenSettings, norm: float) -> float:
    network = NETWORKS[s.network]
    horizon = network.range_mpc * HORIZON_OVER_RANGE
    mass_factor = (gw.chirp_mass(s.m1, s.m2) / BNS_CHIRP_MASS) ** (5 / 6)
    detectors = math.sqrt(network.detectors / 3)
    return norm * detectors * horizon / s.distance_mpc * mass_factor * float(orientation(s.inclination_deg))


_NORM: float | None = None


def signal_to_noise(s: SirenSettings) -> float:
    """Network signal-to-noise ratio of the inspiral. Below 8 nothing is claimed."""
    global _NORM
    if _NORM is None:
        _NORM = _snr_normalisation()
    return _raw_snr(s, _NORM)


# ------------------------------------------------- the distance–inclination plane
POLARISATION = 0.85       # how well a network pins cos ι; fitted to the GW170817 posterior


def _inclination_prior(s: SirenSettings, cos_i: np.ndarray) -> np.ndarray:
    """sin ι dι, times what the network itself says about the inclination.

    A single detector measures one number and cannot separate distance from
    inclination at all. A network sees the two polarisations from different angles,
    which constrains ι — weakly, but enough to stop the distance posterior from
    spreading over the whole factor of 2.8 that the amplitude alone allows.
    """
    prior = np.ones_like(cos_i)                # flat in cos ι is sin ι dι
    sites = NETWORKS[s.network].detectors
    if sites < 2:
        return prior
    width = POLARISATION * math.sqrt(3.0 / sites) * (12.0 / max(signal_to_noise(s), 1e-3))
    truth = abs(math.cos(math.radians(s.inclination_deg)))
    return prior * np.exp(-0.5 * ((cos_i - truth) / max(width, 1e-3)) ** 2)


def distance_posterior(s: SirenSettings, grid: int = 400):
    """p(D) after marginalising over the unknown inclination, with a D² volume prior.

    The measurement constrains the combination w(ι)/D, not D by itself, so every
    inclination the prior allows drags a different distance along with it.
    """
    snr = signal_to_noise(s)
    if snr <= 0:
        raise ValueError("the signal has no amplitude")
    observed = float(orientation(s.inclination_deg)) / s.distance_mpc

    distances = np.linspace(0.2 * s.distance_mpc, 3.0 * s.distance_mpc, grid)
    cos_i = np.linspace(0.0, 1.0, 240)                    # sin ι dι is flat in cos ι
    weights = np.sqrt(((1 + cos_i**2) / 2) ** 2 + cos_i**2) / math.sqrt(2)
    prior = _inclination_prior(s, cos_i)

    model = weights[None, :] / distances[:, None]
    sigma = observed / snr
    likelihood = (np.exp(-0.5 * ((model - observed) / sigma) ** 2) * prior[None, :]).sum(axis=1)
    posterior = likelihood * distances**2                 # sources are spread through volume
    area = np.trapezoid(posterior, distances)
    return distances, posterior / area if area > 0 else posterior


def credible_interval(x: np.ndarray, density: np.ndarray, level: float = 0.68):
    """Median and the equal-tailed interval of a one-dimensional posterior."""
    cdf = np.concatenate([[0.0], np.cumsum(0.5 * (density[1:] + density[:-1]) * np.diff(x))])
    cdf /= cdf[-1]
    low, mid, high = np.interp([(1 - level) / 2, 0.5, (1 + level) / 2], cdf, x)
    return float(mid), float(low), float(high)


def sky_area(s: SirenSettings) -> float:
    """90% localisation area [deg²]. Timing between sites is what localises a merger."""
    # Calibrated on GW170817 (3 sites, SNR 32.4, 28 deg²); more sites triangulate far better.
    by_sites = {2: 9600.0, 3: 204.0, 4: 68.0, 5: 34.0}
    base = by_sites.get(NETWORKS[s.network].detectors, 34.0)
    snr = max(signal_to_noise(s), 1e-3)
    return base * (12.0 / snr) ** 2


# -------------------------------------------------------------- the measurement
@dataclass
class SirenMeasurement:
    settings: SirenSettings
    snr: float
    detected: bool
    distance: float                   # median of the posterior, Mpc
    distance_low: float
    distance_high: float
    sky_area_deg2: float
    volume_mpc3: float
    host_candidates: int
    redshift: float
    h0: float                         # best estimate from this event (or events)
    h0_low: float
    h0_high: float
    h0_single_percent: float          # the error one event of this kind gives
    distances: np.ndarray = None      # the distance posterior, for plotting
    density: np.ndarray = None
    h0_grid: np.ndarray = None
    h0_density: np.ndarray = None

    @property
    def distance_percent(self) -> float:
        return 100 * 0.5 * (self.distance_high - self.distance_low) / self.distance

    @property
    def h0_percent(self) -> float:
        return 100 * 0.5 * (self.h0_high - self.h0_low) / self.h0


def dark_penalty(candidates: int) -> float:
    """How much weaker a dark siren is than one with an identified host.

    Every galaxy in the localisation volume is a candidate. The right one contributes
    the same answer every time while the wrong ones point in random directions, so the
    information survives — it is just diluted. The logarithmic form is a heuristic
    fitted to the published dark-siren results, where a few thousand candidates cost a
    factor of about three against GW170817's identified host.
    """
    return 1.0 + 0.625 * math.log10(max(candidates, 1))


def _redshift_of(distance_mpc: float) -> float:
    cosmo = PRESETS["planck18"].cosmology
    z = np.linspace(1e-4, 1.5, 600)
    d = np.asarray(cosmo.luminosity_distance(z), dtype=float)
    return float(np.interp(distance_mpc, d, z))


def measure(s: SirenSettings) -> SirenMeasurement:
    """Everything one merger (or a set of them) says about H0."""
    cosmo = PRESETS["planck18"].cosmology
    snr = signal_to_noise(s)
    distances, density = distance_posterior(s)
    distance, low, high = credible_interval(distances, density)
    area = sky_area(s)

    # The localisation volume, and how many galaxies a catalogue would list inside it.
    # Both the sky area and the distance range are 90% credible, so they match.
    _mid, d_low90, d_high90 = credible_interval(distances, density, level=0.9)
    solid_angle = area / DEG2_PER_SR
    volume = solid_angle / 3 * (d_high90**3 - d_low90**3)
    candidates = max(1, int(round(volume * GALAXY_DENSITY)))

    z_true = _redshift_of(s.distance_mpc)
    h0_fid = float(cosmo.H0)
    d_fid = float(cosmo.luminosity_distance(z_true))

    # H0 = H0_fid × D_fid(z) / D_measured: the distance posterior maps straight onto H0,
    # and the 1/D turns the long tail towards small distances into one towards large H0.
    h0_grid = h0_fid * d_fid / distances[::-1]
    h0_density = (density * distances**2)[::-1] / (h0_fid * d_fid)
    h0_measured, h0_low, h0_high = credible_interval(h0_grid, h0_density)
    gw_percent = 100 * 0.5 * (h0_high - h0_low) / h0_measured

    # The host's own motion adds an error on cz that no amount of gravitational-wave data removes.
    velocity_percent = 100 * s.peculiar_velocity_km_s / max(C_KM_S * z_true, 1e-6)
    single_percent = math.hypot(gw_percent, velocity_percent)
    if not s.host_known:
        single_percent *= dark_penalty(candidates)

    combined = single_percent / math.sqrt(max(s.events, 1))
    return SirenMeasurement(
        settings=s,
        snr=snr,
        detected=snr >= 8.0,
        distance=distance,
        distance_low=low,
        distance_high=high,
        sky_area_deg2=area,
        volume_mpc3=volume,
        host_candidates=candidates,
        redshift=z_true,
        h0=h0_measured,
        h0_low=h0_measured * (1 - combined / 100),
        h0_high=h0_measured * (1 + combined / 100),
        h0_single_percent=single_percent,
        distances=distances,
        density=density,
        h0_grid=h0_grid,
        h0_density=h0_density,
    )


def events_needed(s: SirenSettings, target_percent: float = 2.0) -> int:
    """How many events like this one it takes to reach a given precision on H0."""
    single = measure(replace(s, events=1)).h0_single_percent
    return max(1, int(math.ceil((single / target_percent) ** 2)))


def horizon_distance(s: SirenSettings) -> float:
    """The furthest this binary could be and still be detected at SNR 8, face-on."""
    face_on = replace(s, inclination_deg=0.0, distance_mpc=100.0)
    return 100.0 * signal_to_noise(face_on) / 8.0


def degeneracy_grid(s: SirenSettings, grid: int = 160):
    """The joint posterior of distance and inclination: the banana every siren paper shows."""
    snr = signal_to_noise(s)
    observed = float(orientation(s.inclination_deg)) / s.distance_mpc
    distances = np.linspace(0.2 * s.distance_mpc, 3.0 * s.distance_mpc, grid)
    inclinations = np.linspace(0.0, 90.0, grid)
    model = orientation(inclinations)[None, :] / distances[:, None]
    sigma = observed / snr
    joint = np.exp(-0.5 * ((model - observed) / sigma) ** 2)
    joint *= distances[:, None] ** 2 * _inclination_prior(s, np.cos(np.radians(inclinations)))[None, :]
    return distances, inclinations, joint / joint.max()
