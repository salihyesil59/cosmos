"""S19 — Likelihood & MCMC Explorer."""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout

from cosmos.gui.simulators.base import SimulatorBase
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import Banner, ParameterSlider, labelled_row, muted_label
from cosmos.gui.widgets.plot import PlotWidget
from cosmos.i18n import tr
from cosmos.physics import inference as inf
from cosmos.physics import supernovae as sn

CHAINS_FOR_RHAT = 4


class MCMCSimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        self.sample = sn.pantheon_sample()
        self.chain: inf.Chain | None = None
        self.chains: list[inf.Chain] = []
        self.frame = 0
        self.grid = None

        data = QGroupBox(tr("1 · The data"))
        dl = QVBoxLayout(data)
        self.sample_box = QComboBox()
        for key, factory in sn.SAMPLES.items():
            self.sample_box.addItem(factory().label, key)
        self.sample_box.setCurrentIndex(self.sample_box.findData("pantheon"))
        dl.addWidget(labelled_row(tr("Sample"), self.sample_box, (
            tr("What the likelihood sees"),
            tr("Every supernova contributes one term to χ². The real Pantheon+ sample is the default; the "
                "simulated ones let you see what fewer or noisier measurements would give."))))
        self.flat = QCheckBox(tr("Assume a flat universe (ΩΛ = 1 − Ωm)"))
        self.flat.setToolTip(tr("One parameter instead of two. The chain then explores a line, not a plane."))
        dl.addWidget(self.flat)
        self.controls.addWidget(data)

        walk = QGroupBox(tr("2 · The chain"))
        wl = QVBoxLayout(walk)
        self.steps = ParameterSlider(
            tr("Steps"), 500, 20000, 4000, decimals=0, log=True,
            info=(tr("Length of the chain"),
                  tr("Each step proposes a new universe and accepts or rejects it. More steps mean a smoother "
                      "posterior, but the useful number is the effective sample size, not the raw count.")),
        )
        self.step_size = ParameterSlider(
            tr("Proposal step σ"), 0.005, 0.5, 0.08, decimals=3, log=True,
            info=(tr("How far each proposal jumps"),
                  tr("Too small and the walker crawls, accepting almost everything but exploring nothing. Too "
                      "large and almost every proposal is rejected. An acceptance rate around 0.25 is healthy.")),
        )
        self.burn_in = ParameterSlider(
            tr("Burn-in (fraction)"), 0.0, 0.5, 0.2, decimals=2, step=0.05,
            info=(tr("Throwing away the start"),
                  tr("The walker begins wherever you put it, not in the good region. The first steps are "
                      "discarded so they do not bias the answer.")),
        )
        self.seed = ParameterSlider(tr("Random seed"), 1, 99, 1, decimals=0, step=1)
        for w in (self.steps, self.step_size, self.burn_in, self.seed):
            wl.addWidget(w)
        row = QHBoxLayout()
        self.run_button = QPushButton(tr("▶ Run the chain"))
        self.run_button.setProperty("role", "primary")
        self.run_button.clicked.connect(self.run)
        self.animate_button = QPushButton(tr("Watch it walk"))
        self.animate_button.setCheckable(True)
        self.animate_button.setToolTip(tr("Reveal the chain step by step."))
        self.animate_button.toggled.connect(self._animate)
        row.addWidget(self.run_button)
        row.addWidget(self.animate_button)
        wl.addLayout(row)
        self.rhat_button = QPushButton(tr("Run {count} chains and check convergence")
                                       .format(count=CHAINS_FOR_RHAT))
        self.rhat_button.setToolTip(tr("Start four walkers from different corners and compare them with R̂."))
        self.rhat_button.clicked.connect(self.run_many)
        wl.addWidget(self.rhat_button)
        self.controls.addWidget(walk)

        results = QGroupBox(tr("What the chain says"))
        rl = QVBoxLayout(results)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.RichText)
        rl.addWidget(self.summary)
        rl.addWidget(muted_label(tr("The magnitude offset (M and H0 together) is fitted away, so the chain "
                            "measures the densities only.")))
        self.controls.addWidget(results)
        self.finish_controls()

        self.banner = Banner("info", "")
        self.display.addWidget(self.banner)
        tabs = QTabWidget()
        self.posterior_plot = PlotWidget(self._draw_posterior, csv_provider=self._csv, export_name="mcmc_posterior")
        self.trace_plot = PlotWidget(self._draw_trace, export_name="mcmc_trace")
        tabs.addTab(self.posterior_plot, tr("Posterior"))
        tabs.addTab(self.trace_plot, tr("Walk and χ²"))
        self.display.addWidget(tabs, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(40)
        self.timer.timeout.connect(self._tick)
        self.sample_box.currentIndexChanged.connect(self._sample_changed)
        self.flat.toggled.connect(self.run)
        self._sample_changed()

    # ------------------------------------------------------------- running
    def _sample_changed(self, *_args) -> None:
        self.sample = sn.SAMPLES[self.sample_box.currentData()]()
        self.grid = sn.fit_grid(self.sample, n=41)
        self.run()

    def run(self, *_args) -> None:
        """One chain, from a deliberately poor starting point."""
        self.chains = []
        self.chain = inf.run_chain(
            self.sample,
            steps=int(self.steps.value()),
            step_size=self.step_size.value(),
            start=(0.8, 0.1),
            seed=int(self.seed.value()),
            flat=self.flat.isChecked(),
            burn_in_fraction=self.burn_in.value(),
        )
        self.frame = len(self.chain.samples)
        self._refresh()

    def run_many(self) -> None:
        """Four walkers from four corners: the standard convergence check."""
        starts = [(0.1, 0.1), (0.9, 0.1), (0.1, 1.2), (0.9, 1.2)]
        self.chains = [
            inf.run_chain(self.sample, steps=int(self.steps.value()), step_size=self.step_size.value(),
                          start=start, seed=int(self.seed.value()) + i, flat=self.flat.isChecked(),
                          burn_in_fraction=self.burn_in.value())
            for i, start in enumerate(starts)
        ]
        self.chain = self.chains[0]
        self.frame = len(self.chain.samples)
        self._refresh()

    def recompute(self) -> None:
        if self.chain is None:
            self.run()
        else:
            self._refresh()

    # ----------------------------------------------------------- animation
    def _animate(self, on: bool) -> None:
        self.animate_button.setText(tr("⏸ Pause") if on else tr("Watch it walk"))
        if on:
            if self.chain is None:
                self.run()
            self.frame = 0
            self.timer.start()
        else:
            self.timer.stop()

    def _tick(self) -> None:
        total = len(self.chain.samples)
        self.frame = min(self.frame + max(total // 120, 5), total)
        self._refresh(animating=True)
        if self.frame >= total:
            self.animate_button.setChecked(False)

    def on_hidden(self) -> None:
        self.animate_button.setChecked(False)

    # -------------------------------------------------------------- output
    def visible_chain(self) -> inf.Chain:
        """The chain as far as the animation has revealed it."""
        if self.frame >= len(self.chain.samples):
            return self.chain
        frame = max(self.frame, 10)
        return inf.Chain(self.chain.samples[:frame], self.chain.log_post[:frame],
                         int(self.chain.accepted * frame / len(self.chain.samples)), self.chain.flat,
                         burn_in=min(self.chain.burn_in, frame // 2))

    def _refresh(self, animating: bool = False) -> None:
        chain = self.visible_chain()
        mean, std = chain.mean(), chain.std()
        lines = [tr("Ωm = <b>{value} ± {error}</b>").format(value=f"{mean[0]:.3f}", error=f"{std[0]:.3f}")]
        if not chain.flat:
            lines.append(tr("ΩΛ = <b>{value} ± {error}</b>")
                         .format(value=f"{mean[1]:.3f}", error=f"{std[1]:.3f}"))
            lines.append(tr("Correlation between them: <b>{value}</b>")
                         .format(value=f"{chain.correlation():+.2f}"))
        low, high = chain.interval(0)
        lines.append(tr("68% interval for Ωm: {low} … {high}")
                     .format(low=f"{low:.3f}", high=f"{high:.3f}"))
        lines.append(tr("Acceptance rate: <b>{rate}</b>  (aim for about 25%)")
                     .format(rate=f"{chain.acceptance:.0%}"))
        lines.append(tr("Steps kept: {kept} of {total}")
                     .format(kept=f"{len(chain.kept):,}", total=f"{len(chain.samples):,}"))
        tau, neff = chain.autocorrelation_length(), chain.effective_samples()
        if np.isfinite(tau):
            lines.append(tr("Autocorrelation length: {tau} steps → <b>{neff}</b> independent samples")
                         .format(tau=f"{tau:.0f}", neff=f"{neff:.0f}"))
        if self.chains:
            rhat = inf.gelman_rubin(self.chains, 0)
            lines.append(tr("R̂ from {count} chains: <b>{rhat}</b> (converged below 1.01)")
                         .format(count=len(self.chains), rhat=f"{rhat:.3f}"))
        best_chi2 = inf.chi2(mean[0], mean[1], self.sample)
        fit = inf.goodness_of_fit(best_chi2, len(self.sample.z), 2 if not chain.flat else 1)
        lines.append(tr("χ² at the mean: {chi2} for {dof} degrees of freedom (χ²/dof = {reduced})")
                     .format(chi2=f"{fit['chi2']:.0f}", dof=fit["dof"], reduced=f"{fit['reduced']:.2f}"))
        self.summary.setText("<br>".join(lines))

        if not animating:
            self._set_banner(chain)
        self.posterior_plot.refresh()
        self.trace_plot.refresh()

    def _set_banner(self, chain: inf.Chain) -> None:
        acceptance = chain.acceptance
        if acceptance < 0.05:
            self.banner.set_message(
                "warning", tr("<b>Almost everything is rejected.</b> The proposal step is too large: the walker "
                              "keeps suggesting universes the data rule out. Make σ smaller."))
        elif acceptance > 0.8:
            self.banner.set_message(
                "warning", tr("<b>Almost everything is accepted.</b> The steps are so small that the walker "
                              "barely moves; the cloud looks tight but it has not explored. Make σ larger."))
        elif self.sample.real:
            self.banner.set_message(
                "success", tr("<b>Real measurement.</b> {citation}. The contours below are your own posterior, "
                              "sampled step by step from these supernovae.").format(citation=self.sample.citation))
        else:
            self.banner.set_message(
                "info", tr("<b>Simulated data.</b> The chain works the same way; only the scatter is "
                           "invented."))

    # --------------------------------------------------------------- plots
    def _draw_posterior(self, fig) -> None:
        p = theme().palette
        chain = self.visible_chain()
        kept = chain.kept
        if chain.flat:
            ax = fig.add_subplot()
            ax.hist(kept[:, 0], bins=40, color=p.series[0], alpha=0.8)
            mean, std = kept[:, 0].mean(), kept[:, 0].std(ddof=1)
            for offset, style in ((0, "-"), (-std, "--"), (std, "--")):
                ax.axvline(mean + offset, color=p.accent2, linestyle=style, linewidth=1.4)
            ax.set_xlabel("Ωm  (flat universe)")
            ax.set_ylabel("Samples per bin")
            ax.set_title(f"Posterior for Ωm: {mean:.3f} ± {std:.3f}", fontsize=9)
            return

        grid = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[1, 3], wspace=0.05, hspace=0.05)
        main = fig.add_subplot(grid[1, 0])
        top = fig.add_subplot(grid[0, 0], sharex=main)
        right = fig.add_subplot(grid[1, 1], sharey=main)

        posterior = inf.posterior_map(chain)
        x_centres, y_centres = posterior.centres
        main.plot(chain.samples[:, 0], chain.samples[:, 1], color=p.muted, linewidth=0.35, alpha=0.35,
                  label="the walk")
        main.contourf(x_centres, y_centres, posterior.density,
                      levels=[posterior.levels[1], posterior.levels[0], posterior.density.max() + 1],
                      colors=[p.mix(p.series[0], 0.45), p.mix(p.series[0], 0.9)], alpha=0.85)
        main.contour(x_centres, y_centres, posterior.density, levels=list(posterior.levels)[::-1],
                     colors=p.series[0], linewidths=1.2)
        if self.grid is not None:
            main.plot([self.grid.best_om], [self.grid.best_ol], "*", color=p.accent2, markersize=13,
                      label="grid best fit")
        main.plot([kept[:, 0].mean()], [kept[:, 1].mean()], "o", color=p.text, markersize=6,
                  label="chain mean")
        line = np.linspace(-0.5, 2.0, 10)
        main.plot(1 - line, line, color=p.success, linestyle=":", linewidth=1.2, label="flat universe")
        # Frame the cloud itself, with room for the flat line and the grid best fit.
        mean, std = kept.mean(axis=0), kept.std(axis=0, ddof=1)
        pad = np.maximum(4 * std, [0.08, 0.12])
        main.set_xlim(max(mean[0] - pad[0], -0.05), mean[0] + pad[0])
        main.set_ylim(mean[1] - pad[1], mean[1] + pad[1])
        main.set_xlabel("Ωm (matter)")
        main.set_ylabel("ΩΛ (dark energy)")
        main.legend(loc="lower right", fontsize=6.5, framealpha=0.6)

        top.hist(kept[:, 0], bins=35, color=p.series[0], alpha=0.85)
        top.tick_params(labelbottom=False, labelleft=False)
        top.set_title("68% and 95% of the samples", fontsize=9)
        right.hist(kept[:, 1], bins=35, orientation="horizontal", color=p.series[0], alpha=0.85)
        right.tick_params(labelbottom=False, labelleft=False)

    def _draw_trace(self, fig) -> None:
        p = theme().palette
        chain = self.visible_chain()
        axes = fig.subplots(3, 1, sharex=True)
        steps = np.arange(len(chain.samples))
        names = ["Ωm", "ΩΛ"]
        for i, ax in enumerate(axes[:2]):
            for j, other in enumerate(self.chains or [chain]):
                colour = p.series[j % 6] if self.chains else p.series[0]
                ax.plot(other.samples[:len(steps), i], color=colour, linewidth=0.8, alpha=0.9)
            ax.axvspan(0, chain.burn_in, color=p.danger, alpha=0.12, linewidth=0)
            ax.set_ylabel(names[i], fontsize=8)
            ax.tick_params(labelsize=7)
            if chain.flat and i == 1:
                ax.set_ylabel("ΩΛ = 1 − Ωm", fontsize=8)
        axes[0].set_title("Where the walker went (red band: burn-in, discarded)", fontsize=9)
        axes[2].plot(steps, -2 * chain.log_post, color=p.series[3], linewidth=0.9)
        axes[2].set_ylabel("χ²", fontsize=8)
        axes[2].set_xlabel("step")
        axes[2].tick_params(labelsize=7)
        finite = np.isfinite(chain.log_post)
        if finite.any():
            best = float(np.min(-2 * chain.log_post[finite]))
            axes[2].set_ylim(best - 5, best + 60)

    def _csv(self):
        chain = self.visible_chain()
        rows = [[f"{i}", f"{om:.5f}", f"{ol:.5f}", f"{-2 * lp:.3f}"]
                for i, ((om, ol), lp) in enumerate(zip(chain.samples, chain.log_post))]
        return ["step", "omega_m", "omega_lambda", "chi2"], rows

    # ---------------------------------------------------------------- state
    def state(self) -> dict:
        chain = self.chain or self.visible_chain()
        mean, std = chain.mean(), chain.std()
        return {
            "sample": self.sample_box.currentData(),
            "flat": self.flat.isChecked(),
            "steps": int(self.steps.value()),
            "step_size": self.step_size.value(),
            "acceptance": chain.acceptance,
            "om_mean": float(mean[0]),
            "om_error": float(std[0]),
            "ol_mean": float(mean[1]),
            "chains": len(self.chains),
            "rhat": inf.gelman_rubin(self.chains, 0) if self.chains else float("nan"),
        }

    def guide_extra(self) -> str:
        return (
            "### " + tr("What the numbers mean") + "\n\n"
            + tr("- **Acceptance rate** — the fraction of proposals the walker took. Near 25% is healthy for "
                 "two parameters; 1% or 95% both mean the step size is wrong.\n"
                 "- **Autocorrelation length** — how many steps before the walker forgets where it was. The "
                 "effective sample size is the chain length divided by it.\n"
                 "- **R̂** — four walkers started far apart should end up describing the same distribution. "
                 "Above 1.01 they have not met yet.\n"
                 "- The magnitude offset is fitted away at every step, which is why H0 never appears here: "
                 "supernovae alone measure the *shape* of the expansion, not its rate.")
        )
