"""Lesson figures for L7.5 (simulations as experiments) and L0.7 (orders of magnitude)."""

from __future__ import annotations

import numpy as np
from matplotlib.patches import FancyBboxPatch

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics import mock

# The chain every mock catalogue goes through, from a random field to a data file.
# Laid out as two rows: what the simulation does, then what the observing does.
CHAIN = [
    [("Initial conditions", "a Gaussian field\nwith the ΛCDM P(k)"),
     ("Gravity", "an N-body run:\nfilaments and voids"),
     ("Haloes", "the lumps galaxies\nlive in"),
     ("Galaxies", "a tuned recipe,\nnot first principles")],
    [("Light cone", "seen as they were\nwhen the light left"),
     ("Redshifts", "distance plus the\ngalaxy's own motion"),
     ("The survey", "footprint, flux limit,\nmeasurement errors"),
     ("Mock catalogue", "a file shaped exactly\nlike the real data")],
]


@figure("mock_chain")
def _mock_chain(fig, p: Palette):
    """From random initial conditions to a file that looks like data."""
    ax = fig.add_subplot()
    ax.set_xlim(-0.05, 4.05)
    ax.set_ylim(0, 2.3)
    ax.axis("off")
    for row, stages in enumerate(CHAIN):
        colour = p.series[0] if row == 0 else p.series[1]
        y = 1.60 if row == 0 else 0.52
        ax.text(0.05, y + 0.56, "the simulation" if row == 0 else "the observing",
                fontsize=8.5, color=colour, weight="bold")
        for i, (title, detail) in enumerate(stages):
            ax.add_patch(FancyBboxPatch((i + 0.05, y), 0.9, 0.52, boxstyle="round,pad=0.01,rounding_size=0.05",
                                        linewidth=1.3, edgecolor=colour, facecolor=p.mix(colour, 0.12)))
            ax.text(i + 0.5, y + 0.38, title, ha="center", va="center", fontsize=8, color=p.text, weight="bold")
            ax.text(i + 0.5, y + 0.20, detail, ha="center", va="center", fontsize=6.4, color=p.muted)
            if i < len(stages) - 1:
                ax.annotate("", xy=(i + 1.04, y + 0.26), xytext=(i + 0.96, y + 0.26),
                            arrowprops={"arrowstyle": "->", "color": p.muted, "lw": 1.2})
    ax.annotate("", xy=(0.5, 1.30), xytext=(3.5, 1.55),
                arrowprops={"arrowstyle": "->", "color": p.muted, "lw": 1.2,
                            "connectionstyle": "arc3,rad=-0.22"})
    ax.text(2.0, 1.41, "the box is then observed", ha="center", fontsize=7, color=p.muted)
    ax.text(2.0, 0.14, "The analysis is run on the mock and must return the cosmology put in at the start.",
            ha="center", fontsize=8, color=p.text)


@figure("cosmic_variance_seeds")
def _cosmic_variance_seeds(fig, p: Palette):
    """The same cosmology, four times: the statistics agree, the structures do not."""
    axes = fig.subplots(2, 2, sharex=True, sharey=True)
    settings = mock.with_effect(mock.PRESETS_MOCK["volume"][1], grid=96, box_mpc=520.0, r_max=200.0,
                                wedge_deg=90.0, density=8e-3, velocities=False, fingers_km_s=0.0)
    for ax, seed in zip(axes.ravel(), (3, 11, 19, 27)):
        cat = mock.build(mock.with_effect(settings, seed=seed))
        x, y = cat.xy(False)
        ax.scatter(y, x, s=0.9, color=p.series[0], alpha=0.75, linewidths=0)
        ax.set_aspect("equal")
        ax.set_title(f"seed {seed}", fontsize=8, color=p.muted, pad=2)
        ax.set_xticks([])
        ax.set_yticks([])
    fig.suptitle("Four universes with identical statistics — cosmic variance is the difference between them",
                 fontsize=9, color=p.text)


@figure("redshift_space_map")
def _redshift_space_map(fig, p: Palette):
    """The same galaxies in real space and in redshift space."""
    left, right = fig.subplots(1, 2, sharex=True, sharey=True)
    settings = mock.with_effect(mock.PRESETS_MOCK["volume"][1], grid=96, box_mpc=520.0, r_max=170.0,
                                wedge_deg=45.0, thickness_deg=6.0, bias=1.8, density=2.5e-2,
                                fingers_km_s=1000.0)
    cat = mock.build(settings)
    for ax, observed, title, colour in ((left, False, "real space: where they are", p.muted),
                                        (right, True, "redshift space: where their redshifts put them",
                                         p.series[0])):
        x, y = cat.xy(observed)
        ax.scatter(y, x, s=1.4, color=colour, alpha=0.8, linewidths=0)
        ax.set_aspect("equal")
        ax.set_title(title, fontsize=8, color=p.muted, pad=3)
        ax.set_xlabel("Mpc/h", fontsize=8)
        ax.tick_params(labelsize=7)
    left.set_ylabel("distance (Mpc/h)", fontsize=8)
    fig.suptitle("Clusters are stretched into fingers pointing at the observer", fontsize=9, color=p.text)


@figure("survey_selection_curve")
def _survey_selection_curve(fig, p: Palette):
    """How much of the galaxy population a flux-limited catalogue keeps."""
    ax = fig.add_subplot()
    r = np.linspace(2, 400, 400)
    for m_limit, label in ((15.5, "m < 15.5 (CfA2)"), (17.77, "m < 17.8 (SDSS main)"),
                           (19.5, "m < 19.5 (BOSS)")):
        ax.semilogy(r, np.maximum(mock.selection(r, m_limit), 1e-5), linewidth=2, label=label)
    ax.axhline(1.0, color=p.border, linestyle=":", linewidth=1)
    ax.set_xlabel("comoving distance (Mpc/h)")
    ax.set_ylabel("fraction bright enough to be seen")
    ax.set_ylim(1e-5, 2)
    ax.set_title("A flux-limited survey keeps only the luminous tail at large distance", fontsize=9)
    ax.legend(fontsize=8)


@figure("orders_of_magnitude")
def _orders_of_magnitude(fig, p: Palette):
    """Everything in the course on one logarithmic ruler."""
    scales = [
        (1e-15, "proton"),
        (1e-10, "atom"),
        (1e-6, "cell"),
        (1.0, "you"),
        (6.4e6, "Earth"),
        (7e8, "Sun"),
        (1.5e11, "Earth–Sun"),
        (4e16, "nearest star"),
        (1e21, "Milky Way"),
        (2.4e22, "Andromeda"),
        (5e23, "Local Supercluster"),
        (1.3e26, "observable universe"),
    ]
    ax = fig.add_subplot()
    # Four alternating heights, so that labels close together on the ruler never collide.
    heights = (0.30, -0.55, 0.60, -0.28)
    ax.hlines(0, -16, 27, color=p.border, linewidth=1.5)
    for i, (value, label) in enumerate(scales):
        x = float(np.log10(value))
        y = heights[i % len(heights)]
        ax.vlines(x, 0, y * 0.85, color=p.series[0], linewidth=1.2)
        ax.plot([x], [0], "o", color=p.series[0], markersize=4)
        ax.text(x, y, label, ha="center", va="bottom" if y > 0 else "top", fontsize=7.5, color=p.text)
    ax.set_xlim(-17, 28)
    ax.set_ylim(-0.95, 0.95)
    ax.set_yticks([])
    ax.set_xticks(range(-15, 28, 5))
    ax.set_xticklabels([f"$10^{{{e}}}$" for e in range(-15, 28, 5)])
    ax.set_xlabel("size in metres")
    ax.set_title("Forty-one powers of ten, from a proton to the observable universe", fontsize=9)
    for spine in ("top", "right", "left"):
        ax.spines[spine].set_visible(False)
