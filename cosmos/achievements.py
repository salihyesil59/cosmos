"""Achievements and badges (G13), computed from the learner's own progress.

Every achievement reports its progress as ``(done, goal)`` so the interface can
show a bar for the ones that are still locked. The rules are GUI independent and
read nothing but :class:`~cosmos.progress.ProgressStore` and the curriculum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cosmos.i18n import tr_noop as _

PERFECT_SCORE = 0.999      # floating-point safe "100%"


@dataclass(frozen=True)
class Achievement:
    id: str
    title: str
    icon: str
    description: str
    progress: Callable[["object", "object"], tuple[int, int]]

    def state(self, store, curriculum) -> tuple[int, int]:
        done, goal = self.progress(store, curriculum)
        return min(done, goal), goal

    def is_earned(self, store, curriculum) -> bool:
        done, goal = self.state(store, curriculum)
        return done >= goal


def _completed(store, curriculum) -> int:
    return store.overall_progress(curriculum)[0]


def _perfect_quizzes(store) -> int:
    return sum(1 for score in store.data.quiz_best.values() if score >= PERFECT_SCORE)


def _levels_completed(store, curriculum) -> int:
    return sum(1 for level in curriculum.levels
               if all(store.is_completed(i) for i in level.lesson_ids))


def _simulators_opened(store) -> int:
    from cosmos.gui.simulators.registry import SIMULATORS

    return len([s for s in store.data.simulators_opened if s in SIMULATORS])


def _all_simulators() -> int:
    from cosmos.gui.simulators.registry import SIMULATORS

    return len(SIMULATORS)


def _challenges_total() -> int:
    from cosmos.content.loader import load_challenges

    return sum(len(steps) for steps in load_challenges().values())


ACHIEVEMENTS: list[Achievement] = [
    Achievement("first-steps", _("First steps"), "🌱",
                _("Complete your first lesson."),
                lambda s, c: (_completed(s, c), 1)),
    Achievement("five-lessons", _("Getting your bearings"), "🧭",
                _("Complete five lessons."),
                lambda s, c: (_completed(s, c), 5)),
    Achievement("halfway", _("Halfway to the horizon"), "🌗",
                _("Complete half of the course."),
                lambda s, c: (_completed(s, c), max(1, len(c.lessons) // 2))),
    Achievement("graduate", _("Cosmologist"), "🎓",
                _("Complete every lesson of the course."),
                lambda s, c: (_completed(s, c), len(c.lessons))),
    Achievement("level-clear", _("Level cleared"), "🏁",
                _("Complete every lesson of one level."),
                lambda s, c: (_levels_completed(s, c), 1)),
    Achievement("all-levels", _("Every level"), "🗺",
                _("Complete every level of the course."),
                lambda s, c: (_levels_completed(s, c), len(c.levels))),
    Achievement("advanced", _("Into the deep end"), "🔭",
                _("Complete the advanced topics of Level 6."),
                lambda s, c: (sum(1 for i in c.levels[-1].lesson_ids if s.is_completed(i)),
                              len(c.levels[-1].lesson_ids))),
    Achievement("perfect-quiz", _("Flawless"), "💯",
                _("Score 100% on a quiz."),
                lambda s, c: (_perfect_quizzes(s), 1)),
    Achievement("five-perfect", _("Perfectionist"), "✨",
                _("Score 100% on five quizzes."),
                lambda s, c: (_perfect_quizzes(s), 5)),
    Achievement("experimenter", _("Experimenter"), "🧪",
                _("Open five different simulators."),
                lambda s, c: (_simulators_opened(s), 5)),
    Achievement("all-simulators", _("Master of instruments"), "🛠",
                _("Open every simulator in the app."),
                lambda s, c: (_simulators_opened(s), _all_simulators())),
    Achievement("challenger", _("Challenge accepted"), "🎯",
                _("Finish a simulator challenge."),
                lambda s, c: (len(s.data.challenges_done), 1)),
    Achievement("challenge-master", _("Challenge master"), "🏆",
                _("Finish every simulator challenge."),
                lambda s, c: (len(s.data.challenges_done), _challenges_total())),
    Achievement("note-taker", _("Note-taker"), "📝",
                _("Write notes on three pages."),
                lambda s, c: (len(s.data.notes), 3)),
    Achievement("curator", _("Curator"), "⭐",
                _("Bookmark five pages."),
                lambda s, c: (len(s.data.bookmarks), 5)),
    Achievement("historian", _("Historian"), "🏛",
                _("Read the history of cosmology from Copernicus to today."),
                lambda s, c: (int("history" in s.data.pages_seen), 1)),
]

BY_ID = {a.id: a for a in ACHIEVEMENTS}


def earned_now(store, curriculum) -> list[Achievement]:
    return [a for a in ACHIEVEMENTS if a.is_earned(store, curriculum)]
