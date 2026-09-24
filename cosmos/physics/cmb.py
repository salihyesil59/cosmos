"""A simplified, physically motivated model of the CMB temperature power spectrum.

This is a teaching model, not a Boltzmann code such as CAMB or CLASS. Peak
*positions* follow from the real sound horizon and distance to last scattering.
Peak *heights* use the tight-coupling oscillator of Hu & Sugiyama with baryon
loading, radiation driving, Doppler contribution, diffusion (Silk) damping and
reionisation, with a handful of constants calibrated so that the Planck 2018
model reproduces the measured spectrum to roughly 15% (peak positions to a
few percent). Trends when parameters change are qualitatively right.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from cosmos.physics import constants as const
from cosmos.physics import structure
from cosmos.physics.cosmology import Cosmology

T_CMB_MICROK = const.T_CMB * 1e6
ELL_MAX = 2500

# Calibration constants, fitted by least squares to ``PLANCK_LANDMARKS``.
CALIBRATION = {
    "phase": 0.2302,          # peaks sit near ℓ ≈ ℓ_A (n − φ)
    "driving": 4.891,         # asymptotic radiation-driving boost of the oscillation amplitude
    "driving_width": 0.3374,  # driving turns on around ℓ ≈ width × ℓ_eq
    "offset": 0.6266,         # weight of the baryon-loading offset (odd/even peak contrast)
    "doppler": 0.0663,        # projection weight of the Doppler (velocity) term
    "damping_ell": 918.71,    # Silk damping multipole for Planck 2018
    "damping_power": 1.4164,
    "plateau": 0.9796,        # Sachs–Wolfe plateau relative to the acoustic normalisation
    "smoothing": 0.2489,      # projection smearing, as a fraction of ℓ_A
}
_NORM: float | None = None

# Approximate Planck 2018 best-fit ΛCDM D_ℓ [μK²] at landmark multipoles (peaks,
# troughs, plateau and damping tail), used only to calibrate the teaching model.
PLANCK_LANDMARKS = [
    (10, 1100), (30, 1350), (100, 2300), (220, 5720), (415, 1700), (537, 2600),
    (678, 1800), (813, 2530), (1000, 850), (1127, 1250), (1270, 700), (1426, 820),
    (1570, 450), (1720, 420), (2000, 230), (2300, 110),
]


@dataclass(frozen=True)
class CMBParameters:
    omega_b: float = 0.02242    # Ω_b h²
    omega_c: float = 0.11933    # Ω_c h²
    h: float = 0.6766
    omega_k: float = 0.0
    n_s: float = 0.9665
    a_s: float = 2.105e-9
    tau: float = 0.0561
    w0: float = -1.0
    wa: float = 0.0
    tcmb: float = const.T_CMB
    neff: float = const.NEFF

    @property
    def omega_m(self) -> float:
        return self.omega_b + self.omega_c

    def cosmology(self) -> Cosmology:
        h2 = self.h * self.h
        om = self.omega_m / h2
        probe = Cosmology(H0=100 * self.h, Om0=om, Ode0=0.0, Ob0=self.omega_b / h2, w0=self.w0, wa=self.wa,
                          Tcmb0=self.tcmb, Neff=self.neff)
        ode = 1.0 - om - probe.Or0 - self.omega_k
        return probe.with_params(Ode0=ode, name="CMB model")


PLANCK = CMBParameters()


@dataclass(frozen=True)
class CMBSpectrum:
    ell: np.ndarray
    d_ell: np.ndarray            # ℓ(ℓ+1)C_ℓ/2π in μK²
    ell_a: float
    r_s: float
    d_m: float
    z_star: float
    r_star: float
    peaks: list[tuple[float, float]]    # (ℓ, D_ℓ) of the first few maxima

    @property
    def theta_star(self) -> float:
        return self.r_s / self.d_m


def _smooth(values: np.ndarray, ell_a: float) -> np.ndarray:
    """Projection onto the sky smears each wavenumber over a range of multipoles."""
    width = max(CALIBRATION["smoothing"] * ell_a, 1.0)
    kernel_x = np.arange(-int(4 * width), int(4 * width) + 1)
    kernel = np.exp(-0.5 * (kernel_x / width) ** 2)
    padded = np.pad(values, len(kernel_x) // 2, mode="edge")
    return np.convolve(padded, kernel / kernel.sum(), mode="valid")


def _components(p: CMBParameters, ell: np.ndarray) -> dict:
    """The tight-coupling oscillator, before anything is squared or added up.

    ``monopole`` is the compression of the plasma and ``dipole`` its velocity. The
    temperature spectrum is built mostly from the monopole; polarisation comes only
    from the dipole, which is why the two are out of phase with each other.
    """
    c = p.cosmology()
    acoustic = structure.acoustic_scale(c)
    ell_a, r_star = acoustic["ell_A"], acoustic["R_star"]
    # Equality scale projected onto the sky.
    k_eq = 0.0746 * p.omega_m * (const.T_CMB / 2.7) ** -2
    ell_eq = k_eq * acoustic["D_M"]

    cal = CALIBRATION
    theta = math.pi * (ell / ell_a + cal["phase"])
    x = ell / (cal["driving_width"] * ell_eq)
    driving = 1 + (cal["driving"] - 1) * x * x / (1 + x * x)

    r = r_star
    amp = (1 / 3 + r) / (1 + r) * driving
    # Gravitational potentials decay on scales that entered during radiation domination,
    # so the baryon-loading offset shrinks where the driving is strong.
    monopole = -amp * np.cos(theta) + cal["offset"] * r * (1 + r) ** 0.25 * 3 / driving
    dipole = amp * (1 + r) ** -0.5 * np.sin(theta) / math.sqrt(3)

    # Diffusion damping: projected scale grows with the distance, shrinks with fewer baryons.
    ell_d = (cal["damping_ell"] * (ell_a / 301.5) * (p.omega_b / 0.02242) ** 0.25
             * (p.omega_m / 0.14175) ** 0.1)
    return {
        "acoustic": acoustic,
        "ell_a": ell_a,
        "ell_d": ell_d,
        "monopole": monopole,
        "dipole": dipole,
        "damping": np.exp(-((ell / ell_d) ** cal["damping_power"])),
        # Large scales outside the horizon at decoupling only see the Sachs–Wolfe plateau.
        "transition": 1 / (1 + (ell / (0.25 * ell_a)) ** -4),
        "tilt": (ell / 80.0) ** (p.n_s - 1),
        "reion": math.exp(-2 * p.tau) + (1 - math.exp(-2 * p.tau)) / (1 + (ell / 15.0) ** 2),
    }


def _raw_spectrum(p: CMBParameters, ell: np.ndarray):
    cal = CALIBRATION
    c = _components(p, ell)
    acoustic_power = _smooth(c["monopole"] ** 2 + cal["doppler"] * c["dipole"] ** 2, c["ell_a"])
    shape = c["transition"] * acoustic_power * c["damping"] + (1 - c["transition"]) * cal["plateau"]
    return shape * c["tilt"] * c["reion"] * p.a_s / 2.1e-9, c["acoustic"]


def _normalisation() -> float:
    global _NORM
    if _NORM is None:
        ell = np.arange(2, ELL_MAX + 1, dtype=float)
        raw, _ = _raw_spectrum(PLANCK, ell)
        sel = (ell > 150) & (ell < 300)
        _NORM = 5720.0 / raw[sel].max()
    return _NORM


def calibration_error() -> float:
    """RMS logarithmic deviation from the Planck landmarks (for tests and calibration)."""
    spec = spectrum()
    model = np.array([spec.d_ell[int(ell) - 2] for ell, _ in PLANCK_LANDMARKS])
    target = np.array([v for _, v in PLANCK_LANDMARKS], dtype=float)
    return float(np.sqrt(np.mean(np.log(model / target) ** 2)))


def find_peaks(ell: np.ndarray, d_ell: np.ndarray, limit: int = 6) -> list[tuple[float, float]]:
    """The first acoustic maxima of a spectrum, whoever computed it."""
    peaks: list[tuple[float, float]] = []
    for i in range(1, len(d_ell) - 1):
        if d_ell[i] > d_ell[i - 1] and d_ell[i] >= d_ell[i + 1] and ell[i] > 100:
            peaks.append((float(ell[i]), float(d_ell[i])))
        if len(peaks) == limit:
            break
    return peaks


def spectrum(p: CMBParameters = PLANCK, ell_max: int = ELL_MAX) -> CMBSpectrum:
    ell = np.arange(2, ell_max + 1, dtype=float)
    raw, acoustic = _raw_spectrum(p, ell)
    d_ell = raw * _normalisation()
    peaks = find_peaks(ell, d_ell)
    return CMBSpectrum(
        ell=ell,
        d_ell=d_ell,
        ell_a=acoustic["ell_A"],
        r_s=acoustic["r_s"],
        d_m=acoustic["D_M"],
        z_star=acoustic["z_star"],
        r_star=acoustic["R_star"],
        peaks=peaks,
    )


# ------------------------------------------------------------------ polarisation
# Thomson scattering turns a quadrupole in the radiation into linear polarisation, and
# the quadrupole seen by an electron at last scattering is produced by the *velocity* of
# the plasma. So polarisation follows the dipole term, which is why the E-mode peaks sit
# where the temperature peaks do not. It is also generated only during the short time the
# plasma is decoupling, which suppresses it on large scales.
POLARISATION = {
    "ell_gen": 780.0,        # below this the finite thickness of last scattering suppresses E modes
    "gen_power": 2.5,        # how steeply that suppression sets in
    "ee_peak": 45.0,         # μK², the height of the EE spectrum near ℓ ≈ 1000
    "te_peak": 150.0,        # μK², the largest swing of the temperature–polarisation cross-spectrum
    "reion_ee": 0.14,        # μK² in the reionisation bump at ℓ ≈ 5 for τ = 0.0561
    "lensing_bb": 0.10,      # μK² at the ℓ ≈ 1000 peak of the lensing B modes
    "tensor_bb": 0.30,       # μK² at ℓ ≈ 80 per unit tensor-to-scalar ratio r
    "tensor_reion": 0.15,    # μK² in the ℓ ≈ 5 tensor bump per unit r, for τ = 0.0561
    "dust_150": 0.013,       # μK² at ℓ = 80: polarised dust in a clean patch at 150 GHz
}
BICEP_LIMIT_R = 0.036        # BICEP/Keck + Planck, 95% upper limit on r (2021)


@dataclass(frozen=True)
class PolarisationSpectra:
    ell: np.ndarray
    ee: np.ndarray                # D_ℓ^EE [μK²]
    te: np.ndarray                # D_ℓ^TE [μK²], and it changes sign
    bb_lensing: np.ndarray        # B modes made by lensing of the E modes
    bb_tensor: np.ndarray         # B modes from primordial gravitational waves
    bb_dust: np.ndarray           # polarised emission from our own Galaxy
    r: float
    a_lens: float

    @property
    def bb_total(self) -> np.ndarray:
        return self.bb_lensing + self.bb_tensor + self.bb_dust

    def at(self, values: np.ndarray, ell: float) -> float:
        return float(np.interp(ell, self.ell, values))


def _lognormal_bump(ell: np.ndarray, centre: float, width: float) -> np.ndarray:
    return np.exp(-0.5 * (np.log(np.maximum(ell, 1e-3) / centre) / width) ** 2)


_POL_NORM: tuple[float, float] | None = None


def _polarisation_normalisation() -> tuple[float, float]:
    """Amplitudes of EE and TE, fixed once on the Planck model.

    They must be constants, not per-spectrum rescalings: otherwise changing τ or A_s
    would move the whole spectrum and then be normalised straight back out, hiding the
    very degeneracy the low-ℓ bump exists to break.
    """
    global _POL_NORM
    if _POL_NORM is None:
        _POL_NORM = (1.0, 1.0)
        planck = polarisation(PLANCK)
        _POL_NORM = (POLARISATION["ee_peak"] / float(planck.ee.max()),
                     POLARISATION["te_peak"] / float(np.abs(planck.te).max()))
    return _POL_NORM


def polarisation(p: CMBParameters = PLANCK, r: float = 0.0, a_lens: float = 1.0,
                 dust: float | None = None, ell_max: int = ELL_MAX) -> PolarisationSpectra:
    """E modes, the TE cross-spectrum and the two kinds of B mode.

    Amplitudes are calibrated so that the Planck 2018 model gives the measured EE peak
    (about 45 μK² near ℓ = 1000) and the observed lensing B-mode level; the *shapes* come
    from the same oscillator as the temperature spectrum, so changing a parameter moves
    the polarisation peaks in the way it really does. Tens of percent, no better.
    """
    ell = np.arange(2, ell_max + 1, dtype=float)
    pol = POLARISATION
    c = _components(p, ell)
    scalar = p.a_s / 2.1e-9

    # Polarisation is only generated while the plasma decouples, so it dies away on
    # scales much larger than the thickness of the last-scattering surface.
    x = (ell / pol["ell_gen"]) ** pol["gen_power"]
    envelope = x / (1 + x) * c["damping"] * c["tilt"] * scalar * math.exp(-2 * p.tau)

    ee_norm, te_norm = _polarisation_normalisation()
    ee = _smooth(c["dipole"] ** 2, c["ell_a"]) * envelope * ee_norm
    # Rescattering after reionisation makes a bump at the horizon size of that epoch.
    ee += pol["reion_ee"] * (p.tau / 0.0561) ** 2 * _lognormal_bump(ell, 5.0, 0.55)
    te = -_smooth(c["monopole"] * c["dipole"], c["ell_a"]) * envelope * te_norm

    # Lensing deflects the E modes and shuffles a little of their power into B modes.
    bb_lensing = a_lens * pol["lensing_bb"] * _lognormal_bump(ell, 1000.0, 1.2)
    # Tensors make B modes directly: one bump at the horizon at recombination, one at
    # the horizon at reionisation. Inside the horizon the waves have already decayed.
    bb_tensor = r * (pol["tensor_bb"] * _lognormal_bump(ell, 80.0, 0.85)
                     + pol["tensor_reion"] * (p.tau / 0.0561) ** 2 * _lognormal_bump(ell, 5.0, 0.6))
    amplitude = pol["dust_150"] if dust is None else dust
    bb_dust = amplitude * (ell / 80.0) ** -0.42          # measured Galactic dust slope at 150 GHz
    return PolarisationSpectra(ell, ee, te, bb_lensing, bb_tensor, bb_dust, r, a_lens)


def sky_patch(spec: CMBSpectrum, size_deg: float = 20.0, n: int = 256, seed: int = 11) -> np.ndarray:
    """Gaussian random temperature map [μK] of a flat sky patch with the given spectrum."""
    rng = np.random.default_rng(seed)
    size_rad = math.radians(size_deg)
    freq = np.fft.fftfreq(n, d=size_rad / n) * 2 * math.pi   # angular wavenumber = ℓ
    lx, ly = np.meshgrid(freq, freq)
    ell = np.hypot(lx, ly)
    d_ell = np.interp(ell, spec.ell, spec.d_ell, left=spec.d_ell[0], right=0.0)
    cl = np.where(ell > 0, 2 * math.pi * d_ell / np.clip(ell * (ell + 1), 1, None), 0.0)
    # White noise shaped by √C_ℓ; dividing by the pixel size gives the flat-sky normalisation.
    white = np.fft.fft2(rng.normal(size=(n, n)))
    pixel = size_rad / n
    return np.real(np.fft.ifft2(white * np.sqrt(cl) / pixel))
