"""The halo mass function (S27): Press–Schechter, Sheth–Tormen and cluster counts."""

import math

import numpy as np
import pytest

from cosmos.physics import halos
from cosmos.physics.cosmology import Cosmology
from cosmos.physics.structure import DELTA_C, LinearPowerSpectrum

PLANCK = Cosmology.flat(H0=67.66, Om0=0.311, Ob0=0.049)


@pytest.fixture(scope="module")
def model():
    return halos.HaloModel(PLANCK, sigma8=0.811)


def test_multiplicities_hold_all_the_mass():
    """∫ f(ν) dln ν = 1 for Press–Schechter (and ≈ 1 for Sheth–Tormen): every particle is in some halo."""
    lnnu = np.linspace(math.log(1e-4), math.log(20), 20000)
    for name in halos.MODELS:
        total = np.trapezoid(halos.multiplicity(np.exp(lnnu), name), lnnu)
        assert total == pytest.approx(1.0, abs=0.02), name      # ST converges slowly as ν → 0


def test_press_schechter_matches_the_structure_module(model):
    spectrum = LinearPowerSpectrum(PLANCK, sigma8=0.811)
    masses = np.logspace(12, 15, 13)
    reference = spectrum.press_schechter(masses)
    ours = np.interp(np.log(masses), np.log(model.masses), model.dn_dlnm(0.0, "press-schechter"))
    assert ours == pytest.approx(reference, rel=0.05)


def test_sigma8_is_what_it_says(model):
    r8_mass = 4 / 3 * math.pi * 8**3 * model.rho_m
    sigma = np.exp(np.interp(math.log(r8_mass), np.log(model.masses), np.log(model.sigma0)))
    assert sigma == pytest.approx(0.811, rel=0.01)


def test_familiar_numbers(model):
    # Today the typical collapsing halo is a group, a few 10¹² M☉/h.
    assert 1e12 < model.nonlinear_mass(0.0) < 1e13
    assert model.nonlinear_mass(1.0) < model.nonlinear_mass(0.0) / 10
    # Clusters above 10¹⁴ M☉/h: of order 10⁻⁵ per (Mpc/h)³ today (Tinker et al. 2008).
    assert 1e-5 < model.n_above_mass(1e14) < 5e-5
    # Sheth–Tormen gives more massive clusters than Press–Schechter.
    assert model.n_above_mass(1e15, 0, "sheth-tormen") > 2 * model.n_above_mass(1e15, 0, "press-schechter")
    # The first atomic-cooling haloes reach one per (Mpc/h)³ around z ≈ 13.
    assert 10 < model.redshift_of_density(halos.ATOMIC_COOLING_MASS, 1.0) < 16
    assert model.n_above_mass(halos.ATOMIC_COOLING_MASS, 20) < 0.1


def test_clusters_weigh_sigma8(model):
    base = model.all_sky_counts(1e15)
    assert 200 < base < 3000                                   # hundreds on the whole sky out to z = 1
    higher = halos.HaloModel(PLANCK, sigma8=0.811 * 1.1).all_sky_counts(1e15)
    lower = halos.HaloModel(PLANCK, sigma8=0.811 * 0.9).all_sky_counts(1e15)
    assert higher / base > 2 and base / lower > 2
    # Rarer objects are more sensitive.
    light = halos.HaloModel(PLANCK, sigma8=0.811 * 1.1).all_sky_counts(1e13) / model.all_sky_counts(1e13)
    assert light < higher / base


def test_growth_is_cached_and_consistent(model):
    d = model.growth_many([0.0, 1.0, 3.0])
    assert d[0] == pytest.approx(1.0)
    assert model.growth(1.0) == pytest.approx(d[1])
    assert np.all(np.diff(d) < 0)
    assert model.nu(1.0) == pytest.approx(DELTA_C / (model.sigma0 * d[1]))
