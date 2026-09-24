"""Bundled observational data sets and clearly labelled simulated samples."""

from __future__ import annotations

import csv
import functools
import zipfile
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


# --------------------------------------------------------------- real data
EXTERNAL_DIR = DATA_DIR / "external"
PANTHEON_FILE = EXTERNAL_DIR / "PantheonPlusSH0ES.dat"
SPARC_ARCHIVE = EXTERNAL_DIR / "Rotmod_LTG.zip"
SPARC_TABLE = EXTERNAL_DIR / "SPARC_Lelli2016c.mrt"

PANTHEON_CITATION = "Pantheon+ (Scolnic et al. 2022; Brout et al. 2022; SH0ES: Riess et al. 2022)"
SPARC_CITATION = "SPARC (Lelli, McGaugh & Schombert 2016)"


@dataclass(frozen=True)
class PantheonSample:
    """The Pantheon+ compilation of type Ia supernovae (real measurements)."""

    name: list[str]
    z: np.ndarray                # CMB-frame redshift, corrected for peculiar velocities
    m_b_corr: np.ndarray         # standardised apparent magnitude
    m_b_corr_err: np.ndarray
    mu: np.ndarray               # SH0ES distance modulus
    mu_err: np.ndarray
    is_calibrator: np.ndarray    # supernovae in galaxies with a Cepheid distance

    def __len__(self) -> int:
        return len(self.z)


@functools.cache
def load_pantheon_plus() -> PantheonSample:
    """Read the bundled Pantheon+SH0ES release (1701 light curves)."""
    names: list[str] = []
    columns: dict[str, list[float]] = {k: [] for k in
                                       ("zHD", "m_b_corr", "m_b_corr_err_DIAG", "MU_SH0ES",
                                        "MU_SH0ES_ERR_DIAG", "IS_CALIBRATOR")}
    with open(PANTHEON_FILE, encoding="utf-8") as fh:
        header = fh.readline().split()
        index = {name: i for i, name in enumerate(header)}
        for line in fh:
            fields = line.split()
            if len(fields) < len(header):
                continue
            names.append(fields[index["CID"]])
            for key in columns:
                columns[key].append(float(fields[index[key]]))
    return PantheonSample(
        name=names,
        z=np.array(columns["zHD"]),
        m_b_corr=np.array(columns["m_b_corr"]),
        m_b_corr_err=np.array(columns["m_b_corr_err_DIAG"]),
        mu=np.array(columns["MU_SH0ES"]),
        mu_err=np.array(columns["MU_SH0ES_ERR_DIAG"]),
        is_calibrator=np.array(columns["IS_CALIBRATOR"]) > 0.5,
    )


@dataclass(frozen=True)
class SparcGalaxy:
    """One galaxy of the SPARC sample: its rotation curve and what the stars and gas explain."""

    name: str
    hubble_type: int
    distance_mpc: float
    inclination_deg: float
    luminosity_36: float          # 10^9 L_sun at 3.6 μm
    disk_scale_kpc: float
    hi_mass: float                # 10^9 M_sun
    v_flat: float                 # asymptotic rotation speed [km/s]
    v_flat_err: float
    quality: int                  # 1 = best, 3 = poor
    radius_kpc: np.ndarray
    velocity_km_s: np.ndarray
    error_km_s: np.ndarray
    v_gas: np.ndarray
    v_disk: np.ndarray
    v_bulge: np.ndarray

    @property
    def label(self) -> str:
        return f"{self.name}  ({self.distance_mpc:.1f} Mpc, V_flat ≈ {self.v_flat:.0f} km/s)"

    def sample(self) -> RotationSample:
        return RotationSample(self.radius_kpc, self.velocity_km_s, self.error_km_s)


def _sparc_table_rows() -> dict[str, dict]:
    """Parse the machine-readable galaxy table (Lelli et al. 2016, Table 1).

    The columns are whitespace separated and no galaxy name contains a space, so
    splitting is safer here than the byte ranges of the header, which are offset
    by one character in the published file.
    """
    columns = ["name", "hubble_type", "distance_mpc", "distance_err", "distance_method",
               "inclination_deg", "inclination_err", "luminosity_36", "luminosity_err",
               "effective_radius", "effective_brightness", "disk_scale_kpc", "disk_brightness",
               "hi_mass", "hi_radius", "v_flat", "v_flat_err", "quality", "reference"]
    integers = {"hubble_type", "distance_method", "quality"}
    rows: dict[str, dict] = {}
    for line in SPARC_TABLE.read_text(encoding="utf-8").splitlines():
        fields = line.split()
        if len(fields) != len(columns):
            continue
        try:
            entry = {name: (value if name in ("name", "reference")
                            else int(value) if name in integers else float(value))
                     for name, value in zip(columns, fields)}
        except ValueError:                       # a line of the header description
            continue
        rows[entry["name"]] = entry
    return rows


@functools.cache
def sparc_catalog() -> dict[str, dict]:
    """Metadata of the 175 SPARC galaxies, keyed by name."""
    return _sparc_table_rows()


@functools.cache
def sparc_names(max_quality: int = 2, min_points: int = 8) -> list[str]:
    """Galaxies worth showing: good-quality curves with enough measured points."""
    with zipfile.ZipFile(SPARC_ARCHIVE) as archive:
        available = {Path(n).name.replace("_rotmod.dat", "") for n in archive.namelist()}
    catalog = sparc_catalog()
    names = [n for n in sorted(available)
             if n in catalog and catalog[n]["quality"] <= max_quality]
    return [n for n in names if len(load_sparc_galaxy(n).radius_kpc) >= min_points]


@functools.cache
def load_sparc_galaxy(name: str) -> SparcGalaxy:
    """Rotation curve and mass-model velocities of one SPARC galaxy."""
    with zipfile.ZipFile(SPARC_ARCHIVE) as archive:
        with archive.open(f"{name}_rotmod.dat") as fh:
            lines = fh.read().decode("utf-8").splitlines()
    values = []
    for line in lines:
        if line.startswith("#") or not line.strip():
            continue
        parts = line.split()
        if len(parts) >= 6:
            values.append([float(p) for p in parts[:6]])
    table = np.array(values, dtype=float)
    meta = sparc_catalog().get(name, {})
    return SparcGalaxy(
        name=name,
        hubble_type=int(meta.get("hubble_type", 0)),
        distance_mpc=float(meta.get("distance_mpc", float("nan"))),
        inclination_deg=float(meta.get("inclination_deg", float("nan"))),
        luminosity_36=float(meta.get("luminosity_36", float("nan"))),
        disk_scale_kpc=float(meta.get("disk_scale_kpc", float("nan"))),
        hi_mass=float(meta.get("hi_mass", float("nan"))),
        v_flat=float(meta.get("v_flat", float("nan"))),
        v_flat_err=float(meta.get("v_flat_err", float("nan"))),
        quality=int(meta.get("quality", 3)),
        radius_kpc=table[:, 0],
        velocity_km_s=table[:, 1],
        error_km_s=np.maximum(table[:, 2], 1.0),
        v_gas=table[:, 3],
        v_disk=table[:, 4],
        v_bulge=table[:, 5],
    )
