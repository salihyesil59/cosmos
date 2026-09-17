"""Lesson figures for L7.3: degeneracies, chain diagnostics and derived parameters."""

from __future__ import annotations

import numpy as np

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette

# The supernova posterior the simulator finds for Pantheon+ (S19, no second probe).
SN_MEAN = np.array([0.31, 0.61])
SN_STD = np.array([0.068, 0.095])
SN_CORRELATION = 0.88


def _sn_covariance() -> np.ndarray:
    off = SN_CORRELATION * SN_STD[0] * SN_STD[1]
    return np.array([[SN_STD[0] ** 2, off], [off, SN_STD[1] ** 2]])


def _ellipse(mean, cov, n_sigma, points=200):
    """Points on the 68% (n=1) or 95% (n=2) contour of a 2D Gaussian."""
    delta_chi2 = {1: 2.30, 2: 6.17}[n_sigma]
    values, vectors = np.linalg.eigh(cov)
    angle = np.linspace(0, 2 * np.pi, points)
    circle = np.stack([np.cos(angle), np.sin(angle)])
    return (vectors @ (np.sqrt(values * delta_chi2)[:, None] * circle)).T + mean


@figure("degeneracy_breaking")
def _degeneracy_breaking(fig, p: Palette):
    """Supernovae alone, the CMB geometry alone, and the two multiplied together."""
    sn_cov = _sn_covariance()
    # The CMB constrains Ωm + ΩΛ = 1.00 ± 0.02: a Gaussian that is infinitely long along the band.
    direction = np.array([1.0, 1.0])
    cmb_precision = np.outer(direction, direction) / 0.02**2
    sn_precision = np.linalg.inv(sn_cov)
    combined_cov = np.linalg.inv(sn_precision + cmb_precision)
    # Product of Gaussians: precision-weighted means (the CMB term only fixes Ωm + ΩΛ = 1).
    combined_mean = combined_cov @ (sn_precision @ SN_MEAN + direction * 1.0 / 0.02**2)

    ax = fig.add_subplot()
    line = np.linspace(-0.2, 1.2, 10)
    ax.fill_between(line, 1 - line - 0.04, 1 - line + 0.04, color=p.series[3], alpha=0.25, linewidth=0,
                    label="CMB: Ωm + ΩΛ = 1.00 ± 0.02 (2σ)")
    for n, alpha in ((2, 0.25), (1, 0.5)):
        ring = _ellipse(SN_MEAN, sn_cov, n)
        ax.fill(ring[:, 0], ring[:, 1], color=p.series[0], alpha=alpha, linewidth=0,
                label="supernovae alone" if n == 1 else None)
    for n, alpha in ((2, 0.55), (1, 0.9)):
        ring = _ellipse(combined_mean, combined_cov, n)
        ax.fill(ring[:, 0], ring[:, 1], color=p.accent2, alpha=alpha, linewidth=0,
                label="both together" if n == 1 else None)
    ax.set_xlim(0.0, 0.7)
    ax.set_ylim(0.2, 1.0)
    ax.set_xlabel("Ωm")
    ax.set_ylabel("ΩΛ")
    ax.legend(loc="upper right", fontsize=8)
    error = np.sqrt(np.diag(combined_cov))
    ax.set_title(f"Crossing directions: ΩΛ goes from ± {SN_STD[1]:.3f} to ± {error[1]:.3f}",
                 fontsize=9, color=p.text)


@figure("chain_diagnostics")
def _chain_diagnostics(fig, p: Palette):
    """A well-mixed chain and a sticky one, with their autocorrelation."""
    rng = np.random.default_rng(12)
    n = 1500
    chains = {}
    for name, rho in (("healthy", 0.6), ("sticky", 0.985)):
        noise = rng.normal(0, np.sqrt(1 - rho**2), n)
        x = np.zeros(n)
        for i in range(1, n):
            x[i] = rho * x[i - 1] + noise[i]
        chains[name] = x

    grid = fig.add_gridspec(2, 2, width_ratios=[2.2, 1])
    colours = {"healthy": p.series[0], "sticky": p.danger}
    acf_ax = fig.add_subplot(grid[:, 1])
    lags = np.arange(150)
    for row, (name, x) in enumerate(chains.items()):
        ax = fig.add_subplot(grid[row, 0])
        ax.plot(x, color=colours[name], linewidth=0.7)
        ax.set_ylabel("parameter", fontsize=8)
        ax.tick_params(labelsize=7)
        centred = x - x.mean()
        acf = np.array([np.dot(centred[:n - lag], centred[lag:]) for lag in lags]) / np.dot(centred, centred)
        positive = acf[1:]
        tau = 1 + 2 * np.sum(positive[:np.argmax(positive < 0.05)] if np.any(positive < 0.05) else positive)
        ax.set_title(f"{name}: τ ≈ {tau:.0f} steps → about {n / tau:.0f} independent samples",
                     fontsize=8.5, color=p.text)
        if row == 1:
            ax.set_xlabel("step", fontsize=8)
        else:
            ax.tick_params(labelbottom=False)
        acf_ax.plot(lags, acf, color=colours[name], linewidth=1.8, label=name)
    acf_ax.axhline(0, color=p.border, linewidth=1)
    acf_ax.set_xlabel("lag (steps)", fontsize=8)
    acf_ax.set_ylabel("autocorrelation", fontsize=8)
    acf_ax.legend(fontsize=8)
    acf_ax.tick_params(labelsize=7)
    acf_ax.set_title("How fast it forgets", fontsize=9, color=p.text)


@figure("derived_parameter")
def _derived_parameter(fig, p: Palette):
    """q0 = Ωm/2 − ΩΛ straight from correlated samples, against the naive error propagation."""
    rng = np.random.default_rng(3)
    samples = rng.multivariate_normal(SN_MEAN, _sn_covariance(), 20000)
    q0 = samples[:, 0] / 2 - samples[:, 1]
    naive = float(np.hypot(0.5 * SN_STD[0], SN_STD[1]))

    left, right = fig.subplots(1, 2)
    left.scatter(samples[:3000, 0], samples[:3000, 1], s=2, color=p.series[0], alpha=0.35)
    om = np.linspace(0.05, 0.6, 10)
    for value in (-0.6, -0.45, -0.3):
        left.plot(om, om / 2 - value, color=p.accent2, linewidth=1, linestyle="--")
        left.text(0.58, 0.3 - value, f"q0 = {value}", color=p.accent2, fontsize=7, ha="right")
    left.set_xlim(0.05, 0.6)
    left.set_ylim(0.25, 1.0)
    left.set_xlabel("Ωm")
    left.set_ylabel("ΩΛ")
    left.set_title("Samples, and lines of constant q0", fontsize=9, color=p.text)

    right.hist(q0, bins=60, density=True, color=p.series[0], alpha=0.75,
               label=f"from the samples: ± {q0.std():.3f}")
    grid = np.linspace(q0.mean() - 0.35, q0.mean() + 0.35, 200)
    right.plot(grid, np.exp(-0.5 * ((grid - q0.mean()) / naive) ** 2) / (naive * np.sqrt(2 * np.pi)),
               color=p.danger, linewidth=1.8, label=f"ignoring the correlation: ± {naive:.3f}")
    right.axvline(0, color=p.muted, linestyle=":", linewidth=1)
    right.set_xlabel("q0 = Ωm/2 − ΩΛ")
    right.set_yticks([])
    right.legend(fontsize=7.5, loc="upper left")
    right.set_title("Error propagation for free", fontsize=9, color=p.text)


@figure("ladder_error_budget")
def _ladder_error_budget(fig, p: Palette):
    """Errors of independent rungs add in quadrature: the biggest one decides."""
    from cosmos.physics import ladder

    result = ladder.build(ladder.LadderSettings())
    names = ["parallax", "calibrators", "flow"]
    values = [result.budget_percent[k] for k in names]
    improved = dict(result.budget_percent)
    improved["flow"] = 0.0
    better_total = np.sqrt(sum(v**2 for v in improved.values()))
    halved = dict(result.budget_percent)
    halved[result.dominant] /= 2
    halved_total = np.sqrt(sum(v**2 for v in halved.values()))

    ax = fig.add_subplot()
    labels = ["1 · parallaxes", "2 · calibrators", "3 · Hubble flow", "total",
              "total with a perfect rung 3", f"total with rung '{result.dominant}' halved"]
    bars = values + [result.error_percent, better_total, halved_total]
    colours = [p.series[0], p.series[1], p.series[2], p.text, p.muted, p.accent2]
    y = np.arange(len(bars))[::-1]
    ax.barh(y, bars, color=colours, alpha=0.85)
    for yi, value in zip(y, bars):
        ax.text(value, yi, f" {value:.2f}%", va="center", fontsize=8, color=p.text)
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlim(0, max(bars) * 1.3)
    ax.set_xlabel("uncertainty on H0 (%)")
    ax.set_title("A simulated ladder (S20): improve the weakest rung first", fontsize=9, color=p.text)
