"""Tests for structure formation, the CMB teaching model, lensing and the N-body toy."""

import math
from dataclasses import replace

import numpy as np
import pytest
from scipy import integrate

from cosmos.physics import cmb, lensing, structure
from cosmos.physics.cosmology import Cosmology
from cosmos.physics.nbody import NBodyConfig, NBodySimulation
from cosmos.physics.presets import PRESETS

PLANCK = PRESETS["planck18"].cosmology


# ----------------------------------------------------------------- growth
def test_growth_is_scale_factor_in_einstein_de_sitter():
    eds = PRESETS["eds"].cosmology
    np.testing.assert_allclose(structure.growth_factor(eds, np.array([0.1, 0.5, 1.0])), [0.1, 0.5, 1.0], rtol=1e-6)


def test_growth_matches_heath_integral_for_lcdm():
    c = Cosmology(H0=70, Om0=0.3, Ode0=0.7, Tcmb0=0)

    def heath(a):
        e = lambda x: math.sqrt(c.E2_of_a(x))  # noqa: E731
        return 2.5 * c.Om0 * e(a) * integrate.quad(lambda x: 1 / (x * e(x)) ** 3, 0, a)[0]

    assert structure.growth_factor(c, 1.0, normalize=False) == pytest.approx(heath(1.0), rel=1e-5)
    assert structure.growth_factor(c, 0.5) == pytest.approx(heath(0.5) / heath(1.0), rel=1e-5)


def test_dark_energy_suppresses_growth():
    assert structure.growth_factor(PLANCK, 1.0, normalize=False) < 0.8
    assert structure.growth_rate(PLANCK, 1.0) == pytest.approx(0.52, abs=0.02)


# ---------------------------------------------------------- acoustic scale
def test_planck_acoustic_scale():
    acoustic = structure.acoustic_scale(PLANCK)
    assert acoustic["z_star"] == pytest.approx(1090, abs=5)
    assert acoustic["r_s"] == pytest.approx(144.4, rel=0.01)
    assert 100 * acoustic["theta_star"] == pytest.approx(1.0411, rel=0.005)
    assert acoustic["r_drag"] == pytest.approx(147.1, rel=0.01)


# --------------------------------------------------------- power spectrum
def test_power_spectrum_normalisation_and_turnover():
    pk = structure.LinearPowerSpectrum(PLANCK)
    assert pk.sigma_r(8.0) == pytest.approx(0.811, rel=1e-3)
    k = np.logspace(-3, 0, 600)
    k_peak = k[np.argmax(pk(k))]
    assert 0.01 < k_peak < 0.03  # turnover near the equality scale
    # Growth: power at z = 1 is suppressed by D(z=1)^2.
    d1 = structure.growth_factor(PLANCK, 0.5)
    assert pk(0.1, z=1.0) == pytest.approx(pk(0.1) * d1 * d1, rel=1e-6)


def test_bao_wiggles_and_correlation_peak():
    k = np.logspace(-3, 0, 400)
    ratio = structure.transfer_eisenstein_hu(PLANCK, k) ** 2 / structure.transfer_no_wiggle(PLANCK, k) ** 2
    band = (k > 0.05) & (k < 0.3)
    assert 0.02 < ratio[band].max() - 1 < 0.15
    pk = structure.LinearPowerSpectrum(PLANCK)
    r = np.linspace(85, 130, 91)
    xi = pk.correlation_function(r)
    r_peak = r[np.argmax(r * r * xi)]
    assert r_peak == pytest.approx(structure.drag_sound_horizon(PLANCK) * PLANCK.h, rel=0.05)


def test_press_schechter_more_massive_halos_are_rarer_and_form_later():
    pk = structure.LinearPowerSpectrum(PLANCK)
    m = np.logspace(11, 15, 9)
    today = pk.press_schechter(m)
    assert np.all(np.diff(today) < 0)
    early = pk.press_schechter(m, z=3.0)
    assert early[-1] < today[-1] * 1e-2


def test_jeans_mass_after_recombination():
    rho_b = PLANCK.critical_density0 * PLANCK.Ob0 * 1091**3
    cs = math.sqrt(5 / 3 * 1.380649e-23 * 3000 / (1.22 * 1.67262e-27)) / 1e3
    assert 1e4 < structure.jeans_mass(cs, rho_b) < 1e7


# -------------------------------------------------------------------- CMB
def test_cmb_model_matches_planck_landmarks():
    assert cmb.calibration_error() < 0.2
    spec = cmb.spectrum()
    first, second, third = (spec.peaks[i][0] for i in range(3))
    assert first == pytest.approx(220, abs=15)
    assert second == pytest.approx(537, abs=30)
    assert third == pytest.approx(813, abs=30)


def test_cmb_trends():
    base = cmb.spectrum()
    ratio = base.peaks[0][1] / base.peaks[1][1]
    more_baryons = cmb.spectrum(replace(cmb.PLANCK, omega_b=0.03))
    assert more_baryons.peaks[0][1] / more_baryons.peaks[1][1] > ratio
    open_space = cmb.spectrum(replace(cmb.PLANCK, omega_k=0.05))
    closed_space = cmb.spectrum(replace(cmb.PLANCK, omega_k=-0.05))
    assert closed_space.peaks[0][0] < base.peaks[0][0] < open_space.peaks[0][0]
    tilted = cmb.spectrum(replace(cmb.PLANCK, n_s=1.05))
    assert tilted.d_ell[1998] / base.d_ell[1998] > tilted.d_ell[8] / base.d_ell[8]


def test_cmb_sky_patch_has_expected_rms():
    spec = cmb.spectrum()
    patch = cmb.sky_patch(spec, size_deg=20, n=256)
    assert 50 < patch.std() < 200  # tens of microkelvin, as observed


# ---------------------------------------------------------------- lensing
def test_einstein_radius_of_a_galaxy_and_a_cluster():
    theta_galaxy = lensing.einstein_radius_sis(PLANCK, 250, 0.3, 2.0)
    assert 1.0 < theta_galaxy < 3.0
    theta_cluster = lensing.einstein_radius_sis(PLANCK, 1200, 0.3, 2.0)
    assert 20 < theta_cluster < 60
    theta_e = lensing.einstein_radius_point(PLANCK, 1e12, 0.5, 2.0)
    mass = lensing.mass_inside_einstein_radius(PLANCK, theta_e, 0.5, 2.0)
    assert mass == pytest.approx(1e12, rel=1e-9)


def test_point_lens_images_satisfy_lens_equation():
    theta_e, beta = 1.0, 0.4
    for theta in lensing.point_lens_image_positions(beta, theta_e):
        ax, _ = lensing.deflection(np.array([theta]), np.array([0.0]), [("point", 0.0, 0.0, theta_e)])
        assert theta - ax[0] == pytest.approx(beta)
    assert lensing.point_lens_magnification(1e-3, 1.0) > 100
    assert lensing.point_lens_magnification(10.0, 1.0) == pytest.approx(1.0, abs=0.001)


# ----------------------------------------------------------------- N-body
def test_nbody_large_scale_modes_grow_linearly():
    sim = NBodySimulation(NBodyConfig(amplitude=0.02))
    g = sim.config.grid
    k = np.fft.fftfreq(g) * g
    kx, ky = np.meshgrid(k, k, indexing="ij")
    sel = (np.hypot(kx, ky) > 0) & (np.hypot(kx, ky) <= 6)
    start = np.abs(np.fft.fft2(sim.density())[sel]).sum()
    d0 = sim.growth
    sim.run_to(0.5)
    end = np.abs(np.fft.fft2(sim.density())[sel]).sum()
    assert end / start == pytest.approx(0.5 / d0, rel=0.05)


def test_nbody_conserves_mass_and_forms_structure():
    sim = NBodySimulation(NBodyConfig(particles_per_side=64, grid=64))
    sim.run_to(2.5)
    rho = sim.density()
    assert rho.mean() == pytest.approx(0.0, abs=1e-9)
    assert sim.collapsed_fraction() > 0.1
    assert np.all((sim.density_image() >= 0) & (sim.density_image() <= 1))


def test_warm_dark_matter_removes_small_scale_structure():
    cold = NBodySimulation(NBodyConfig(particles_per_side=64, grid=64))
    warm = NBodySimulation(NBodyConfig(particles_per_side=64, grid=64, cutoff=6))
    assert warm.initial_delta.std() < cold.initial_delta.std()
    cold.run_to(1.0)
    warm.run_to(1.0)
    assert warm.collapsed_fraction() < cold.collapsed_fraction()


def test_polarisation_peaks_interleave_with_the_temperature():
    """L5.7: temperature comes from compression, polarisation from velocity."""
    tt = cmb.spectrum()
    pol = cmb.polarisation()
    ee_peaks = [l for l, _v in cmb.find_peaks(pol.ell, pol.ee, limit=4)]
    tt_peaks = [l for l, _v in tt.peaks[:5]]
    # Every E-mode peak sits between two temperature peaks.
    for ell in ee_peaks[:3]:
        below = [t for t in tt_peaks if t < ell]
        above = [t for t in tt_peaks if t > ell]
        assert below and above, ell
        assert max(below) + 60 < ell < min(above) - 60, (ell, tt_peaks)
    # Measured EE peaks sit near ell = 400, 690, 990.
    for measured, published in zip(ee_peaks, (400, 690, 990, 1290)):
        assert abs(measured - published) < 0.1 * published


def test_polarisation_is_suppressed_on_large_scales():
    pol = cmb.polarisation()
    assert pol.at(pol.ee, 1000) > 50 * pol.at(pol.ee, 100)
    assert pol.at(pol.ee, 100) > pol.at(pol.ee, 30)
    assert 30 < float(pol.ee.max()) < 60           # Planck measures about 45 uK^2


def test_the_reionisation_bump_scales_as_tau_squared():
    low = cmb.polarisation(cmb.CMBParameters(tau=0.03))
    high = cmb.polarisation(cmb.CMBParameters(tau=0.09))
    assert high.at(high.ee, 5) / low.at(low.ee, 5) == pytest.approx((0.09 / 0.03) ** 2, rel=0.1)
    # And the acoustic peaks are damped by exp(-2 tau) at the same time.
    assert high.ee.max() / low.ee.max() == pytest.approx(math.exp(-2 * (0.09 - 0.03)), rel=0.05)


def test_te_oscillates_and_changes_sign():
    pol = cmb.polarisation()
    assert pol.te.min() < -100 and pol.te.max() > 100
    crossings = np.sum(np.diff(np.sign(pol.te[50:1500])) != 0)
    assert crossings > np.sum(np.diff(np.sign(pol.ee[50:1500] - pol.ee[50:1500].mean())) != 0)


def test_b_modes_have_the_right_budget():
    """L5.7: lensing, dust and inflation, and which wins at ell = 80."""
    pol = cmb.polarisation(r=0.1)
    assert pol.at(pol.bb_lensing, 1000) == pytest.approx(cmb.POLARISATION["lensing_bb"], rel=0.02)
    assert pol.at(pol.bb_tensor, 80) == pytest.approx(0.1 * cmb.POLARISATION["tensor_bb"], rel=0.02)
    # Lensing peaks at small scales, tensors at ell = 80 and then die inside the horizon.
    assert pol.at(pol.bb_lensing, 1000) > 5 * pol.at(pol.bb_lensing, 80)
    assert pol.at(pol.bb_tensor, 80) > 3 * pol.at(pol.bb_tensor, 500)
    assert pol.bb_total.shape == pol.ell.shape

    # BICEP2 announced r = 0.2; at today's limit the signal is no larger than the lensing.
    limit = cmb.polarisation(r=cmb.BICEP_LIMIT_R)
    assert limit.at(limit.bb_tensor, 80) < 1.5 * limit.at(limit.bb_lensing, 80)
    assert cmb.polarisation(r=0.2).at(cmb.polarisation(r=0.2).bb_tensor, 80) > 4 * limit.at(
        limit.bb_lensing, 80)


def test_delensing_and_a_clean_patch_uncover_a_small_signal():
    dirty = cmb.polarisation(r=0.005, a_lens=1.0, dust=0.05)
    assert dirty.at(dirty.bb_tensor, 80) < dirty.at(dirty.bb_lensing, 80) + dirty.at(dirty.bb_dust, 80)
    clean = cmb.polarisation(r=0.005, a_lens=0.1, dust=0.0)
    assert clean.at(clean.bb_tensor, 80) > clean.at(clean.bb_lensing, 80) + clean.at(clean.bb_dust, 80)
    assert clean.at(clean.bb_lensing, 80) == pytest.approx(0.1 * dirty.at(dirty.bb_lensing, 80), rel=1e-9)


def test_the_temperature_spectrum_is_untouched_by_the_refactor():
    """The components helper must reproduce the calibrated TT model exactly."""
    ell = np.arange(2, 400, dtype=float)
    c = cmb._components(cmb.PLANCK, ell)
    power = cmb._smooth(c["monopole"] ** 2 + cmb.CALIBRATION["doppler"] * c["dipole"] ** 2, c["ell_a"])
    shape = c["transition"] * power * c["damping"] + (1 - c["transition"]) * cmb.CALIBRATION["plateau"]
    expected = shape * c["tilt"] * c["reion"] * cmb.PLANCK.a_s / 2.1e-9
    raw, _acoustic = cmb._raw_spectrum(cmb.PLANCK, ell)
    assert np.allclose(raw, expected)
    assert cmb.calibration_error() < 0.2
