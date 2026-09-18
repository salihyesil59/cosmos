"""S22 Standard Siren Explorer: the H0 measurement behind L6.5 and L6.9."""

import math
from dataclasses import replace

import numpy as np
import pytest

from cosmos.physics import gravitational_waves as gw
from cosmos.physics import sirens

GW170817 = sirens.PRESETS_SIREN["gw170817"][1]


def test_orientation_spans_a_factor_of_root_eight():
    assert sirens.orientation(0.0) == pytest.approx(1.0)
    assert sirens.orientation(180.0) == pytest.approx(1.0)          # face-off is as loud as face-on
    assert sirens.orientation(90.0) == pytest.approx(0.5 / math.sqrt(2))
    # Amplitude ratio 2√2, so an edge-on binary is heard to 35% of the distance.
    assert sirens.orientation(0.0) / sirens.orientation(90.0) == pytest.approx(2 * math.sqrt(2))
    assert np.all(np.diff(sirens.orientation(np.linspace(0, 90, 40))) < 0)


def test_gw170817_reproduces_the_published_event():
    m = sirens.measure(GW170817)
    assert m.snr == pytest.approx(32.4, rel=1e-6)                   # the calibration point
    assert m.detected
    assert m.sky_area_deg2 == pytest.approx(28.0, rel=0.05)         # published 28 deg²
    assert m.distance == pytest.approx(40.0, rel=0.15)              # published 40 Mpc
    assert m.distance_low < 40.0 < m.distance_high
    assert m.distance - m.distance_low > m.distance_high - m.distance   # the tail runs to small D
    assert 60 < m.h0 < 80                                           # published 70 +12 −8
    assert 10 < m.h0_single_percent < 25


def test_signal_to_noise_scales_as_the_physics_says():
    louder = sirens.measure(replace(GW170817, distance_mpc=20.0))
    assert louder.snr == pytest.approx(2 * sirens.measure(GW170817).snr, rel=1e-9)
    heavier = replace(GW170817, m1=2.92, m2=2.54)                   # twice the chirp mass
    ratio = sirens.signal_to_noise(heavier) / sirens.signal_to_noise(GW170817)
    assert ratio == pytest.approx(2 ** (5 / 6), rel=1e-6)
    assert gw.chirp_mass(2.92, 2.54) == pytest.approx(2 * gw.chirp_mass(1.46, 1.27), rel=1e-9)


def test_detection_threshold_and_horizon():
    far = replace(GW170817, distance_mpc=5000.0)
    assert not sirens.measure(far).detected
    horizon = sirens.horizon_distance(GW170817)
    at_horizon = replace(GW170817, distance_mpc=horizon, inclination_deg=0.0)
    assert sirens.signal_to_noise(at_horizon) == pytest.approx(8.0, rel=1e-6)


def test_better_networks_hear_further_and_localise_better():
    reach = {key: sirens.horizon_distance(replace(GW170817, network=key)) for key in sirens.NETWORKS}
    assert reach["et"] > reach["aplus"] > reach["design"] > reach["o2"]
    # At a fixed signal-to-noise ratio the area is set by the number of sites.
    areas = []
    for key in ("two", "o2", "o4", "aplus"):
        s = replace(GW170817, network=key)
        areas.append(sirens.sky_area(s) * sirens.signal_to_noise(s) ** 2)
    assert areas == sorted(areas, reverse=True)
    assert areas[0] / areas[1] > 20                                 # two sites give a ring, not a patch


def test_the_inclination_degeneracy_widens_the_distance():
    """The amplitude alone cannot separate distance from inclination."""
    distances, density = sirens.distance_posterior(GW170817)
    mid, low, high = sirens.credible_interval(distances, density)
    assert 0.05 < (high - low) / mid < 0.5
    # With no network polarisation information the posterior is far wider.
    plain = sirens.POLARISATION
    try:
        sirens.POLARISATION = 1e6
        wide_mid, wide_low, wide_high = sirens.credible_interval(*sirens.distance_posterior(GW170817))
    finally:
        sirens.POLARISATION = plain
    assert (wide_high - wide_low) / wide_mid > (high - low) / mid

    _d, _i, joint = sirens.degeneracy_grid(GW170817)
    assert joint.max() == pytest.approx(1.0)
    assert joint.shape[0] == joint.shape[1]


def test_a_dark_siren_costs_a_factor_that_grows_with_the_candidates():
    assert sirens.dark_penalty(1) == pytest.approx(1.0)
    assert sirens.dark_penalty(10000) == pytest.approx(3.5, rel=0.05)
    assert sirens.dark_penalty(100) < sirens.dark_penalty(100000)

    bright = sirens.measure(replace(GW170817, host_known=True))
    dark = sirens.measure(replace(GW170817, host_known=False))
    assert dark.distance == pytest.approx(bright.distance)          # the wave does not care
    assert dark.host_candidates > 1
    assert dark.h0_single_percent == pytest.approx(
        bright.h0_single_percent * sirens.dark_penalty(dark.host_candidates), rel=1e-9)

    # A nearby, well-localised event has few candidates, so going dark costs little.
    # A distant one badly located by two detectors has a million, and costs everything.
    vague = sirens.measure(sirens.PRESETS_SIREN["gw190425"][1])
    assert vague.host_candidates > 100 * dark.host_candidates
    assert vague.h0_single_percent > 3 * dark.h0_single_percent


def test_peculiar_velocity_dominates_nearby():
    near = sirens.measure(replace(GW170817, peculiar_velocity_km_s=0.0))
    with_motion = sirens.measure(GW170817)
    assert with_motion.h0_single_percent > near.h0_single_percent
    # Far away the same velocity error is negligible.
    far = replace(GW170817, distance_mpc=1000.0, network="aplus")
    assert (sirens.measure(far).h0_single_percent
            == pytest.approx(sirens.measure(replace(far, peculiar_velocity_km_s=0.0)).h0_single_percent,
                             rel=0.02))


def test_combining_events_beats_down_the_error():
    one = sirens.measure(replace(GW170817, events=1))
    hundred = sirens.measure(replace(GW170817, events=100))
    assert hundred.h0_percent == pytest.approx(one.h0_percent / 10, rel=1e-9)
    assert hundred.h0_single_percent == pytest.approx(one.h0_single_percent, rel=1e-9)

    needed = sirens.events_needed(GW170817, 2.0)
    assert sirens.measure(replace(GW170817, events=needed)).h0_percent <= 2.0
    assert sirens.measure(replace(GW170817, events=needed - 1)).h0_percent > 2.0


def test_every_preset_is_usable():
    for key, (label, settings) in sirens.PRESETS_SIREN.items():
        m = sirens.measure(settings)
        assert label and m.snr > 5, key
        assert m.distance > 0 and m.h0_single_percent > 0, key
        # The redshift the host would have, at the true distance, in the fiducial cosmology.
        # D_L = (1 + z) D_C grows faster than cz/H0, so z stays below D_L H0/c ≈ D_L / 4430 Mpc.
        assert settings.distance_mpc / 8000 < m.redshift < settings.distance_mpc / 4000, key
    assert sirens.measure(sirens.PRESETS_SIREN["et"][1]).h0_percent < 2.0
    assert not sirens.PRESETS_SIREN["gw190425"][1].host_known
