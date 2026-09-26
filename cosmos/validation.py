"""What the physics engine is checked against, and by how much it misses (`V4`).

The Data & methods page says the engine is verified against astropy and against
published numbers. That is the kind of claim a reader has to take on trust, and
it is worth more as a table: this quantity, compared with that reference, over
this range, agreeing to within *this much*.

Every check here knows how to run itself and returns the largest disagreement it
found. The test suite runs all of them on every change. The comparisons against
astropy cannot run in a packaged build, because astropy is a development
dependency and not shipped — so the numbers are also recorded in
``cosmos/data/validation.json`` when the checks are run, and the app shows the
recorded value with the date it was measured. A test compares the recorded file
with a fresh run, so a stale number cannot sit there looking respectable.

Nothing here imports Qt. ``numpy`` and the physics engine are imported inside the
check functions, so reading the catalogue costs nothing.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

RECORD = Path(__file__).resolve().parent / "data" / "validation.json"

#: The three kinds of thing an answer can be checked against, worst first in the
#: sense of how much they can tell you: another implementation, mathematics, and
#: a number somebody published.
AGAINST_ASTROPY = "astropy"
AGAINST_CLOSED_FORM = "closed form"
AGAINST_PUBLISHED = "published value"


@dataclass(frozen=True)
class Check:
    """One comparison the engine has to survive."""

    id: str
    quantity: str                 #: what is being computed
    against: str                  #: one of the three constants above
    reference: str                #: the thing compared with, named
    detail: str                   #: what is varied, and over what range
    tolerance: float              #: the largest disagreement allowed
    relative: bool = True         #: relative difference, or absolute in ``unit``
    unit: str = ""

    def format(self, value: float) -> str:
        if self.relative:
            return f"{value:.2e}" if value else "0"
        return f"{value:.4g} {self.unit}".strip()


#: Model parameters the astropy comparisons sweep. Flat, open and closed, so a
#: curvature term that is wrong somewhere cannot hide.
def _models():
    from cosmos.physics import Cosmology
    from cosmos.physics.presets import PRESETS

    return [
        PRESETS["planck18"].cosmology,
        PRESETS["wmap9"].cosmology,
        Cosmology(H0=70, Om0=0.3, Ode0=0.0),        # open, with radiation
        Cosmology(H0=70, Om0=0.5, Ode0=0.8),        # closed, accelerating
    ]


def _redshifts():
    import numpy as np

    return np.array([0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0])


def _astropy_model(c):
    from astropy.cosmology import LambdaCDM

    return LambdaCDM(H0=c.H0, Om0=c.Om0, Ode0=c.Ode0, Tcmb0=c.Tcmb0, Neff=c.Neff, m_nu=0.0, Ob0=c.Ob0)


def _worst_relative(pairs) -> float:
    """The largest |ours - theirs| / |theirs| over every value in every model."""
    import numpy as np

    worst = 0.0
    for ours, theirs in pairs:
        ours, theirs = np.atleast_1d(ours), np.atleast_1d(theirs)
        scale = np.where(theirs == 0, 1.0, np.abs(theirs))
        worst = max(worst, float(np.max(np.abs(ours - theirs) / scale)))
    return worst


def _worst_absolute(pairs) -> float:
    import numpy as np

    worst = 0.0
    for ours, theirs in pairs:
        worst = max(worst, float(np.max(np.abs(np.atleast_1d(ours) - np.atleast_1d(theirs)))))
    return worst


# --------------------------------------------------------- against astropy

def _check_expansion_rate() -> float:
    z = _redshifts()
    return _worst_relative((m.efunc(z), _astropy_model(m).efunc(z)) for m in _models())


def _check_age() -> float:
    z = _redshifts()
    return _worst_relative((m.age(z), _astropy_model(m).age(z).value) for m in _models())


def _check_lookback_time() -> float:
    z = _redshifts()
    return _worst_relative(
        (m.lookback_time(z), _astropy_model(m).lookback_time(z).value) for m in _models())


def _check_comoving_distance() -> float:
    z = _redshifts()
    return _worst_relative(
        (m.comoving_distance(z), _astropy_model(m).comoving_distance(z).value) for m in _models())


def _check_luminosity_distance() -> float:
    z = _redshifts()
    return _worst_relative(
        (m.luminosity_distance(z), _astropy_model(m).luminosity_distance(z).value) for m in _models())


def _check_angular_diameter_distance() -> float:
    z = _redshifts()
    return _worst_relative(
        (m.angular_diameter_distance(z), _astropy_model(m).angular_diameter_distance(z).value)
        for m in _models())


def _check_distance_modulus() -> float:
    z = _redshifts()
    return _worst_absolute(
        (m.distance_modulus(z), _astropy_model(m).distmod(z).value) for m in _models())


def _check_critical_density() -> float:
    return _worst_relative(
        (m.critical_density0, _astropy_model(m).critical_density0.to("kg/m3").value)
        for m in _models())


def _check_radiation_density() -> float:
    return _worst_relative(
        (m.Or0, _astropy_model(m).Ogamma0 + _astropy_model(m).Onu0) for m in _models())


def _check_evolving_dark_energy() -> float:
    """Dark energy with a changing equation of state, w(a) = w0 + wa (1 - a)."""
    from astropy.cosmology import w0waCDM

    from cosmos.physics import Cosmology

    z = _redshifts()
    worst = 0.0
    for w0, wa in ((-0.75, -0.9), (-0.9, 0.3), (-1.2, 0.0)):
        c = Cosmology(H0=68, Om0=0.31, Ode0=0.69, w0=w0, wa=wa)
        ref = w0waCDM(H0=68, Om0=0.31, Ode0=0.69, w0=w0, wa=wa, Tcmb0=c.Tcmb0, Neff=c.Neff, m_nu=0.0)
        worst = max(worst, _worst_relative([
            (c.efunc(z), ref.efunc(z)),
            (c.luminosity_distance(z), ref.luminosity_distance(z).value),
            (c.Ode(z), ref.Ode(z)),
        ]))
    return worst


# ------------------------------------------------------ against mathematics

def _check_einstein_de_sitter_age() -> float:
    """A flat matter-only universe is exactly two thirds of the Hubble time old."""
    from cosmos.physics import Cosmology

    c = Cosmology(H0=70, Om0=1.0, Ode0=0.0, Tcmb0=0)
    return _worst_relative([(c.age(), 2 / 3 * c.hubble_time)])


def _check_milne_age() -> float:
    """An empty universe coasts, so its age is exactly the Hubble time."""
    from cosmos.physics import Cosmology

    c = Cosmology(H0=70, Om0=0.0, Ode0=0.0, Tcmb0=0)
    return _worst_relative([(c.age(), c.hubble_time)])


def _check_eds_comoving_distance() -> float:
    """Einstein-de Sitter has a closed form: D_C = 2 (c/H0) [1 - 1/sqrt(1+z)]."""
    import numpy as np

    from cosmos.physics import Cosmology

    c = Cosmology(H0=70, Om0=1.0, Ode0=0.0, Tcmb0=0)
    z = _redshifts()
    exact = 2 * c.hubble_distance * (1 - 1 / np.sqrt(1 + z))
    return _worst_relative([(c.comoving_distance(z), exact)])


def _check_distance_duality() -> float:
    """Etherington's relation, which any metric theory must satisfy: D_L = (1+z)^2 D_A."""
    import numpy as np

    z = _redshifts()
    return _worst_relative(
        (m.luminosity_distance(z), (1 + z) ** 2 * np.asarray(m.angular_diameter_distance(z)))
        for m in _models())


# --------------------------------------------------- against published work

def _check_planck18_age() -> float:
    """Planck 2018 VI, Table 2: the age of the universe is 13.797 +/- 0.023 Gyr."""
    from cosmos.physics.presets import PRESETS

    return _worst_absolute([(PRESETS["planck18"].cosmology.age(), 13.797)])


def _check_last_scattering_redshift() -> float:
    """RECFAST and CAMB put the visibility peak at z = 1090 for Planck 2018."""
    from cosmos.physics import recombination as rec

    return _worst_relative([(rec.history().z_peak, 1090.0)])


def _check_helium_abundance() -> float:
    """Standard BBN at the Planck baryon density gives Yp = 0.247."""
    from cosmos.physics import bbn

    eta = float(bbn.eta10_from_omega_b_h2(0.02237))
    return _worst_absolute([(bbn.abundances(eta).yp, 0.247)])


def _check_deuterium_abundance() -> float:
    """The same calculation gives D/H = 2.5e-5, the most sensitive baryometer there is."""
    from cosmos.physics import bbn

    eta = float(bbn.eta10_from_omega_b_h2(0.02237))
    return _worst_relative([(bbn.abundances(eta).d_h, 2.5e-5)])


# ------------------------------------------------------------- the catalogue

CHECKS: tuple[Check, ...] = (
    Check("expansion_rate", "Expansion rate E(z) = H(z)/H0", AGAINST_ASTROPY,
          "astropy LambdaCDM", "Four models — flat, open and closed — at seven redshifts from "
          "0.01 to 10", 1e-6),
    Check("age", "Age of the universe at redshift z", AGAINST_ASTROPY,
          "astropy LambdaCDM", "The same four models and seven redshifts", 1e-4),
    Check("lookback_time", "Lookback time", AGAINST_ASTROPY,
          "astropy LambdaCDM", "The same four models and seven redshifts", 1e-4),
    Check("comoving_distance", "Comoving distance", AGAINST_ASTROPY,
          "astropy LambdaCDM", "The same four models and seven redshifts", 1e-5),
    Check("luminosity_distance", "Luminosity distance", AGAINST_ASTROPY,
          "astropy LambdaCDM", "The same four models and seven redshifts", 1e-5),
    Check("angular_diameter_distance", "Angular diameter distance", AGAINST_ASTROPY,
          "astropy LambdaCDM", "The same four models and seven redshifts", 1e-5),
    Check("distance_modulus", "Distance modulus", AGAINST_ASTROPY,
          "astropy LambdaCDM", "The same four models and seven redshifts", 1e-4,
          relative=False, unit="mag"),
    Check("critical_density", "Critical density today", AGAINST_ASTROPY,
          "astropy LambdaCDM", "Four models", 1e-4),
    Check("radiation_density", "Radiation density, photons and neutrinos", AGAINST_ASTROPY,
          "astropy LambdaCDM", "Four models, with Neff = 3.046", 1e-4),
    Check("evolving_dark_energy", "Dark energy with w(a) = w0 + wa(1 - a)", AGAINST_ASTROPY,
          "astropy w0waCDM", "Three (w0, wa) pairs, comparing E(z), luminosity distance and "
          "the dark energy density", 1e-5),

    Check("einstein_de_sitter_age", "Age of a flat matter-only universe", AGAINST_CLOSED_FORM,
          "two thirds of the Hubble time", "The exact solution of the Friedmann equation "
          "for Om = 1", 1e-6),
    Check("milne_age", "Age of an empty universe", AGAINST_CLOSED_FORM,
          "the Hubble time", "An empty universe coasts, so a(t) is a straight line", 1e-6),
    Check("eds_comoving_distance", "Comoving distance in a flat matter-only universe",
          AGAINST_CLOSED_FORM, "2 (c/H0) [1 - 1/sqrt(1+z)]",
          "The closed form, at seven redshifts", 1e-6),
    Check("distance_duality", "Luminosity against angular diameter distance",
          AGAINST_CLOSED_FORM, "Etherington's relation D_L = (1+z)^2 D_A",
          "A geometric identity that holds in any metric theory; four models, seven "
          "redshifts", 1e-12),

    Check("planck18_age", "Age of the universe, Planck 2018 parameters", AGAINST_PUBLISHED,
          "Planck 2018 VI, Table 2: 13.797 +/- 0.023 Gyr", "The published value has its own "
          "uncertainty, so the tolerance here is the measurement's, not the engine's", 0.03,
          relative=False, unit="Gyr"),
    Check("last_scattering_redshift", "Redshift of last scattering", AGAINST_PUBLISHED,
          "RECFAST and CAMB: z = 1090", "Where the visibility function peaks, for Planck 2018", 0.02),
    Check("helium_abundance", "Primordial helium fraction Yp", AGAINST_PUBLISHED,
          "standard BBN at the Planck baryon density: 0.247",
          "The app's own light-element network, at Omega_b h^2 = 0.02237", 0.003,
          relative=False),
    Check("deuterium_abundance", "Primordial deuterium, D/H", AGAINST_PUBLISHED,
          "standard BBN at the Planck baryon density: 2.5e-5",
          "The same network and baryon density", 0.05),
)

RUNNERS: dict[str, Callable[[], float]] = {
    "expansion_rate": _check_expansion_rate,
    "age": _check_age,
    "lookback_time": _check_lookback_time,
    "comoving_distance": _check_comoving_distance,
    "luminosity_distance": _check_luminosity_distance,
    "angular_diameter_distance": _check_angular_diameter_distance,
    "distance_modulus": _check_distance_modulus,
    "critical_density": _check_critical_density,
    "radiation_density": _check_radiation_density,
    "evolving_dark_energy": _check_evolving_dark_energy,
    "einstein_de_sitter_age": _check_einstein_de_sitter_age,
    "milne_age": _check_milne_age,
    "eds_comoving_distance": _check_eds_comoving_distance,
    "distance_duality": _check_distance_duality,
    "planck18_age": _check_planck18_age,
    "last_scattering_redshift": _check_last_scattering_redshift,
    "helium_abundance": _check_helium_abundance,
    "deuterium_abundance": _check_deuterium_abundance,
}


@dataclass(frozen=True)
class Result:
    check: Check
    worst: float

    @property
    def passed(self) -> bool:
        return self.worst <= self.check.tolerance

    @property
    def headroom(self) -> float:
        """How much of the allowance is used. Below 1 is a pass."""
        return self.worst / self.check.tolerance if self.check.tolerance else 0.0


def astropy_available() -> bool:
    """astropy is a development dependency, so a packaged build does not have it."""
    from importlib.util import find_spec

    return find_spec("astropy") is not None


def runnable(check: Check) -> bool:
    return check.against != AGAINST_ASTROPY or astropy_available()


def run(check: Check) -> Result:
    return Result(check, RUNNERS[check.id]())


def run_all(include_astropy: bool = True) -> list[Result]:
    """Run every check that can run here."""
    return [run(c) for c in CHECKS
            if runnable(c) and (include_astropy or c.against != AGAINST_ASTROPY)]


# ------------------------------------------------------------ the record

def write_record(path: Path | None = None) -> dict:
    """Run everything and save the numbers, so a build without astropy can show them."""
    results = run_all()
    if len(results) != len(CHECKS):
        raise RuntimeError("refusing to record a partial run; install astropy first")
    record = {
        "measured": date.today().isoformat(),
        "worst": {r.check.id: r.worst for r in results},
    }
    (path or RECORD).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n",
                                encoding="utf-8")
    return record


def read_record(path: Path | None = None) -> dict | None:
    """The numbers from the last full run, or None if they were never recorded."""
    try:
        return json.loads((path or RECORD).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
