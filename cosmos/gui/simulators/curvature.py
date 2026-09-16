"""S8 — Curvature Visualizer."""

from __future__ import annotations

import math

import numpy as np
from matplotlib.patches import Circle
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGroupBox, QLabel, QTabWidget, QVBoxLayout

from cosmos.gui.labels import physics
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import ParameterSlider, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import geometry
from cosmos.physics.presets import PRESETS

PARTICLE_HORIZON_GPC = PRESETS["planck18"].cosmology.particle_horizon() / 1e3


class CurvatureSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)

        shapes = QGroupBox(tr("1 · Shapes drawn in space"))
        sl = QVBoxLayout(shapes)
        self.side = ParameterSlider(
            tr("Triangle side (curvature radii)"), 0.05, 2.0, 1.0, decimals=2, step=0.05,
            info=(tr("Triangle size"), tr("Side length of an equilateral triangle, measured in units of the radius of "
                      "curvature R. Small triangles look flat in every geometry; large ones reveal the curvature.")),
        )
        self.radius = ParameterSlider(
            tr("Circle radius (curvature radii)"), 0.05, 3.0, 1.0, decimals=2, step=0.05,
            info=(tr("Circle radius"), tr("Distance from the centre to the circle, measured along the curved space.")),
        )
        sl.addWidget(self.side)
        sl.addWidget(self.radius)
        self.controls.addWidget(shapes)

        universe = QGroupBox(tr("2 · Our universe"))
        ul = QVBoxLayout(universe)
        self.omega_k = ParameterSlider(
            tr("Ωk  curvature parameter"), -0.1, 0.1, -0.01, decimals=3, step=0.001,
            info=(tr("Curvature parameter"), tr("Ωk < 0 closed (spherical), Ωk > 0 open (hyperbolic). Measurements give "
                      "|Ωk| < 0.002.")),
        )
        self.distance = ParameterSlider(
            tr("Distance to a ruler (curvature radii)"), 0.1, 3.0, 1.0, decimals=2, step=0.05,
            info=(tr("Ruler distance"), tr("How far away a ruler of fixed length is. Its apparent angle depends on the "
                      "geometry, which is how the CMB measures curvature.")),
        )
        ul.addWidget(self.omega_k)
        ul.addWidget(self.distance)
        self.controls.addWidget(universe)

        results = QGroupBox(tr("Measurements"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("Closed space behaves like the surface of a sphere, open space like a "
                            "saddle. The hyperbolic triangle is drawn in the Poincaré disk: straight "
                            "lines of that space appear as circular arcs.")))
        self.controls.addWidget(results)
        self.finish_controls()

        tabs = QTabWidget()
        self.triangles = PlotWidget(self._draw_triangles, export_name="curved_triangles")
        self.circles = PlotWidget(self._draw_circles, export_name="curved_circles")
        self.sizes = PlotWidget(self._draw_sizes, export_name="angular_size_geometry")
        tabs.addTab(self.triangles, tr("Triangles"))
        tabs.addTab(self.circles, tr("Circles"))
        tabs.addTab(self.sizes, tr("Apparent sizes"))
        self.display.addWidget(tabs, 1)

        for w in (self.side, self.radius, self.omega_k, self.distance):
            w.valueChanged.connect(self.schedule_update)
        self.recompute()

    # ------------------------------------------------------------ compute
    def recompute(self) -> None:
        a = self.side.value()
        r = self.radius.value()
        sums = {k: math.degrees(geometry.angle_sum(a, k)) for k in (1, 0, -1)}
        ratios = {k: float(geometry.circumference(r, k)) / (2 * math.pi * r) for k in (1, 0, -1)}
        ok = self.omega_k.value()
        radius_gpc = geometry.curvature_radius_mpc(ok, PRESETS["planck18"].cosmology.H0) / 1e3
        k_universe = 0 if abs(ok) < 1e-9 else (-1 if ok > 0 else 1)
        if math.isinf(radius_gpc):
            universe = "Space is exactly flat: the curvature radius is infinite."
        else:
            span = PARTICLE_HORIZON_GPC / radius_gpc
            try:
                excess = math.degrees(geometry.angle_sum(min(span, 2.0), k_universe)) - 180
                excess_text = f"{excess:+.2f}°"
            except ValueError:
                excess_text = tr("undefined (too large)")
            universe = (
                tr("Curvature radius: <b>{radius} Gpc</b> ({geometry})<br>"
                   "Observable universe radius: {horizon} Gpc = <b>{span} R</b><br>"
                   "Angle excess of a triangle with sides that long: <b>{excess}</b>")
                .format(radius=f"{radius_gpc:.0f}", geometry=physics(geometry.GEOMETRIES[k_universe]),
                        horizon=f"{PARTICLE_HORIZON_GPC:.1f}", span=f"{span:.2f}", excess=excess_text)
            )
        self.summary.setText(
            tr("<b>Triangle angle sums</b> (side {side} R)<br>"
               "Closed: <b>{closed}°</b> · Flat: <b>{flat}°</b> · Open: <b>{open_}°</b><br><br>"
               "<b>Circumference ÷ 2πr</b> (radius {radius} R)<br>"
               "Closed: <b>{closed_ratio}</b> · Flat: <b>1.000</b> · Open: <b>{open_ratio}</b><br><br>")
            .format(side=f"{a:.2f}", closed=f"{sums[1]:.1f}", flat=f"{sums[0]:.1f}", open_=f"{sums[-1]:.1f}",
                    radius=f"{r:.2f}", closed_ratio=f"{ratios[1]:.3f}", open_ratio=f"{ratios[-1]:.3f}")
            + universe
        )
        for plot in (self.triangles, self.circles, self.sizes):
            plot.refresh()

    # --------------------------------------------------------------- plots
    def _draw_triangles(self, fig) -> None:
        p = theme().palette
        a = self.side.value()
        # Closed: a triangle on a sphere of unit radius.
        grid = fig.add_gridspec(2, 2, width_ratios=[1.5, 1])
        ax = fig.add_subplot(grid[:, 0], projection="3d")
        u, v = np.mgrid[0:2 * np.pi:40j, 0:np.pi:20j]
        ax.plot_wireframe(np.cos(u) * np.sin(v), np.sin(u) * np.sin(v), np.cos(v), color=p.border, linewidth=0.4)
        verts = geometry.spherical_triangle(a)
        for i in range(3):
            arc = geometry.sphere_geodesic(verts[i], verts[(i + 1) % 3])
            ax.plot(arc[:, 0], arc[:, 1], arc[:, 2], color=p.series[3], linewidth=2.4)
        ax.view_init(elev=60, azim=30)
        ax.set_box_aspect((1, 1, 1), zoom=1.25)
        ax.set_axis_off()
        ax.set_title(f"Closed: {math.degrees(geometry.angle_sum(a, 1)):.1f}°", color=p.text, fontsize=10)

        # Flat.
        ax = fig.add_subplot(grid[0, 1])
        tri = np.array([[math.cos(t), math.sin(t)] for t in np.radians([90, 210, 330, 90])]) * a / math.sqrt(3)
        ax.plot(tri[:, 0], tri[:, 1], color=p.series[2], linewidth=2.4)
        ax.set_aspect("equal")
        lim = 1.25 * max(a / math.sqrt(3), 0.2)
        ax.set_xlim(-lim, lim)
        ax.set_ylim(-lim, lim)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title("Flat: 180.0°", color=p.text, fontsize=10)

        # Open: Poincaré disk.
        ax = fig.add_subplot(grid[1, 1])
        ax.add_patch(Circle((0, 0), 1, fill=False, color=p.border, linewidth=1))
        for edge in geometry.poincare_triangle(a):
            ax.plot(edge[:, 0], edge[:, 1], color=p.series[0], linewidth=2.4)
        ax.set_aspect("equal")
        ax.set_xlim(-1.05, 1.05)
        ax.set_ylim(-1.05, 1.05)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_title(f"Open: {math.degrees(geometry.angle_sum(a, -1)):.1f}°", color=p.text, fontsize=10)

    def _draw_circles(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        r = np.linspace(0.01, 3.0, 300)
        for k, color, label in [(1, p.series[3], "Closed"), (0, p.series[2], "Flat"), (-1, p.series[0], "Open")]:
            ax.plot(r, geometry.circumference(r, k) / (2 * np.pi), color=color, linewidth=2.2, label=label)
        ax.axvline(self.radius.value(), color=p.muted, linestyle="--")
        ax.axvline(np.pi, color=p.border, linestyle=":")
        ax.text(np.pi * 1.01, 0.3, "circle shrinks to a point:\nthe antipode of a sphere", fontsize=8, color=p.muted)
        ax.set_ylim(0, 4)
        ax.set_xlabel("Circle radius r (curvature radii)")
        ax.set_ylabel("Circumference ÷ 2π (curvature radii)")
        ax.legend(loc="upper left", fontsize=8)

    def _draw_sizes(self, fig) -> None:
        p = theme().palette
        ax = fig.add_subplot()
        d = np.linspace(0.05, 3.0, 400)
        ruler = 0.05
        for k, color, label in [(1, p.series[3], "Closed"), (0, p.series[2], "Flat"), (-1, p.series[0], "Open")]:
            ax.semilogy(d, np.degrees(geometry.angular_size(ruler, d, k)), color=color, linewidth=2.2, label=label)
        ax.axvline(self.distance.value(), color=p.muted, linestyle="--")
        ax.set_ylim(0.1, 60)
        ax.set_xlabel("Distance to the ruler (curvature radii)")
        ax.set_ylabel("Apparent angle (degrees)")
        ax.set_title("A ruler of fixed length: bigger on the sky in closed space, smaller in open space", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
