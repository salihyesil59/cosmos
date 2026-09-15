"""A two-dimensional particle-mesh (PM) simulation of structure formation.

This is a teaching toy: particles live in a periodic square and gravity is
solved on a grid with fast Fourier transforms. Time is measured by the linear
growth factor ``D`` of an Einstein–de Sitter universe, in which the equations
of motion become

    d²x/dD² + (3 / 2D) dx/dD = −(3 / 2D) ∇φ,     ∇²φ = δ / D,

so that small density fluctuations grow exactly as δ ∝ D. Initial conditions
use the Zel'dovich approximation for a Gaussian random field with a power-law
spectrum P(k) ∝ kⁿ and an optional small-scale cutoff (warm dark matter).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np


@dataclass
class NBodyConfig:
    particles_per_side: int = 128
    grid: int = 128
    spectral_index: float = -1.0
    amplitude: float = 1.0         # RMS linear density contrast per grid cell at D = 1
    cutoff: float = 0.0            # warm dark matter cutoff scale in grid cells (0 = cold)
    seed: int = 42


@dataclass
class NBodySimulation:
    config: NBodyConfig = field(default_factory=NBodyConfig)

    def __post_init__(self):
        self.reset()

    # ------------------------------------------------------------ setup
    def reset(self) -> None:
        cfg = self.config
        n, g = cfg.particles_per_side, cfg.grid
        rng = np.random.default_rng(cfg.seed)
        k = np.fft.fftfreq(g) * 2 * math.pi * g   # wavenumbers in units of 1/box
        kx, ky = np.meshgrid(k, k, indexing="ij")
        k2 = kx * kx + ky * ky
        kmag = np.sqrt(k2)
        with np.errstate(divide="ignore"):
            power = np.where(k2 > 0, kmag**cfg.spectral_index, 0.0)
        power[g // 2, :] = 0
        power[:, g // 2] = 0
        noise = np.fft.fft2(rng.normal(size=(g, g)))
        delta_k = noise * np.sqrt(power)
        delta = np.real(np.fft.ifft2(delta_k))
        delta *= cfg.amplitude / max(delta.std(), 1e-12)
        delta_k = np.fft.fft2(delta)
        if cfg.cutoff > 0:
            # Warm dark matter erases small-scale fluctuations but leaves large scales untouched.
            delta_k *= np.exp(-0.5 * (kmag * cfg.cutoff / g) ** 2)
            delta = np.real(np.fft.ifft2(delta_k))
        self.initial_delta = delta

        # Zel'dovich displacement field ψ with ∇·ψ = −δ.
        with np.errstate(divide="ignore", invalid="ignore"):
            inv_k2 = np.where(k2 > 0, 1.0 / k2, 0.0)
        psi_x = np.real(np.fft.ifft2(1j * kx * inv_k2 * delta_k))
        psi_y = np.real(np.fft.ifft2(1j * ky * inv_k2 * delta_k))

        q = (np.arange(n) + 0.5) / n
        qx, qy = np.meshgrid(q, q, indexing="ij")
        self.q = np.stack([qx.ravel(), qy.ravel()], axis=1)
        disp = np.stack([
            _interp_cic(psi_x, self.q), _interp_cic(psi_y, self.q)
        ], axis=1)
        self.growth = 0.02            # starting growth factor D (δ is tiny)
        self.pos = (self.q + self.growth * disp) % 1.0
        self.vel = disp.copy()        # dx/dD in the linear regime
        self.steps = 0

    # --------------------------------------------------------- dynamics
    def density(self, grid: int | None = None) -> np.ndarray:
        """Density contrast δ on a grid, using cloud-in-cell assignment."""
        g = grid or self.config.grid
        rho = _deposit_cic(self.pos, g)
        return rho / rho.mean() - 1.0

    def _acceleration(self) -> np.ndarray:
        g = self.config.grid
        delta = self.density(g)
        freq = np.fft.fftfreq(g)
        k = freq * 2 * math.pi
        kx, ky = np.meshgrid(k, k, indexing="ij")
        k2 = kx * kx + ky * ky
        with np.errstate(divide="ignore", invalid="ignore"):
            inv_k2 = np.where(k2 > 0, -1.0 / k2, 0.0)
        # Cloud-in-cell assignment and interpolation each smooth the force by W(k);
        # dividing by W² restores the correct large-scale growth.
        fx, fy = np.meshgrid(freq, freq, indexing="ij")
        window = (np.sinc(fx) * np.sinc(fy)) ** 2
        # φ in units where the box length is 1: ∇²φ = δ/D  →  φ_k = −δ_k / (k² D), k per box.
        phi_k = np.fft.fft2(delta) * inv_k2 / (g * g) / self.growth / np.maximum(window, 0.3) ** 2
        gx = np.real(np.fft.ifft2(-1j * kx * g * phi_k))
        gy = np.real(np.fft.ifft2(-1j * ky * g * phi_k))
        return np.stack([_interp_cic(gx, self.pos), _interp_cic(gy, self.pos)], axis=1)

    def step(self, d_growth: float) -> None:
        """Advance by ``d_growth`` with a kick–drift–kick leapfrog."""
        d = self.growth
        acc = self._acceleration()
        half = 0.5 * d_growth
        self.vel += half * (-1.5 / d) * (self.vel - acc)
        self.pos = (self.pos + d_growth * self.vel) % 1.0
        self.growth = d + d_growth
        acc = self._acceleration()
        self.vel += half * (-1.5 / self.growth) * (self.vel - acc)
        self.steps += 1

    def run_to(self, target_growth: float, max_step: float = 0.03) -> None:
        while self.growth < target_growth - 1e-12:
            self.step(min(max_step, target_growth - self.growth, 0.04 * self.growth))

    # --------------------------------------------------------- analysis
    def collapsed_fraction(self, threshold: float = 4.0) -> float:
        """Fraction of particles in cells denser than ``1 + threshold`` times the mean."""
        g = self.config.grid
        delta = self.density(g)
        idx = (self.pos * g).astype(int) % g
        return float(np.mean(delta[idx[:, 0], idx[:, 1]] > threshold))

    def density_image(self, pixels: int = 256) -> np.ndarray:
        """Log-scaled density map in the range 0..1 for display."""
        rho = _deposit_cic(self.pos, pixels)
        rho = rho / rho.mean()
        img = np.log10(np.clip(rho, 0.05, None))
        return np.clip((img + 1.3) / 2.8, 0.0, 1.0)


def _deposit_cic(pos: np.ndarray, g: int) -> np.ndarray:
    x = pos[:, 0] * g - 0.5
    y = pos[:, 1] * g - 0.5
    i0 = np.floor(x).astype(int)
    j0 = np.floor(y).astype(int)
    fx, fy = x - i0, y - j0
    rho = np.zeros(g * g)
    for di, wx in ((0, 1 - fx), (1, fx)):
        for dj, wy in ((0, 1 - fy), (1, fy)):
            flat = ((i0 + di) % g) * g + (j0 + dj) % g
            rho += np.bincount(flat, weights=wx * wy, minlength=g * g)
    return rho.reshape(g, g)


def _interp_cic(field: np.ndarray, pos: np.ndarray) -> np.ndarray:
    g = field.shape[0]
    x = pos[:, 0] * g - 0.5
    y = pos[:, 1] * g - 0.5
    i0 = np.floor(x).astype(int)
    j0 = np.floor(y).astype(int)
    fx, fy = x - i0, y - j0
    out = np.zeros(len(pos))
    for di, wx in ((0, 1 - fx), (1, fx)):
        for dj, wy in ((0, 1 - fy), (1, fy)):
            out += field[(i0 + di) % g, (j0 + dj) % g] * wx * wy
    return out
