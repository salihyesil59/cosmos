"""S15 — Inflation Slow-Roll Simulator."""

from __future__ import annotations

import numpy as np
from matplotlib.patches import Rectangle
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.physics import inflation


class InflationSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.frame = 0
        self._markers = []
        self.result = None
        self.trajectory = None

        model = QGroupBox("1 · The inflaton potential")
        ml = QVBoxLayout(model)
        self.potential = QComboBox()
        for key, pot in inflation.POTENTIALS.items():
            self.potential.addItem(pot.label, key)
            self.potential.setItemData(self.potential.count() - 1, pot.description, Qt.ToolTipRole)
        self.potential.setCurrentIndex(list(inflation.POTENTIALS).index("starobinsky"))
        ml.addWidget(labelled_row("Model", self.potential, (
            "Inflation models",
            "Each model is a different shape for the energy of the inflaton field. The field rolls slowly down "
            "the potential; the shape decides how the universe expands and which fluctuations are created.")))
        self.description = muted_label("")
        ml.addWidget(self.description)
        self.parameter = ParameterSlider("Parameter", 1.0, 40.0, 7.0, decimals=1, step=0.5)
        ml.addWidget(self.parameter)
        self.n_star = ParameterSlider(
            "N*  e-folds before the end", 40, 70, 55, decimals=0, step=1,
            info=("N*", "When the scales we observe in the CMB left the horizon, measured in e-folds before "
                  "inflation ended. It depends on how the universe reheated; 50–60 is typical."),
        )
        ml.addWidget(self.n_star)
        self.controls.addWidget(model)

        run = QGroupBox("2 · Watch the field roll")
        rl = QVBoxLayout(run)
        row = QHBoxLayout()
        self.play = QPushButton("▶ Play")
        self.play.setCheckable(True)
        self.play.setProperty("role", "primary")
        self.play.toggled.connect(self._toggle)
        rewind = QPushButton("Rewind")
        rewind.clicked.connect(self._rewind)
        row.addWidget(self.play)
        row.addWidget(rewind)
        rl.addLayout(row)
        self.controls.addWidget(run)

        results = QGroupBox("Predictions")
        vl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        vl.addWidget(self.summary)
        self.controls.addWidget(results)
        self.finish_controls()

        self.verdict = Banner("info")
        self.display.addWidget(self.verdict)
        self.plot = PlotWidget(self._draw, export_name="inflation", csv_provider=self._csv)
        self.display.addWidget(self.plot, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self.potential.currentIndexChanged.connect(self._potential_changed)
        self.parameter.valueChanged.connect(self.schedule_update)
        self.n_star.valueChanged.connect(self.schedule_update)
        self._potential_changed()

    # ------------------------------------------------------------ model
    def pot(self) -> inflation.Potential:
        return inflation.POTENTIALS[self.potential.currentData()]

    def _potential_changed(self) -> None:
        pot = self.pot()
        self.description.setText(pot.description)
        has_parameter = bool(pot.parameter_label)
        self.parameter.setVisible(has_parameter)
        if has_parameter:
            lo, hi = pot.parameter_range
            self.parameter.label.setText(pot.parameter_label)
            self.parameter.set_range(lo, hi)
            self.parameter.setValue(pot.parameter_default, emit=False)
        self.recompute()

    def recompute(self) -> None:
        pot = self.pot()
        param = self.parameter.value() if pot.parameter_label else None
        try:
            self.result = inflation.predictions(pot, self.n_star.value(), param)
            self.trajectory = inflation.evolve(pot, param, n_before=max(65.0, self.n_star.value() + 8), extra=2.5)
        except ValueError:
            self.verdict.set_message("warning", "This parameter value does not give enough inflation. Try another.")
            return
        r = self.result
        ok = r.consistent
        self.verdict.set_message(
            "success" if ok else "danger",
            ("<b>Consistent with observations.</b> " if ok else "<b>Ruled out by observations.</b> ")
            + f"Planck measures nₛ = {inflation.N_S_MEASURED} ± {inflation.N_S_ERROR}; "
            f"BICEP/Keck limit r < {inflation.R_UPPER_LIMIT}.",
        )
        self.summary.setText(
            f"Spectral index nₛ: <b>{r.n_s:.4f}</b><br>"
            f"Tensor-to-scalar ratio r: <b>{r.r:.4f}</b><br>"
            f"Slow-roll ε = {r.epsilon:.2e}, η = {r.eta:.2e}<br>"
            f"Field when CMB scales left: φ* = {r.phi_star:.2f} M_Pl<br>"
            f"Field at the end: {r.phi_end:.2f} M_Pl<br>"
            f"Energy scale V*¼: <b>{r.energy_scale_gev:.2e} GeV</b><br>"
            f"Hubble rate during inflation: {r.hubble_gev:.2e} GeV<br>"
            f"Full solution: inflation lasted {self.trajectory.end_efold:.1f} e-folds from the start of the run"
        )
        self.frame = len(self.trajectory.efolds) - 1 if not self.play.isChecked() else self.frame
        self.plot.refresh()

    # ---------------------------------------------------------- animation
    def _toggle(self, on: bool) -> None:
        self.play.setText("⏸ Pause" if on else "▶ Play")
        if on:
            if self.frame >= len(self.trajectory.efolds) - 1:
                self.frame = 0
            self.timer.start()
        else:
            self.timer.stop()

    def _rewind(self) -> None:
        self.frame = 0
        self._update_markers()

    def _tick(self) -> None:
        n = len(self.trajectory.efolds)
        step = max(1, n // 250)
        self.frame = min(self.frame + step, n - 1)
        self._update_markers()
        if self.frame >= n - 1:
            self.play.setChecked(False)

    def on_hidden(self) -> None:
        self.play.setChecked(False)

    def _update_markers(self) -> None:
        if not self._markers or self.trajectory is None:
            return
        tr = self.trajectory
        i = self.frame
        pot = self.pot()
        param = self.parameter.value() if pot.parameter_label else pot.parameter_default
        ball, efold_marker = self._markers
        ball.set_data([tr.phi[i]], [float(pot.v(tr.phi[i], param))])
        efold_marker.set_data([tr.efolds[i]], [max(tr.epsilon_h[i], 1e-8)])
        self.plot.canvas.draw_idle()

    # ---------------------------------------------------------------- draw
    def _draw(self, fig) -> None:
        p = theme().palette
        if self.result is None:
            return
        pot = self.pot()
        param = self.parameter.value() if pot.parameter_label else pot.parameter_default
        r, tr = self.result, self.trajectory
        grid = fig.add_gridspec(2, 2)

        ax = fig.add_subplot(grid[0, 0])
        lo = min(tr.phi.min(), r.phi_end) - 0.5
        hi = max(tr.phi.max(), r.phi_star) + 0.5
        if pot.key in ("natural", "hilltop"):
            lo, hi = 0.0, max(tr.phi.max(), r.phi_end) * 1.05
        phi = np.linspace(lo, hi, 500)
        v = pot.v(phi, param)
        ax.plot(phi, v, color=p.series[0], linewidth=2.2)
        slow = inflation.epsilon(pot, phi, param) < 1
        ax.fill_between(phi, 0, np.where(slow, v, np.nan), color=p.series[0], alpha=0.12, linewidth=0,
                        label="slow roll (ε < 1)")
        ax.axvline(r.phi_star, color=p.accent2, linestyle="--", linewidth=1)
        ax.axvline(r.phi_end, color=p.danger, linestyle=":", linewidth=1)
        ball, = ax.plot([tr.phi[self.frame]], [float(pot.v(tr.phi[self.frame], param))], "o", color=p.accent2,
                        markersize=10, zorder=5)
        ax.set_xlabel("Inflaton field φ (M_Pl)", fontsize=8)
        ax.set_ylabel("V(φ) (arbitrary units)", fontsize=8)
        ax.set_title("Potential: φ* dashed, end dotted", fontsize=8)
        ax.legend(loc="best", fontsize=7)

        ax = fig.add_subplot(grid[0, 1])
        ax.add_patch(Rectangle((inflation.N_S_MEASURED - 2 * inflation.N_S_ERROR, 0),
                               4 * inflation.N_S_ERROR, inflation.R_UPPER_LIMIT,
                               color=p.success, alpha=0.2, linewidth=0, label="allowed (approx. 95%)"))
        for i, (key, other) in enumerate(inflation.POTENTIALS.items()):
            pts = []
            for n in (50, 55, 60):
                try:
                    res = inflation.predictions(other, n)
                    pts.append((res.n_s, max(res.r, 1e-4)))
                except ValueError:
                    pass
            if pts:
                xs, ys = zip(*pts)
                ax.plot(xs, ys, "-o", color=p.series[i % 6], markersize=3, linewidth=1.2, label=other.label.split("  ")[0])
        ax.scatter([r.n_s], [max(r.r, 1e-4)], color=p.text, marker="*", s=120, zorder=5, label="your model")
        ax.set_yscale("log")
        ax.set_xlim(0.93, 0.99)
        ax.set_ylim(1e-4, 1.0)
        ax.set_xlabel("Spectral index nₛ", fontsize=8)
        ax.set_ylabel("Tensor-to-scalar ratio r", fontsize=8)
        ax.set_title("nₛ and r for N* = 50–60", fontsize=8)
        ax.legend(loc="upper left", bbox_to_anchor=(0.0, 0.82), fontsize=5.5, framealpha=0.55)

        ax = fig.add_subplot(grid[1, 0])
        ax.semilogy(tr.efolds, np.maximum(tr.epsilon_h, 1e-8), color=p.series[1], linewidth=1.8)
        ax.axhline(1, color=p.danger, linestyle=":", linewidth=1)
        ax.axvline(tr.end_efold, color=p.danger, linestyle=":", linewidth=1)
        marker, = ax.plot([tr.efolds[self.frame]], [max(tr.epsilon_h[self.frame], 1e-8)], "o", color=p.accent2)
        ax.set_xlabel("e-folds of expansion N = ln a", fontsize=8)
        ax.set_ylabel("ε_H = −Ḣ/H²", fontsize=8)
        ax.set_title("Inflation lasts while ε_H < 1", fontsize=8)

        ax = fig.add_subplot(grid[1, 1])
        x, y, i_end = inflation.comoving_hubble_radius_history(n_inflation=max(self.trajectory.end_efold, 1))
        ax.plot(x[:i_end], y[:i_end], color=p.series[0], linewidth=2, label="inflation")
        ax.plot(x[i_end:], y[i_end:], color=p.series[2], linewidth=2, label="after inflation")
        ax.axhline(0, color=p.accent2, linestyle="--", linewidth=1, label="observable universe today")
        ax.set_xlabel("log₁₀ scale factor a", fontsize=8)
        ax.set_ylabel("log₁₀ comoving Hubble radius", fontsize=8)
        ax.set_title("Comoving Hubble radius", fontsize=8)
        ax.legend(loc="lower left", fontsize=6)
        for axis in fig.axes:
            axis.tick_params(labelsize=7)
        self._markers = [ball, marker]

    def _csv(self):
        tr = self.trajectory
        rows = [[f"{n:.4f}", f"{f:.6g}", f"{h:.6g}", f"{e:.6g}"]
                for n, f, h, e in zip(tr.efolds, tr.phi, tr.hubble, tr.epsilon_h)]
        return ["efolds", "phi_MPl", "H_MPl", "epsilon_H"], rows
