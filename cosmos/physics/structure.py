"""Growth of structure: linear growth, sound horizon, power spectrum, halo abundance.

Wavenumbers ``k`` are in h/Mpc and lengths in Mpc/h unless a name says
otherwise (``_mpc`` suffix means plain Mpc).
"""

from __future__ import annotations

import math

import numpy as np
from scipy import integrate, special

from cosmos.physics import constants as const
from cosmos.physics.cosmology import Cosmology

DELTA_C = 1.686  # linear overdensity at collapse (spherical model)
C_KM_S = const.C / 1e3


# ----------------------------------------------------------------- growth
def _e2_no_radiation(c: Cosmology, a):
    a = np.asarray(a, dtype=float)
    return c.Om0 * a**-3 + (c.Ok0 + c.Or0) * a**-2 + c.Ode0 * c.de_density_ratio(a)


def growth_factor(c: Cosmology, a, normalize: bool = True):
    """Linear growth factor D(a) of matter perturbations.

    Solves ``D'' + (2 + dlnH/dlna) D' = 1.5 Ωm(a) D`` in ``ln a`` starting deep in
    the matter era (radiation is neglected, as is standard for late-time growth;
    its tiny density is folded into the curvature term). With ``normalize`` the
    result is 1 today, otherwise it equals ``a`` in the early matter era.
    """
    def rhs(lna, y):
        a = math.exp(lna)
        e2 = float(_e2_no_radiation(c, a))
        rho_de = c.Ode0 * float(c.de_density_ratio(a))
        de2 = -3 * c.Om0 * a**-3 - 2 * (c.Ok0 + c.Or0) * a**-2 - 3 * (1 + float(c.w_of_a(a))) * rho_de
        dlnh = 0.5 * de2 / e2
        om_a = c.Om0 * a**-3 / e2
        d, dp = y
        return [dp, -(2 + dlnh) * dp + 1.5 * om_a * d]

    a_arr = np.atleast_1d(np.asarray(a, dtype=float))
    a_start = 1e-4
    targets = np.log(np.clip(a_arr, a_start, None))
    order = np.argsort(targets)
    t_eval = np.unique(np.concatenate([targets[order], [0.0]]))
    sol = integrate.solve_ivp(
        rhs, (math.log(a_start), max(0.0, t_eval[-1])), [a_start, a_start], t_eval=t_eval, rtol=1e-8, atol=1e-12
    )
    d_of = dict(zip(sol.t, sol.y[0]))
    result = np.array([d_of[t] for t in targets])
    result = np.where(a_arr < a_start, a_arr, result)
    if normalize:
        result = result / d_of[0.0]
    return result if np.ndim(a) else float(result[0])


def growth_rate(c: Cosmology, a, gamma: float = 0.55):
    """Logarithmic growth rate f = dlnD/dlna, using the accurate fit Ωm(a)^γ."""
    a = np.asarray(a, dtype=float)
    om_a = c.Om0 * a**-3 / _e2_no_radiation(c, a)
    return om_a**gamma


# ------------------------------------------------------- sound horizon
def photon_density_h2(tcmb: float = const.T_CMB) -> float:
    """ω_γ = Ω_γ h²."""
    probe = Cosmology(H0=100.0, Om0=0.0, Ode0=0.0, Tcmb0=tcmb)
    return probe.Ogamma0


def z_decoupling(omega_b: float, omega_m: float) -> float:
    """Redshift of photon decoupling z* (Hu & Sugiyama 1996 fit)."""
    g1 = 0.0783 * omega_b**-0.238 / (1 + 39.5 * omega_b**0.763)
    g2 = 0.560 / (1 + 21.1 * omega_b**1.81)
    return 1048 * (1 + 0.00124 * omega_b**-0.738) * (1 + g1 * omega_m**g2)


def z_drag(omega_b: float, omega_m: float) -> float:
    """Redshift of the baryon drag epoch (Eisenstein & Hu 1998 fit)."""
    b1 = 0.313 * omega_m**-0.419 * (1 + 0.607 * omega_m**0.674)
    b2 = 0.238 * omega_m**0.223
    return 1291 * omega_m**0.251 / (1 + 0.659 * omega_m**0.828) * (1 + b1 * omega_b**b2)


def sound_horizon(c: Cosmology, z: float) -> float:
    """Comoving sound horizon at redshift ``z`` [Mpc]: ∫ c_s dt/a before z."""
    omega_b = c.Ob0 * c.h**2
    omega_g = c.Ogamma0 * c.h**2
    a_end = 1.0 / (1.0 + z)

    def integrand(a):
        r = 0.75 * omega_b / omega_g * a
        cs = 1.0 / math.sqrt(3 * (1 + r))
        return cs / math.sqrt(a**4 * c.E2_of_a(a))

    val, _ = integrate.quad(integrand, 0, a_end, limit=200, epsrel=1e-8)
    return val * c.hubble_distance


def acoustic_scale(c: Cosmology) -> dict:
    """Decoupling redshift, sound horizon, distance and angular acoustic scale."""
    omega_b, omega_m = c.Ob0 * c.h**2, c.Om0 * c.h**2
    zs = z_decoupling(omega_b, omega_m)
    rs = sound_horizon(c, zs)
    dm = float(c.transverse_comoving_distance(zs))
    return {
        "z_star": zs,
        "r_s": rs,
        "D_M": dm,
        "theta_star": rs / dm,
        "ell_A": math.pi * dm / rs,
        "R_star": 0.75 * omega_b / (c.Ogamma0 * c.h**2) / (1 + zs),
        "r_drag": drag_sound_horizon(c),
    }


# --------------------------------------------------- power spectrum
def transfer_no_wiggle(c: Cosmology, k):
    """Eisenstein & Hu (1998) zero-baryon-oscillation transfer function, k in h/Mpc."""
    k = np.asarray(k, dtype=float)
    h = c.h
    om, ob = c.Om0, c.Ob0
    omega_m, omega_b = om * h * h, ob * h * h
    fb = ob / om
    theta = c.Tcmb0 / 2.7 if c.Tcmb0 > 0 else const.T_CMB / 2.7
    s = 44.5 * math.log(9.83 / omega_m) / math.sqrt(1 + 10 * omega_b**0.75)  # Mpc
    alpha = 1 - 0.328 * math.log(431 * omega_m) * fb + 0.38 * math.log(22.3 * omega_m) * fb * fb
    k_mpc = k * h
    gamma_eff = om * h * (alpha + (1 - alpha) / (1 + (0.43 * k_mpc * s) ** 4))
    q = k * theta**2 / gamma_eff
    l0 = np.log(2 * math.e + 1.8 * q)
    c0 = 14.2 + 731 / (1 + 62.5 * q)
    return l0 / (l0 + c0 * q * q)


def silk_scale(c: Cosmology) -> float:
    """Silk damping wavenumber [1/Mpc] (Eisenstein & Hu 1998 fit)."""
    h = c.h
    omega_m, omega_b = c.Om0 * h * h, c.Ob0 * h * h
    return 1.6 * omega_b**0.52 * omega_m**0.73 * (1 + (10.4 * omega_m) ** -0.95)


def drag_sound_horizon(c: Cosmology) -> float:
    """Sound horizon at the baryon drag epoch r_d [Mpc] (Aubourg et al. 2015 fit, massless ν)."""
    h = c.h
    omega_m, omega_b = c.Om0 * h * h, c.Ob0 * h * h
    return 55.154 / (omega_m**0.25351 * omega_b**0.12807)


def transfer_eisenstein_hu(c: Cosmology, k):
    """Eisenstein & Hu (1998) transfer function including baryon acoustic oscillations.

    ``k`` in h/Mpc. Accurate to a few percent for ΛCDM-like parameters.
    """
    h = c.h
    k_mpc = np.asarray(k, dtype=float) * h
    omega_m, omega_b = c.Om0 * h * h, c.Ob0 * h * h
    fb = omega_b / omega_m
    fc = 1 - fb
    theta = (c.Tcmb0 if c.Tcmb0 > 0 else const.T_CMB) / 2.7

    z_eq = 2.50e4 * omega_m * theta**-4
    k_eq = 7.46e-2 * omega_m * theta**-2
    zd = z_drag(omega_b, omega_m)
    r_d = 31.5 * omega_b * theta**-4 * (zd / 1e3) ** -1
    r_eq = 31.5 * omega_b * theta**-4 * (z_eq / 1e3) ** -1
    s = (2 / (3 * k_eq) * math.sqrt(6 / r_eq)
         * math.log((math.sqrt(1 + r_d) + math.sqrt(r_d + r_eq)) / (1 + math.sqrt(r_eq))))
    k_silk = silk_scale(c)
    q = k_mpc / (13.41 * k_eq)

    a1 = (46.9 * omega_m) ** 0.670 * (1 + (32.1 * omega_m) ** -0.532)
    a2 = (12.0 * omega_m) ** 0.424 * (1 + (45.0 * omega_m) ** -0.582)
    alpha_c = a1**-fb * a2 ** (-(fb**3))
    bb1 = 0.944 / (1 + (458 * omega_m) ** -0.708)
    bb2 = (0.395 * omega_m) ** -0.0266
    beta_c = 1 / (1 + bb1 * (fc**bb2 - 1))

    def t0(alpha, beta):
        lg = np.log(math.e + 1.8 * beta * q)
        cc = 14.2 / alpha + 386 / (1 + 69.9 * q**1.08)
        return lg / (lg + cc * q * q)

    ks = np.clip(k_mpc * s, 1e-8, None)
    f = 1 / (1 + (ks / 5.4) ** 4)
    t_c = f * t0(1.0, beta_c) + (1 - f) * t0(alpha_c, beta_c)

    y = (1 + z_eq) / (1 + zd)
    sq = math.sqrt(1 + y)
    g_y = y * (-6 * sq + (2 + 3 * y) * math.log((sq + 1) / (sq - 1)))
    alpha_b = 2.07 * k_eq * s * (1 + r_d) ** -0.75 * g_y
    beta_node = 8.41 * omega_m**0.435
    s_tilde = s / (1 + (beta_node / ks) ** 3) ** (1 / 3)
    beta_b = 0.5 + fb + (3 - 2 * fb) * math.sqrt((17.2 * omega_m) ** 2 + 1)
    t_b = (t0(1.0, 1.0) / (1 + (ks / 5.2) ** 2)
           + alpha_b / (1 + (beta_b / ks) ** 3) * np.exp(-((k_mpc / k_silk) ** 1.4)))
    t_b = t_b * np.sinc(k_mpc * s_tilde / math.pi)
    return fb * t_b + fc * t_c


def eisenstein_hu_sound_horizon(c: Cosmology) -> float:
    """Sound horizon s [Mpc] used inside the Eisenstein & Hu transfer function."""
    h = c.h
    omega_m, omega_b = c.Om0 * h * h, c.Ob0 * h * h
    theta = (c.Tcmb0 if c.Tcmb0 > 0 else const.T_CMB) / 2.7
    z_eq = 2.50e4 * omega_m * theta**-4
    k_eq = 7.46e-2 * omega_m * theta**-2
    zd = z_drag(omega_b, omega_m)
    r_d = 31.5 * omega_b * theta**-4 * (zd / 1e3) ** -1
    r_eq = 31.5 * omega_b * theta**-4 * (z_eq / 1e3) ** -1
    return (2 / (3 * k_eq) * math.sqrt(6 / r_eq)
            * math.log((math.sqrt(1 + r_d) + math.sqrt(r_d + r_eq)) / (1 + math.sqrt(r_eq))))


def tophat_window(x):
    x = np.asarray(x, dtype=float)
    small = x < 1e-3
    out = np.empty_like(x)
    xs = x[~small]
    out[~small] = 3 * (np.sin(xs) - xs * np.cos(xs)) / xs**3
    out[small] = 1 - x[small] ** 2 / 10
    return out


class LinearPowerSpectrum:
    """Linear matter power spectrum P(k, z) in (Mpc/h)³, normalised to σ8."""

    def __init__(self, c: Cosmology, n_s: float = 0.9665, sigma8: float = 0.811, wiggles: bool = True):
        self.c, self.n_s, self.sigma8, self.wiggles = c, n_s, sigma8, wiggles
        self._norm = 1.0
        self._norm = (sigma8 / self.sigma_r(8.0)) ** 2

    def shape(self, k):
        k = np.asarray(k, dtype=float)
        t = transfer_eisenstein_hu(self.c, k) if self.wiggles else transfer_no_wiggle(self.c, k)
        return k**self.n_s * t * t

    def __call__(self, k, z: float = 0.0):
        d = growth_factor(self.c, 1 / (1 + z)) if z else 1.0
        return self._norm * self.shape(k) * d * d

    def sigma_r(self, r, z: float = 0.0):
        """RMS linear overdensity in top-hat spheres of radius r [Mpc/h]."""
        k = np.logspace(-4, 2, 3000)
        pk = self(k, z)
        r = np.atleast_1d(np.asarray(r, dtype=float))
        out = np.array([
            math.sqrt(integrate.simpson(k**3 * pk * tophat_window(k * ri) ** 2 / (2 * math.pi**2), x=np.log(k)))
            for ri in r
        ])
        return out if out.size > 1 else float(out[0])

    def correlation_function(self, r, smoothing: float = 2.0):
        """Two-point correlation ξ(r) with Gaussian smoothing [Mpc/h] for convergence."""
        k = np.linspace(1e-4, 3.0, 30000)
        pk = self(k) * np.exp(-((k * smoothing) ** 2))
        r = np.atleast_1d(np.asarray(r, dtype=float))
        kr = np.outer(r, k)
        integrand = k * k * pk * np.sinc(kr / math.pi) / (2 * math.pi**2)
        return integrate.simpson(integrand, x=k, axis=1)

    def mass_of_radius(self, r):
        rho_m = 2.775e11 * self.c.Om0  # mean matter density in (M☉/h) / (Mpc/h)³
        return 4 / 3 * math.pi * np.asarray(r) ** 3 * rho_m

    def radius_of_mass(self, m):
        rho_m = 2.775e11 * self.c.Om0
        return (3 * np.asarray(m) / (4 * math.pi * rho_m)) ** (1 / 3)

    def press_schechter(self, masses, z: float = 0.0):
        """Press–Schechter halo mass function dn/dlnM [(h/Mpc)³] for masses in M☉/h."""
        m = np.asarray(masses, dtype=float)
        r = self.radius_of_mass(m)
        sig = np.asarray(self.sigma_r(r, z))
        dlns = np.gradient(np.log(sig), np.log(m))
        nu = DELTA_C / sig
        rho_m = 2.775e11 * self.c.Om0
        return math.sqrt(2 / math.pi) * rho_m / m * nu * np.abs(dlns) * np.exp(-nu * nu / 2)


def jeans_length(sound_speed_km_s: float, density_kg_m3: float) -> float:
    """Jeans length λ_J = c_s √(π / Gρ) [m]."""
    return sound_speed_km_s * 1e3 * math.sqrt(math.pi / (const.G * density_kg_m3))


def jeans_mass(sound_speed_km_s: float, density_kg_m3: float) -> float:
    """Mass inside a sphere of diameter λ_J [M☉]."""
    lam = jeans_length(sound_speed_km_s, density_kg_m3)
    return 4 / 3 * math.pi * (lam / 2) ** 3 * density_kg_m3 / const.M_SUN


def spherical_bessel_j0(x):
    return special.spherical_jn(0, x)
