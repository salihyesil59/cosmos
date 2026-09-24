"""Hydrogen recombination (S25): Saha, Peebles and the last-scattering surface."""

import math

import numpy as np
import pytest

from cosmos.physics import recombination as rec


@pytest.fixture(scope="module")
def planck():
    return rec.history()


def test_saha_is_ionised_early_and_neutral_late():
    x = rec.saha_fraction(np.array([3000.0, 1370.0, 800.0]))
    assert x[0] == pytest.approx(1.0, abs=1e-6)
    assert x[1] == pytest.approx(0.5, abs=0.05)
    assert x[2] < 1e-5


def test_saha_solves_its_own_equation():
    z = 1400.0
    x = float(rec.saha_fraction(z))
    t = rec.const.T_CMB * (1 + z)
    s = (float(rec._thermal_factor(t)) * math.exp(-rec.B_HYDROGEN / (rec.const.K_B * t))
         / float(rec.hydrogen_density(z, 0.02237)))
    assert x * x / (1 - x) == pytest.approx(s, rel=1e-9)


def test_the_bottleneck_delays_recombination(planck):
    """Peebles lags Saha by roughly a hundred in redshift, as every textbook shows."""
    assert planck.z_half("saha") == pytest.approx(1370, abs=25)
    assert 60 < planck.z_half("saha") - planck.z_half() < 160
    assert np.all(planck.x_peebles >= planck.x_saha - 1e-6)


def test_last_scattering_matches_the_full_codes(planck):
    """RECFAST and CAMB put the visibility peak at z ≈ 1090 with Δz ≈ 190 for Planck 2018."""
    assert planck.z_peak == pytest.approx(1090, rel=0.02)
    assert planck.width == pytest.approx(195, rel=0.1)
    assert np.interp(1.0, planck.tau[::-1], planck.z[::-1]) == pytest.approx(1090, rel=0.02)
    area = abs(np.trapezoid(planck.visibility, planck.z))
    assert area == pytest.approx(1.0, abs=0.01)              # almost every photon scattered in the window


def test_a_residue_freezes_out(planck):
    assert 1e-4 < planck.x_freeze < 1e-3
    fewer_baryons = rec.history(omega_b_h2=0.01)
    assert fewer_baryons.x_freeze > planck.x_freeze          # fewer protons to find


def test_recombination_follows_temperature_not_redshift(planck):
    hotter = rec.history(t_cmb=2 * rec.const.T_CMB, z_start=900, z_end=100)
    t_ours = planck.temperature(planck.z_peak)
    t_hot = hotter.temperature(hotter.z_peak)
    assert t_hot == pytest.approx(t_ours, rel=0.08)
    assert hotter.z_peak < 0.6 * planck.z_peak


def test_photon_counts():
    assert rec.photon_to_baryon_ratio() == pytest.approx(1.64e9, rel=0.02)   # 1/η with η = 6.1e-10
    t_equal = rec.photons_equal_atoms_temperature()
    assert 5000 < t_equal < 7000                                            # kT ≈ B / ln(1/η)
    assert rec.ionising_photons_per_baryon(t_equal) == pytest.approx(1.0, rel=0.05)
    # 13.6 eV corresponds to 158 000 K, fifty times hotter than last scattering.
    assert rec.B_HYDROGEN / rec.const.K_B == pytest.approx(157_887, rel=1e-3)
