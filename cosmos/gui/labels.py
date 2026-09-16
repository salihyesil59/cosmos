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

# The status of a lesson, as LessonStatus spells it.
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
