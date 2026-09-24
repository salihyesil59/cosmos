"""Prose that comes out of the physics layer, marked so the interface can translate it.

``cosmos.physics`` knows nothing about Qt or about translations: it returns plain
English for a universe's geometry, its fate and the unit of a time span. Those
strings are marked here, next to the interface that shows them, and translated
with :func:`physics` at the moment they are displayed.

:func:`tests.test_i18n` checks that this table still covers everything the
physics layer can produce, so a new fate or a new unit cannot slip through
untranslated.
"""

from __future__ import annotations

from cosmos.i18n import tr, tr_noop

GEOMETRIES = [tr_noop("flat"), tr_noop("open"), tr_noop("closed")]

FATES = [
    tr_noop("accelerates forever"),
    tr_noop("expands forever"),
    tr_noop("recollapses in a Big Crunch"),
    tr_noop("ends in a Big Rip"),
    tr_noop("has no Big Bang"),
]

FATE_EXPLANATIONS = [
    tr_noop("Dark energy eventually dominates. The expansion speeds up forever and "
            "distant galaxies disappear beyond our horizon."),
    tr_noop("Gravity slows the expansion but never stops it. The universe keeps "
            "growing, ever more slowly."),
    tr_noop("Gravity wins: the expansion stops, reverses, and the universe collapses "
            "back into a hot, dense state."),
    tr_noop("Phantom dark energy (w < −1) grows denser as space expands. The expansion rate "
            "diverges in a finite time and tears apart galaxies, stars and finally atoms."),
    tr_noop("Going back in time the universe never shrinks to zero size: dark energy "
            "is so dominant that it either 'bounces' at a minimum size or has been "
            "expanding forever. Such models contradict observations of "
            "high-redshift objects and the CMB."),
]

# Second probes of the MCMC explorer (inference.PROBES).
PROBES = [
    tr_noop("Supernovae only"),
    tr_noop("No second measurement: the supernovae decide alone."),
    tr_noop("+ CMB geometry (Ωm + ΩΛ = 1.00 ± 0.02)"),
    tr_noop("The acoustic scale of the CMB says space is close to flat: Ωm + ΩΛ ≈ 1."),
    tr_noop("+ BAO matter density (Ωm = 0.30 ± 0.02)"),
    tr_noop("Baryon acoustic oscillations with a sound-horizon prior pin down the matter density."),
]

# Observing programmes of the distance ladder (ladder.PRESETS).
LADDER_PRESETS = [
    tr_noop("Hubble Key Project style (2001)"),
    tr_noop("SH0ES style (2022)"),
    tr_noop("A future Gaia-era ladder"),
]

# Survey programmes and tracers of the Survey Designer (survey.PRESETS_SURVEY, survey.TRACERS).
SURVEYS = [
    tr_noop("BOSS CMASS style (2014)"),
    tr_noop("DESI luminous red galaxies (2021–26)"),
    tr_noop("DESI quasars (2021–26)"),
    tr_noop("Euclid spectroscopic style (2023–29)"),
    tr_noop("A small pilot survey"),
    tr_noop("Bright galaxies (BGS)"),
    tr_noop("The brightest nearby galaxies: dense but only a small volume."),
    tr_noop("Luminous red galaxies (LRG)"),
    tr_noop("Massive, old, strongly clustered galaxies: the classic BAO tracer."),
    tr_noop("Emission-line galaxies (ELG)"),
    tr_noop("Star-forming galaxies with bright [O II] lines: numerous at high redshift, weakly clustered."),
    tr_noop("Quasars (QSO)"),
    tr_noop("Rare but luminous: they reach far, but so few that shot noise dominates."),
    tr_noop("Hα emitters (space infrared)"),
    tr_noop("Galaxies seen in Hα with a slitless spectrograph from space, as Euclid does."),
]

# Mock surveys of the Redshift Survey Slice (mock.PRESETS_MOCK).
MOCK_SURVEYS = [
    tr_noop("CfA2 style: the Great Wall slice (1989)"),
    tr_noop("SDSS main galaxy sample style (2005)"),
    tr_noop("Volume limited: the same density everywhere"),
    tr_noop("Photometric redshifts: colours instead of spectra"),
    tr_noop("The true universe: no observing effects at all"),
]

# Events and detector networks of the Standard Siren Explorer (sirens.PRESETS_SIREN, sirens.NETWORKS).
SIRENS = [
    tr_noop("GW170817: the first standard siren (2017)"),
    tr_noop("GW190425: no counterpart, no host (2019)"),
    tr_noop("A dark siren: black holes, no light"),
    tr_noop("Fifty bright sirens from one observing run"),
    tr_noop("Einstein Telescope: a siren catalogue"),
    tr_noop("Two detectors only"),
    tr_noop("With sites on one continent a merger can be found but barely located: "
            "GW190425 landed in a patch of 8400 deg²."),
    tr_noop("LIGO–Virgo, 2017 (O2)"),
    tr_noop("The network that detected GW170817, with Virgo only just sensitive enough."),
    tr_noop("LIGO–Virgo–KAGRA, 2023 (O4)"),
    tr_noop("Today's network: two LIGO detectors, Virgo and KAGRA."),
    tr_noop("Advanced detectors at design sensitivity"),
    tr_noop("What the current instruments were built to reach."),
    tr_noop("A+ upgrade (late 2020s)"),
    tr_noop("Upgraded mirrors and squeezed light, with LIGO-India joining."),
    tr_noop("Einstein Telescope (2030s)"),
    tr_noop("A ten-kilometre underground triangle: thousands of events a year, out to high redshift."),
]

# The status of a lesson, as LessonStatus spells it.
BACKUP_ERRORS = [
    tr_noop("The file is not valid JSON."),
    tr_noop("The file does not contain a Cosmos backup."),
    tr_noop("The backup was made by a newer version of Cosmos."),
    tr_noop("The backup is damaged."),
]

LESSON_STATUS = [tr_noop("completed"), tr_noop("ready"), tr_noop("not ready")]

# The units format_time() and the zoom simulator can choose.
TIME_UNITS = [
    tr_noop("s"), tr_noop("minutes"), tr_noop("hours"), tr_noop("days"),
    tr_noop("years"), tr_noop("million years"), tr_noop("billion years"),
    tr_noop("seconds"), tr_noop("nanoseconds"),
]


def physics(text: str) -> str:
    """Translate a string that the physics layer produced."""
    return tr(text)
