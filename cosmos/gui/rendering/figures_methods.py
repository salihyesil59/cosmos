"""Lesson figures for Level 7: how cosmologists read data and turn it into numbers."""

from __future__ import annotations

import numpy as np

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette


@figure("linear_vs_log")
def _linear_vs_log(fig, p: Palette):
    """The same data on a linear and on a logarithmic axis."""
    x = np.array([1.0, 3.0, 10.0, 30.0, 100.0, 300.0, 1000.0])
    y = 2.0 * x**1.5
    axes = fig.subplots(1, 2)
    for ax, log in zip(axes, (False, True)):
        ax.plot(x, y, "o-", color=p.series[0], linewidth=2, markersize=5)
        if log:
            ax.set_xscale("log")
            ax.set_yscale("log")
            ax.set_title("Logarithmic axes: a power law is a straight line", fontsize=9, color=p.text)
            ax.set_ylabel("y (log)")
        else:
            ax.set_title("Linear axes: everything hides in the corner", fontsize=9, color=p.text)
            ax.set_ylabel("y")
        ax.set_xlabel("x")
    fig.suptitle("y = 2 x^1.5, plotted twice", fontsize=9, color=p.text)


@figure("error_bars_and_fit")
def _error_bars_and_fit(fig, p: Palette):
    """Data with error bars, a fitted line, and the residuals underneath."""
    rng = np.random.default_rng(7)
    x = np.linspace(0.5, 10, 14)
    truth = 1.6 * x + 3.0
    sigma = np.full_like(x, 1.6)
    y = truth + rng.normal(0, sigma)
    slope, intercept = np.polyfit(x, y, 1, w=1 / sigma)
    model = slope * x + intercept

    top, bottom = fig.subplots(2, 1, sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    top.errorbar(x, y, yerr=sigma, fmt="o", color=p.text, markersize=4, capsize=3, label="measurements")
    top.plot(x, model, color=p.series[0], linewidth=2, label=f"fit: y = {slope:.2f}x + {intercept:.2f}")
    top.fill_between(x, model - sigma, model + sigma, color=p.series[0], alpha=0.15, linewidth=0)
    top.set_ylabel("measured quantity")
    top.legend(loc="upper left", fontsize=8)
    top.set_title("Error bars say how much the points are allowed to miss the line", fontsize=9, color=p.text)

    residual = (y - model) / sigma
    bottom.axhline(0, color=p.series[0], linewidth=1.5)
    bottom.axhspan(-1, 1, color=p.series[0], alpha=0.12, linewidth=0)
    bottom.errorbar(x, residual, yerr=1, fmt="o", color=p.text, markersize=4, capsize=3)
    bottom.set_ylabel("residual (σ)")
    bottom.set_xlabel("x")
    bottom.set_ylim(-3.2, 3.2)


@figure("confidence_contours")
def _confidence_contours(fig, p: Palette):
    """A correlated two-parameter posterior, with 68% and 95% contours."""
    rng = np.random.default_rng(19)
    mean = np.array([0.33, 0.68])
    cov = np.array([[0.05**2, 0.9 * 0.05 * 0.09], [0.9 * 0.05 * 0.09, 0.09**2]])
    samples = rng.multivariate_normal(mean, cov, 40000)
    density, x_edges, y_edges = np.histogram2d(samples[:, 0], samples[:, 1], bins=60)
    flat = np.sort(density.ravel())[::-1]
    cumulative = np.cumsum(flat) / flat.sum()
    levels = [float(flat[np.searchsorted(cumulative, level)]) for level in (0.95, 0.68)]

    ax = fig.add_subplot()
    x = 0.5 * (x_edges[1:] + x_edges[:-1])
    y = 0.5 * (y_edges[1:] + y_edges[:-1])
    ax.contourf(x, y, density.T, levels=levels + [density.max() + 1],
                colors=[p.mix(p.series[0], 0.3), p.mix(p.series[0], 0.7)])
    ax.plot(*mean, "o", color=p.text, markersize=5)
    ax.axvline(mean[0], color=p.muted, linestyle=":", linewidth=1)
    ax.axhline(mean[1], color=p.muted, linestyle=":", linewidth=1)
    line = np.linspace(0.0, 1.0, 10)
    ax.plot(line, 1 - line, color=p.success, linestyle="--", linewidth=1.4, label="flat universe")
    ax.text(0.52, 0.86, "95%", color=p.text, fontsize=8)
    ax.text(0.40, 0.74, "68%", color=p.text, fontsize=8)
    ax.set_xlim(0.15, 0.6)
    ax.set_ylim(0.35, 1.0)
    ax.set_xlabel("Ωm")
    ax.set_ylabel("ΩΛ")
    ax.legend(loc="lower left", fontsize=8)
    ax.set_title("Two parameters, one measurement: the contours lean because they are correlated",
                 fontsize=9, color=p.text)


@figure("chi2_parabola")
def _chi2_parabola(fig, p: Palette):
    """χ² against one parameter: the minimum is the answer, the curvature is the error bar."""
    x = np.linspace(0.1, 0.6, 400)
    best, sigma = 0.334, 0.018
    chi2 = 1368 + ((x - best) / sigma) ** 2
    ax = fig.add_subplot()
    ax.plot(x, chi2 - chi2.min(), color=p.series[0], linewidth=2.2)
    for level, label, colour in ((1, "1σ (Δχ² = 1)", p.accent2), (4, "2σ (Δχ² = 4)", p.warning),
                                 (25, "5σ (Δχ² = 25)", p.danger)):
        ax.axhline(level, color=colour, linestyle="--", linewidth=1.2)
        ax.text(0.585, level * 1.05, label, color=colour, fontsize=8, ha="right")
    ax.axvline(best, color=p.muted, linestyle=":", linewidth=1)
    ax.annotate(f"best fit Ωm = {best}", (best, 0.4), textcoords="offset points", xytext=(8, 0),
                color=p.text, fontsize=8)
    ax.set_ylim(0, 30)
    ax.set_xlabel("Ωm")
    ax.set_ylabel("Δχ² above the minimum")
    ax.set_title("How far you may move before the fit gets worse", fontsize=9, color=p.text)


@figure("mcmc_walk")
def _mcmc_walk(fig, p: Palette):
    """A short Metropolis walk over a correlated likelihood."""
    rng = np.random.default_rng(4)
    mean = np.array([0.33, 0.68])
    cov = np.array([[0.05**2, 0.9 * 0.05 * 0.09], [0.9 * 0.05 * 0.09, 0.09**2]])
    inverse = np.linalg.inv(cov)

    def log_p(point):
        d = point - mean
        return -0.5 * d @ inverse @ d

    point = np.array([0.7, 0.15])
    path = [point.copy()]
    current = log_p(point)
    for _ in range(600):
        proposal = point + rng.normal(0, 0.05, 2)
        candidate = log_p(proposal)
        if np.log(rng.random()) < candidate - current:
            point, current = proposal, candidate
        path.append(point.copy())
    path = np.array(path)

    ax = fig.add_subplot()
    ax.plot(path[:, 0], path[:, 1], color=p.muted, linewidth=0.7, alpha=0.8)
    ax.scatter(path[60:, 0], path[60:, 1], s=6, color=p.series[0], alpha=0.6, label="samples kept")
    ax.scatter(path[:60, 0], path[:60, 1], s=6, color=p.danger, alpha=0.8, label="burn-in, discarded")
    ax.plot(*path[0], "s", color=p.danger, markersize=7)
    ax.annotate("start", path[0], textcoords="offset points", xytext=(8, -4), color=p.danger, fontsize=8)
    ax.plot(*mean, "*", color=p.accent2, markersize=14, label="truth")
    ax.set_xlabel("Ωm")
    ax.set_ylabel("ΩΛ")
    ax.legend(loc="upper right", fontsize=8)
    ax.set_title("The walker forgets where it started and then samples the posterior",
                 fontsize=9, color=p.text)
