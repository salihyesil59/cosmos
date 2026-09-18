"""S23 Redshift Survey Slice: the mock catalogue behind L7.5."""

import math
from dataclasses import replace

import numpy as np
import pytest

from cosmos.physics import mock


@pytest.fixture(scope="module")
def truth():
    """A volume-limited catalogue with no observing effects at all."""
    return mock.build(mock.PRESETS_MOCK["truth"][1])


def test_wedge_geometry(truth):
    s = truth.settings
    assert len(truth) > 2000
    assert np.all(truth.r_true <= s.r_max)
    assert np.all(np.abs(np.degrees(truth.angle)) <= s.wedge_deg / 2 + 1e-6)
    latitude = np.degrees(np.arcsin(truth.direction[:, 2]))
    assert np.all(np.abs(latitude) <= s.thickness_deg / 2 + 1e-6)
    # Unit directions, and the observed positions lie along them.
    assert np.allclose(np.linalg.norm(truth.direction, axis=1), 1.0)
    assert np.allclose(np.linalg.norm(truth.points(False), axis=1), truth.r_true)


def test_truth_has_no_observing_effects(truth):
    assert np.allclose(truth.r_obs, truth.r_true, atol=1e-6)
    assert np.allclose(truth.velocity, 0.0)
    assert mock.finger_length(truth) == 0.0
    assert mock.summary(truth)["completeness"] == 1.0


def _wedge_volume(s) -> float:
    solid_angle = math.radians(s.wedge_deg) * 2 * math.sin(math.radians(s.thickness_deg) / 2)
    return solid_angle / 3 * (s.r_max**3 - mock.inner_radius(s) ** 3)


def test_measured_density_matches_the_input(truth):
    """Averaged over universes the density is the one that was asked for; one universe scatters."""
    volume = _wedge_volume(truth.settings)
    counts = [len(mock.build(replace(truth.settings, seed=seed))) for seed in range(1, 9)]
    assert np.mean(counts) / volume == pytest.approx(truth.settings.density, rel=0.08)
    assert len(truth) / volume == pytest.approx(truth.settings.density, rel=0.3)


def test_the_seed_picks_one_universe_out_of_many(truth):
    other = mock.build(replace(truth.settings, seed=23))
    # Same statistics, different realisation: the counts differ by far more than Poisson noise.
    assert len(other) == pytest.approx(len(truth), rel=0.5)
    assert abs(len(other) - len(truth)) > 3 * math.sqrt(len(truth))
    edges = np.geomspace(4.0, 40.0, 7)
    _r, xi_a = mock.correlation_function(truth, observed=False, edges=edges)
    _r, xi_b = mock.correlation_function(other, observed=False, edges=edges)
    assert not np.allclose(xi_a, xi_b)
    assert np.nanmean(xi_b) == pytest.approx(np.nanmean(xi_a), rel=0.7)


def test_bias_raises_the_clustering(truth):
    edges = np.geomspace(5.0, 30.0, 6)
    _r, weak = mock.correlation_function(mock.build(replace(truth.settings, bias=0.8)),
                                         observed=False, edges=edges)
    _r, strong = mock.correlation_function(mock.build(replace(truth.settings, bias=2.4)),
                                           observed=False, edges=edges)
    assert np.nanmean(strong) > 2 * np.nanmean(weak)


def test_redshift_space_squashes_large_scales_and_stretches_small_ones(truth):
    observed = mock.build(replace(truth.settings, velocities=True, fingers_km_s=600.0))
    edges = np.geomspace(1.5, 60.0, 14)
    s, xi_real = mock.correlation_function(observed, observed=False, edges=edges)
    _s, xi_zspace = mock.correlation_function(observed, observed=True, edges=edges)
    small, large = s < 5, (s > 8) & (s < 25)
    assert np.nanmean(xi_zspace[small]) < np.nanmean(xi_real[small])       # fingers of God
    assert np.nanmean(xi_zspace[large]) > np.nanmean(xi_real[large])       # Kaiser squashing


def test_velocities_follow_the_growth_rate(truth):
    with_flow = mock.build(replace(truth.settings, velocities=True, fingers_km_s=0.0))
    assert 0.4 < with_flow.growth_rate < 0.65                              # f ≈ Ωm(z)^0.55 today
    assert 150 < mock.summary(with_flow)["rms_velocity"] < 900
    # The shift is the line-of-sight part of the Zel'dovich displacement, so it has both signs.
    assert np.mean(with_flow.radial_shift < 0) == pytest.approx(0.5, abs=0.15)


def test_fingers_of_god_grow_with_the_dispersion(truth):
    lengths = [mock.finger_length(mock.build(replace(truth.settings, fingers_km_s=v)))
               for v in (0.0, 400.0, 1200.0)]
    assert lengths[0] == 0.0
    assert lengths[1] < lengths[2]
    assert lengths[2] > 8.0


def test_flux_limit_thins_the_catalogue_with_distance(truth):
    assert mock.selection(1.0, 0.0)[0] == 1.0                              # no limit, nothing lost
    limited = mock.build(replace(truth.settings, flux_limit=17.0, density=3e-2))
    report = mock.summary(limited)
    assert 0 < report["completeness"] < 0.3
    assert report["density_drop"] < 0.1
    centres, measured, expected = mock.radial_profile(limited)
    assert centres[0] > mock.inner_radius(limited.settings)
    assert measured[0] > 5 * measured[-1]
    assert expected[-1] < 0.05 * expected[0]
    # Brighter limits keep more of the population, at every distance.
    faint = mock.selection(np.array([50.0, 150.0]), 19.0)
    bright = mock.selection(np.array([50.0, 150.0]), 15.5)
    assert np.all(faint > bright)


def test_photometric_redshifts_blur_the_map_radially(truth):
    blurred = mock.build(replace(truth.settings, redshift_error=0.02))
    shift = np.std(blurred.radial_shift)
    assert shift > 40                                                      # 0.02 × c / H0 ≈ 60 Mpc/h
    edges = np.geomspace(2.0, 20.0, 8)
    _s, sharp_xi = mock.correlation_function(truth, observed=True, edges=edges)
    _s, blurred_xi = mock.correlation_function(blurred, observed=True, edges=edges)
    assert np.nanmean(blurred_xi) < 0.3 * np.nanmean(sharp_xi)


def test_correlation_function_is_normalised_by_the_randoms(truth):
    edges = np.geomspace(3.0, 50.0, 9)
    s, xi = mock.correlation_function(truth, observed=False, edges=edges)
    assert s.shape == (len(edges) - 1,)
    assert np.all(np.isfinite(xi))
    assert xi[0] > xi[-1]                                                  # clustering falls with separation
    assert xi[-1] < 0.3


def test_random_catalogue_fills_the_wedge_without_structure(truth):
    radii = truth.r_true
    random = mock.random_catalogue(truth, 4000, radii, seed=5)
    assert random.shape == (4000, 3)
    distance = np.linalg.norm(random, axis=1)
    assert np.all(distance <= truth.settings.r_max + 1e-6)
    assert np.all(np.abs(np.degrees(np.arctan2(random[:, 1], random[:, 0])))
                  <= truth.settings.wedge_deg / 2 + 1e-6)
    assert np.all(np.abs(np.degrees(np.arcsin(random[:, 2] / distance)))
                  <= truth.settings.thickness_deg / 2 + 1e-6)
    # The randoms follow the data's radial profile, which is what makes Landy–Szalay work.
    assert np.median(distance) == pytest.approx(float(np.median(radii)), rel=0.05)


def test_presets_and_errors(truth):
    for key, (label, settings) in mock.PRESETS_MOCK.items():
        assert label and mock.summary(mock.build(settings))["galaxies"] > 100, key
    with pytest.raises(ValueError):
        mock.build(replace(truth.settings, r_max=truth.settings.box_mpc))
    with pytest.raises(ValueError):
        mock.build(replace(truth.settings, density=1e-12))
    with pytest.raises(ValueError):
        mock.build(replace(truth.settings, wedge_deg=0.0, thickness_deg=0.0))
