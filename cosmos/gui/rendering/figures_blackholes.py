"""Lesson figures for L5.7 (CMB polarisation) and L6.9 (black holes in cosmology)."""

from __future__ import annotations

import numpy as np

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics import cmb

# Component masses of some landmark mergers, in solar masses, with the year they were announced.
MERGERS = [
    ("GW150914", 35.6, 30.6, 2016),
    ("GW170817", 1.46, 1.27, 2017),
    ("GW190425", 2.0, 1.4, 2020),
    ("GW190521", 85.0, 66.0, 2020),
    ("GW190814", 23.2, 2.6, 2020),
    ("GW200105", 8.9, 1.9, 2021),
]
PAIR_GAP = (50.0, 120.0)          # where pair instability is expected to leave no remnant
NEUTRON_STAR_MAX = 2.5            # roughly the heaviest a neutron star can be


@figure("cmb_polarisation")
def _cmb_polarisation(fig, p: Palette):
    """E-mode peaks fall in the temperature troughs."""
    ax = fig.add_subplot()
    tt = cmb.spectrum()
    pol = cmb.polarisation()
    ax.plot(tt.ell, tt.d_ell / 120.0, color=p.muted, linewidth=1.3, linestyle="--",
            label="temperature TT, divided by 120")
    ax.plot(pol.ell, pol.ee, color=p.series[0], linewidth=2.2, label="E modes (EE)")
    for ell, height in cmb.find_peaks(pol.ell, pol.ee, limit=4):
        ax.scatter([ell], [height], color=p.series[0], s=20, zorder=4)
    for ell, height in tt.peaks[:4]:
        ax.scatter([ell], [height / 120.0], color=p.muted, s=16, zorder=4)
    ax.set_xlim(2, 2000)
    ax.set_ylim(0, 55)
    ax.set_xlabel("Multipole ℓ")
    ax.set_ylabel("power (μK²)")
    ax.set_title("Compression makes the temperature peaks, velocity makes the E-mode peaks", fontsize=9)
    ax.legend(fontsize=8, loc="upper left")


@figure("b_mode_budget")
def _b_mode_budget(fig, p: Palette):
    """What stands between a telescope and a primordial B mode."""
    ax = fig.add_subplot()
    pol = cmb.polarisation(r=0.1)
    small = cmb.polarisation(r=cmb.BICEP_LIMIT_R)
    ax.loglog(pol.ell, pol.bb_dust, color=p.warning, linewidth=1.8, linestyle="-.",
              label="polarised Galactic dust (a clean patch)")
    ax.loglog(pol.ell, pol.bb_lensing, color=p.muted, linewidth=1.8, label="lensing B modes")
    ax.loglog(pol.ell, pol.bb_tensor, color=p.series[0], linewidth=2.2, label="inflation, r = 0.1")
    ax.loglog(small.ell, small.bb_tensor, color=p.series[0], linewidth=1.3, linestyle=":",
              label=f"r = {cmb.BICEP_LIMIT_R} (today's limit)")
    ax.axvline(80, color=p.border, linewidth=1, linestyle=":")
    ax.annotate("ℓ ≈ 80\nthe horizon at\nrecombination", (80, 3e-5), textcoords="offset points",
                xytext=(8, 0), fontsize=7, color=p.muted)
    ax.set_xlim(2, 2000)
    ax.set_ylim(1e-5, 0.5)
    ax.set_xlabel("Multipole ℓ")
    ax.set_ylabel("B-mode power (μK²)")
    ax.set_title("The primordial signal has to be dug out of dust and lensing", fontsize=9)
    ax.legend(fontsize=7.5, loc="lower right")


@figure("black_hole_masses")
def _black_hole_masses(fig, p: Palette):
    """The compact objects gravitational waves have found, and the gaps between them."""
    ax = fig.add_subplot()
    ax.axhspan(PAIR_GAP[0], PAIR_GAP[1], color=p.mix(p.danger, 0.18), zorder=0)
    ax.axhspan(NEUTRON_STAR_MAX, 5.0, color=p.mix(p.warning, 0.15), zorder=0)
    ax.text(0.55, np.sqrt(PAIR_GAP[0] * PAIR_GAP[1]), "pair-instability gap: no remnant expected",
            fontsize=7.5, color=p.danger, va="center")
    ax.text(0.55, np.sqrt(NEUTRON_STAR_MAX * 5.0), "lower mass gap", fontsize=7.5, color=p.warning,
            va="center")
    for i, (name, m1, m2, _year) in enumerate(MERGERS):
        x = i + 1
        ax.plot([x, x], [m2, m1], color=p.border, linewidth=1)
        for mass in (m1, m2):
            neutron = mass < NEUTRON_STAR_MAX
            ax.scatter([x], [mass], s=26, zorder=3,
                       color=p.series[1] if neutron else p.series[0],
                       marker="s" if neutron else "o")
        ax.annotate(name, (x, m1), textcoords="offset points", xytext=(0, 9), ha="center",
                    fontsize=7, color=p.text)
    ax.scatter([], [], color=p.series[0], s=26, label="black hole")
    ax.scatter([], [], color=p.series[1], s=26, marker="s", label="neutron star")
    ax.set_yscale("log")
    ax.set_ylim(0.8, 220)
    ax.set_xlim(0.4, len(MERGERS) + 0.8)
    ax.set_xticks([])
    ax.set_ylabel("mass (M☉)")
    ax.set_title("What LIGO and Virgo have weighed", fontsize=9)
    ax.legend(fontsize=7.5, loc="upper right")


@figure("primordial_black_holes")
def _primordial_black_holes(fig, p: Palette):
    """Which masses a primordial black hole could have, and what rules them out."""
    ax = fig.add_subplot()
    # Fraction of the dark matter allowed, as a function of mass. A teaching sketch of the
    # published constraint envelope, good to an order of magnitude.
    windows = [
        (1e10, 1e15, 1e-10, "evaporated by now"),
        (1e15, 1e17, 3e-8, "gamma-ray background"),
        (1e17, 1e22, 1.0, "open window"),
        (1e22, 1e26, 3e-2, "microlensing"),
        (1e26, 1e32, 3e-3, "clusters, CMB"),
        (1e32, 1e37, 1e-2, "wide binaries"),
    ]
    for low, high, allowed, label in windows:
        colour = p.success if allowed > 0.5 else p.danger
        ax.fill_between([low, high], [allowed, allowed], 1.0, color=p.mix(colour, 0.25), zorder=1)
        ax.plot([low, high], [allowed, allowed], color=colour, linewidth=1.8, zorder=2)
        ax.annotate(label, (np.sqrt(low * high), allowed), textcoords="offset points", xytext=(0, 5),
                    ha="center", fontsize=6.8, color=p.muted)
    ax.axvline(1.989e33, color=p.border, linestyle=":", linewidth=1)
    ax.text(1.989e33, 2e-11, " one solar mass", fontsize=7, color=p.muted)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e10, 1e37)
    ax.set_ylim(1e-11, 3)
    ax.set_xlabel("black hole mass (g)")
    ax.set_ylabel("allowed fraction of the dark matter")
    ax.set_title("Only an asteroid-mass window is still wide open", fontsize=9)
