"""Optional exact CMB spectra from CAMB (E6).

The app ships a fast teaching model (:mod:`cosmos.physics.cmb`) that gets the
peak positions right and the peak heights to about 15%. If the optional package
`camb <https://camb.readthedocs.io>`_ is installed, the same parameters can be
sent to a real Boltzmann code instead and the simulator plots the exact
spectrum. Nothing else in the app depends on CAMB being present.

    pip install camb
"""

from __future__ import annotations

import functools

import numpy as np

from cosmos.physics.cmb import ELL_MAX, CMBParameters, CMBSpectrum, find_peaks

# Cheap accuracy settings: the spectrum is for teaching, not for a likelihood.
LENS_ACCURACY = 1


@functools.cache
def version() -> str | None:
    """The installed CAMB version, or None when CAMB is not available."""
    try:
        import camb
    except Exception:            # noqa: BLE001 - a broken install must not break the app
        return None
    return str(camb.__version__)


def available() -> bool:
    return version() is not None


def spectrum(p: CMBParameters = CMBParameters(), ell_max: int = ELL_MAX) -> CMBSpectrum:
    """The lensed TT spectrum of ``p``, computed by CAMB.

    Returns the same :class:`~cosmos.physics.cmb.CMBSpectrum` as the teaching
    model, so the simulator can swap one for the other.
    """
    import camb

    pars = camb.CAMBparams()
    pars.set_cosmology(
        H0=100 * p.h,
        ombh2=p.omega_b,
        omch2=p.omega_c,
        omk=p.omega_k,
        tau=max(p.tau, 1e-4),        # CAMB needs a positive optical depth
        TCMB=p.tcmb,
        nnu=p.neff,
    )
    pars.InitPower.set_params(As=p.a_s, ns=p.n_s)
    if p.w0 != -1.0 or p.wa != 0.0:
        pars.set_dark_energy(w=p.w0, wa=p.wa, dark_energy_model="ppf")
    pars.set_for_lmax(int(ell_max), lens_potential_accuracy=LENS_ACCURACY)

    results = camb.get_results(pars)
    powers = results.get_cmb_power_spectra(pars, CMB_unit="muK", spectra=["total"])["total"]
    ell = np.arange(2, min(ell_max, powers.shape[0] - 1) + 1, dtype=float)
    d_ell = np.asarray(powers[2:len(ell) + 2, 0], dtype=float)      # column 0 is TT, already ℓ(ℓ+1)Cℓ/2π

    if not np.all(np.isfinite(d_ell)) or d_ell.size < 100:
        # CAMB occasionally returns an unusable spectrum; the caller falls back to the model.
        raise ValueError("CAMB returned a spectrum that is not finite")

    derived = results.get_derived_params()
    r_s = float(derived["rstar"])                                   # Mpc
    d_m = float(derived["DAstar"]) * 1e3                            # Gpc -> Mpc
    return CMBSpectrum(
        ell=ell,
        d_ell=d_ell,
        ell_a=float(np.pi * d_m / r_s),
        r_s=r_s,
        d_m=d_m,
        z_star=float(derived["zstar"]),
        r_star=baryon_loading(p, float(derived["zstar"])),
        peaks=find_peaks(ell, d_ell),
    )


def baryon_loading(p: CMBParameters, z_star: float) -> float:
    """R* = 3ρ_b / 4ρ_γ at decoupling, the quantity CAMB does not report directly."""
    return 31500 * p.omega_b * (p.tcmb / 2.7) ** -4 / (1 + z_star)
