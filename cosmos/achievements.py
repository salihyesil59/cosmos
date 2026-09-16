"""Achievements and badges (G13), computed from the learner's own progress.

Every achievement reports its progress as ``(done, goal)`` so the interface can
show a bar for the ones that are still locked. The rules are GUI independent and
read nothing but :class:`~cosmos.progress.ProgressStore` and the curriculum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

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
    Achievement("first-steps", "First steps", "🌱",
                "Complete your first lesson.",
                lambda s, c: (_completed(s, c), 1)),
    Achievement("five-lessons", "Getting your bearings", "🧭",
                "Complete five lessons.",
                lambda s, c: (_completed(s, c), 5)),
    Achievement("halfway", "Halfway to the horizon", "🌗",
                "Complete half of the course.",
                lambda s, c: (_completed(s, c), max(1, len(c.lessons) // 2))),
    Achievement("graduate", "Cosmologist", "🎓",
                "Complete every lesson of the course.",
                lambda s, c: (_completed(s, c), len(c.lessons))),
    Achievement("level-clear", "Level cleared", "🏁",
                "Complete every lesson of one level.",
                lambda s, c: (_levels_completed(s, c), 1)),
    Achievement("all-levels", "Every level", "🗺",
                "Complete every level of the course.",
                lambda s, c: (_levels_completed(s, c), len(c.levels))),
    Achievement("advanced", "Into the deep end", "🔭",
                "Complete the advanced topics of Level 6.",
                lambda s, c: (sum(1 for i in c.levels[-1].lesson_ids if s.is_completed(i)),
                              len(c.levels[-1].lesson_ids))),
    Achievement("perfect-quiz", "Flawless", "💯",
                "Score 100% on a quiz.",
                lambda s, c: (_perfect_quizzes(s), 1)),
    Achievement("five-perfect", "Perfectionist", "✨",
                "Score 100% on five quizzes.",
                lambda s, c: (_perfect_quizzes(s), 5)),
    Achievement("experimenter", "Experimenter", "🧪",
                "Open five different simulators.",
                lambda s, c: (_simulators_opened(s), 5)),
    Achievement("all-simulators", "Master of instruments", "🛠",
                "Open every simulator in the app.",
                lambda s, c: (_simulators_opened(s), _all_simulators())),
    Achievement("challenger", "Challenge accepted", "🎯",
                "Finish a simulator challenge.",
                lambda s, c: (len(s.data.challenges_done), 1)),
    Achievement("challenge-master", "Challenge master", "🏆",
                "Finish every simulator challenge.",
                lambda s, c: (len(s.data.challenges_done), _challenges_total())),
    Achievement("note-taker", "Note-taker", "📝",
                "Write notes on three pages.",
                lambda s, c: (len(s.data.notes), 3)),
    Achievement("curator", "Curator", "⭐",
                "Bookmark five pages.",
                lambda s, c: (len(s.data.bookmarks), 5)),
    Achievement("historian", "Historian", "🏛",
                "Read the history of cosmology from Copernicus to today.",
                lambda s, c: (int("history" in s.data.pages_seen), 1)),
]

BY_ID = {a.id: a for a in ACHIEVEMENTS}


def earned_now(store, curriculum) -> list[Achievement]:
    return [a for a in ACHIEVEMENTS if a.is_earned(store, curriculum)]
