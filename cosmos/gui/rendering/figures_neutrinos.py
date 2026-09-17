"""Lesson figures for L4.7: what oscillations and cosmology say about neutrino mass."""

from __future__ import annotations

import numpy as np

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics import neutrinos


@figure("neutrino_mass_sum")
def _neutrino_mass_sum(fig, p: Palette):
    """Σmν against the lightest mass for both orderings, with the laboratory and cosmological limits."""
    lightest = np.logspace(-4, 0, 300)
    ax = fig.add_subplot()
    for ordering, colour, label in (("normal", p.series[0], "normal ordering"),
                                    ("inverted", p.series[1], "inverted ordering")):
        total = [sum(neutrinos.masses(m, ordering)) for m in lightest]
        ax.plot(lightest, total, color=colour, linewidth=2.2, label=label)
    ax.axhspan(0.12, 10, color=p.danger, alpha=0.1, linewidth=0)
    positions = {"KATRIN (tritium decay)": 1.08, "Planck 2018 CMB + BAO": 1.08,
                 "DESI 2024 BAO + CMB": 1.06, "DESI 2025 BAO + CMB": 0.8}
    for bound in neutrinos.BOUNDS:
        if bound.kind == "floor":
            continue
        colour = p.warning if bound.kind == "laboratory" else p.danger
        ax.axhline(bound.value_ev, color=colour, linestyle="--", linewidth=1.1)
        ax.text(1.2e-4, bound.value_ev * positions.get(bound.name, 1.08),
                f"{bound.name}: Σmν < {bound.value_ev:.3g} eV", color=colour, fontsize=7)
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(1e-4, 1)
    ax.set_ylim(0.04, 3.5)
    ax.set_xlabel("mass of the lightest neutrino (eV)")
    ax.set_ylabel("Σmν (eV)")
    ax.legend(loc="lower right", fontsize=8)
    ax.set_title("Oscillations set the floor, cosmology the ceiling", fontsize=9, color=p.text)


@figure("neutrino_suppression")
def _neutrino_suppression(fig, p: Palette):
    """Massive neutrinos stream out of small clumps and lower the small-scale matter power."""
    k = np.logspace(-4, 0.3, 300)
    ax = fig.add_subplot()
    for total, colour in ((0.06, p.series[0]), (0.12, p.series[2]), (0.3, p.warning), (0.6, p.danger)):
        ratio = neutrinos.power_suppression(k, total)
        fraction = neutrinos.neutrino_fraction(total, 0.31, 0.674)
        ax.plot(k, ratio, color=colour, linewidth=2,
                label=f"Σmν = {total} eV  (fν = {fraction:.1%}, ΔP/P → −{8 * fraction:.0%})")
    ax.axvspan(0.02, 0.3, color=p.muted, alpha=0.12, linewidth=0)
    ax.text(0.024, 0.66, "scales galaxy surveys\nmeasure well", color=p.muted, fontsize=7.5)
    ax.axhline(1, color=p.border, linewidth=1)
    ax.set_xscale("log")
    ax.set_ylim(0.6, 1.03)
    ax.set_xlabel("wavenumber k (h/Mpc):  large scales ← → small scales")
    ax.set_ylabel("P(k) with / without mass")
    ax.legend(loc="lower left", fontsize=7.5)
    ax.set_title("Hot neutrinos cannot fall into small clumps (teaching approximation)", fontsize=9,
                 color=p.text)
