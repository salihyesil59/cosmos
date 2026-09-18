"""Building a mock redshift survey from a simulated universe (S23, L7.5).

A mock catalogue is how cosmologists test an analysis: start from a simulated
density field whose cosmology you *know*, put galaxies in it, observe it the way a
real telescope would, and check that the analysis gives back the number you put in.

The chain implemented here is the one every mock goes through:

1. **Initial conditions.** A Gaussian random field with the linear ΛCDM power
   spectrum, drawn from a seed. Change the seed and you get a different universe
   with the same statistics.
2. **Growth.** Instead of an N-body run, the field is turned into a *lognormal*
   density field, ``1 + δ_g = exp(b δ_L − b²σ²/2)``. It is not the real non-linear
   field, but it is positive everywhere, it has roughly the right one-point
   distribution, and it keeps the input power spectrum on large scales.
3. **Galaxies.** Galaxies are Poisson-sampled from that field, so they are discrete
   tracers with shot noise, biased by ``b`` with respect to the matter.
4. **Observation.** An observer sits at the centre of the box and keeps a wedge of
   the sky. Galaxies are seen in *redshift* space: the Zel'dovich velocity field
   shifts them along the line of sight (the Kaiser squashing), random motions inside
   clusters stretch them (fingers of God), a flux limit thins them out with distance,
   and a photometric redshift error blurs them radially.

Everything is a teaching approximation — this is a lognormal mock, not an N-body
simulation — but every effect a real cone diagram shows is here and can be switched
off one at a time.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
from scipy import integrate, interpolate, spatial

from cosmos.physics import structure
from cosmos.physics.presets import PRESETS

C_KM_S = 299_792.458

# Schechter luminosity function used for the flux limit (r band, magnitudes include 5 log h).
M_STAR = -20.8
ALPHA = -1.2
M_FAINT = -16.0


@dataclass(frozen=True)
class MockSettings:
    seed: int = 7
    box_mpc: float = 700.0          # comoving side of the simulated box, Mpc/h
    grid: int = 160                 # cells per side
    sigma8: float = 0.811
    bias: float = 1.3               # galaxy bias: how much harder galaxies clump than matter
    density: float = 3e-2           # galaxies per (Mpc/h)³ in the universe, before any flux limit
    wedge_deg: float = 120.0        # opening angle of the slice
    thickness_deg: float = 4.0      # how thick the slice is on the sky
    r_max: float = 300.0            # depth of the wedge, Mpc/h
    velocities: bool = True         # peculiar velocities: Kaiser squashing
    fingers_km_s: float = 500.0     # velocity dispersion inside the densest regions
    flux_limit: float = 0.0         # apparent magnitude limit (0 = volume limited)
    redshift_error: float = 0.0     # σ_z / (1 + z): 0 = spectroscopic


PRESETS_MOCK: dict[str, tuple[str, MockSettings]] = {
    "cfa2": ("CfA2 style: the Great Wall slice (1989)", MockSettings(
        wedge_deg=135.0, thickness_deg=6.0, r_max=180.0, flux_limit=15.5, density=1e-1, bias=1.2)),
    "sdss": ("SDSS main galaxy sample style (2005)", MockSettings(
        wedge_deg=120.0, thickness_deg=4.0, r_max=300.0, flux_limit=17.77, density=3e-2)),
    "volume": ("Volume limited: the same density everywhere", MockSettings(
        wedge_deg=120.0, thickness_deg=4.0, r_max=300.0, flux_limit=0.0, density=3e-3)),
    "photometric": ("Photometric redshifts: colours instead of spectra", MockSettings(
        wedge_deg=120.0, thickness_deg=4.0, r_max=300.0, flux_limit=0.0, density=3e-3,
        redshift_error=0.01)),
    "truth": ("The true universe: no observing effects at all", MockSettings(
        wedge_deg=120.0, thickness_deg=4.0, r_max=300.0, flux_limit=0.0, density=3e-3,
        velocities=False, fingers_km_s=0.0)),
}


@dataclass
class Catalogue:
    """Galaxies in one wedge, in real space and as the observer sees them."""

    settings: MockSettings
    direction: np.ndarray           # unit vector towards each galaxy, (N, 3)
    r_true: np.ndarray              # true comoving distance, Mpc/h
    r_obs: np.ndarray               # distance inferred from the observed redshift, Mpc/h
    z_true: np.ndarray
    z_obs: np.ndarray
    velocity: np.ndarray            # line-of-sight peculiar velocity, km/s
    overdensity: np.ndarray         # 1 + δ_g of the cell each galaxy came from
    sigma_linear: float = 0.0       # RMS of the smoothed linear field
    growth_rate: float = 0.0        # f = dlnD/dlna at the middle of the wedge

    def __len__(self) -> int:
        return int(self.r_true.size)

    @property
    def angle(self) -> np.ndarray:
        """Position angle inside the wedge, radians."""
        return np.arctan2(self.direction[:, 1], self.direction[:, 0])

    def points(self, observed: bool = True) -> np.ndarray:
        """Comoving positions, (N, 3) in Mpc/h, as seen in redshift or in real space."""
        r = self.r_obs if observed else self.r_true
        return self.direction * r[:, None]

    def xy(self, observed: bool = True) -> tuple[np.ndarray, np.ndarray]:
        """Cartesian coordinates for the cone diagram, Mpc/h."""
        r = self.r_obs if observed else self.r_true
        angle = self.angle
        return r * np.cos(angle), r * np.sin(angle)

    @property
    def radial_shift(self) -> np.ndarray:
        return self.r_obs - self.r_true


# --------------------------------------------------------------------- selection
def _schechter_fraction(m_limit: np.ndarray) -> np.ndarray:
    """Fraction of the luminosity function brighter than an absolute magnitude limit."""
    m_grid = np.linspace(-24.0, M_FAINT, 400)
    x = 10 ** (-0.4 * (m_grid - M_STAR))
    phi = x ** (ALPHA + 1) * np.exp(-x)                    # dn / dM, up to a constant
    total = integrate.simpson(phi, x=m_grid)
    cumulative = integrate.cumulative_trapezoid(phi, m_grid, initial=0.0)
    return np.interp(np.clip(m_limit, m_grid[0], m_grid[-1]), m_grid, cumulative / total)


def selection(r_mpc_h, m_limit: float, h: float = 0.6766) -> np.ndarray:
    """Fraction of galaxies at distance ``r`` [Mpc/h] bright enough to make the catalogue.

    A flux-limited survey keeps only galaxies above an apparent magnitude, so far away
    it keeps only the rare luminous ones. With ``m_limit = 0`` nothing is lost.
    """
    r = np.atleast_1d(np.asarray(r_mpc_h, dtype=float))
    if m_limit <= 0:
        return np.ones_like(r)
    distance_pc = np.maximum(r / h, 1e-3) * 1e6            # luminosity distance ≈ comoving at low z
    absolute_limit = m_limit - 5 * np.log10(distance_pc / 10.0) + 5 * math.log10(h)
    return _schechter_fraction(absolute_limit)


# ---------------------------------------------------------------- density field
@dataclass
class _Field:
    delta: np.ndarray               # linear density contrast on the grid
    psi: tuple                      # Zel'dovich displacement per axis, Mpc/h
    sigma: float


_FIELD_CACHE: dict[tuple, _Field] = {}


def _linear_field(settings: MockSettings) -> _Field:
    key = (settings.seed, settings.grid, settings.box_mpc, settings.sigma8)
    cached = _FIELD_CACHE.get(key)
    if cached is not None:
        return cached

    n, box = settings.grid, settings.box_mpc
    cosmo = PRESETS["planck18"].cosmology
    spectrum = structure.LinearPowerSpectrum(cosmo, sigma8=settings.sigma8)

    k_axis = np.fft.fftfreq(n, d=box / n) * 2 * math.pi
    k_last = np.fft.rfftfreq(n, d=box / n) * 2 * math.pi
    k2 = (k_axis[:, None, None] ** 2 + k_axis[None, :, None] ** 2 + k_last[None, None, :] ** 2)
    k_mag = np.sqrt(k2)

    power = np.zeros_like(k_mag)
    inside = k_mag > 0
    power[inside] = spectrum(k_mag[inside])
    # The grid cannot represent anything below a cell, so damp the field there instead of aliasing it.
    power *= np.exp(-((k_mag * box / n) ** 2) / 2)

    rng = np.random.default_rng(settings.seed)
    white = np.fft.rfftn(rng.normal(size=(n, n, n)))
    cell_volume = (box / n) ** 3
    delta_k = white * np.sqrt(power / cell_volume)
    delta = np.fft.irfftn(delta_k, s=(n, n, n), axes=(0, 1, 2)).astype(np.float32)

    with np.errstate(divide="ignore", invalid="ignore"):
        inv_k2 = np.where(k2 > 0, 1.0 / k2, 0.0)
    psi = tuple(
        np.fft.irfftn(1j * k * inv_k2 * delta_k, s=(n, n, n), axes=(0, 1, 2)).astype(np.float32)
        for k in (k_axis[:, None, None], k_axis[None, :, None], k_last[None, None, :])
    )
    built = _Field(delta, psi, float(delta.std()))
    del delta_k, white, power, k2, k_mag, inv_k2
    if len(_FIELD_CACHE) > 3:
        _FIELD_CACHE.clear()
    _FIELD_CACHE[key] = built
    return built


# ------------------------------------------------------------------- catalogue
def inner_radius(settings: MockSettings) -> float:
    """Where the wedge starts. Inside a few cells the grid cannot resolve the slice."""
    return 3.0 * settings.box_mpc / settings.grid


def _distance_redshift_tables(cosmo, r_max: float):
    z = np.linspace(0.0, 1.5 * r_max / 3000.0 + 0.05, 240)
    r = np.asarray(cosmo.comoving_distance(z), dtype=float) * cosmo.h    # Mpc/h
    return interpolate.interp1d(r, z), interpolate.interp1d(z, r)


def build(settings: MockSettings) -> Catalogue:
    """Poisson-sample a wedge of the simulated universe and observe it."""
    if settings.r_max >= 0.5 * settings.box_mpc:
        raise ValueError("the wedge must fit inside the box")

    field = _linear_field(settings)
    n, box = settings.grid, settings.box_mpc
    cell = box / n
    cosmo = PRESETS["planck18"].cosmology

    # Cells that can contribute to the wedge, with the observer at the centre of the box.
    # The slice is often thinner than a cell, so the mask is widened by one cell in every
    # direction and the exact wedge cut is applied to the galaxies afterwards: a cell that
    # straddles the boundary then contributes exactly the fraction of it that lies inside.
    axis = (np.arange(n) + 0.5) * cell - box / 2
    ix, iy, iz = np.meshgrid(axis, axis, axis, indexing="ij")
    radius = np.sqrt(ix * ix + iy * iy + iz * iz)
    half_wedge = math.radians(settings.wedge_deg) / 2
    half_thick = math.radians(settings.thickness_deg) / 2
    r_min = inner_radius(settings)
    with np.errstate(invalid="ignore", divide="ignore"):
        latitude = np.arcsin(np.divide(iz, radius, out=np.zeros_like(radius), where=radius > 0))
    margin = np.arctan2(cell, np.maximum(radius, cell))
    inside = (radius > r_min - cell) & (radius < settings.r_max + cell)
    inside &= np.abs(latitude) < half_thick + margin
    inside &= np.abs(np.arctan2(iy, ix)) < half_wedge + margin
    cells = np.flatnonzero(inside)
    if cells.size == 0:
        raise ValueError("the wedge is empty: widen it or make it deeper")

    linear = field.delta.reshape(-1)[cells].astype(float)
    bias = settings.bias
    galaxy_density = np.exp(bias * linear - 0.5 * (bias * field.sigma) ** 2)

    r_cell = radius.reshape(-1)[cells]
    expected = settings.density * cell**3 * galaxy_density * selection(r_cell, settings.flux_limit, cosmo.h)

    rng = np.random.default_rng(settings.seed + 1)
    counts = rng.poisson(expected)
    keep = counts > 0
    index = np.repeat(np.arange(cells.size)[keep], counts[keep])
    if index.size == 0:
        raise ValueError("no galaxies survive: raise the density or the magnitude limit")

    # Scatter each galaxy inside its cell, then keep exactly those that land in the wedge.
    centres = np.stack([ix.reshape(-1)[cells], iy.reshape(-1)[cells], iz.reshape(-1)[cells]], axis=1)
    position = centres[index] + rng.uniform(-0.5, 0.5, size=(index.size, 3)) * cell
    r_true = np.linalg.norm(position, axis=1)
    with np.errstate(invalid="ignore", divide="ignore"):
        galaxy_latitude = np.arcsin(np.divide(position[:, 2], r_true, out=np.zeros_like(r_true),
                                              where=r_true > 0))
    fits = (r_true > r_min) & (r_true < settings.r_max)
    fits &= np.abs(galaxy_latitude) < half_thick
    fits &= np.abs(np.arctan2(position[:, 1], position[:, 0])) < half_wedge
    position, index, r_true = position[fits], index[fits], r_true[fits]
    if r_true.size == 0:
        raise ValueError("no galaxies survive: raise the density or the magnitude limit")

    to_z, to_r = _distance_redshift_tables(cosmo, settings.r_max)
    z_true = np.asarray(to_z(r_true), dtype=float)
    z_mid = float(to_z(0.6 * settings.r_max))
    growth_rate = float(structure.growth_rate(cosmo, 1 / (1 + z_mid)))
    hubble = float(cosmo.H(z_mid)) / (1 + z_mid) / cosmo.h          # km/s per comoving Mpc/h

    # Line-of-sight peculiar velocity: coherent infall from the Zel'dovich field plus
    # a random dispersion in the densest cells (fingers of God).
    direction = position / np.maximum(r_true[:, None], 1e-6)
    shift = np.zeros_like(r_true)
    if settings.velocities:
        psi = np.stack([component.reshape(-1)[cells][index] for component in field.psi], axis=1)
        shift = growth_rate * np.sum(psi * direction, axis=1)
    if settings.fingers_km_s > 0:
        crowding = np.clip(galaxy_density[index] / 10.0, 0.0, None) ** (1 / 3)
        dispersion = settings.fingers_km_s * np.minimum(crowding, 2.5)
        shift = shift + rng.normal(0.0, np.maximum(dispersion, 1e-6)) / hubble
    velocity = shift * hubble

    z_ceiling = float(to_z(settings.r_max * 1.4))
    z_obs = np.asarray(to_z(np.clip(r_true + shift, 0.5 * cell, settings.r_max * 1.4)), dtype=float)
    if settings.redshift_error > 0:
        z_obs = z_obs + rng.normal(0.0, settings.redshift_error * (1 + z_obs))
    z_obs = np.clip(z_obs, 1e-5, z_ceiling)
    r_obs = np.asarray(to_r(z_obs), dtype=float)

    return Catalogue(
        settings=settings,
        direction=direction,
        r_true=r_true,
        r_obs=r_obs,
        z_true=z_true,
        z_obs=z_obs,
        velocity=velocity,
        overdensity=galaxy_density[index],
        sigma_linear=field.sigma,
        growth_rate=growth_rate,
    )


# -------------------------------------------------------------------- analysis
def radial_profile(cat: Catalogue, bins: int = 24):
    """Measured galaxy density against distance, with the expected selection curve."""
    edges = np.linspace(inner_radius(cat.settings), cat.settings.r_max, bins + 1)
    counts, _ = np.histogram(cat.r_obs, bins=edges)
    solid_angle = math.radians(cat.settings.wedge_deg) * 2 * math.sin(math.radians(cat.settings.thickness_deg) / 2)
    shell = solid_angle / 3 * np.diff(edges**3)
    centres = 0.5 * (edges[:-1] + edges[1:])
    with np.errstate(divide="ignore", invalid="ignore"):
        measured = np.where(shell > 0, counts / shell, 0.0)
    expected = cat.settings.density * selection(centres, cat.settings.flux_limit)
    return centres, measured, expected


MAX_PAIRS = 6000                   # galaxies used for pair counting, so the GUI stays responsive


def random_catalogue(cat: Catalogue, size: int, radii: np.ndarray, seed: int = 99) -> np.ndarray:
    """Points filling the same wedge with the same radial profile but no structure."""
    rng = np.random.default_rng(seed)
    angle = rng.uniform(-1, 1, size) * math.radians(cat.settings.wedge_deg) / 2
    sin_lat = rng.uniform(-1, 1, size) * math.sin(math.radians(cat.settings.thickness_deg) / 2)
    latitude = np.arcsin(sin_lat)
    r = rng.choice(radii, size=size)
    return np.stack([r * np.cos(latitude) * np.cos(angle),
                     r * np.cos(latitude) * np.sin(angle),
                     r * sin_lat], axis=1)


def correlation_function(cat: Catalogue, observed: bool = True, edges=None,
                         randoms: int = 5, seed: int = 99):
    """Landy–Szalay two-point correlation ξ(s) of the wedge, in Mpc/h.

    Counting pairs of galaxies is only half the job: a survey has edges and a
    selection function, so the same counting is repeated on a random catalogue with
    the same geometry and the same radial profile but no structure at all. Then

        ξ = (DD − 2DR + RR) / RR.

    The randoms take their radii from the data, as real surveys do. That removes the
    selection function without having to model it, at the price of also removing a
    little real clustering — which is why ξ measured from a small, steeply selected
    slice runs into noise and crosses zero well before 60 Mpc/h.
    """
    edges = np.geomspace(1.5, 60.0, 14) if edges is None else np.asarray(edges, dtype=float)
    data = cat.points(observed)
    radii = cat.r_obs if observed else cat.r_true
    if len(cat) > MAX_PAIRS:
        pick = np.random.default_rng(seed).choice(len(cat), MAX_PAIRS, replace=False)
        data, radii = data[pick], radii[pick]

    random = random_catalogue(cat, randoms * len(data), radii, seed)
    n_random = random.shape[0]

    tree_d = spatial.cKDTree(data)
    tree_r = spatial.cKDTree(random)
    dd = np.diff(tree_d.count_neighbors(tree_d, edges, cumulative=True)).astype(float)
    dr = np.diff(tree_d.count_neighbors(tree_r, edges, cumulative=True)).astype(float)
    rr = np.diff(tree_r.count_neighbors(tree_r, edges, cumulative=True)).astype(float)

    n_d, n_r = float(data.shape[0]), float(n_random)
    norm_dd = dd / (n_d * (n_d - 1))
    norm_dr = dr / (n_d * n_r)
    norm_rr = rr / (n_r * (n_r - 1))
    with np.errstate(divide="ignore", invalid="ignore"):
        xi = np.where(norm_rr > 0, (norm_dd - 2 * norm_dr + norm_rr) / norm_rr, np.nan)
    return np.sqrt(edges[:-1] * edges[1:]), xi


def finger_length(cat: Catalogue, threshold: float = 8.0) -> float:
    """Median radial stretch, in Mpc/h, of the galaxies in the densest regions."""
    dense = cat.overdensity > threshold
    if not np.any(dense):
        return 0.0
    return float(np.median(np.abs(cat.radial_shift[dense])))


def completeness(settings: MockSettings) -> float:
    """Fraction of the galaxies in the wedge that make it into the catalogue."""
    if settings.flux_limit <= 0:
        return 1.0
    r = np.linspace(inner_radius(settings), settings.r_max, 300)
    weight = r * r
    return float(np.sum(selection(r, settings.flux_limit) * weight) / np.sum(weight))


def summary(cat: Catalogue) -> dict:
    """The numbers the simulator reports and the challenges check."""
    s = cat.settings
    far = float(selection(0.9 * s.r_max, s.flux_limit)[0])
    near = float(selection(0.1 * s.r_max, s.flux_limit)[0])
    return {
        "galaxies": len(cat),
        "median_z": float(np.median(cat.z_obs)),
        "max_z": float(np.max(cat.z_obs)),
        "rms_velocity": float(np.sqrt(np.mean(cat.velocity**2))),
        "median_shift": float(np.median(np.abs(cat.radial_shift))),
        "finger_length": finger_length(cat),
        "completeness": completeness(s),
        "density_drop": far / near if near > 0 else 1.0,
    }


def with_effect(settings: MockSettings, **changes) -> MockSettings:
    """A copy of the settings with one observing effect switched on or off."""
    return replace(settings, **changes)
