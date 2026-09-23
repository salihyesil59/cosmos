import numpy as np
import pytest

from cosmos.physics import datasets, hubble, rotation, spectra


def test_relativistic_doppler_roundtrip():
    for v in [100.0, 30_000.0, 200_000.0]:
        z = spectra.relativistic_doppler_z(v)
        assert spectra.velocity_from_relativistic_z(z) == pytest.approx(v, rel=1e-9)


def test_classical_doppler_small_velocity_limit():
    v = 300.0
    assert spectra.classical_doppler_z(v) == pytest.approx(spectra.relativistic_doppler_z(v), rel=1e-3)


def test_wavelength_colours():
    assert spectra.wavelength_to_rgb(300) == (0, 0, 0)
    r, g, b = spectra.wavelength_to_rgb(650)
    assert r > 200 and g < 50 and b == 0
    assert spectra.band_name(550) == "visible light"
    assert spectra.band_name(2000) == "infrared"


def test_hubble_fit_recovers_slope():
    d = np.linspace(10, 300, 50)
    fit = hubble.fit_through_origin(d, 70 * d)
    assert fit.H0 == pytest.approx(70)
    assert fit.hubble_time_gyr == pytest.approx(13.97, abs=0.01)


def test_hubble_1929_fit_is_hubbles_famous_slope():
    data = datasets.load_hubble_1929()
    assert len(data.names) == 24
    fit = hubble.fit_through_origin(data.distance_mpc, data.velocity_km_s)
    assert 380 < fit.H0 < 520


def test_simulated_sample_is_labelled_and_reasonable():
    data = datasets.simulated_modern_sample()
    assert data.simulated
    fit = hubble.fit_through_origin(data.distance_mpc, data.velocity_km_s)
    assert fit.H0 == pytest.approx(70, abs=5)


def test_keplerian_and_halo_behaviour():
    r = np.array([5.0, 20.0, 80.0])
    kep = rotation.keplerian_velocity(r, 1e11)
    assert kep[0] / kep[1] == pytest.approx(2.0)
    # A Milky-Way-like NFW halo gives ~150-200 km/s at tens of kpc.
    halo = rotation.nfw_velocity(20.0, 1e12, 10)
    assert 120 < float(halo) < 220
    # A Freeman disk peaks at 2.15 scale lengths.
    rr = np.linspace(0.1, 20, 2000)
    v = rotation.disk_velocity(rr, 5e10, 3.0)
    assert rr[np.argmax(v)] == pytest.approx(2.15 * 3.0, rel=0.01)


def test_enclosed_mass_inverts_keplerian():
    m = rotation.enclosed_mass(10.0, rotation.keplerian_velocity(10.0, 3e10))
    assert float(m) == pytest.approx(3e10, rel=1e-9)
