"""Lesson figures for L7.4 (how surveys are built) and L7.6 (systematic errors)."""

from __future__ import annotations

import numpy as np

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics import survey

# Approximate footprints of well-known surveys: area (deg²), typical reach in redshift, objects, kind.
SURVEYS = [
    ("2dFGRS", 1_500, 0.2, 2.2e5, "spectroscopic"),
    ("SDSS", 8_000, 0.15, 9e5, "spectroscopic"),
    ("BOSS", 10_000, 0.7, 1.5e6, "spectroscopic"),
    ("DESI", 14_000, 2.5, 4e7, "spectroscopic"),
    ("Euclid", 14_000, 2.0, 1.5e9, "imaging"),
    ("Rubin LSST", 18_000, 3.0, 2e10, "imaging"),
    ("COSMOS-Web (JWST)", 0.54, 10.0, 8e5, "imaging"),
    ("JADES (JWST)", 0.05, 14.0, 1e5, "imaging"),
]


LABEL_OFFSETS = {"DESI": (-14, 8), "Euclid": (-14, -12), "Rubin LSST": (12, 8)}


@figure("survey_landscape")
def _survey_landscape(fig, p: Palette):
    """Wide and shallow against narrow and deep."""
    ax = fig.add_subplot()
    colours = {"spectroscopic": p.series[0], "imaging": p.series[1]}
    for name, area, depth, objects, kind in SURVEYS:
        size = 25 * (np.log10(objects) - 4) ** 1.6
        ax.scatter([area], [depth], s=size, color=colours[kind], alpha=0.75, edgecolor=p.text, linewidth=0.5)
        offset = LABEL_OFFSETS.get(name, (8, 4))
        ax.annotate(name, (area, depth), textcoords="offset points", xytext=offset, fontsize=7.5, color=p.text,
                    ha="right" if offset[0] < 0 else "left")
    for kind, colour in colours.items():
        ax.scatter([], [], s=40, color=colour, label=f"{kind} (bubble: number of objects)")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(0.02, 1e5)
    ax.set_ylim(0.1, 30)
    ax.set_xlabel("sky area (deg²)   —   the full sky is 41 000 deg²")
    ax.set_ylabel("typical redshift reach")
    ax.legend(loc="upper right", fontsize=7.5)
    ax.set_title("Wide and shallow or narrow and deep (approximate footprints)", fontsize=9, color=p.text)


@figure("effective_volume")
def _effective_volume(fig, p: Palette):
    """How much of the volume a survey really uses, as a function of n̄P."""
    n_p = np.logspace(-2, 2, 200)
    ax = fig.add_subplot()
    ax.plot(n_p, (n_p / (1 + n_p)) ** 2, color=p.series[0], linewidth=2.2)
    ax.axvspan(1e-2, 1, color=p.danger, alpha=0.08, linewidth=0)
    ax.text(0.012, 0.9, "shot-noise limited", color=p.danger, fontsize=8)
    ax.text(12, 0.55, "sample-variance\nlimited", color=p.success, fontsize=8)
    for tracer in survey.TRACERS.values():
        value = tracer.density * tracer.bias0**2 * survey.P_BAO
        ax.plot([value], [(value / (1 + value)) ** 2], "o", color=p.accent2, markersize=6)
        ax.annotate(tracer.label.split(" (")[0], (value, (value / (1 + value)) ** 2), textcoords="offset points",
                    xytext=(6, -12), fontsize=7, color=p.text)
    ax.set_xscale("log")
    ax.set_ylim(0, 1.05)
    ax.set_xlabel("n̄P  (galaxy density × clustering power at the BAO scale)")
    ax.set_ylabel("V_eff / V")
    ax.set_title("Beyond n̄P ≈ 3 more galaxies barely help; below 1 every galaxy counts", fontsize=9,
                 color=p.text)


@figure("systematic_floor")
def _systematic_floor(fig, p: Palette):
    """Statistical errors keep falling; a systematic floor does not."""
    n = np.logspace(2, 8, 200)
    statistical = 30 / np.sqrt(n)
    ax = fig.add_subplot()
    ax.plot(n, statistical, color=p.series[0], linewidth=2, label="statistical only: ∝ 1/√N")
    for floor, colour in ((0.3, p.warning), (1.0, p.danger)):
        ax.plot(n, np.hypot(statistical, floor), color=colour, linewidth=2,
                label=f"with a {floor}% systematic floor")
        ax.axhline(floor, color=colour, linestyle=":", linewidth=1)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("number of objects N")
    ax.set_ylabel("total error (%)")
    ax.legend(fontsize=8, loc="upper right")
    ax.set_title("Past the floor, a bigger survey buys almost nothing", fontsize=9, color=p.text)


@figure("malmquist_bias")
def _malmquist_bias(fig, p: Palette):
    """A flux-limited sample sees only the bright members at large distances."""
    rng = np.random.default_rng(8)
    n = 6000
    distance = 1000 * rng.random(n) ** (1 / 3)                 # uniform in volume, Mpc
    absolute = rng.normal(-19.3, 0.4, n)
    apparent = absolute + 5 * np.log10(distance * 1e6) - 5
    seen = apparent < 18.5
    ax = fig.add_subplot()
    ax.scatter(distance[~seen], absolute[~seen], s=3, color=p.muted, alpha=0.35, label="too faint to be detected")
    ax.scatter(distance[seen], absolute[seen], s=3, color=p.series[0], alpha=0.55, label="in the catalogue")
    edges = np.linspace(100, 1000, 10)
    centres = 0.5 * (edges[1:] + edges[:-1])
    counts = np.array([np.sum(seen & (distance >= lo) & (distance < hi)) for lo, hi in zip(edges[:-1], edges[1:])])
    means = np.array([absolute[seen & (distance >= lo) & (distance < hi)].mean() if count else np.nan
                      for (lo, hi), count in zip(zip(edges[:-1], edges[1:]), counts)])
    keep = counts >= 5
    ax.plot(centres[keep], means[keep], "s-", color=p.accent2, linewidth=2, markersize=5,
            label="mean of the catalogue")
    ax.axhline(-19.3, color=p.text, linestyle="--", linewidth=1, label="true mean")
    ax.invert_yaxis()
    ax.set_xlabel("distance (Mpc)")
    ax.set_ylabel("absolute magnitude")
    ax.legend(fontsize=7.5, loc="lower left")
    ax.set_title("Malmquist bias: far away, only the brightest make the cut (simulated catalogue)",
                 fontsize=9, color=p.text)
