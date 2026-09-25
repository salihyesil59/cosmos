"""Where every number in the app comes from (`V1`).

The course plots two very different kinds of thing. Some of it is real: files of
published measurements, bundled so that the app works offline. The rest the app
makes up — samples drawn to look like a survey, a toy universe evolved under
gravity, a teaching model of the microwave background — and a learner has to be
able to tell which is which without reading the source.

The app already says so at each plot. This module is the other half: one record
of every source, kept beside the code rather than in a document that drifts away
from it. The Reference page renders it, ``tests/test_provenance.py`` checks that
it still matches the files on disk and the simulators that exist, and anyone
reading the repository finds the same list here.

Nothing here imports numpy or Qt, so the record can be read by a test, by a
build script, or by a person, without starting the application.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
EXTERNAL_DIR = DATA_DIR / "external"


@dataclass(frozen=True)
class Measurement:
    """A file of real measurements that ships with the app."""

    file: str                      #: path relative to ``cosmos/data``
    title: str
    holds: str                     #: what is in the file
    archive: str                   #: the release it was taken from
    url: str
    retrieved: str                 #: ISO date
    cite: str                      #: the papers to cite, not this app
    terms: str                     #: how it may be redistributed
    used_by: tuple[str, ...]       #: simulator ids
    prepared: str = ""             #: what was changed; empty when redistributed as published
    caveat: str = ""               #: what the app does *not* do with it
    figures: str = ""              #: lesson figures drawn from it

    @property
    def path(self) -> Path:
        return DATA_DIR / self.file


@dataclass(frozen=True)
class Generated:
    """Data the app invents, and labels as invented wherever it is shown."""

    title: str
    holds: str
    how: str                       #: the recipe, in one or two sentences
    module: str                    #: where the recipe lives
    shown_in: tuple[str, ...]      #: simulator ids, or "" entries for lesson figures
    figures: str = ""              #: lesson figures drawn from it


# --------------------------------------------------------------- real data

MEASUREMENTS: tuple[Measurement, ...] = (
    Measurement(
        file="hubble1929.csv",
        title="Hubble's 1929 galaxies",
        holds="The 24 galaxies of Table 1: distance as Hubble estimated it and radial "
              "velocity corrected for solar motion.",
        archive="Hubble, E. (1929), PNAS 15, 168, Table 1",
        url="https://doi.org/10.1073/pnas.15.3.168",
        retrieved="2026-09-14",
        cite="Hubble 1929, PNAS 15, 168",
        terms="A table typed out of a 1929 paper, long out of copyright.",
        used_by=("S5",),
        caveat="Hubble's distances are too small by a factor of about seven, so a fit to "
               "them gives H0 near 400–500 km/s/Mpc. That error is the point of the "
               "exercise, not a defect of the file.",
        figures="The 1929 diagram in L1.2.",
    ),
    Measurement(
        file="external/PantheonPlusSH0ES.dat",
        title="Pantheon+SH0ES supernovae",
        holds="1701 light curves of 1550 type Ia supernovae with their standardised "
              "magnitudes and distance moduli. The app reads the redshift, `m_b_corr`, "
              "`MU_SH0ES` and the calibrator flag.",
        archive="PantheonPlusSH0ES/DataRelease "
                "(`Pantheon+_Data/4_DISTANCES_AND_COVAR/Pantheon+SH0ES.dat`)",
        url="https://github.com/PantheonPlusSH0ES/DataRelease",
        retrieved="2026-09-16",
        cite="Scolnic et al. 2022, ApJ 938, 113; Brout et al. 2022, ApJ 938, 110; "
             "Riess et al. 2022, ApJ 934, L7",
        terms="A public data release, redistributed unchanged. Cite the papers.",
        used_by=("S16", "S19"),
        caveat="The covariance matrix of the published analysis is not bundled, so every "
               "fit in the app uses diagonal errors only. The numbers you get are close "
               "to the published ones but are teaching fits, not a repeat of the "
               "published cosmology.",
    ),
    Measurement(
        file="external/Rotmod_LTG.zip",
        title="SPARC rotation curves",
        holds="One file per galaxy: radius, observed rotation velocity and its error, and "
              "the velocities expected from gas, disk and bulge alone.",
        archive="SPARC — rotation curves of 175 disk galaxies",
        url="http://astroweb.cwru.edu/SPARC/",
        retrieved="2026-09-16",
        cite="Lelli, McGaugh & Schombert 2016, AJ 152, 157",
        terms="A public archive, redistributed unchanged. Cite the paper.",
        used_by=("S6",),
    ),
    Measurement(
        file="external/SPARC_Lelli2016c.mrt",
        title="SPARC galaxy table",
        holds="Table 1 in machine-readable form: distance, inclination, luminosity, "
              "Hubble type and quality flag for every galaxy in the archive.",
        archive="SPARC — Table 1",
        url="http://astroweb.cwru.edu/SPARC/",
        retrieved="2026-09-16",
        cite="Lelli, McGaugh & Schombert 2016, AJ 152, 157",
        terms="A public archive, redistributed unchanged. Cite the paper.",
        used_by=("S6",),
    ),
    Measurement(
        file="external/wmap_ilc_9yr.npz",
        title="WMAP nine-year sky map",
        holds="The Internal Linear Combination map of the whole sky — nine years in five "
              "frequency bands, combined so that everything without a thermal spectrum "
              "cancels — and the KQ85 analysis mask beside it.",
        archive="NASA LAMBDA, WMAP DR5",
        url="https://lambda.gsfc.nasa.gov/product/wmap/dr5/ilc_map_get.html",
        retrieved="2026-09-23",
        cite="Bennett et al. 2013, ApJS 208, 20; Hinshaw et al. 2013, ApJS 208, 19",
        terms="A NASA public data product. Cite the papers.",
        used_by=("S24",),
        prepared="The published map is HEALPix (nside 512, NESTED). It has been resampled "
                 "onto a 1024 × 512 longitude–latitude grid in galactic coordinates and "
                 "converted from mK to µK, so that the app needs no HEALPix library. "
                 "`tools/fetch_sky_data.py` rebuilds the file from the original.",
        caveat="Resampling costs a little of the finest detail: the grid has an rms of "
               "67 µK outside the mask against the 70 µK of the published map at full "
               "resolution.",
    ),
    Measurement(
        file="external/sdss_slice_dr18.csv",
        title="SDSS DR18 redshift slice",
        holds="25 149 spectroscopic galaxies from the equatorial strip that produced the "
              "first cone diagrams: right ascension, declination, redshift and r-band "
              "Petrosian magnitude.",
        archive="SDSS SkyServer, DR18 spectroscopic galaxies",
        url="https://skyserver.sdss.org/",
        retrieved="2026-09-23",
        cite="Almeida et al. 2023, ApJS 267, 44 (SDSS-IV/V DR18)",
        terms="Public survey data. SDSS asks that its funding acknowledgement be carried "
              "with the data; it is at https://www.sdss.org/.",
        used_by=("S23",),
        prepared="A subset, selected in the SkyServer: 120° < RA < 250°, |dec| < 1.5°, "
                 "0.005 < z < 0.15, with `zWarning = 0`. Magnitudes are −9999 where SDSS "
                 "has none.",
    ),
)


# ---------------------------------------------------------- generated data

GENERATED: tuple[Generated, ...] = (
    Generated(
        title="A modern-looking Hubble sample",
        holds="40 galaxies between 10 and 400 Mpc, to sit beside Hubble's own 24.",
        how="Drawn from a universe with H0 = 70 km/s/Mpc, then given a random peculiar "
            "velocity (σ = 300 km/s) and a 7% distance error, which is what a modern "
            "standard candle costs.",
        module="cosmos.physics.datasets",
        shown_in=("S5",),
    ),
    Generated(
        title="Simulated supernova samples",
        holds="Two samples of type Ia supernovae: one the size and depth of the 1998 "
              "discovery papers, one resembling a modern survey.",
        how="Distance moduli computed in a flat universe with Ωm = 0.3, then scattered "
            "with the measurement errors and redshift distribution of the real surveys, "
            "so the 1998 analysis can be repeated step by step.",
        module="cosmos.physics.supernovae",
        shown_in=("S16", "S19"),
    ),
    Generated(
        title="An illustrative rotation curve",
        holds="The 'observed' curve of a Milky-Way-like spiral, with error bars.",
        how="Generated from a disk, a bulge and a halo, with the flat outer shape real "
            "spirals show. It is the first entry in the galaxy list; every other entry "
            "is a measured SPARC galaxy.",
        module="cosmos.physics.datasets",
        shown_in=("S6",),
        figures="The rotation-curve figure in L3.2 and the MOND comparison in L6.7.",
    ),
    Generated(
        title="The CMB power spectrum",
        holds="The temperature and polarisation spectra that respond to the sliders.",
        how="A teaching model: peak positions follow the real sound horizon and angular "
            "diameter distance, peak heights are approximate to about 15%. Installing "
            "the optional package `camb` switches the simulator to exact spectra from a "
            "Boltzmann code.",
        module="cosmos.physics.cmb",
        shown_in=("S12",),
    ),
    Generated(
        title="Simulated patches of sky",
        holds="A 20° × 20° patch of microwave background with the spots the current "
              "parameters imply.",
        how="A Gaussian random field drawn from the power spectrum above. It is a picture "
            "of the model, not an observation; the real sky is in S24.",
        module="cosmos.physics.cmb",
        shown_in=("S12",),
        figures="The simulated sky patch in L5.1.",
    ),
    Generated(
        title="A toy universe under gravity",
        holds="Particles that start almost uniform and end in filaments, walls and voids.",
        how="A two-dimensional particle-mesh run inside the app: a Gaussian random field "
            "is laid down with the Zel'dovich approximation, gravity is solved on a grid "
            "with Fourier transforms, and the particles are stepped forward in the growth "
            "factor. Two dimensions and at most 192 × 192 particles, against the three "
            "dimensions and billions of a research simulation.",
        module="cosmos.physics.nbody",
        shown_in=("S13",),
        figures="The three snapshots in L5.5.",
    ),
    Generated(
        title="Mock redshift surveys",
        holds="Catalogues of galaxies with positions and redshifts, ready to be analysed "
              "as if they were a survey.",
        how="A lognormal mock: a Gaussian field with the right power spectrum is "
            "exponentiated to make a positive density, galaxies are Poisson-sampled from "
            "it, and the survey's own selection is applied. A lognormal mock, not an "
            "N-body one — which is exactly why S23 puts it beside the real SDSS slice.",
        module="cosmos.physics.mock",
        shown_in=("S21", "S23"),
        figures="The mock chain and the redshift-space map in L7.5.",
    ),
    Generated(
        title="Olbers' star fields",
        holds="The night sky of a universe with a given star density, size and expansion.",
        how="Stars drawn at random through the volume and painted in order of distance, "
            "so the sky fills up as the universe is made older or denser.",
        module="cosmos.physics.olbers",
        shown_in=("S17",),
        figures="The sky-coverage figure in L0.6.",
    ),
    Generated(
        title="The cosmic web illustration",
        holds="The picture of filaments and voids used in the early lessons.",
        how="Points scattered along the edges of a Voronoi tessellation of 110 random "
            "seeds, which is enough to look like filaments and voids in a lesson that "
            "comes long before the physics that makes them. The figure says "
            "'illustration, not real data' in its own title.",
        module="cosmos.gui.rendering.figures",
        shown_in=(),
        figures="The cosmic-web illustration in L1.4.",
    ),
)


# ------------------------------------------------------------------ helpers

def bundled_files() -> set[str]:
    """The data files this record accounts for, relative to ``cosmos/data``."""
    return {m.file for m in MEASUREMENTS}


def measurement_for(file: str) -> Measurement | None:
    return next((m for m in MEASUREMENTS if m.file == file), None)


def sources_for(simulator_id: str) -> tuple[tuple[Measurement, ...], tuple[Generated, ...]]:
    """What a simulator plots: the real files first, then what it generates."""
    return (
        tuple(m for m in MEASUREMENTS if simulator_id in m.used_by),
        tuple(g for g in GENERATED if simulator_id in g.shown_in),
    )

