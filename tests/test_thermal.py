import math

import numpy as np
import pytest

from cosmos.physics import thermal as th
from cosmos.physics.presets import PRESETS


def test_fermion_entropy_limits():
    assert th.fermion_entropy_fraction(1e-6) == pytest.approx(1.0, rel=1e-6)
    assert th.fermion_entropy_fraction(30) < 1e-8


def test_neutrino_temperature_ratio():
    assert th.neutrino_to_photon_temperature(20.0) == pytest.approx(1.0, abs=1e-3)
    assert th.neutrino_to_photon_temperature(0.005) == pytest.approx((4 / 11) ** (1 / 3), rel=1e-4)
    ratios = th.neutrino_to_photon_temperature(np.logspace(1, -2, 30))
    assert np.all(np.diff(ratios) <= 1e-12)  # photons are heated monotonically
    assert th.neutrino_temperature_today() == pytest.approx(1.945, abs=0.001)


def test_number_densities():
    assert th.photon_number_density() == pytest.approx(410.7, abs=0.5)
    assert 3 * th.neutrino_number_density_per_species() == pytest.approx(336, abs=1)


def test_neutrino_decoupling_near_one_mev():
    t_dec = th.neutrino_decoupling_temperature()
    assert 0.8 < t_dec < 3.0
    assert float(th.weak_rate_over_hubble(t_dec)) == pytest.approx(1.0)


def test_baryon_to_photon_ratio_from_planck():
    c = PRESETS["planck18"].cosmology
    eta = th.baryon_to_photon_ratio(c.Ob0 * c.h**2)
    assert eta == pytest.approx(6.1e-10, rel=0.03)


def test_nucleon_equilibrium_drops_below_eta_at_tens_of_mev():
    t = np.logspace(1, 3, 3000)
    ratio = th.nucleon_equilibrium_ratio(t)
    crossing = t[np.argmin(np.abs(np.log(ratio / 6.1e-10)))]
    assert 20 < crossing < 60
    assert math.isclose(float(th.kelvin_from_mev(1.0)), 1.1605e10, rel_tol=1e-3)
