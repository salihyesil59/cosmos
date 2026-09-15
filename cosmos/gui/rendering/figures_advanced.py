"""Lesson figures for Level 6: advanced topics."""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Rectangle

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics import constants as const
from cosmos.physics.presets import PRESETS

MPC_TO_GLY = const.MPC / const.LIGHT_YEAR / 1e9


@figure("conformal_diagram")
def _conformal_diagram(fig, p: Palette):
    c = PRESETS["planck18"].cosmology
    a, _t, chi = c.conformal_history(a_max=6.0, n=3000)
    g = MPC_TO_GLY
    eta = chi * g
    chi0 = c.particle_horizon() * g
    chi_inf = chi0 + c.event_horizon() * g
    ax = fig.add_subplot()
    for comoving in (10, 20, 30, 40, 50):
        for sign in (1, -1):
            ax.axvline(sign * comoving, color=p.border, linewidth=0.7)
    past = eta <= chi0
    ax.fill_between([-chi0, 0, chi0], [0, chi0, 0], color=p.accent2, alpha=0.15, linewidth=0)
    ax.plot([-chi0, 0, chi0], [0, chi0, 0], color=p.accent2, linewidth=2.2, label="Our past light cone")
    ax.plot(chi[past] * g, eta[past], color=p.series[0], linewidth=1.8, label="Particle horizon")
    ax.plot(-chi[past] * g, eta[past], color=p.series[0], linewidth=1.8)
    ax.plot([-(chi_inf - chi0), 0, chi_inf - chi0], [chi_inf, chi0, chi_inf], color=p.danger, linewidth=1.8,
            label="Future light cone (reaches the event horizon)")
    ax.axhline(chi0, color=p.muted, linestyle=":", linewidth=1)
    ax.text(-55, chi0 + 1, "today", color=p.muted, fontsize=8)
    ax.axhline(chi_inf, color=p.danger, linestyle="--", linewidth=1)
    ax.text(-55, chi_inf + 1, "conformal time runs out (ΛCDM)", color=p.danger, fontsize=8)
    ax.set_xlim(-60, 60)
    ax.set_ylim(0, chi_inf + 6)
    ax.set_xlabel("Comoving distance (billion light-years)")
    ax.set_ylabel("Conformal time × c (billion ly)")
    ax.set_title("In comoving coordinates with conformal time, light travels at 45° and galaxies stand still",
                 fontsize=9)
    ax.legend(loc="upper right", fontsize=7)


@figure("equation_of_state_dilution")
def _equation_of_state_dilution(fig, p: Palette):
    ax = fig.add_subplot()
    a = np.logspace(-2, 1, 200)
    cases = [(1 / 3, "radiation  w = 1/3"), (0.0, "matter  w = 0"), (-1 / 3, "curvature-like  w = −1/3"),
             (-1.0, "cosmological constant  w = −1"), (-1.3, "phantom  w = −1.3")]
    for i, (w, label) in enumerate(cases):
        ax.loglog(a, a ** (-3 * (1 + w)), color=p.series[i % 6], linewidth=2, label=label)
    ax.axvline(1, color=p.muted, linestyle=":")
    ax.set_xlabel("Scale factor a (a = 1 today)")
    ax.set_ylabel("Energy density ÷ today's value")
    ax.set_title("ρ ∝ a^(−3(1+w)) follows from the fluid equation of general relativity", fontsize=9)
    ax.legend(loc="lower left", fontsize=8)


@figure("inflation_hubble_radius")
def _inflation_hubble_radius(fig, p: Palette):
    from cosmos.physics import inflation

    x, y, i_end = inflation.comoving_hubble_radius_history(n_inflation=62)
    ax = fig.add_subplot()
    ax.plot(x[:i_end], y[:i_end], color=p.series[0], linewidth=2.2, label="during inflation (shrinks)")
    ax.plot(x[i_end:], y[i_end:], color=p.series[2], linewidth=2.2, label="after inflation (grows)")
    scale = 0.0
    ax.axhline(scale, color=p.accent2, linestyle="--", linewidth=1.4, label="size of today's observable universe")
    crossings = np.nonzero(np.diff(np.sign(y - scale)))[0]
    for i in crossings[:2]:
        ax.scatter([x[i]], [scale], color=p.accent2, zorder=5)
    if crossings.size >= 2:
        ax.annotate("our observable universe\nleaves the horizon", (x[crossings[0]], scale),
                    textcoords="offset points", xytext=(8, -32), color=p.text, fontsize=8)
        ax.annotate("and re-enters it today", (x[crossings[1]], scale), textcoords="offset points",
                    xytext=(-120, -22), color=p.text, fontsize=8)
    ax.set_xlabel("log₁₀ scale factor a")
    ax.set_ylabel("log₁₀ comoving Hubble radius (today = 0)")
    ax.set_title("Inflation lets regions that look causally disconnected today share a common past", fontsize=9)
    ax.legend(loc="lower left", fontsize=8)


@figure("ns_r_plane")
def _ns_r_plane(fig, p: Palette):
    from cosmos.physics import inflation

    ax = fig.add_subplot()
    ax.add_patch(Rectangle((inflation.N_S_MEASURED - 2 * inflation.N_S_ERROR, 1e-4), 4 * inflation.N_S_ERROR,
                           inflation.R_UPPER_LIMIT - 1e-4, color=p.success, alpha=0.22, linewidth=0,
                           label="allowed by Planck + BICEP/Keck (approx.)"))
    for i, (key, pot) in enumerate(inflation.POTENTIALS.items()):
        pts = [inflation.predictions(pot, n) for n in (50, 55, 60)]
        ax.plot([r.n_s for r in pts], [max(r.r, 1e-4) for r in pts], "-o", color=p.series[i % 6], markersize=4,
                linewidth=1.5, label=pot.label.split("  ")[0])
    ax.set_yscale("log")
    ax.set_xlim(0.935, 0.985)
    ax.set_ylim(1e-3, 0.6)
    ax.set_xlabel("Spectral index nₛ")
    ax.set_ylabel("Tensor-to-scalar ratio r")
    ax.set_title("Predictions for 50–60 e-folds", fontsize=9)
    ax.legend(loc="upper left", fontsize=7)


@figure("reionization_history")
def _reionization_history(fig, p: Palette):
    from cosmos.physics import reionization as re

    c = PRESETS["planck18"].cosmology
    z = np.linspace(0, 20, 400)
    ax = fig.add_subplot()
    for z_re, color in [(6.0, p.series[2]), (7.7, p.series[0]), (10.0, p.series[3])]:
        tau = re.optical_depth(c, z_re)
        ax.plot(z, re.ionized_fraction(z, z_re), color=color, linewidth=2,
                label=f"midpoint z = {z_re:g}  →  τ = {tau:.3f}")
    ax.axvspan(0, 3.5, color=p.border, alpha=0.3, linewidth=0)
    ax.text(0.3, 1.14, "helium fully\nionised", color=p.muted, fontsize=7)
    ax.set_xlim(0, 20)
    ax.set_ylim(0, 1.25)
    ax.set_xlabel("Redshift z")
    ax.set_ylabel("Free electrons per hydrogen atom")
    ax.set_title("Reionisation histories and their CMB optical depth (Planck: τ = 0.054 ± 0.007)", fontsize=9)
    ax.legend(loc="upper right", fontsize=8)


@figure("global_21cm")
def _global_21cm(fig, p: Palette):
    from cosmos.physics import reionization as re

    c = PRESETS["planck18"].cosmology
    z = np.logspace(np.log10(5), np.log10(250), 600)
    tb = re.global_21cm_signal(c, z)
    nu = re.frequency_mhz(z)
    ax = fig.add_subplot()
    ax.plot(nu, tb, color=p.series[0], linewidth=2.2)
    ax.axhline(0, color=p.muted, linewidth=0.8)
    ax.set_xscale("log")
    ax.set_xlim(nu.min(), nu.max())
    labels = [(80, "dark ages\n(collisions)"), (18, "cosmic dawn\n(first stars)"), (10, "X-ray heating"),
              (7, "reionisation")]
    for zz, text in labels:
        ax.annotate(text, (re.frequency_mhz(zz), float(np.interp(zz, z, tb))), textcoords="offset points",
                    xytext=(0, -30 if zz > 15 else 12), ha="center", color=p.text, fontsize=7)
    ax.set_xlabel("Observed frequency (MHz)   ← earlier · later →")
    ax.set_ylabel("21-cm brightness δT_b (mK)")
    ax.set_ylim(-230, 60)
    ax.set_title("Schematic sky-averaged 21-cm signal (teaching model, not a measurement)", fontsize=9)
    top = ax.secondary_xaxis("top", functions=(lambda f: 1420.4 / np.maximum(f, 1e-3) - 1,
                                               lambda zz: 1420.4 / (1 + np.maximum(zz, -0.99))))
    top.set_xticks([200, 100, 50, 30, 20, 15, 10, 7])
    top.set_xticklabels(["200", "100", "50", "30", "20", "15", "10", "7"])
    top.set_xlabel("Redshift", color=p.muted, fontsize=8)
    top.tick_params(colors=p.muted, labelsize=7)


@figure("gw_chirp")
def _gw_chirp(fig, p: Palette):
    from cosmos.physics import gravitational_waves as gw

    fig.set_layout_engine("constrained")
    ax1, ax2 = fig.subplots(2, 1, sharex=True, height_ratios=[1.4, 1])
    t, h, f = gw.chirp_waveform(28.0, 440.0, duration_s=0.3)
    ax1.plot(t, h * 1e21, color=p.series[0], linewidth=1.2)
    ax1.set_ylabel("Strain h (×10⁻²¹)", fontsize=8)
    ax1.set_title("Inspiral of two 32 M☉ black holes 440 Mpc away (like GW150914)", fontsize=9)
    ax2.semilogy(t, f, color=p.series[1], linewidth=2)
    ax2.set_ylabel("Frequency (Hz)", fontsize=8)
    ax2.set_xlabel("Time before merger (s)", fontsize=8)
    for axis in (ax1, ax2):
        axis.tick_params(labelsize=7)


@figure("h0_measurements")
def _h0_measurements(fig, p: Palette):
    ax = fig.add_subplot()
    rows = [
        ("Planck CMB (2018)", 67.4, 0.5, 0.5, "early"),
        ("ACT CMB (2020)", 67.9, 1.5, 1.5, "early"),
        ("GW170817 siren (2017)", 70.0, 8.0, 12.0, "other"),
        ("CCHP red giants (2019)", 69.8, 1.9, 1.9, "late"),
        ("H0LiCOW lensing (2019)", 73.3, 1.8, 1.7, "late"),
        ("SH0ES Cepheids (2022)", 73.04, 1.04, 1.04, "late"),
    ]
    colors = {"early": p.series[0], "late": p.series[1], "other": p.series[2]}
    for i, (label, value, lo, hi, kind) in enumerate(rows):
        ax.errorbar([value], [i], xerr=[[lo], [hi]], fmt="o", color=colors[kind], capsize=3, markersize=6)
        ax.text(value, i + 0.28, f"{value:g}", ha="center", color=p.text, fontsize=7)
    ax.axvspan(66.9, 67.9, color=p.series[0], alpha=0.12, linewidth=0)
    ax.axvspan(72.0, 74.08, color=p.series[1], alpha=0.12, linewidth=0)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xlim(60, 84)
    ax.set_xlabel("H0 (km/s/Mpc)")
    ax.set_title("Early universe (blue) vs local (orange)", fontsize=9)


@figure("s8_measurements")
def _s8_measurements(fig, p: Palette):
    ax = fig.add_subplot()
    rows = [
        ("Planck CMB (2018)", 0.832, 0.013, 0.013, p.series[0]),
        ("KiDS-1000 (2021)", 0.766, 0.014, 0.020, p.series[1]),
        ("DES Year 3 (2022)", 0.776, 0.017, 0.017, p.series[1]),
    ]
    for i, (label, value, lo, hi, color) in enumerate(rows):
        ax.errorbar([value], [i], xerr=[[lo], [hi]], fmt="o", color=color, capsize=3, markersize=6)
    ax.set_yticks(range(len(rows)), [r[0] for r in rows])
    ax.set_xlim(0.7, 0.88)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_xlabel("S8 = σ8 √(Ωm / 0.3)")
    ax.set_title("Clustering today (lensing surveys, orange) vs the CMB prediction (blue)", fontsize=9)


@figure("mond_vs_dark_matter")
def _mond_vs_dark_matter(fig, p: Palette):
    from cosmos.physics import datasets, rotation

    ax = fig.add_subplot()
    r = np.linspace(0.3, 30, 300)
    visible = rotation.total_velocity(rotation.disk_velocity(r, 5e10, 3.0), rotation.bulge_velocity(r, 1e10, 0.5))
    halo = rotation.nfw_velocity(r, 1e12, 10.0)
    data = datasets.illustrative_rotation_data()
    ax.errorbar(data.radius_kpc, data.velocity_km_s, yerr=data.error_km_s, fmt="o", color=p.text, markersize=4,
                label="Measured-style data (illustrative)")
    ax.plot(r, visible, color=p.series[3], linewidth=2, label="Newton, visible matter only")
    ax.plot(r, rotation.total_velocity(visible, halo), color=p.series[0], linewidth=2, label="Newton + dark matter halo")
    ax.plot(r, rotation.mond_velocity(r, visible), color=p.series[5], linewidth=2, linestyle="--",
            label="MOND, visible matter only")
    ax.set_ylim(0, 300)
    ax.set_xlabel("Distance from the centre (kpc)")
    ax.set_ylabel("Orbital speed (km/s)")
    ax.legend(loc="lower right", fontsize=8)


@figure("dark_energy_models")
def _dark_energy_models(fig, p: Palette):
    from cosmos.physics.cosmology import Cosmology

    fig.set_layout_engine("constrained")
    ax1, ax2 = fig.subplots(1, 2)
    z = np.linspace(0, 3, 200)
    a = 1 / (1 + z)
    base = Cosmology.flat(H0=67.7, Om0=0.31, Tcmb0=0)
    models = [
        ("Cosmological constant", -1.0, 0.0, p.series[0]),
        ("Thawing quintessence (w0 = −0.9, wa = −0.1)", -0.9, -0.1, p.series[2]),
        ("DESI-like (w0 = −0.75, wa = −0.9)", -0.75, -0.9, p.series[1]),
        ("Phantom (w = −1.2)", -1.2, 0.0, p.series[3]),
    ]
    for label, w0, wa, color in models:
        c = Cosmology.flat(H0=67.7, Om0=0.31, Tcmb0=0, w0=w0, wa=wa)
        ax1.plot(z, c.w_of_a(a), color=color, linewidth=2, label=label)
        ax2.plot(z, c.efunc(z) / base.efunc(z), color=color, linewidth=2)
    ax1.axhline(-1, color=p.muted, linewidth=0.8)
    ax1.set_xlabel("Redshift z", fontsize=8)
    ax1.set_ylabel("Equation of state w(z)", fontsize=8)
    ax1.legend(loc="lower left", fontsize=6)
    ax2.axhline(1, color=p.muted, linewidth=0.8)
    ax2.set_xlabel("Redshift z", fontsize=8)
    ax2.set_ylabel("H(z) ÷ H(z) for Λ", fontsize=8)
    for axis in (ax1, ax2):
        axis.tick_params(labelsize=7)


@figure("possible_fates")
def _possible_fates(fig, p: Palette):
    from cosmos.physics.cosmology import Cosmology

    ax = fig.add_subplot()
    models = [
        ("Cosmological constant: eternal acceleration", Cosmology.flat(H0=70, Om0=0.3, Tcmb0=0), p.series[0]),
        ("Phantom w = −1.5: Big Rip", Cosmology.flat(H0=70, Om0=0.3, Tcmb0=0, w0=-1.5), p.series[3]),
        ("Negative Λ (ΩΛ = −0.3): Big Crunch", Cosmology(H0=70, Om0=0.3, Ode0=-0.3, Tcmb0=0), p.series[1]),
        ("Dark energy fading away (w0 = −0.75, wa = −0.9)",
         Cosmology.flat(H0=70, Om0=0.3, Tcmb0=0, w0=-0.75, wa=-0.9), p.series[2]),
    ]
    for label, c, color in models:
        hist = c.expansion_history(t_future=60, a_max=12)
        ax.plot(hist.t, hist.a, color=color, linewidth=2, label=label)
    ax.axvline(0, color=p.muted, linestyle=":")
    ax.text(0.5, 0.3, "today", color=p.muted, fontsize=8)
    ax.set_xlim(-14, 60)
    ax.set_ylim(0, 10)
    ax.set_xlabel("Time from today (billion years)")
    ax.set_ylabel("Scale factor a")
    ax.legend(loc="upper left", fontsize=8)
