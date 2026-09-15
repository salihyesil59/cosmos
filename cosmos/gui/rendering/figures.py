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
