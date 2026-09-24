"""Direct detection of WIMPs (S29): rates, limits and the modulation."""

import math

import numpy as np
import pytest

from cosmos.physics import detection as det


def test_kinematics():
    # A 100 GeV WIMP at 220 km/s gives xenon at most about 27 keV.
    m_a = det.nucleus_mass(131.29)
    mu = det.reduced_mass(100, m_a)
    e_max = 2 * mu**2 * (220 / det.C_KM_S) ** 2 / m_a * 1e6
    assert e_max == pytest.approx(26.7, rel=0.02)
    # v_min inverts that: the speed needed for E_max is 220 km/s.
    assert det.v_min(e_max, 100, 131.29) == pytest.approx(220, rel=1e-6)


def test_form_factor_and_halo():
    f2 = det.helm_form_factor_sq([0.0, 10.0, 30.0], 131.29)
    assert f2[0] == pytest.approx(1.0) and 0 < f2[2] < f2[1] < 1
    assert det.helm_form_factor_sq(10.0, 28.09) > f2[1]          # small nuclei are nearly point-like
    eta = det.eta([0.0, 300.0, 1000.0])
    assert eta[0] > eta[1] > 0 and eta[2] == 0.0
    # With no velocity cut, η(0) is the mean inverse speed, about 1/(v0 √π) · ... ≈ 3.5e-3 s/km.
    assert eta[0] == pytest.approx(3.5e-3, rel=0.15)


def test_rates_scale_as_they_should():
    base = det.expected_events(50, 1e-46, "xenon", 1.0, 5, 50)
    assert det.expected_events(50, 2e-46, "xenon", 1.0, 5, 50) == pytest.approx(2 * base)
    assert det.expected_events(50, 1e-46, "xenon", 3.0, 5, 50) == pytest.approx(3 * base)
    # Order of magnitude: tens of events per tonne-year at 1e-46 cm² near 50 GeV on xenon.
    assert 5 < base < 100
    # Coherence: per kilogram, xenon beats argon for heavy WIMPs.
    assert base > det.expected_events(50, 1e-46, "argon", 1.0, 5, 50)
    # Xenon is blind to a 5 GeV WIMP above 5 keV, silicon with a low threshold is not.
    assert det.expected_events(5, 1e-42, "xenon", 1.0, 5, 50) == 0
    assert det.expected_events(5, 1e-42, "silicon", 0.001, 0.1, 10) > 1


def test_poisson_limits():
    assert det.upper_limit(0) == pytest.approx(2.3026, rel=1e-4)
    assert det.upper_limit(1) > det.upper_limit(0)
    assert det.discovery_significance(10, 1) > 5 > det.discovery_significance(2, 1)
    assert det.discovery_significance(0, 1) == 0


def test_the_xenon_limit_looks_like_lz():
    """LZ (2024): 2.2e-48 cm² near 36 GeV with 4.2 tonne-years."""
    masses = np.geomspace(5, 1e4, 60)
    curve = det.exclusion_curve(masses, det.EXPERIMENTS["lz"])
    best = int(np.nanargmin(curve))
    assert 20 < masses[best] < 80
    assert 1e-48 < curve[best] < 1e-47
    assert np.isinf(det.exclusion_curve([3.0], det.EXPERIMENTS["lz"])[0])
    # Above the minimum the limit weakens roughly in proportion to the mass.
    ratio = det.exclusion_curve([5000], det.EXPERIMENTS["lz"])[0] / det.exclusion_curve([500], det.EXPERIMENTS["lz"])[0]
    assert ratio == pytest.approx(10, rel=0.2)


def test_light_targets_reach_lower_masses():
    lz = det.exclusion_curve([8.0], det.EXPERIMENTS["lz"])[0]
    silicon = det.exclusion_curve([8.0], det.EXPERIMENTS["silicon"])[0]
    germanium = det.exclusion_curve([8.0], det.EXPERIMENTS["germanium"])[0]
    assert math.isfinite(silicon) and math.isfinite(germanium)
    assert germanium < lz or not math.isfinite(lz)


def test_annual_modulation_peaks_in_june():
    days, counts = det.modulation(60, 1e-46, "xenon", 1.0, 5, 50)
    assert abs(days[int(np.argmax(counts))] - det.PEAK_DAY) <= 5
    amplitude = (counts.max() - counts.min()) / (counts.max() + counts.min())
    assert 0.003 < amplitude < 0.1
