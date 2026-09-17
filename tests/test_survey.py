"""S21 Survey Designer: the effective-volume forecast behind L7.4 and L7.6."""

import math
from dataclasses import replace

import numpy as np
import pytest

from cosmos.physics import survey


def test_boss_calibration():
    result = survey.forecast(survey.PRESETS_SURVEY["boss"][1])
    assert result.statistical_percent == pytest.approx(1.0, rel=1e-6)
    assert not result.diluted


def test_error_scales_with_effective_volume():
    base = survey.forecast(survey.PRESETS_SURVEY["desi_lrg"][1])
    quadrupled = survey.forecast(replace(base.settings, area_deg2=base.settings.area_deg2 / 4))
    assert quadrupled.volume == pytest.approx(base.volume / 4, rel=1e-6)
    assert quadrupled.statistical_percent == pytest.approx(2 * base.statistical_percent, rel=1e-6)
    for b in base.bins:
        assert b.effective_volume == pytest.approx(b.volume * (b.n_p / (1 + b.n_p)) ** 2)


def test_regimes():
    lrg = survey.forecast(survey.PRESETS_SURVEY["desi_lrg"][1])
    qso = survey.forecast(survey.PRESETS_SURVEY["desi_qso"][1])
    assert lrg.n_p > 3 and qso.n_p < 1
    # Sample-variance limited: doubling the density barely helps. Shot-noise limited: it helps a lot.
    denser_lrg = survey.forecast(replace(lrg.settings, density=2 * lrg.settings.density))
    denser_qso = survey.forecast(replace(qso.settings, density=2 * qso.settings.density))
    assert denser_lrg.statistical_percent > 0.9 * lrg.statistical_percent
    assert denser_qso.statistical_percent < 0.6 * qso.statistical_percent


def test_telescope_time_dilutes_the_density():
    settings = replace(survey.PRESETS_SURVEY["desi_lrg"][1], years=0.2)
    result = survey.forecast(settings)
    assert result.diluted
    assert result.density_used == pytest.approx(settings.density * result.spectra_available / result.targets_needed)
    assert result.galaxies == pytest.approx(result.spectra_available)


def test_systematic_floor_adds_in_quadrature():
    settings = replace(survey.PRESETS_SURVEY["desi_lrg"][1], systematic_floor=0.3)
    result = survey.forecast(settings)
    assert result.total_percent == pytest.approx(math.hypot(result.statistical_percent, 0.3))


def test_best_area_is_where_np_is_one():
    settings = survey.PRESETS_SURVEY["pilot"][1]
    areas, errors = survey.area_tradeoff(settings, np.geomspace(100, 41_000, 120))
    best = float(areas[int(np.argmin(errors))])
    result = survey.forecast(settings)
    volume = survey.forecast(replace(settings, area_deg2=best, density=1e-9)).volume * 1e9
    n_p = result.galaxies / volume * survey.TRACERS[settings.tracer].bias0 ** 2 * survey.P_BAO
    assert n_p == pytest.approx(1.0, rel=0.1)


def test_distances_follow_the_model():
    result = survey.forecast(survey.PRESETS_SURVEY["desi_lrg"][1])
    values = [b.dv_over_rd for b in result.bins]
    assert all(later > earlier for earlier, later in zip(values, values[1:]))
    assert result.bins[0].dv_over_rd == pytest.approx(1705 / 147.09, rel=0.03)      # D_V(0.45) ≈ 1.7 Gpc
    with pytest.raises(ValueError):
        survey.forecast(replace(result.settings, z_min=1.0, z_max=0.5))
