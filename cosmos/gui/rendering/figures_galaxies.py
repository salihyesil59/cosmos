"""Lesson figures for L5.8 (galaxy formation)."""

from __future__ import annotations

import numpy as np

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics import galaxies


@figure("stellar_halo_relation")
def _stellar_halo_relation(fig, p: Palette):
    """The fraction of each halo's mass that ended up in stars."""
    ax = fig.add_subplot()
    m = np.logspace(9.5, 15.5, 300)
    ax.loglog(m, galaxies.stellar_fraction(m), color=p.series[0], linewidth=2.4,
              label="stars / halo mass (Moster et al. 2013)")
    ax.axhline(galaxies.BARYON_FRACTION, color=p.series[1], linestyle="--", linewidth=1.4,
               label=f"all the baryons: Ωb/Ωm = {galaxies.BARYON_FRACTION:.2f}")
    peak = galaxies.peak_halo_mass()
    ax.axvline(peak, color=p.muted, linestyle=":", linewidth=1)
    ax.text(peak, 2.4e-4, "  the Milky Way's halo", color=p.muted, fontsize=7.5)
    ax.text(10**10.0, 1.5e-3, "supernovae\nblow the gas out", color=p.series[3], fontsize=8, ha="center")
    ax.text(10**14.6, 1.5e-3, "black holes\nkeep it hot", color=p.series[3], fontsize=8, ha="center")
    ax.set_ylim(1.5e-4, 0.4)
    ax.set_xlabel("halo mass (M☉)")
    ax.set_ylabel("stellar mass / halo mass")
    ax.set_title("Galaxy formation is inefficient everywhere, and least inefficient at 10¹² M☉", fontsize=9)
    ax.legend(fontsize=7.5, loc="upper right")
