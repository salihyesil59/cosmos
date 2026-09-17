"""S20 distance ladder, L4.7 neutrino mass and the L7.3 additions to the inference engine."""

from dataclasses import replace

import numpy as np
import pytest

from cosmos.physics import inference as inf
from cosmos.physics import ladder, neutrinos
from cosmos.physics import supernovae as sn


# ------------------------------------------------------------------ ladder
def test_a_noiseless_ladder_recovers_the_truth():
    for truth in (67.4, 73.0):
        result = ladder.build(ladder.LadderSettings(true_h0=truth), noise=False)
        assert result.h0 == pytest.approx(truth, rel=2e-3)


def test_error_budget_adds_in_quadrature():
    result = ladder.build(ladder.LadderSettings())
    parts = np.array(list(result.budget_percent.values()))
    assert result.error_percent == pytest.approx(np.sqrt(np.sum(parts**2)))
    assert set(result.budget_percent) == set(ladder.RUNGS)
    assert result.dominant in ladder.RUNGS


def test_more_data_shrinks_only_its_own_rung():
    base = ladder.build(ladder.LadderSettings())
    more_flow = ladder.build(replace(base.settings, n_flow=base.settings.n_flow * 16))
    assert more_flow.budget_percent["flow"] == pytest.approx(base.budget_percent["flow"] / 4, rel=0.25)
    assert more_flow.budget_percent["parallax"] == pytest.approx(base.budget_percent["parallax"], rel=0.3)


def test_monte_carlo_spread_matches_the_quoted_error():
    settings = ladder.PRESETS["shoes"][1]
    runs = ladder.monte_carlo(settings, 250)
    quoted = ladder.build(settings).h0_error
    assert runs.mean() == pytest.approx(settings.true_h0, abs=0.6)
    assert runs.std(ddof=1) == pytest.approx(quoted, rel=0.25)


def test_systematics_shift_h0_in_the_expected_direction():
    assert ladder.systematic_shift(ladder.LadderSettings()) == pytest.approx(0.0, abs=1e-9)
    # Larger parallaxes → closer Cepheids → fainter calibration → closer hosts → larger H0.
    assert ladder.systematic_shift(ladder.LadderSettings(parallax_offset_uas=20)) > 1.0
    # Brighter-looking host Cepheids make the hosts look closer, which also raises H0.
    assert ladder.systematic_shift(ladder.LadderSettings(crowding_bias=0.05)) > 1.0
    assert ladder.systematic_shift(ladder.LadderSettings(crowding_bias=-0.05)) < -1.0


def test_tension_with_planck():
    result = ladder.build(ladder.PRESETS["shoes"][1])
    assert result.tension_with(ladder.PLANCK_H0) > 2
    assert abs(result.tension_with((result.h0, 0.5))) < 1e-9


# ----------------------------------------------------------------- neutrinos
def test_mass_orderings_and_their_floors():
    m1, m2, m3 = neutrinos.masses(0.0, "normal")
    assert m1 == 0
    assert m2**2 == pytest.approx(neutrinos.DM21_SQ)
    assert m3**2 == pytest.approx(neutrinos.DM3L_SQ_NORMAL)
    assert neutrinos.minimum_sum("normal") == pytest.approx(0.0587, abs=5e-4)
    assert neutrinos.minimum_sum("inverted") == pytest.approx(0.0992, abs=5e-4)
    heavy = neutrinos.masses(1.0, "inverted")
    assert max(heavy) - min(heavy) < 0.002                      # degenerate at large masses
    with pytest.raises(ValueError):
        neutrinos.masses(0.0, "sideways")
    floors = {b.name: b.value_ev for b in neutrinos.BOUNDS if b.kind == "floor"}
    assert floors["Oscillations, normal ordering"] == pytest.approx(neutrinos.minimum_sum("normal"), abs=5e-4)


def test_neutrino_density_and_suppression():
    assert neutrinos.omega_nu_h2(0.9314) == pytest.approx(0.01)
    f = neutrinos.neutrino_fraction(0.06, 0.31, 0.674)
    assert 0.004 < f < 0.005
    ratio = neutrinos.power_suppression(np.array([1e-5, 1.0]), 0.06)
    assert ratio[0] == pytest.approx(1.0, abs=2e-3)
    assert ratio[1] == pytest.approx(1 - 8 * f, abs=1e-3)
    assert np.all(neutrinos.power_suppression([0.1], 0.0) == 1)
    assert neutrinos.is_allowed(0.08) and not neutrinos.is_allowed(0.03) and not neutrinos.is_allowed(0.3)
    assert neutrinos.nonrelativistic_redshift(0.05) == pytest.approx(93.5)


# ----------------------------------------------------------------- inference
@pytest.fixture(scope="module")
def sample():
    return sn.pantheon_sample()


def test_a_second_probe_breaks_the_degeneracy(sample):
    alone = inf.run_chain(sample, steps=3000, start=(0.8, 0.1))
    combined = inf.run_chain(sample, steps=3000, step_size=0.025, start=(0.8, 0.1), probe="cmb")
    assert combined.probe == "cmb"
    assert combined.std()[1] < alone.std()[1] / 3
    assert abs(1 - combined.mean().sum()) < 0.05
    assert alone.correlation() > 0.7                            # the supernova degeneracy
    bao = inf.run_chain(sample, steps=3000, step_size=0.025, start=(0.8, 0.1), probe="bao")
    assert bao.mean()[0] == pytest.approx(0.30, abs=0.03)


def test_probes_are_gaussian_priors():
    assert inf.PROBES["none"].log_prior(0.3, 0.7) == 0.0
    assert inf.PROBES["cmb"].log_prior(0.3, 0.7) == pytest.approx(0.0)
    assert inf.PROBES["cmb"].log_prior(0.3, 0.72) == pytest.approx(-0.5)      # one σ off
    assert inf.PROBES["bao"].log_prior(0.34, 0.0) == pytest.approx(-2.0)      # two σ off


def test_derived_parameters_include_the_correlation(sample):
    chain = inf.run_chain(sample, steps=4000, start=(0.8, 0.1))
    derived = inf.derived_parameters(chain)
    kept = chain.kept
    assert derived["q0"][0] == pytest.approx(np.mean(kept[:, 0] / 2 - kept[:, 1]))
    assert derived["q0"][1] < inf.naive_q0_error(chain)       # positive correlation partly cancels
    assert derived["accelerating"][0] > 0.95
    assert derived["omega_k"][0] == pytest.approx(1 - chain.mean().sum())


def test_smoothed_posterior_map_keeps_its_levels(sample):
    chain = inf.run_chain(sample, steps=2000, start=(0.8, 0.1))
    posterior = inf.posterior_map(chain, bins=40, smooth=1.2)
    assert posterior.density.shape == (40, 40)
    assert posterior.levels[0] > posterior.levels[1] > 0
