"""Illustrative figures embedded in lessons via ``{{figure:name}}``.

Each figure is drawn from the physics engine, so the numbers shown in lessons
always agree with the simulators.
"""

from __future__ import annotations

import functools
import io

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from matplotlib.ticker import NullFormatter

from cosmos.gui.theme import Palette, style_axes, style_legend
from cosmos.physics import constants as const
from cosmos.physics import datasets, hubble, rotation
from cosmos.physics.presets import PRESETS

FIGURE_WIDTH_PX = 640
FIGURE_HEIGHT_PX = 340

_REGISTRY = {}


def figure(name):
    def register(func):
        _REGISTRY[name] = func
        return func

    return register


def available() -> list[str]:
    return sorted(_REGISTRY)


@functools.lru_cache(maxsize=64)
def render_png(name: str, palette: Palette, device_ratio: float = 1.0) -> bytes:
    if name not in _REGISTRY:
        raise KeyError(f"unknown figure {name!r}")
    dpi = 100 * device_ratio
    fig = Figure(figsize=(FIGURE_WIDTH_PX / 100, FIGURE_HEIGHT_PX / 100), dpi=dpi)
    fig.patch.set_facecolor(palette.surface)
    FigureCanvasAgg(fig)
    _REGISTRY[name](fig, palette)
    for ax in fig.axes:
        style_axes(ax, palette)
        if ax.get_legend():
            style_legend(ax.get_legend(), palette)
    if fig.get_layout_engine() is None:
        fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", facecolor=palette.surface)
    return buf.getvalue()


# ---------------------------------------------------------------- figures
@figure("scales_ladder")
def _scales(fig, p: Palette):
    ax = fig.add_subplot()
    items = [
        ("Human", 1.7),
        ("Earth", 1.2742e7),
        ("Sun", 1.3927e9),
        ("Earth's orbit", 2 * const.AU),
        ("Nearest star (distance)", 4.24 * const.LIGHT_YEAR),
        ("Milky Way", 1.0e5 * const.LIGHT_YEAR),
        ("Andromeda (distance)", 2.5e6 * const.LIGHT_YEAR),
        ("Laniakea supercluster", 5.2e8 * const.LIGHT_YEAR),
        ("Observable universe", 9.3e10 * const.LIGHT_YEAR),
    ]
    names = [n for n, _ in items]
    sizes = np.log10([s for _, s in items])
    colors = [p.series[i % 6] for i in range(len(items))]
    ax.barh(range(len(items)), sizes, color=colors, height=0.6)
    ax.set_yticks(range(len(items)), names)
    ax.invert_yaxis()
    ax.set_xlabel("Size in metres (powers of ten: 10^x)")
    ax.set_xlim(0, 28)
    for i, s in enumerate(sizes):
        ax.text(s + 0.3, i, f"$10^{{{s:.0f}}}$ m", va="center", color=p.text, fontsize=8)


@figure("hubble_1929")
def _hubble_1929(fig, p: Palette):
    ax = fig.add_subplot()
    data = datasets.load_hubble_1929()
    fit = hubble.fit_through_origin(data.distance_mpc, data.velocity_km_s)
    ax.scatter(data.distance_mpc, data.velocity_km_s, color=p.series[0], zorder=3, label="Hubble's galaxies (1929)")
    d = np.linspace(0, 2.2, 10)
    ax.plot(d, fit.H0 * d, color=p.series[1], label=f"Best fit: v = {fit.H0:.0f} km/s/Mpc × d")
    ax.axhline(0, color=p.muted, linewidth=0.8)
    ax.set_xlabel("Distance (Mpc, Hubble's estimates)")
    ax.set_ylabel("Recession velocity (km/s)")
    ax.legend(loc="upper left")


@figure("scale_factor_models")
def _scale_factor_models(fig, p: Palette):
    ax = fig.add_subplot()
    for i, key in enumerate(["planck18", "eds", "open_matter", "closed_matter"]):
        cosmo = PRESETS[key].cosmology.with_params(H0=70.0)
        hist = cosmo.expansion_history(t_future=30)
        ax.plot(hist.t, hist.a, color=p.series[i], label=PRESETS[key].label, linewidth=2)
    ax.axvline(0, color=p.muted, linestyle="--", linewidth=1)
    ax.text(0.3, 2.3, "today", color=p.muted, fontsize=8)
    ax.set_xlim(-16, 30)
    ax.set_ylim(0, 2.6)
    ax.set_xlabel("Time from today (Gyr)")
    ax.set_ylabel("Scale factor a(t)")
    ax.legend(loc="upper left")


@figure("density_evolution")
def _density_evolution(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    a = np.logspace(-6, 1, 400)
    ax.loglog(a, c.Or0 * a**-4, color=p.series[3], linewidth=2, label="Radiation  ∝ a⁻⁴")
    ax.loglog(a, c.Om0 * a**-3, color=p.series[0], linewidth=2, label="Matter  ∝ a⁻³")
    ax.loglog(a, c.Ode0 * np.ones_like(a), color=p.series[2], linewidth=2, label="Dark energy (Λ)  constant")
    a_eq = c.Or0 / c.Om0
    a_de = (c.Om0 / c.Ode0) ** (1 / 3)
    for x, label in [(a_eq, "matter–radiation\nequality"), (a_de, "matter–Λ\nequality"), (1.0, "today")]:
        ax.axvline(x, color=p.muted, linestyle=":", linewidth=1)
        ax.text(x * 1.15, 1e14, label, color=p.muted, fontsize=7, va="top")
    ax.set_ylim(1e-3, 1e18)
    ax.set_xlabel("Scale factor a")
    ax.set_ylabel("Density ÷ today's critical density")
    ax.legend(loc="lower left")


@figure("rotation_curves")
def _rotation_curves(fig, p: Palette):
    ax = fig.add_subplot()
    r = np.linspace(0.3, 30, 300)
    disk = rotation.disk_velocity(r, 5e10, 3.0)
    bulge = rotation.bulge_velocity(r, 1e10, 0.5)
    halo = rotation.nfw_velocity(r, 1e12, 10.0)
    visible = rotation.total_velocity(disk, bulge)
    obs = datasets.illustrative_rotation_data()
    ax.errorbar(obs.radius_kpc, obs.velocity_km_s, yerr=obs.error_km_s, fmt="o", color=p.text,
                markersize=4, label="Measured (illustrative)")
    ax.plot(r, visible, color=p.series[1], linewidth=2, label="Expected from visible matter")
    ax.plot(r, rotation.total_velocity(visible, halo), color=p.series[0], linewidth=2, label="Visible + dark matter halo")
    ax.set_xlabel("Distance from galactic centre (kpc)")
    ax.set_ylabel("Orbital speed (km/s)")
    ax.set_ylim(0, 300)
    ax.legend(loc="lower right")


@figure("energy_budget")
def _energy_budget(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    dm = c.Om0 - c.Ob0
    values = [c.Ode0, dm, c.Ob0]
    labels = [f"Dark energy\n{c.Ode0:.1%}", f"Dark matter\n{dm:.1%}", f"Ordinary matter\n{c.Ob0:.1%}"]
    wedges, texts = ax.pie(values, labels=labels, colors=[p.series[2], p.series[0], p.series[1]],
                           startangle=90, wedgeprops=dict(edgecolor=p.surface, linewidth=2))
    for t in texts:
        t.set_color(p.text)
    ax.set_title("Energy content of the universe today (Planck 2018)")
    ax.axis("equal")


@figure("cmb_blackbody")
def _cmb_blackbody(fig, p: Palette):
    ax = fig.add_subplot()
    freq_ghz = np.linspace(1, 700, 600)
    nu = freq_ghz * 1e9
    t = const.T_CMB
    intensity = 2 * const.H_PLANCK * nu**3 / const.C**2 / np.expm1(const.H_PLANCK * nu / (const.K_B * t))
    mjy = intensity / 1e-20  # 1 MJy/sr = 1e-20 W m^-2 Hz^-1 sr^-1
    ax.plot(freq_ghz, mjy, color=p.series[0], linewidth=2, label=f"Blackbody spectrum, T = {t} K")
    peak = freq_ghz[np.argmax(mjy)]
    ax.axvline(peak, color=p.muted, linestyle=":", linewidth=1)
    ax.text(peak + 8, mjy.max() * 0.5, f"peak ≈ {peak:.0f} GHz\n(λ ≈ 1–2 mm, microwaves)", color=p.muted, fontsize=8)
    ax.set_title("COBE/FIRAS measured this shape with deviations below 0.005%", fontsize=9)
    ax.set_xlabel("Frequency (GHz)")
    ax.set_ylabel("Intensity (MJy/sr)")
    ax.legend(loc="upper right")


@figure("temperature_history")
def _temperature_history(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    z = np.logspace(-2, 10, 160)
    age_years = c.age(z) * 1e9
    temp = c.Tcmb(z)
    ax.loglog(age_years, temp, color=p.series[0], linewidth=2)
    labelled = [
        (c.age(3.6e8) * 1e9, c.Tcmb(3.6e8), "Nucleosynthesis (~1–20 min)"),
        (c.age(3400) * 1e9, c.Tcmb(3400), "Matter–radiation equality"),
        (c.age(1090) * 1e9, c.Tcmb(1090), "Recombination / CMB released"),
        (c.age(0) * 1e9, c.Tcmb(0), "Today (2.7 K)"),
    ]
    for x, y, text in labelled:
        ax.scatter([x], [y], color=p.series[1], zorder=3, s=22)
        ax.annotate(text, (x, y), textcoords="offset points", xytext=(8, 6), color=p.text, fontsize=8)
    ax.set_xlabel("Age of the universe (years)")
    ax.set_ylabel("Temperature of radiation (K)")
    ax.set_xlim(1e-6, 1e11)


@figure("distance_ladder")
def _distance_ladder(fig, p: Palette):
    ax = fig.add_subplot()
    rungs = [
        ("Radar ranging", 1e-11, 1e-8),
        ("Parallax (Gaia)", 1e-6, 1e-2),
        ("Main-sequence fitting", 1e-4, 0.1),
        ("Cepheid variables", 1e-3, 40),
        ("Tip of the red giant branch", 1e-2, 30),
        ("Type Ia supernovae", 5, 3000),
        ("Hubble–Lemaître law (redshift)", 50, 30000),
    ]
    for i, (name, lo, hi) in enumerate(rungs):
        ax.barh(i, np.log10(hi) - np.log10(lo), left=np.log10(lo), color=p.series[i % 6], height=0.55)
        ax.text(np.log10(hi) + 0.15, i, name, va="center", color=p.text, fontsize=8)
    ax.set_yticks([])
    ax.invert_yaxis()
    ax.set_xlim(-11.5, 7.5)
    ticks = [-10, -8, -6, -4, -2, 0, 2, 4]
    ax.set_xticks(ticks, [f"$10^{{{t}}}$" for t in ticks])
    ax.set_xlabel("Distance (Mpc)")


@figure("discovery_timeline")
def _discovery_timeline(fig, p: Palette):
    early = [
        (1543, "Copernicus:\nSun at the centre"),
        (1610, "Galileo's\ntelescope"),
        (1687, "Newton's\ngravity"),
        (1785, "Herschel maps\nthe Milky Way"),
        (1823, "Olbers'\nparadox"),
    ]
    modern = [
        (1915, "General\nrelativity"),
        (1924, "Andromeda is\na galaxy"),
        (1929, "Hubble–Lemaître\nlaw"),
        (1948, "Big Bang vs.\nsteady state"),
        (1965, "CMB\ndiscovered"),
        (1992, "COBE sees\nCMB ripples"),
        (1998, "Accelerating\nexpansion"),
        (2018, "Planck final\nresults"),
    ]
    fig.set_layout_engine("constrained")
    grid = fig.add_gridspec(1, 2, width_ratios=[1, 1.6])
    for idx, (events, lo, hi) in enumerate([(early, 1520, 1850), (modern, 1905, 2030)]):
        ax = fig.add_subplot(grid[idx])
        ax.axhline(0, color=p.muted, linewidth=1.5)
        for i, (year, label) in enumerate(events):
            height = [1.0, -1.0, 2.0, -2.0][i % 4]
            color = p.series[i % 6]
            ax.plot([year, year], [0, height * 0.8], color=color, linewidth=1)
            ax.scatter([year], [0], color=color, zorder=3, s=22)
            ax.text(year, height * 0.85, f"{year}\n{label}", ha="center", va="bottom" if height > 0 else "top",
                    fontsize=7, color=p.text)
        ax.set_xlim(lo, hi)
        ax.set_ylim(-3.2, 3.2)
        ax.set_yticks([])
        ax.grid(False)
        if idx == 1:
            ax.spines["left"].set_linestyle((0, (3, 3)))
    fig.suptitle("Milestones of cosmology (note the change of time scale)", fontsize=9, color=p.text)


@figure("olbers_sky_coverage")
def _olbers_sky_coverage(fig, p: Palette):
    ax = fig.add_subplot()
    # A static universe with 10^9 Sun-like stars per cubic megaparsec.
    n_stars = 1e9 / const.MPC**3
    sigma = np.pi * 6.96e8**2
    mean_free_path = 1 / (n_stars * sigma) / const.LIGHT_YEAR
    r = np.logspace(6, 26, 400)
    covered = -np.expm1(-r / mean_free_path)
    ax.loglog(r, covered, color=p.series[0], linewidth=2.2, label="Fraction of the sky covered by stars")
    horizon = 13.8e9
    ax.axvline(horizon, color=p.accent2, linestyle="--", linewidth=1.2)
    ax.text(horizon * 1.4, 1e-18, "light-travel limit\n(13.8 billion ly)", color=p.accent2, fontsize=8)
    ax.axvline(mean_free_path, color=p.danger, linestyle=":", linewidth=1.2)
    ax.text(mean_free_path * 1.5, 1e-6, "sky fully\ncovered\n(~10²⁴ ly)", color=p.danger, fontsize=8)
    ax.set_xlabel("How far we can look (light-years)")
    ax.set_ylabel("Fraction of sky covered")
    ax.set_ylim(1e-20, 3)
    ax.legend(loc="lower right", fontsize=8)


@figure("cosmic_web_illustration")
def _cosmic_web(fig, p: Palette):
    from scipy.spatial import Voronoi

    rng = np.random.default_rng(42)
    seeds = np.column_stack([rng.uniform(-0.2, 2.0, 110), rng.uniform(-0.2, 1.2, 110)])
    vor = Voronoi(seeds)
    points = []
    for a, b in vor.ridge_vertices:
        if a < 0 or b < 0:
            continue
        va, vb = vor.vertices[a], vor.vertices[b]
        length = np.linalg.norm(vb - va)
        k = int(260 * length) + 1
        t = rng.uniform(0, 1, k)
        pts = va + np.outer(t, vb - va) + rng.normal(0, 0.009, (k, 2))
        points.append(pts)
    for v in vor.vertices:
        points.append(v + rng.normal(0, 0.012, (18, 2)))
    points.append(rng.uniform(0, 1, (200, 2)) * [1.8, 1.0])
    pts = np.vstack(points)
    inside = (pts[:, 0] > 0) & (pts[:, 0] < 1.8) & (pts[:, 1] > 0) & (pts[:, 1] < 1)
    pts = pts[inside]
    ax = fig.add_subplot()
    ax.scatter(pts[:, 0], pts[:, 1], s=1.2, color=p.series[0], alpha=0.75, linewidths=0)
    ax.set_xlim(0, 1.8)
    ax.set_ylim(0, 1)
    ax.set_aspect("equal")
    ax.set_axis_off()
    ax.set_title("Illustration (not real data): galaxies trace filaments and clusters around empty voids",
                 fontsize=8, color=p.text)


_MPC_TO_GLY = const.MPC / const.LIGHT_YEAR / 1e9


@figure("horizons_spacetime")
def _horizons_spacetime(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    a, t, chi = c.conformal_history(a_max=8.0, n=4000)
    t0 = float(c.age(0))
    chi0 = c.particle_horizon()
    chi_inf = chi0 + c.event_horizon()
    to_gly = _MPC_TO_GLY
    hubble = c.hubble_distance / np.sqrt(c.E2_of_a(a)) * to_gly
    particle = a * chi * to_gly
    event = a * (chi_inf - chi) * to_gly
    past = t <= t0
    cone = a[past] * (chi0 - chi[past]) * to_gly
    ax.fill_between(t[past], 0, cone, color=p.accent2, alpha=0.12, linewidth=0)
    ax.plot(t[past], cone, color=p.accent2, linewidth=2.2, label="Our past light cone")
    ax.plot(t, hubble, color=p.series[2], linewidth=1.8, linestyle="--", label="Hubble sphere (v = c)")
    ax.plot(t, event, color=p.danger, linewidth=1.8, label="Event horizon")
    ax.plot(t, particle, color=p.series[0], linewidth=2, label="Particle horizon (observable universe)")
    ax.axvline(t0, color=p.muted, linestyle=":", linewidth=1)
    ax.annotate("today", (t0, 30), textcoords="offset points", xytext=(4, 0), color=p.muted, fontsize=8)
    ax.set_xlim(0, 40)
    ax.set_ylim(0, 70)
    ax.set_xlabel("Time since the Big Bang (billion years)")
    ax.set_ylabel("Proper distance from us (billion ly)")
    ax.legend(loc="upper right", fontsize=8)


@figure("distance_measures")
def _distance_measures(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    z = np.logspace(-2, np.log10(20), 200)
    to_gly = _MPC_TO_GLY
    ax.loglog(z, c.luminosity_distance(z) * to_gly, color=p.series[1], linewidth=2, label="Luminosity distance")
    ax.loglog(z, c.comoving_distance(z) * to_gly, color=p.series[0], linewidth=2, label="Comoving distance")
    ax.loglog(z, c.light_travel_distance(z) * to_gly, color=p.series[4], linewidth=2, label="Light-travel distance")
    ax.loglog(z, c.angular_diameter_distance(z) * to_gly, color=p.series[2], linewidth=2,
              label="Angular diameter distance")
    ax.loglog(z, z * c.hubble_distance * to_gly, color=p.muted, linestyle=":", label="Hubble's law  d = cz/H₀")
    ax.set_ylim(0.1, 500)
    ax.set_xlabel("Redshift z")
    ax.set_ylabel("Distance (billion light-years)")
    ax.legend(loc="upper left", fontsize=8)


@figure("angular_size")
def _angular_size(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    z = np.logspace(-1.3, 1.3, 200)
    size_kpc = 30.0
    arcsec = size_kpc / c.kpc_per_arcsec(z)
    euclid = size_kpc / (z * c.hubble_distance * 1e3) * 648000 / np.pi
    ax.loglog(z, arcsec, color=p.series[0], linewidth=2.2, label="Expanding universe (Planck 2018)")
    ax.loglog(z, euclid, color=p.muted, linestyle=":", label="Static Euclidean space with d = cz/H₀")
    z_peak, _ = c.angular_diameter_distance_peak()
    ax.scatter([z_peak], [size_kpc / c.kpc_per_arcsec(z_peak)], color=p.accent2, zorder=3)
    ax.annotate(f"smallest at z ≈ {z_peak:.1f}", (z_peak, size_kpc / c.kpc_per_arcsec(z_peak)),
                textcoords="offset points", xytext=(-20, -22), color=p.accent2, fontsize=8)
    ax.set_xlabel("Redshift z")
    ax.set_ylabel("Angular size (arcseconds)")
    ax.set_title("Apparent size of a galaxy 30 kpc across", fontsize=9)
    ax.set_ylim(0.5, 100)
    ax.legend(loc="upper right", fontsize=8)


@figure("age_integrand")
def _age_integrand(fig, p: Palette):
    ax = fig.add_subplot()
    c = PRESETS["planck18"].cosmology
    a = np.linspace(1e-4, 1.0, 600)
    integrand = 1.0 / np.sqrt(a * a * c.E2_of_a(a)) * c.hubble_time
    ax.fill_between(a, 0, integrand, color=p.series[0], alpha=0.25, linewidth=0)
    ax.plot(a, integrand, color=p.series[0], linewidth=2.2, label="1 / (a H)  — time spent per unit growth of a")
    eds = PRESETS["eds"].cosmology.with_params(H0=c.H0)
    ax.plot(a, 1.0 / np.sqrt(a * a * eds.E2_of_a(a)) * eds.hubble_time, color=p.series[1], linestyle="--",
            linewidth=1.6, label="Einstein–de Sitter (matter only)")
    ax.text(0.5, 3.5, f"shaded area = age\n≈ {c.age():.1f} billion years", color=p.text, fontsize=9, ha="center")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 30)
    ax.set_xlabel("Scale factor a  (Big Bang → today)")
    ax.set_ylabel("dt/da (billion years)")
    ax.legend(loc="upper right", fontsize=8)


@figure("age_vs_matter")
def _age_vs_matter(fig, p: Palette):
    from cosmos.physics.cosmology import Cosmology

    ax = fig.add_subplot()
    h0 = PRESETS["planck18"].cosmology.H0
    om = np.linspace(0.05, 1.5, 60)
    flat = [Cosmology(H0=h0, Om0=m, Ode0=1 - m, Tcmb0=0).age() for m in om]
    open_ = [Cosmology(H0=h0, Om0=m, Ode0=0.0, Tcmb0=0).age() for m in om]
    ax.axhspan(12.0, 13.5, color=p.accent2, alpha=0.15, linewidth=0)
    ax.text(1.02, 12.25, "ages of the oldest stars", color=p.accent2, fontsize=8)
    ax.plot(om, flat, color=p.series[0], linewidth=2.2, label="Flat, with dark energy (ΩΛ = 1 − Ωm)")
    ax.plot(om, open_, color=p.series[3], linewidth=2.2, label="No dark energy (ΩΛ = 0)")
    ax.scatter([0.31], [PRESETS["planck18"].cosmology.age()], color=p.accent2, zorder=4, marker="*", s=120,
               label="Our universe (Planck 2018)")
    ax.set_xlabel("Matter density Ωm")
    ax.set_ylabel("Age of the universe (billion years)")
    ax.set_title(f"H0 = {h0:.1f} km/s/Mpc", fontsize=9)
    ax.set_ylim(6, 26)
    ax.legend(loc="upper right", fontsize=8)


@figure("neutrino_decoupling")
def _neutrino_decoupling(fig, p: Palette):
    from cosmos.physics import thermal

    fig.set_layout_engine("constrained")
    ax1, ax2 = fig.subplots(1, 2)
    t = np.logspace(-1.5, 1.5, 200)
    ax1.loglog(t, thermal.weak_rate_over_hubble(t), color=p.series[0], linewidth=2.2)
    ax1.axhline(1, color=p.muted, linestyle=":")
    t_dec = thermal.neutrino_decoupling_temperature()
    ax1.axvline(t_dec, color=p.accent2, linestyle="--", linewidth=1)
    ax1.text(t_dec * 1.15, 1e-3, f"decoupling\n≈ {t_dec:.1f} MeV", color=p.accent2, fontsize=8)
    ax1.text(4, 3e2, "coupled", color=p.text, fontsize=8)
    ax1.text(0.05, 3e-3, "free\nstreaming", color=p.text, fontsize=8)
    ax1.set_xlabel("Temperature (MeV)  → cooling")
    ax1.set_ylabel("Weak rate Γ ÷ expansion rate H")
    ax1.invert_xaxis()
    ax1.set_title("Neutrinos decouple", fontsize=9)

    t2 = np.logspace(1, -2, 80)
    ax2.semilogx(t2, thermal.neutrino_to_photon_temperature(t2), color=p.series[2], linewidth=2.2)
    ax2.axhline(thermal.RELIC_NEUTRINO_RATIO, color=p.muted, linestyle=":")
    ax2.text(8, thermal.RELIC_NEUTRINO_RATIO + 0.01, "(4/11)^(1/3) ≈ 0.714", color=p.muted, fontsize=8)
    ax2.axvline(thermal.M_ELECTRON_MEV, color=p.accent2, linestyle="--", linewidth=1)
    ax2.text(thermal.M_ELECTRON_MEV * 1.2, 0.80, "mₑc²", color=p.accent2, fontsize=8, ha="right")
    ax2.set_xlabel("Photon temperature (MeV)  → cooling")
    ax2.set_ylabel("T_ν / T_γ")
    ax2.set_ylim(0.68, 1.03)
    ax2.invert_xaxis()
    ax2.set_title("e⁺e⁻ annihilation heats photons", fontsize=9)


@figure("baryon_asymmetry")
def _baryon_asymmetry(fig, p: Palette):
    from cosmos.physics import thermal

    ax = fig.add_subplot()
    t = np.logspace(np.log10(12), np.log10(200), 300)
    eq = thermal.nucleon_equilibrium_ratio(t)
    eta = 6.1e-10
    ax.loglog(t, eq, color=p.series[0], linewidth=2.2, label="Nucleons per photon in thermal equilibrium")
    ax.axhline(eta, color=p.accent2, linewidth=2, label="Observed baryon excess η ≈ 6 × 10⁻¹⁰")
    ax.axhline(1e-18, color=p.danger, linestyle="--", linewidth=1.5,
               label="Leftover if matter and antimatter were equal (≈ 10⁻¹⁸)")
    ax.set_xlabel("Temperature (MeV)   → the universe cools")
    ax.set_ylabel("Number per photon")
    ax.set_ylim(1e-22, 1)
    ax.set_xticks([200, 100, 50, 20], ["200", "100", "50", "20"])
    ax.xaxis.set_minor_formatter(NullFormatter())
    ax.invert_xaxis()
    ax.legend(loc="lower left", fontsize=8)
