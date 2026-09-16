"""The bundled real measurements (E1+): Pantheon+ supernovae and SPARC rotation curves."""

import numpy as np
import pytest

from cosmos.physics import datasets, supernovae as sn


def test_pantheon_release_is_complete():
    data = datasets.load_pantheon_plus()
    assert len(data) == 1701                      # light curves in the Pantheon+SH0ES release
    assert len(set(data.name)) == 1543            # distinct supernovae (some have two light curves)
    assert 0.001 < data.z.min() < 0.002 and 2.2 < data.z.max() < 2.3
    assert data.is_calibrator.sum() == 77         # supernovae in Cepheid host galaxies
    assert np.all(np.isfinite(data.mu)) and np.all(data.mu_err > 0)
    # The magnitudes use the SH0ES absolute calibration the app already assumes.
    nearby = (data.z > 0.02) & (data.z < 0.15)
    assert np.median(data.mu[nearby] - data.m_b_corr[nearby]) == pytest.approx(-sn.M_CEPHEID, abs=0.01)


def test_pantheon_sample_is_ready_for_the_fits():
    sample = sn.pantheon_sample()
    assert sample.real and "Pantheon+" in sample.label and "Scolnic" in sample.citation
    assert 1300 < len(sample.z) < 1500
    assert sample.z.min() >= 0.023                # the peculiar-velocity cut
    assert np.all(np.diff(sample.z) >= 0)         # sorted, as the plots expect
    assert np.all(sample.error > 0)
    assert sn.SAMPLES["pantheon"] is sn.pantheon_sample


def test_the_real_supernovae_give_the_published_cosmology():
    """The headline result of the last thirty years, fitted from the bundled data."""
    sample = sn.pantheon_sample()
    fit = sn.fit_grid(sample, n=61)
    assert fit.best_om == pytest.approx(0.33, abs=0.08)
    assert fit.best_ol == pytest.approx(0.65, abs=0.12)
    assert fit.best_ol > fit.best_om              # dark energy dominates
    assert fit.acceleration_sigma > 4             # acceleration, with diagonal errors only
    flat = sn.fit_flat(sample)
    assert flat.best_om == pytest.approx(0.33, abs=0.05)
    assert fit.hubble_constant(sn.M_CEPHEID) == pytest.approx(73.0, abs=1.5)


def test_sparc_catalogue():
    catalog = datasets.sparc_catalog()
    assert len(catalog) == 175
    ngc3198 = catalog["NGC3198"]
    assert ngc3198["distance_mpc"] == pytest.approx(13.8, abs=0.1)
    assert ngc3198["v_flat"] == pytest.approx(150.1, abs=0.5)
    assert ngc3198["quality"] == 1
    assert all(1 <= row["quality"] <= 3 for row in catalog.values())
    names = datasets.sparc_names()
    assert 100 < len(names) < 175 and "NGC3198" in names and names == sorted(names)


@pytest.mark.parametrize("name", ["NGC3198", "NGC2403", "DDO154", "UGC02885"])
def test_sparc_rotation_curves(name):
    galaxy = datasets.load_sparc_galaxy(name)
    assert galaxy.name == name and galaxy.quality <= 2
    assert len(galaxy.radius_kpc) >= 8
    assert np.all(np.diff(galaxy.radius_kpc) > 0)
    assert np.all(galaxy.error_km_s > 0)
    assert galaxy.velocity_km_s.max() == pytest.approx(galaxy.v_flat, rel=0.35)
    assert galaxy.sample().radius_kpc is galaxy.radius_kpc


def test_rotation_curves_are_flat_where_kepler_would_fall():
    """The measurement that made dark matter unavoidable."""
    galaxy = datasets.load_sparc_galaxy("NGC3198")
    outer = galaxy.radius_kpc > 0.5 * galaxy.radius_kpc.max()
    speeds = galaxy.velocity_km_s[outer]
    assert speeds.std() / speeds.mean() < 0.1                     # flat to within 10%
    keplerian = speeds[0] * np.sqrt(galaxy.radius_kpc[outer][0] / galaxy.radius_kpc[outer])
    assert speeds[-1] > 1.3 * keplerian[-1]                       # far above the Keplerian fall-off
    # Stars and gas alone cannot do it: the baryonic curve falls short in the outskirts.
    baryons = np.sqrt(galaxy.v_gas**2 + galaxy.v_disk**2 + galaxy.v_bulge**2)[outer]
    assert np.mean(baryons) < 0.8 * np.mean(speeds)


def test_data_files_carry_their_provenance():
    readme = (datasets.EXTERNAL_DIR / "README.md").read_text(encoding="utf-8")
    for source in ("Pantheon", "SPARC", "Scolnic", "Lelli", "Retrieved" if "Retrieved" in readme else "2026-09-16"):
        assert source in readme
    assert datasets.PANTHEON_FILE.exists() and datasets.SPARC_ARCHIVE.exists()
