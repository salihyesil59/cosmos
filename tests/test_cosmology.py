"""Physics engine tests, cross-checked against astropy where possible."""

import math

import numpy as np
import pytest

from cosmos.physics import Cosmology, Fate
from cosmos.physics.cosmology import no_big_bang_boundary, recollapse_boundary
from cosmos.physics.presets import PRESETS

astropy_cosmo = pytest.importorskip("astropy.cosmology")
Z = np.array([0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0])


def astropy_model(c: Cosmology):
    return astropy_cosmo.LambdaCDM(
        H0=c.H0, Om0=c.Om0, Ode0=c.Ode0, Tcmb0=c.Tcmb0, Neff=c.Neff, m_nu=0.0, Ob0=c.Ob0
    )


MODELS = [
    PRESETS["planck18"].cosmology,
    PRESETS["wmap9"].cosmology,
    Cosmology(H0=70, Om0=0.3, Ode0=0.0),        # open, with radiation
    Cosmology(H0=70, Om0=0.5, Ode0=0.8),        # closed, accelerating
]


@pytest.mark.parametrize("model", MODELS, ids=lambda m: f"Om{m.Om0}_Ode{m.Ode0:.3f}")
class TestAgainstAstropy:
    def test_radiation_density(self, model):
        ref = astropy_model(model)
        assert model.Ogamma0 == pytest.approx(ref.Ogamma0, rel=1e-4)
        assert model.Or0 == pytest.approx(ref.Ogamma0 + ref.Onu0, rel=1e-4)
        assert model.Ok0 == pytest.approx(ref.Ok0, abs=1e-6)

    def test_expansion_rate(self, model):
        ref = astropy_model(model)
        np.testing.assert_allclose(model.efunc(Z), ref.efunc(Z), rtol=1e-6)

    def test_age_and_lookback(self, model):
        ref = astropy_model(model)
        assert model.age(0) == pytest.approx(ref.age(0).value, rel=1e-4)
        np.testing.assert_allclose(model.age(Z), ref.age(Z).value, rtol=1e-4)
        np.testing.assert_allclose(model.lookback_time(Z), ref.lookback_time(Z).value, rtol=1e-4)

    def test_distances(self, model):
        ref = astropy_model(model)
        np.testing.assert_allclose(model.comoving_distance(Z), ref.comoving_distance(Z).value, rtol=1e-5)
        np.testing.assert_allclose(model.luminosity_distance(Z), ref.luminosity_distance(Z).value, rtol=1e-5)
        np.testing.assert_allclose(
            model.angular_diameter_distance(Z), ref.angular_diameter_distance(Z).value, rtol=1e-5
        )
        np.testing.assert_allclose(model.distance_modulus(Z), ref.distmod(Z).value, atol=1e-4)

    def test_critical_density(self, model):
        ref = astropy_model(model)
        assert model.critical_density0 == pytest.approx(ref.critical_density0.to("kg/m3").value, rel=1e-4)


def test_planck18_age_is_about_13_8_gyr():
    assert PRESETS["planck18"].cosmology.age() == pytest.approx(13.79, abs=0.05)


def test_einstein_de_sitter_age_is_two_thirds_hubble_time():
    c = PRESETS["eds"].cosmology
    assert c.age() == pytest.approx(2 / 3 * c.hubble_time, rel=1e-6)


def test_milne_age_equals_hubble_time():
    c = PRESETS["milne"].cosmology
    assert c.age() == pytest.approx(c.hubble_time, rel=1e-6)


def test_flat_constructor_is_flat():
    c = Cosmology.flat(H0=70, Om0=0.3)
    assert abs(c.Ok0) < 1e-12
    assert c.geometry == "flat"


@pytest.mark.parametrize(
    "om, ode, fate",
    [
        (0.3, 0.7, Fate.ACCELERATES_FOREVER),
        (0.3, 0.0, Fate.EXPANDS_FOREVER),
        (1.0, 0.0, Fate.EXPANDS_FOREVER),
        (2.0, 0.0, Fate.BIG_CRUNCH),
        (0.3, -0.5, Fate.BIG_CRUNCH),
        (0.3, 2.5, Fate.NO_BIG_BANG),
        (0.0, 1.0, Fate.NO_BIG_BANG),
    ],
)
def test_fate_classification(om, ode, fate):
    assert Cosmology(H0=70, Om0=om, Ode0=ode, Tcmb0=0).fate() is fate


@pytest.mark.parametrize("om", [1.5, 2.0, 3.0])
def test_recollapse_boundary_matches_numerical_classifier(om):
    edge = float(recollapse_boundary(np.array([om]))[0])
    assert Cosmology(Om0=om, Ode0=edge - 0.01, Tcmb0=0).fate() is Fate.BIG_CRUNCH
    assert Cosmology(Om0=om, Ode0=edge + 0.01, Tcmb0=0).fate() is not Fate.BIG_CRUNCH


@pytest.mark.parametrize("om", [0.1, 0.3, 0.8, 2.0])
def test_no_big_bang_boundary_matches_numerical_classifier(om):
    edge = float(no_big_bang_boundary(np.array([om]))[0])
    assert Cosmology(Om0=om, Ode0=edge - 0.02, Tcmb0=0).has_big_bang()
    assert not Cosmology(Om0=om, Ode0=edge + 0.02, Tcmb0=0).has_big_bang()


def test_expansion_history_passes_through_today():
    c = PRESETS["planck18"].cosmology
    hist = c.expansion_history(t_future=20)
    assert np.interp(0.0, hist.t, hist.a) == pytest.approx(1.0, abs=1e-6)
    assert hist.age == pytest.approx(c.age(), rel=1e-9)
    assert hist.crunch_time is None
    # a(t) must be monotonic for this universe.
    assert np.all(np.diff(hist.a) >= 0)


def test_expansion_history_detects_crunch():
    c = PRESETS["closed_matter"].cosmology
    hist = c.expansion_history(t_future=100)
    assert hist.crunch_time is not None
    # Closed matter-only universes are time-symmetric: total lifetime = 2 * time to max expansion.
    om = c.Om0
    theta_max = math.pi
    lifetime = om / (om - 1) ** 1.5 * theta_max * c.hubble_time
    assert hist.crunch_time - hist.big_bang_time == pytest.approx(lifetime, rel=1e-3)


def test_deceleration_parameter_today():
    c = Cosmology(H0=70, Om0=0.3, Ode0=0.7, Tcmb0=0)
    assert c.deceleration_parameter(0) == pytest.approx(0.15 - 0.7)
