"""The bundled real sky: the WMAP map (S24) and the SDSS slice (E15)."""

import math
import sys
from pathlib import Path

import numpy as np
import pytest

from cosmos.physics import mock, sdss, skymap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

pytestmark = pytest.mark.skipif(not (skymap.available() and sdss.available()),
                                reason="run tools/fetch_sky_data.py to download the real data")


# ------------------------------------------------------------------- HEALPix
def test_the_two_healpix_orderings_describe_the_same_sphere():
    """The resampling is only trustworthy if the pixel geometry is right."""
    from fetch_sky_data import healpix_nested_angles, healpix_ring_angles

    for nside in (1, 2, 4, 8, 16):
        ring = np.array(sorted(zip(*(np.round(a, 9) for a in healpix_ring_angles(nside)))))
        nested = np.array(sorted(zip(*(np.round(a, 9) for a in healpix_nested_angles(nside)))))
        assert np.allclose(ring, nested), nside


def test_healpix_pixels_tile_the_sphere_evenly():
    from fetch_sky_data import healpix_ring_angles

    theta, phi = healpix_ring_angles(32)
    assert len(theta) == 12 * 32 * 32
    x = np.sin(theta) * np.cos(phi)
    y = np.sin(theta) * np.sin(phi)
    z = np.cos(theta)
    # Equal-area pixels spread evenly: the mean unit vector must vanish.
    for axis in (x, y, z):
        assert abs(axis.mean()) < 1e-12
    assert 0 < theta.min() and theta.max() < math.pi


# ------------------------------------------------------------ the WMAP map
def test_the_map_looks_like_the_published_one():
    sky = skymap.load()
    assert sky.shape == (512, 1024)
    assert sky.temperature.dtype == float
    assert set(np.unique(sky.mask)) <= {0.0, 1.0}

    stats = skymap.weighted_stats(sky, sky.temperature)
    # WMAP publishes about 70 µK rms for the ILC map; resampling loses a little.
    assert 60 < stats["rms"] < 75
    assert abs(stats["mean"]) < 15                      # the monopole is already out
    assert -450 < stats["min"] < -150 and 150 < stats["max"] < 450
    # The KQ85 mask keeps about three quarters of the sky.
    assert 0.70 < stats["sky_fraction"] < 0.80


def test_the_mask_removes_the_galaxy():
    sky = skymap.load()
    masked = skymap.weighted_stats(sky, sky.temperature, use_mask=True)
    whole = skymap.weighted_stats(sky, sky.temperature, use_mask=False)
    assert whole["sky_fraction"] == pytest.approx(1.0)
    assert whole["rms"] > masked["rms"], "the Galaxy adds power"
    assert abs(whole["min"]) > abs(masked["min"])
    # What the mask cuts is the galactic plane, so it should mostly remove low latitudes.
    kept = sky.mask.mean(axis=1)
    equator = sky.shape[0] // 2
    assert kept[equator] < 0.4 and kept[equator - 120] > 0.8


def test_the_grid_is_weighted_by_solid_angle():
    """A cell at the pole covers far less sky than one at the equator."""
    sky = skymap.load()
    weights = sky.weights
    assert weights.shape == sky.shape
    assert weights[0].mean() < 0.02 and weights[sky.shape[0] // 2].mean() > 0.99
    # An unweighted rms would over-count the poles; the weighted one must differ.
    unweighted = float(np.std(sky.temperature))
    weighted = skymap.weighted_stats(sky, sky.temperature, use_mask=False)["rms"]
    assert weighted != pytest.approx(unweighted, rel=1e-6)


def test_smoothing_throws_structure_away():
    sky = skymap.load()
    scales, rms = skymap.rms_against_smoothing(sky)
    assert scales[0] == 0
    assert np.all(np.diff(rms) <= 1e-9), "blurring can never add structure"
    assert rms[-1] < 0.6 * rms[0], "most of the power is on small scales"
    # A high-pass filter keeps the small scales and loses the large ones.
    fine = skymap.high_pass(sky, sky.temperature, 5.0)
    blurred = skymap.smooth(sky, sky.temperature, 5.0)
    assert np.allclose(fine + blurred, sky.temperature, atol=1e-9)


def test_the_correlation_function_measures_the_acoustic_scale():
    sky = skymap.load()
    theta, curve = skymap.correlation(sky, sky.temperature, samples=2500)
    assert np.isfinite(curve).all()
    # C(0) must match the variance: about (67 µK)².
    assert 3000 < curve[0] < 7000
    assert curve[0] > curve[-1], "distant points are less alike"
    half = skymap.correlation_half_width(theta, curve)
    # The spots are about a degree across; the map's own 1° beam widens them a little.
    assert 0.8 < half < 3.0


def test_removing_the_dipole_barely_changes_a_cleaned_map():
    sky = skymap.load()
    cleaned, coefficients = skymap.remove_monopole_and_dipole(sky, sky.temperature)
    assert coefficients.shape == (4,)
    # WMAP already took them out, so only a few µK of residual should be found.
    assert np.all(np.abs(coefficients) < 50)
    before = skymap.weighted_stats(sky, sky.temperature)["rms"]
    after = skymap.weighted_stats(sky, cleaned)["rms"]
    assert after <= before and after > 0.9 * before


def test_the_hottest_and_coldest_spots_are_inside_the_mask():
    sky = skymap.load()
    hot, cold = skymap.hottest_and_coldest(sky, sky.temperature)
    for latitude, longitude, value in (hot, cold):
        assert -90 <= latitude <= 90 and 0 <= longitude <= 360
        row = int((latitude + 90) / 180 * sky.shape[0])
        column = int(longitude / 360 * sky.shape[1]) % sky.shape[1]
        assert sky.mask[min(row, sky.shape[0] - 1), column] > 0
    assert hot[2] > 0 > cold[2]


# ------------------------------------------------------------ the SDSS slice
def test_the_slice_is_the_equatorial_strip():
    data = sdss.load()
    assert len(data) > 20_000
    assert sdss.RA_RANGE[0] <= data.ra.min() and data.ra.max() <= sdss.RA_RANGE[1]
    assert sdss.DEC_RANGE[0] <= data.dec.min() and data.dec.max() <= sdss.DEC_RANGE[1]
    assert sdss.Z_RANGE[0] <= data.z.min() and data.z.max() <= sdss.Z_RANGE[1]
    # SkyServer writes -9999 for a missing magnitude; those must not become galaxies
    # that are absurdly bright.
    magnitudes = data.magnitude[np.isfinite(data.magnitude)]
    assert magnitudes.min() > 0 and magnitudes.max() < 35


def test_redshifts_become_distances():
    z = np.array([0.0, 0.05, 0.1, 0.15])
    distance = sdss.comoving_distance(z)
    assert distance[0] == pytest.approx(0.0, abs=1.0)
    assert np.all(np.diff(distance) > 0)
    # At low redshift, cz/H0 in Mpc/h is 3000 z to within a few percent.
    assert distance[1] == pytest.approx(3000 * 0.05, rel=0.05)


def test_the_slice_becomes_a_catalogue_the_app_can_measure():
    cat = sdss.catalogue()
    assert len(cat) == len(sdss.load())
    assert np.allclose(np.linalg.norm(cat.direction, axis=1), 1.0)
    assert np.allclose(cat.r_true, cat.r_obs), "the true distance of a real galaxy is unknown"
    assert np.all(cat.velocity == 0)

    settings = cat.settings
    assert settings.wedge_deg == pytest.approx(sdss.RA_RANGE[1] - sdss.RA_RANGE[0])
    assert settings.thickness_deg == pytest.approx(sdss.DEC_RANGE[1] - sdss.DEC_RANGE[0])
    assert not settings.velocities and settings.flux_limit == 0
    # The wedge is centred, so the angles straddle zero.
    angles = np.degrees(cat.angle)
    assert angles.min() == pytest.approx(-settings.wedge_deg / 2, abs=1.0)
    assert angles.max() == pytest.approx(settings.wedge_deg / 2, abs=1.0)


def test_real_galaxies_cluster():
    """The whole point of bundling it: the sky's own answer, measured the same way."""
    cat = sdss.catalogue()
    separation, xi = mock.correlation_function(cat, observed=True)
    assert np.isfinite(xi).all()
    assert xi[0] > xi[-1] > -0.2
    # ξ(s) around 5 Mpc/h is of order 1 — the classic galaxy clustering amplitude.
    near = xi[np.argmin(np.abs(separation - 5.0))]
    assert 0.5 < near < 4.0
    # It falls steeply, which is what makes it a correlation function and not noise.
    far = xi[np.argmin(np.abs(separation - 20.0))]
    assert far < 0.4 * near


def test_the_summary_is_quotable():
    report = sdss.summary()
    assert report["galaxies"] > 20_000
    assert 0.02 < report["median_z"] < 0.12
    assert 350 < report["depth"] < 500                 # Mpc/h at z = 0.15
    assert report["volume"] > 1e6
    assert 1e-3 < report["density"] < 5e-2
    assert 10 < report["brightest"] < report["faintest"] < 35
