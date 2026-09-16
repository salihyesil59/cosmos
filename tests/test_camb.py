"""The optional CAMB engine (E6) and how it compares with the teaching model."""

import numpy as np
import pytest

from cosmos.physics import cmb
from cosmos.physics import camb_backend as backend

camb = pytest.importorskip("camb", reason="CAMB is optional: pip install camb")

EXACT = backend.spectrum(cmb.PLANCK)
MODEL = cmb.spectrum(cmb.PLANCK)


def test_backend_reports_itself():
    assert backend.available() and backend.version()


def test_exact_spectrum_matches_planck():
    ell, d_ell = EXACT.ell, EXACT.d_ell
    assert ell[0] == 2 and ell[-1] >= 2000
    assert np.all(np.isfinite(d_ell)) and np.all(d_ell > 0)
    first = EXACT.peaks[0]
    assert first[0] == pytest.approx(220, abs=6)              # the measured first acoustic peak
    assert first[1] == pytest.approx(5750, rel=0.1)           # ... at about 5700 μK²
    assert EXACT.r_s == pytest.approx(144.4, abs=1.5)         # sound horizon [Mpc]
    assert EXACT.z_star == pytest.approx(1089.9, abs=5)
    assert 100 * EXACT.theta_star == pytest.approx(1.0411, abs=0.005)
    assert EXACT.r_star == pytest.approx(0.62, abs=0.05)      # baryon loading at decoupling


def test_teaching_model_agrees_with_the_boltzmann_code():
    """The approximation the app uses by default must stay honest."""
    for (exact_ell, exact_d), (model_ell, model_d) in zip(EXACT.peaks[:3], MODEL.peaks[:3]):
        assert model_ell == pytest.approx(exact_ell, rel=0.05)
        assert model_d == pytest.approx(exact_d, rel=0.2)
    for key in ("r_s", "d_m", "z_star"):
        assert getattr(MODEL, key) == pytest.approx(getattr(EXACT, key), rel=0.01)


def test_parameters_change_the_spectrum_as_expected():
    from dataclasses import replace

    more_baryons = backend.spectrum(replace(cmb.PLANCK, omega_b=0.030))
    open_universe = backend.spectrum(replace(cmb.PLANCK, omega_k=0.05))
    ratio = lambda s: s.peaks[0][1] / s.peaks[1][1]           # noqa: E731 - local helper
    assert ratio(more_baryons) > ratio(EXACT)                 # baryons raise the odd peaks
    assert open_universe.peaks[0][0] > EXACT.peaks[0][0]      # open space shifts the peaks right


def test_app_works_without_camb(monkeypatch):
    """Everything must degrade to the teaching model when CAMB is missing."""
    monkeypatch.setattr(backend, "version", lambda: None)
    assert backend.available() is False


def test_a_broken_spectrum_is_refused(monkeypatch):
    """A non-finite spectrum must raise, so the simulator can fall back to the teaching model."""
    import numpy as np

    real_get_results = camb.get_results

    def broken(pars, *args, **kwargs):
        results = real_get_results(pars, *args, **kwargs)

        class Wrapper:
            def get_cmb_power_spectra(self, *a, **k):
                spectra = results.get_cmb_power_spectra(*a, **k)
                spectra["total"] = np.full_like(spectra["total"], np.nan)
                return spectra

            def get_derived_params(self):
                return results.get_derived_params()

        return Wrapper()

    monkeypatch.setattr(camb, "get_results", broken)
    with pytest.raises(ValueError, match="not finite"):
        backend.spectrum(cmb.PLANCK)
