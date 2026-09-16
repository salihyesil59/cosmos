"""Likelihoods, χ² and MCMC (L7.2, S19)."""

import math

import numpy as np
import pytest

from cosmos.physics import inference as inf
from cosmos.physics import supernovae as sn

SAMPLE = sn.pantheon_sample()


def test_chi2_prefers_the_measured_universe():
    best = inf.chi2(0.33, 0.67, SAMPLE)
    assert best == pytest.approx(600, abs=60)
    assert inf.chi2(1.0, 0.0, SAMPLE) > best + 300        # matter only is badly beaten
    assert inf.chi2(0.0, 0.0, SAMPLE) > best              # ... and so is an empty universe
    assert math.isinf(inf.chi2(-5.0, -5.0, SAMPLE))       # a model with no Big Bang scores nothing
    assert inf.log_likelihood(0.33, 0.67, SAMPLE) == pytest.approx(-0.5 * best)


def test_a_chain_finds_the_same_answer_as_the_grid():
    chain = inf.run_chain(SAMPLE, steps=3000, step_size=0.08, start=(0.8, 0.1), seed=3)
    grid = sn.fit_grid(SAMPLE, n=41)
    mean, std = chain.mean(), chain.std()
    assert mean[0] == pytest.approx(grid.best_om, abs=0.08)
    assert mean[1] == pytest.approx(grid.best_ol, abs=0.12)
    assert 0.1 < chain.acceptance < 0.6
    assert chain.correlation() > 0.6                       # the classic Ωm–ΩΛ degeneracy
    assert 0.02 < std[0] < 0.15
    low, high = chain.interval(0)
    assert low < mean[0] < high
    assert chain.burn_in == 600 and len(chain.kept) == 2400


def test_flat_assumption_tightens_the_answer():
    free = inf.run_chain(SAMPLE, steps=3000, seed=4)
    flat = inf.run_chain(SAMPLE, steps=3000, seed=4, flat=True)
    assert np.allclose(flat.kept[:, 0] + flat.kept[:, 1], 1.0)
    assert flat.std()[0] < free.std()[0] / 2
    assert flat.mean()[0] == pytest.approx(0.334, abs=0.04)   # the published Pantheon+ value


def test_step_size_shows_up_in_the_acceptance_rate():
    timid = inf.run_chain(SAMPLE, steps=800, step_size=0.004, seed=5)
    reckless = inf.run_chain(SAMPLE, steps=800, step_size=0.6, seed=5)
    assert timid.acceptance > 0.8                            # accepts everything, explores nothing
    assert reckless.acceptance < 0.15
    assert timid.autocorrelation_length() > 10


def test_convergence_check():
    chains = [inf.run_chain(SAMPLE, steps=1500, seed=i, start=s)
              for i, s in enumerate([(0.1, 0.1), (0.9, 0.1), (0.1, 1.2), (0.9, 1.2)])]
    assert inf.gelman_rubin(chains, 0) < 1.1
    assert math.isnan(inf.gelman_rubin(chains[:1], 0))       # one chain proves nothing
    stuck = [inf.run_chain(SAMPLE, steps=400, step_size=0.002, seed=i, start=s)
             for i, s in enumerate([(0.1, 0.1), (0.9, 1.2)])]
    assert inf.gelman_rubin(stuck, 0) > 1.1                  # too timid to meet


def test_posterior_levels_enclose_the_right_fractions():
    chain = inf.run_chain(SAMPLE, steps=4000, seed=6)
    posterior = inf.posterior_map(chain, bins=40)
    inner, outer = posterior.levels
    total = posterior.density.sum()
    assert inner > outer
    assert posterior.density[posterior.density >= inner].sum() / total == pytest.approx(0.68, abs=0.05)
    assert posterior.density[posterior.density >= outer].sum() / total == pytest.approx(0.95, abs=0.05)
    assert posterior.extent[0] < chain.mean()[0] < posterior.extent[1]


@pytest.mark.parametrize("sigma,dof,expected", [(1, 1, 1.0), (2, 1, 4.0), (5, 1, 25.0), (1, 2, 2.30), (2, 2, 6.18)])
def test_delta_chi2_thresholds(sigma, dof, expected):
    """The numbers quoted in lesson L7.2."""
    assert inf.delta_chi2_for_sigma(sigma, dof) == pytest.approx(expected, abs=0.02)
    assert inf.sigma_from_delta_chi2(expected, dof) == pytest.approx(sigma, abs=0.01)


def test_goodness_of_fit():
    fit = inf.goodness_of_fit(1000.0, 1000, 3)
    assert fit["dof"] == 997 and fit["reduced"] == pytest.approx(1.003, abs=0.01)
    assert 0.2 < fit["p_value"] < 0.8                        # a perfectly ordinary fit
    assert inf.goodness_of_fit(3000.0, 1000, 3)["p_value"] < 1e-6
