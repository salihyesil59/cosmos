"""Tests for Level 6 physics: geometry, inflation, reionisation, gravitational waves, supernovae, MOND."""

import math

import numpy as np
import pytest

from cosmos.physics import geometry, gravitational_waves as gw, inflation, reionization, rotation, supernovae
from cosmos.physics.cosmology import Cosmology
from cosmos.physics.presets import PRESETS

PLANCK = PRESETS["planck18"].cosmology


# ---------------------------------------------------------------- geometry
def test_triangle_angle_sums():
    assert math.degrees(geometry.angle_sum(math.pi / 2, 1)) == pytest.approx(270.0)  # an octant of the sphere
    assert math.degrees(geometry.angle_sum(1.0, 0)) == pytest.approx(180.0)
    assert math.degrees(geometry.angle_sum(1e-4, 1)) == pytest.approx(180.0, abs=1e-4)
    assert geometry.angle_sum(1.0, -1) < math.pi < geometry.angle_sum(1.0, 1)
    # Gauss-Bonnet: angle excess equals area for unit curvature.
    assert geometry.triangle_area(0.8, 1) == pytest.approx(geometry.angle_sum(0.8, 1) - math.pi)


def test_triangle_drawings_have_the_requested_side():
    v = geometry.spherical_triangle(1.1)
    assert math.acos(np.dot(v[0], v[1])) == pytest.approx(1.1)
    edges = geometry.poincare_triangle(1.3)
    p, q = edges[0][0], edges[0][-1]
    d = math.acosh(1 + 2 * np.sum((p - q) ** 2) / ((1 - p @ p) * (1 - q @ q)))
    assert d == pytest.approx(1.3)


def test_circles_and_angular_sizes():
    assert geometry.circumference(math.pi / 2, 1) == pytest.approx(2 * math.pi)
    assert geometry.circumference(1.0, -1) > 2 * math.pi
    closed, flat, open_ = (float(geometry.angular_size(0.01, 1.0, k)) for k in (1, 0, -1))
    assert closed > flat > open_
    assert math.isinf(geometry.curvature_radius_mpc(0.0, 70))
    assert geometry.curvature_radius_mpc(-0.01, 70) == pytest.approx(42828, rel=1e-3)


# --------------------------------------------------------------- inflation
def test_quadratic_inflation_matches_analytic_slow_roll():
    pot = inflation.POTENTIALS["quadratic"]
    n = 55.0
    res = inflation.predictions(pot, n)
    assert res.n_s == pytest.approx(1 - 2 / (n + 0.5), abs=1e-4)
    assert res.r == pytest.approx(8 / (n + 0.5), rel=1e-3)
    assert not res.consistent
    assert res.energy_scale_gev == pytest.approx(2e16, rel=0.1)


def test_starobinsky_fits_the_data():
    res = inflation.predictions(inflation.POTENTIALS["starobinsky"], 55)
    assert res.n_s == pytest.approx(0.965, abs=0.002)
    assert res.r < 0.005
    assert res.consistent


def test_full_evolution_ends_inflation_near_slow_roll_estimate():
    for key in inflation.POTENTIALS:
        traj = inflation.evolve(inflation.POTENTIALS[key], n_before=60.0, extra=1.0)
        assert 58 < traj.end_efold < 63
        assert np.all(np.isfinite(traj.hubble))


def test_comoving_hubble_radius_shrinks_during_inflation():
    x, y, i_end = inflation.comoving_hubble_radius_history()
    assert np.all(np.diff(y[:i_end]) < 0)
    assert y[-1] < y[-50] + 1e-9 or y[-1] < 0.5  # it shrinks again once dark energy dominates


# ------------------------------------------------------------ reionisation
def test_planck_optical_depth():
    assert reionization.optical_depth(PLANCK, 7.7) == pytest.approx(0.054, abs=0.003)
    assert reionization.reionization_redshift(PLANCK, 0.054) == pytest.approx(7.7, abs=0.3)
    assert reionization.frequency_mhz(0.0) == pytest.approx(1420.4, abs=0.1)


def test_21cm_signal_shape():
    z = np.linspace(5, 200, 800)
    tb = reionization.global_21cm_signal(PLANCK, z)
    assert -250 < tb.min() < -80                      # cosmic-dawn absorption trough
    assert 12 < z[np.argmin(tb)] < 25
    assert abs(tb[z > 190]).max() < 20                # gas and CMB coupled at very high z
    assert abs(float(np.interp(5.5, z, tb))) < 5      # neutral hydrogen gone after reionisation


# ---------------------------------------------------- gravitational waves
def test_gw150914_like_chirp():
    assert gw.time_to_merger(35.0, 30.0) == pytest.approx(0.17, abs=0.02)
    t, h, f = gw.chirp_waveform(30.0, 410.0)
    assert 5e-22 < np.abs(h).max() < 3e-21
    assert np.all(np.diff(f) >= 0)
    assert gw.frequency_at(float(gw.time_to_merger(100.0, 30.0)), 30.0) == pytest.approx(100.0)


def test_standard_siren():
    assert gw.chirp_mass(1.46, 1.27) == pytest.approx(1.186, abs=0.002)
    h = float(gw.strain_amplitude(100.0, 1.2, 40.0))
    assert gw.siren_distance_from_amplitude(h, 100.0, 1.2) == pytest.approx(40.0)
    assert gw.siren_hubble_constant(3017, 43.8) == pytest.approx(69, abs=1)


# -------------------------------------------------------------- supernovae
def test_luminosity_distance_grid_matches_cosmology():
    z = np.array([0.1, 0.8, 2.0])
    for om, ol in [(0.3, 0.7), (0.4, 0.0), (1.2, 0.6)]:
        c = Cosmology(H0=70, Om0=om, Ode0=ol, Tcmb0=0)
        grid = supernovae.dimensionless_luminosity_distance(z, om, ol)[0] * c.hubble_distance
        np.testing.assert_allclose(grid, c.luminosity_distance(z), rtol=2e-4)


def test_modern_sample_recovers_truth_and_hubble_tension():
    sample = supernovae.modern_sample()
    fit = supernovae.fit_grid(sample)
    assert fit.best_om == pytest.approx(0.3, abs=0.1)
    assert fit.best_ol == pytest.approx(0.7, abs=0.15)
    assert fit.acceleration_sigma > 5
    assert fit.hubble_constant(supernovae.M_CEPHEID) == pytest.approx(73.0, abs=1.0)
    assert fit.hubble_constant(supernovae.M_INVERSE_LADDER) == pytest.approx(68.2, abs=1.0)


def test_discovery_sample_prefers_dark_energy():
    sample = supernovae.discovery_sample()
    assert len(sample.z) == 60
    flat = supernovae.fit_flat(sample)
    assert flat.acceleration_sigma > 3
    assert 0.15 < flat.best_om < 0.45


# -------------------------------------------------------------------- MOND
def test_mond_gives_flat_rotation_curve():
    r = np.array([100.0, 200.0, 400.0])  # deep-MOND regime, far outside the visible galaxy
    mass = 6e10
    v = rotation.mond_velocity(r, rotation.keplerian_velocity(r, mass))
    expected = (6.674e-11 * mass * 1.98847e30 * rotation.A0_MOND) ** 0.25 / 1e3
    np.testing.assert_allclose(v, expected, rtol=0.05)
    inner = rotation.mond_velocity(0.5, rotation.keplerian_velocity(0.5, mass))
    assert float(inner) == pytest.approx(float(rotation.keplerian_velocity(0.5, mass)), rel=0.05)
