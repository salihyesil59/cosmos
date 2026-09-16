"""Timeline, Big Bang nucleosynthesis and Olbers' paradox."""

import math

import numpy as np
import pytest

from cosmos.physics import bbn, olbers
from cosmos.physics.timeline import EPOCHS, T_MAX_S, T_MIN_S, YEAR_S, Timeline, format_time


@pytest.fixture(scope="module")
def timeline():
    return Timeline()


def test_timeline_temperatures(timeline):
    assert timeline.temperature_k(1.0) == pytest.approx(1e10, rel=0.1)
    assert timeline.temperature_k(180.0) == pytest.approx(1e9, rel=0.1)       # BBN: T ≈ 0.086 MeV
    assert timeline.temperature_k(3.8e5 * YEAR_S) == pytest.approx(2950, rel=0.05)
    assert timeline.temperature_k(timeline.age_s) == pytest.approx(2.7255, rel=0.01)
    times = np.logspace(math.log10(T_MIN_S), math.log10(T_MAX_S), 400)
    temps = [timeline.temperature_k(t) for t in times]
    assert all(b < a for a, b in zip(temps, temps[1:]))


def test_timeline_composition_and_epochs(timeline):
    assert timeline.dominant(1e3 * YEAR_S) == "radiation"
    assert timeline.dominant(1e8 * YEAR_S) == "matter"
    assert timeline.dominant(timeline.age_s) == "dark energy"
    assert [e.name for e in timeline.epochs_at(13.8e9 * YEAR_S)] == ["Today"]
    assert "Big Bang nucleosynthesis" in [e.name for e in timeline.epochs_at(300.0)]
    assert timeline.particle_horizon_m(timeline.age_s) / (1e9 * 9.4607e15) == pytest.approx(46, rel=0.03)
    assert all(e.start_s >= T_MIN_S and e.status in ("speculative", "theory", "tested", "observed") for e in EPOCHS)
    assert format_time(180) == "3 minutes"
    assert format_time(13.8e9 * YEAR_S) == "13.8 billion years"


def test_bbn_planck_values():
    eta = float(bbn.eta10_from_omega_b_h2(0.02237))
    ab = bbn.abundances(eta)
    assert ab.yp == pytest.approx(0.247, abs=0.003)
    assert ab.d_h == pytest.approx(2.5e-5, rel=0.05)
    assert ab.li7_h == pytest.approx(5e-10, rel=0.15)
    # The lithium problem: prediction about three times the observed value.
    assert ab.li7_h / bbn.OBSERVED["Li7/H"][0] > 2.5


def test_bbn_trends():
    eta = np.linspace(1, 10, 200)
    ab = bbn.abundances(eta)
    assert np.all(np.diff(ab.yp) > 0) and np.all(np.diff(ab.d_h) < 0) and np.all(np.diff(ab.he3_h) < 0)
    assert 1.5 < eta[np.argmin(ab.li7_h)] < 3.5                                  # the lithium dip
    assert bbn.abundances(6.1, delta_neff=1).yp > bbn.abundances(6.1).yp + 0.01
    assert bbn.abundances(6.1, neutron_lifetime=900).yp > bbn.abundances(6.1).yp


def test_bbn_deuterium_measures_baryons():
    eta = bbn.eta10_from_deuterium(bbn.OBSERVED["D/H"][0])
    assert float(bbn.omega_b_h2_from_eta10(eta)) == pytest.approx(0.0222, rel=0.03)
    t_nuc = bbn.deuterium_bottleneck_temperature(6e-10)
    assert 0.06 < t_nuc < 0.08                     # MeV: far below the 2.2 MeV binding energy
    y, t = bbn.simple_helium_estimate(6e-10)
    assert 0.22 < y < 0.26 and 150 < t < 400


def test_olbers_analytic():
    mfp = olbers.mean_free_path(1e-3)
    assert mfp == pytest.approx(1 / (math.pi * 1e-3))
    assert olbers.sky_coverage(math.inf, mfp) == 1.0
    assert olbers.sky_brightness(math.inf, mfp) == 1.0
    # Expansion keeps even an infinitely old sky dark when the Hubble length is short.
    assert olbers.sky_brightness(math.inf, mfp, hubble_length=mfp / 100) < 0.03


def test_olbers_monte_carlo_matches_analytic():
    for density, depth in [(5e-4, 300), (2e-3, 400), (2e-3, 3000)]:
        expected = olbers.sky_coverage(depth, olbers.mean_free_path(density))
        mean = np.mean([olbers.generate_sky(density, depth, pixels=120, seed=s).coverage for s in range(40)])
        assert mean == pytest.approx(expected, abs=0.03)
    sky = olbers.generate_sky(2e-3, math.inf, hubble_length=300.0, pixels=120)
    assert sky.coverage == 1.0
    assert sky.brightness == pytest.approx(olbers.sky_brightness(math.inf, olbers.mean_free_path(2e-3), 300.0), abs=0.1)


def test_olbers_real_universe():
    real = olbers.real_universe()
    assert 1e23 < real.mean_free_path_ly < 1e25
    assert real.coverage < 1e-12
    assert real.daylight_factor == pytest.approx(46000, rel=0.05)
