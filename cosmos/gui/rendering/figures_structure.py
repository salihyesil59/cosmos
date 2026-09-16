"""Lesson figures for Level 5: the CMB and the growth of cosmic structure."""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Circle

from cosmos.gui.rendering.figures import figure
from cosmos.gui.theme import Palette
from cosmos.physics.presets import PRESETS


@figure("cmb_power_spectrum")
def _cmb_power_spectrum(fig, p: Palette):
    from cosmos.physics import cmb

    ax = fig.add_subplot()
    spec = cmb.spectrum()
    ax.plot(spec.ell, spec.d_ell, color=p.series[0], linewidth=2.2)
    ax.set_xscale("log")
    ax.set_xlim(2, 2500)
    ax.set_ylim(0, 7200)
    for i, (ell, d) in enumerate(spec.peaks[:3]):
        offset = [(0, 6), (-26, 22), (22, 22)][i]
        ax.annotate(f"peak {i + 1}\nℓ ≈ {ell:.0f}", (ell, d), textcoords="offset points", xytext=offset,
                    ha="center", color=p.text, fontsize=8,
                    arrowprops=dict(arrowstyle="-", color=p.muted, linewidth=0.6) if i else None)
    ax.axvspan(2, 40, color=p.series[2], alpha=0.10, linewidth=0)
    ax.text(9, 6300, "Sachs–Wolfe\nplateau", color=p.series[2], fontsize=8, ha="center")
    ax.axvspan(1300, 2500, color=p.series[3], alpha=0.10, linewidth=0)
    ax.text(1800, 6300, "damping\ntail", color=p.series[3], fontsize=8, ha="center")
    ax.set_xlabel("Multipole ℓ   (angular size ≈ 180° / ℓ)")
    ax.set_ylabel("ℓ(ℓ+1)Cℓ / 2π  (μK²)")
    ax.set_title("CMB temperature power spectrum (teaching model, Planck 2018 parameters)", fontsize=9)


@figure("cmb_sky_patch")
def _cmb_sky_patch(fig, p: Palette):
    from cosmos.physics import cmb

    fig.set_layout_engine("constrained")
    spec = cmb.spectrum()
    patch = cmb.sky_patch(spec, size_deg=20, n=256, seed=3)
    ax = fig.add_subplot()
    im = ax.imshow(patch, cmap="RdBu_r", extent=(0, 20, 0, 20), vmin=-300, vmax=300, origin="lower")
    ax.set_xlabel("degrees")
    ax.set_ylabel("degrees")
    ax.set_title("A simulated 20° × 20° patch of the CMB (not real data)", fontsize=9)
    ax.grid(False)
    bar = fig.colorbar(im, ax=ax, shrink=0.9)
    bar.set_label("ΔT (μK)", color=p.text)
    bar.ax.tick_params(colors=p.muted)


@figure("acoustic_oscillator")
def _acoustic_oscillator(fig, p: Palette):
    ax = fig.add_subplot()
    x = np.linspace(0, 4 * np.pi, 500)
    for r, color, label in [(0.0, p.series[2], "no baryons (R = 0)"), (0.6, p.series[1], "with baryons (R ≈ 0.6)")]:
        ax.plot(x / np.pi, -(1 / 3 + r) * np.cos(x) + r, color=color, linewidth=2.2, label=label)
    ax.axhline(0, color=p.muted, linewidth=0.8)
    for n in (1, 2, 3):
        ax.axvline(n, color=p.border, linestyle=":")
        ax.text(n, 1.62, "compression" if n % 2 else "rarefaction", ha="center", fontsize=8, color=p.text)
    ax.set_xlabel("Phase of the sound wave at decoupling  (k rₛ / π)")
    ax.set_ylabel("Effective temperature  Θ₀ + Ψ")
    ax.set_ylim(-1.1, 1.8)
    ax.legend(loc="lower right", fontsize=8)


@figure("bao_correlation")
def _bao_correlation(fig, p: Palette):
    from cosmos.physics import structure

    c = PRESETS["planck18"].cosmology
    pk = structure.LinearPowerSpectrum(c)
    r = np.linspace(20, 180, 161)
    xi = pk.correlation_function(r)
    ax = fig.add_subplot()
    ax.plot(r, r * r * xi, color=p.series[0], linewidth=2.2, label="Correlation function (linear theory)")
    rd = structure.drag_sound_horizon(c) * c.h
    ax.axvline(rd, color=p.accent2, linestyle="--", linewidth=1.2)
    top = float(np.max(r * r * xi))
    ax.text(rd + 4, top * 0.75, f"sound horizon\nr_d ≈ {rd:.0f} Mpc/h\n(≈ {rd / c.h:.0f} Mpc)",
            color=p.accent2, fontsize=8)
    ax.set_xlabel("Separation between galaxies r  (Mpc/h)")
    ax.set_ylabel("r² ξ(r)  (Mpc/h)²")
    ax.legend(loc="lower left", fontsize=8)


@figure("bao_wiggles")
def _bao_wiggles(fig, p: Palette):
    from cosmos.physics import structure

    c = PRESETS["planck18"].cosmology
    k = np.logspace(-2.3, -0.3, 500)
    ratio = structure.transfer_eisenstein_hu(c, k) ** 2 / structure.transfer_no_wiggle(c, k) ** 2
    ax = fig.add_subplot()
    ax.semilogx(k, ratio, color=p.series[1], linewidth=2.2)
    ax.axhline(1, color=p.muted, linewidth=0.8)
    ax.set_xlabel("Wavenumber k  (h/Mpc)")
    ax.set_ylabel("P(k) ÷ smooth P(k)")
    ax.set_title("Baryon acoustic oscillations in the matter power spectrum (Eisenstein & Hu 1998)", fontsize=9)


@figure("growth_factor")
def _growth_factor(fig, p: Palette):
    from cosmos.physics import structure
    from cosmos.physics.cosmology import Cosmology

    ax = fig.add_subplot()
    a = np.logspace(-2, 0, 120)
    models = [
        (PRESETS["eds"].cosmology, "Einstein–de Sitter:  D = a", p.series[1], "--"),
        (PRESETS["planck18"].cosmology, "ΛCDM (Planck 2018)", p.series[0], "-"),
        (Cosmology(H0=67.7, Om0=0.3, Ode0=0.0, Tcmb0=0), "Open, matter only (Ωm = 0.3)", p.series[3], "-."),
    ]
    for c, label, color, style in models:
        ax.loglog(a, structure.growth_factor(c, a, normalize=False), color=color, linestyle=style, linewidth=2,
                  label=label)
    ax.set_xlabel("Scale factor a")
    ax.set_ylabel("Growth factor D(a)")
    ax.set_title("Density contrasts grow as δ ∝ D until dark energy or curvature take over", fontsize=9)
    ax.legend(loc="upper left", fontsize=8)


@figure("matter_power_spectrum")
def _matter_power_spectrum(fig, p: Palette):
    from cosmos.physics import structure

    c = PRESETS["planck18"].cosmology
    pk = structure.LinearPowerSpectrum(c)
    k = np.logspace(-3.5, 0.5, 500)
    ax = fig.add_subplot()
    for z, color in [(0, p.series[0]), (2, p.series[2]), (6, p.series[4])]:
        ax.loglog(k, pk(k, z=z), color=color, linewidth=2, label=f"z = {z}")
    k_eq = 0.0746 * c.Om0 * c.h
    ax.axvline(k_eq, color=p.accent2, linestyle="--", linewidth=1)
    ax.text(k_eq * 1.2, 15, "matter–radiation\nequality scale", color=p.accent2, fontsize=8)
    ax.set_ylim(5, 1e5)
    ax.set_xlabel("Wavenumber k  (h/Mpc)   ← large scales · small scales →")
    ax.set_ylabel("P(k)  (Mpc/h)³")
    ax.legend(loc="lower left", fontsize=8)


@figure("halo_mass_function")
def _halo_mass_function(fig, p: Palette):
    from cosmos.physics import structure

    c = PRESETS["planck18"].cosmology
    pk = structure.LinearPowerSpectrum(c)
    m = np.logspace(9, 16, 60)
    dlnm = np.log(m[1] / m[0])
    ax = fig.add_subplot()
    for z, color in [(0, p.series[0]), (2, p.series[2]), (4, p.series[1]), (8, p.series[3])]:
        dn = pk.press_schechter(m, z=z)
        cumulative = np.cumsum((dn * dlnm)[::-1])[::-1]
        ax.loglog(m, cumulative, color=color, linewidth=2, label=f"z = {z}")
    ax.set_ylim(1e-9, 1e2)
    ax.set_xlabel("Halo mass M  (M☉/h)")
    ax.set_ylabel("Halos heavier than M per (Mpc/h)³")
    ax.set_title("Press–Schechter: small halos form first, massive clusters only recently", fontsize=9)
    ax.legend(loc="lower left", fontsize=8)


@figure("nbody_snapshots")
def _nbody_snapshots(fig, p: Palette):
    from cosmos.physics.nbody import NBodyConfig, NBodySimulation

    fig.set_layout_engine("constrained")
    sim = NBodySimulation(NBodyConfig(particles_per_side=128, grid=128, seed=7))
    axes = fig.subplots(1, 3)
    for ax, target in zip(axes, (0.15, 0.8, 2.5)):
        sim.run_to(target)
        ax.imshow(sim.density_image().T, cmap="magma", origin="lower", vmin=0, vmax=1, interpolation="bilinear")
        ax.set_title(f"growth factor D = {target:g}", fontsize=9, color=p.text)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
    fig.suptitle("2D toy simulation: ripples become filaments, then halos merge (not real data)",
                 fontsize=9, color=p.text)


@figure("lensing_images")
def _lensing_images(fig, p: Palette):
    from cosmos.physics import lensing

    fig.set_layout_engine("constrained")
    n, field = 220, 8.0
    coords = (np.arange(n) + 0.5) / n * field - field / 2
    tx, ty = np.meshgrid(coords, coords)
    cases = [
        ("Source offset: two images", [("point", 0.0, 0.0, 1.2)], 0.7, 0.3),
        ("Perfect alignment: Einstein ring", [("point", 0.0, 0.0, 1.2)], 0.0, 0.0),
        ("Cluster: stretched arcs",
         [("sis", 0.0, 0.0, 1.4), ("sis", 1.2, 0.6, 0.6), ("sis", -1.0, -0.8, 0.5)], 0.3, 0.2),
    ]
    axes = fig.subplots(1, 3)
    for ax, (title, lenses, sx, sy) in zip(axes, cases):
        dx, dy = lensing.deflection(tx, ty, lenses)
        img = lensing.source_galaxy(tx - dx, ty - dy, sx, sy, size=0.25)
        ax.imshow(img, cmap="inferno", origin="lower", extent=(-4, 4, -4, 4))
        _kind, x0, y0, te = lenses[0]
        ax.add_patch(Circle((x0, y0), te, fill=False, color=p.series[0], linestyle=":", linewidth=0.8))
        ax.set_title(title, fontsize=8, color=p.text)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)


@figure("bbn_abundances")
def _bbn_abundances(fig, p: Palette):
    from cosmos.physics import bbn

    eta = np.logspace(np.log10(0.8), np.log10(15), 300)
    ab = bbn.abundances(eta)
    planck = float(bbn.eta10_from_omega_b_h2(bbn.PLANCK_OMEGA_B_H2[0]))
    top, middle, bottom = fig.subplots(3, 1, sharex=True, gridspec_kw={"height_ratios": [1, 1.4, 1]})
    rows = [(top, [("Yp", ab.yp, p.series[0], "⁴He mass fraction Yₚ")]),
            (middle, [("D/H", ab.d_h, p.series[1], "D/H"), ("He3/H", ab.he3_h, p.series[4], "³He/H")]),
            (bottom, [("Li7/H", ab.li7_h, p.series[3], "⁷Li/H")])]
    for ax, series in rows:
        for key, values, colour, label in series:
            obs, err = bbn.OBSERVED[key]
            ax.plot(eta, values, color=colour, linewidth=2, label=label)
            ax.axhspan(obs - err, obs + err, color=colour, alpha=0.3, linewidth=0)
        ax.axvspan(planck - 0.1, planck + 0.1, color=p.success, alpha=0.35, linewidth=0)
        ax.set_xscale("log")
        ax.legend(loc="best", fontsize=7)
    top.set_ylim(0.21, 0.27)
    top.set_title("Light elements from the first minutes (bands: observed; green: CMB baryon density)", fontsize=9)
    middle.set_yscale("log")
    middle.set_ylim(3e-6, 3e-4)
    bottom.set_yscale("log")
    bottom.set_ylim(8e-11, 2e-9)
    bottom.set_xlabel("η₁₀ = baryons per 10¹⁰ photons")
