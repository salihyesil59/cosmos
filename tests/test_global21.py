"""The 21-cm global signal (S28) and the galaxy–halo connection (L5.8)."""

import math

import numpy as np
import pytest

from cosmos.physics import constants as const
from cosmos.physics import galaxies
from cosmos.physics import global21 as g21


@pytest.fixture(scope="module")
def standard():
    return g21.signal()


def test_frequency_and_redshift():
    assert g21.frequency(0) == pytest.approx(1420.4, rel=1e-4)
    assert g21.redshift(78.0) == pytest.approx(17.2, abs=0.05)


def test_the_gas_leaves_the_cmb_behind(standard):
    z, tk, tg = standard.z, standard.t_gas, standard.t_gamma
    i300 = int(np.argmin(abs(z - 300)))
    assert tk[i300] / tg[i300] > 0.85                  # still nearly coupled at z = 300
    i25 = int(np.argmin(abs(z - 25)))
    # By z = 25 it has cooled almost adiabatically since z ≈ 150: T ∝ (1+z)².
    assert tk[i25] == pytest.approx(const.T_CMB * 151 * (26 / 151) ** 2, rel=0.35)
    assert tk[i25] < tg[i25] / 3


def test_two_troughs_and_a_hump(standard):
    depth, z = standard.dark_ages
    assert depth == pytest.approx(-40, abs=10) and 60 < z < 120      # ~16 MHz, physics alone
    depth, z = standard.cosmic_dawn
    assert -250 < depth < -100 and 14 < z < 25
    assert standard.emission_peak > 5
    assert math.isfinite(standard.heating_crossing)
    # No hydrogen after reionisation, so no signal.
    assert abs(standard.delta_tb[-1]) < 1


def test_astrophysics_moves_the_signal(standard):
    cold = g21.signal(g21.Astrophysics(heating=0.0))
    assert cold.emission_peak == 0 and cold.cosmic_dawn[0] < standard.cosmic_dawn[0]
    late = g21.signal(g21.Astrophysics(z_alpha=12.0, z_heat=9.0))
    assert g21.frequency(late.cosmic_dawn[1]) > g21.frequency(standard.cosmic_dawn[1])
    radio = g21.signal(g21.Astrophysics(radio_excess=1.0))
    assert radio.cosmic_dawn[0] < -400                                 # EDGES-like depth
    # The dark ages are untouched by the stars.
    assert late.dark_ages[0] == pytest.approx(standard.dark_ages[0], rel=1e-3)


def test_edges_profile():
    assert g21.edges_profile(78.3) == pytest.approx(-530, rel=1e-3)
    assert abs(g21.edges_profile(55.0)) < 20


def test_stellar_to_halo_mass():
    peak = galaxies.peak_halo_mass()
    assert 3e11 < peak < 1.5e12
    assert galaxies.stellar_fraction(peak) == pytest.approx(0.035, rel=0.15)
    assert galaxies.star_formation_efficiency(peak) == pytest.approx(0.22, abs=0.05)
    assert galaxies.stellar_fraction(1e10) < 0.002 and galaxies.stellar_fraction(1e15) < 0.002
    # The Milky Way: a 1.3e12 halo holds a few 10¹⁰ M☉ of stars and a disc a few kpc across.
    assert 2e10 < galaxies.stellar_mass(1.3e12) < 8e10
    r_vir = galaxies.virial_radius_kpc(1.3e12)
    assert 200 < r_vir < 260
    assert 3 < galaxies.disk_scale_length(r_vir) < 8
    assert galaxies.virial_temperature(1e12) == pytest.approx(1.7e6, rel=0.1)
