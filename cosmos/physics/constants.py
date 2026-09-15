"""Physical constants and unit conversions (SI units).

Values follow CODATA 2018 and IAU 2012/2015 resolutions.
"""

import math

# Fundamental constants
C = 299_792_458.0              # speed of light [m/s]
G = 6.674_30e-11               # gravitational constant [m^3 kg^-1 s^-2]
H_PLANCK = 6.626_070_15e-34    # Planck constant [J s]
HBAR = H_PLANCK / (2 * math.pi)
K_B = 1.380_649e-23            # Boltzmann constant [J/K]
SIGMA_SB = 5.670_374_419e-8    # Stefan-Boltzmann constant [W m^-2 K^-4]
M_PROTON = 1.672_621_923_69e-27  # proton mass [kg]
EV = 1.602_176_634e-19         # electron volt [J]

# Radiation constant a = 4 sigma / c
A_RAD = 4 * SIGMA_SB / C

# Lengths
AU = 149_597_870_700.0          # astronomical unit [m]
LIGHT_YEAR = C * 365.25 * 86_400  # Julian light-year [m]
PARSEC = AU * 648_000 / math.pi  # parsec [m]
KPC = 1e3 * PARSEC
MPC = 1e6 * PARSEC
GPC = 1e9 * PARSEC

# Times
YEAR = 365.25 * 86_400          # Julian year [s]
GYR = 1e9 * YEAR

# Masses
M_SUN = 1.988_47e30             # solar mass [kg]

# Cosmology
T_CMB = 2.7255                  # CMB temperature today [K] (Fixsen 2009)
NEFF = 3.046                    # effective number of neutrino species

# Conversion helpers
KM_S_MPC_TO_SI = 1e3 / MPC      # (km/s/Mpc) -> 1/s


def hubble_to_si(h0_km_s_mpc: float) -> float:
    """Convert a Hubble constant in km/s/Mpc into 1/s."""
    return h0_km_s_mpc * KM_S_MPC_TO_SI
