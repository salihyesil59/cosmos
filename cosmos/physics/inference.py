"""How a measurement becomes a number: likelihoods, χ² and MCMC (L7.2, S19).

The example throughout is the one the course already knows — type Ia supernovae
constraining Ωm and ΩΛ — but nothing here is specific to supernovae: the same
three steps (a model, a likelihood, a sampler) are what every parameter in
cosmology comes from.

The magnitude offset (which mixes the absolute magnitude of a supernova with H0)
is marginalised analytically, so the likelihood depends on the two density
parameters alone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import stats

from cosmos.physics.supernovae import SupernovaSample, dimensionless_luminosity_distance

PARAMETER_LABELS = {"om": "Ωm", "ol": "ΩΛ"}
DEFAULT_BOUNDS = {"om": (0.0, 1.5), "ol": (-0.5, 2.0)}


def chi2(om: float, ol: float, sample: SupernovaSample) -> float:
    """χ² of one model, with the magnitude offset fitted away."""
    dl = dimensionless_luminosity_distance(sample.z, om, ol)[0]
    if not np.all(np.isfinite(dl)) or np.any(dl <= 0):
        return math.inf
    shape = 5 * np.log10(dl)
    weight = 1 / sample.error**2
    residual = sample.m - shape
    offset = np.sum(weight * residual) / np.sum(weight)      # the analytic best offset
    return float(np.sum(weight * (residual - offset) ** 2))


def log_likelihood(om: float, ol: float, sample: SupernovaSample) -> float:
    value = chi2(om, ol, sample)
    return -0.5 * value if math.isfinite(value) else -math.inf


def in_bounds(om: float, ol: float, bounds: dict[str, tuple[float, float]]) -> bool:
    return (bounds["om"][0] <= om <= bounds["om"][1]) and (bounds["ol"][0] <= ol <= bounds["ol"][1])


@dataclass
class Chain:
    """A Metropolis–Hastings chain and everything the interface shows about it."""

    samples: np.ndarray                  # (steps, 2): Ωm and ΩΛ
    log_post: np.ndarray
    accepted: int
    flat: bool                           # ΩΛ was tied to 1 − Ωm
    burn_in: int = 0
    label: str = ""

    @property
    def acceptance(self) -> float:
        return self.accepted / max(len(self.samples) - 1, 1)

    @property
    def kept(self) -> np.ndarray:
        return self.samples[self.burn_in:]

    def mean(self) -> np.ndarray:
        return self.kept.mean(axis=0)

    def std(self) -> np.ndarray:
        return self.kept.std(axis=0, ddof=1)

    def interval(self, index: int, level: float = 0.68) -> tuple[float, float]:
        low = 50 * (1 - level)
        return tuple(np.percentile(self.kept[:, index], [low, 100 - low]))

    def correlation(self) -> float:
        if self.flat or len(self.kept) < 10:
            return 0.0
        return float(np.corrcoef(self.kept[:, 0], self.kept[:, 1])[0, 1])

    def autocorrelation_length(self, index: int = 0, max_lag: int = 200) -> float:
        """Roughly how many steps the walker needs to forget where it was."""
        x = self.kept[:, index]
        x = x - x.mean()
        if len(x) < 20 or np.allclose(x, 0):
            return float("nan")
        total = 1.0
        norm = float(np.dot(x, x))
        for lag in range(1, min(max_lag, len(x) // 3)):
            rho = float(np.dot(x[:-lag], x[lag:])) / norm
            if rho <= 0.05:
                break
            total += 2 * rho
        return total

    def effective_samples(self, index: int = 0) -> float:
        tau = self.autocorrelation_length(index)
        return float(len(self.kept) / tau) if tau and math.isfinite(tau) else float("nan")


def run_chain(sample: SupernovaSample, steps: int = 4000, step_size: float = 0.08,
              start: tuple[float, float] = (0.5, 0.5), seed: int = 1, flat: bool = False,
              bounds: dict[str, tuple[float, float]] | None = None, burn_in_fraction: float = 0.2) -> Chain:
    """Metropolis–Hastings: propose, compare, accept or stay."""
    bounds = bounds or DEFAULT_BOUNDS
    rng = np.random.default_rng(seed)
    om, ol = start
    if flat:
        ol = 1 - om
    current = log_likelihood(om, ol, sample)
    samples = np.empty((steps, 2))
    posts = np.empty(steps)
    accepted = 0
    for i in range(steps):
        proposal_om = om + rng.normal(0, step_size)
        proposal_ol = (1 - proposal_om) if flat else ol + rng.normal(0, step_size * 1.4)
        if in_bounds(proposal_om, proposal_ol, bounds):
            candidate = log_likelihood(proposal_om, proposal_ol, sample)
            if math.log(rng.random()) < candidate - current:
                om, ol, current = proposal_om, proposal_ol, candidate
                accepted += 1
        samples[i] = (om, ol)
        posts[i] = current
    return Chain(samples, posts, accepted, flat, burn_in=int(steps * burn_in_fraction))


def gelman_rubin(chains: list[Chain], index: int = 0) -> float:
    """R̂: how much wider the chains are together than each is on its own. 1.0 is converged."""
    kept = [c.kept[:, index] for c in chains if len(c.kept) > 10]
    if len(kept) < 2:
        return float("nan")
    n = min(len(k) for k in kept)
    kept = np.array([k[:n] for k in kept])
    means = kept.mean(axis=1)
    within = kept.var(axis=1, ddof=1).mean()
    between = n * means.var(ddof=1)
    if within <= 0:
        return float("nan")
    var_plus = (n - 1) / n * within + between / n
    return float(math.sqrt(var_plus / within))


@dataclass
class Posterior:
    """A 2D histogram of the chain, with the levels that enclose 68% and 95%."""

    x_edges: np.ndarray
    y_edges: np.ndarray
    density: np.ndarray
    levels: tuple[float, float] = field(default=(0.0, 0.0))

    @property
    def extent(self) -> tuple[float, float, float, float]:
        return (self.x_edges[0], self.x_edges[-1], self.y_edges[0], self.y_edges[-1])

    @property
    def centres(self) -> tuple[np.ndarray, np.ndarray]:
        return (0.5 * (self.x_edges[1:] + self.x_edges[:-1]), 0.5 * (self.y_edges[1:] + self.y_edges[:-1]))


def posterior_map(chain: Chain, bins: int = 45) -> Posterior:
    x, y = chain.kept[:, 0], chain.kept[:, 1]
    density, x_edges, y_edges = np.histogram2d(x, y, bins=bins)
    return Posterior(x_edges, y_edges, density.T, credible_levels(density))


def credible_levels(density: np.ndarray, levels=(0.68, 0.95)) -> tuple[float, ...]:
    """Density values that enclose the given fractions of the samples."""
    flat = np.sort(density.ravel())[::-1]
    total = flat.sum()
    if total <= 0:
        return tuple(0.0 for _ in levels)
    cumulative = np.cumsum(flat) / total
    return tuple(float(flat[np.searchsorted(cumulative, level)]) if level < cumulative[-1] else 0.0
                 for level in levels)


# ------------------------------------------------------- χ² and significance
def sigma_from_delta_chi2(delta_chi2: float, dof: int = 1) -> float:
    """How many standard deviations a Δχ² corresponds to (two-sided, Gaussian)."""
    if delta_chi2 <= 0:
        return 0.0
    p = stats.chi2.sf(delta_chi2, dof)
    if p <= 0:
        return math.inf
    return float(stats.norm.isf(p / 2))


def delta_chi2_for_sigma(sigma: float, dof: int = 1) -> float:
    """The Δχ² a claim of ``sigma`` standard deviations needs."""
    p = 2 * stats.norm.sf(sigma)
    return float(stats.chi2.isf(p, dof))


def goodness_of_fit(chi2_value: float, n_points: int, n_parameters: int) -> dict[str, float]:
    """χ² per degree of freedom and the probability of a worse fit by chance."""
    dof = max(n_points - n_parameters, 1)
    return {
        "chi2": chi2_value,
        "dof": dof,
        "reduced": chi2_value / dof,
        "p_value": float(stats.chi2.sf(chi2_value, dof)),
    }
