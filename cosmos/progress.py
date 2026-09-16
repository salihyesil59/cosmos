"""Learner progress: persistence and recommendations (GUI independent)."""

from __future__ import annotations

import enum
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

from cosmos.content.loader import Curriculum

PASS_SCORE = 0.7


class LessonStatus(enum.Enum):
    COMPLETED = "completed"
    READY = "ready"            # all prerequisites completed
    NOT_READY = "not ready"    # some prerequisites missing (still openable)


@dataclass
class UserData:
    theme: str = "dark"
    tour_completed: bool = False
    default_preset: str = "planck18"
    math_view: str = "full"                                         # "full" or "intuitive" lesson view
    language: str = ""                                              # interface language code; "" follows the system
    last_route: str = "home"
    quiz_best: dict[str, float] = field(default_factory=dict)       # lesson id -> best score 0..1
    completed: dict[str, str] = field(default_factory=dict)         # lesson id -> ISO timestamp
    lessons_opened: list[str] = field(default_factory=list)
    simulators_opened: list[str] = field(default_factory=list)
    notes: dict[str, str] = field(default_factory=dict)             # route -> the learner's own note
    bookmarks: list[str] = field(default_factory=list)              # routes, most recent first
    challenges_done: list[str] = field(default_factory=list)        # "S1/redshift-1100"
    pages_seen: list[str] = field(default_factory=list)             # route kinds the learner has visited
    achievements: dict[str, str] = field(default_factory=dict)      # achievement id -> ISO timestamp

    @classmethod
    def from_dict(cls, data: dict) -> "UserData":
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


class ProgressStore:
    """Reads and writes :class:`UserData` as JSON."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.data = self._load()

    def _load(self) -> UserData:
        try:
            return UserData.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        except (OSError, ValueError, TypeError):
            return UserData()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(asdict(self.data), indent=2), encoding="utf-8")
        os.replace(tmp, self.path)

    def reset(self) -> None:
        """Clear the learning record but keep the learner's own writing and settings."""
        kept = self.data
        self.data = UserData(theme=kept.theme, default_preset=kept.default_preset, tour_completed=True,
                             math_view=kept.math_view, notes=dict(kept.notes),
                             bookmarks=list(kept.bookmarks))
        self.save()

    # ----------------------------------------------------------- recording
    def record_quiz(self, lesson_id: str, score: float) -> bool:
        """Store a quiz result; returns True if this attempt completed the lesson."""
        best = max(score, self.data.quiz_best.get(lesson_id, 0.0))
        self.data.quiz_best[lesson_id] = best
        newly = score >= PASS_SCORE and lesson_id not in self.data.completed
        if newly:
            self.data.completed[lesson_id] = datetime.now().isoformat(timespec="seconds")
        self.save()
        return newly

    def mark_opened(self, kind: str, item_id: str) -> None:
        bucket = self.data.lessons_opened if kind == "lesson" else self.data.simulators_opened
        if item_id not in bucket:
            bucket.append(item_id)
            self.save()

    def mark_page_seen(self, page: str) -> None:
        if page not in self.data.pages_seen:
            self.data.pages_seen.append(page)
            self.save()

    def record_challenge(self, simulator_id: str, challenge_id: str) -> bool:
        """Remember a solved simulator challenge; returns True the first time."""
        key = f"{simulator_id}/{challenge_id}"
        if key in self.data.challenges_done:
            return False
        self.data.challenges_done.append(key)
        self.save()
        return True

    def is_challenge_done(self, simulator_id: str, challenge_id: str) -> bool:
        return f"{simulator_id}/{challenge_id}" in self.data.challenges_done

    # ------------------------------------------------------- achievements
    def refresh_achievements(self, curriculum: Curriculum) -> list[str]:
        """Record any newly earned achievements and return their ids."""
        from cosmos.achievements import ACHIEVEMENTS

        new = []
        for achievement in ACHIEVEMENTS:
            if achievement.id in self.data.achievements:
                continue
            if achievement.is_earned(self, curriculum):
                self.data.achievements[achievement.id] = datetime.now().isoformat(timespec="seconds")
                new.append(achievement.id)
        if new:
            self.save()
        return new

    # ------------------------------------------------ notes and bookmarks
    def note(self, route: str) -> str:
        return self.data.notes.get(route, "")

    def set_note(self, route: str, text: str) -> None:
        text = text.strip()
        if text == self.note(route):
            return
        if text:
            self.data.notes[route] = text
        else:
            self.data.notes.pop(route, None)
        self.save()

    def is_bookmarked(self, route: str) -> bool:
        return route in self.data.bookmarks

    def toggle_bookmark(self, route: str) -> bool:
        """Add or remove a bookmark; returns the new state."""
        if route in self.data.bookmarks:
            self.data.bookmarks.remove(route)
            added = False
        else:
            self.data.bookmarks.insert(0, route)
            added = True
        self.save()
        return added

    def remove_bookmark(self, route: str) -> None:
        if route in self.data.bookmarks:
            self.data.bookmarks.remove(route)
            self.save()

    # ------------------------------------------------------------- queries
    def is_completed(self, lesson_id: str) -> bool:
        return lesson_id in self.data.completed

    def status(self, curriculum: Curriculum, lesson_id: str) -> LessonStatus:
        if self.is_completed(lesson_id):
            return LessonStatus.COMPLETED
        prereqs = curriculum.lessons[lesson_id].prerequisites
        if all(self.is_completed(p) for p in prereqs):
            return LessonStatus.READY
        return LessonStatus.NOT_READY

    def missing_prerequisites(self, curriculum: Curriculum, lesson_id: str) -> list[str]:
        return [p for p in curriculum.lessons[lesson_id].prerequisites if not self.is_completed(p)]

    def next_recommended(self, curriculum: Curriculum) -> str | None:
        """First lesson in course order that is ready but not completed."""
        for lesson_id in curriculum.ordered_ids:
            if self.status(curriculum, lesson_id) is LessonStatus.READY:
                return lesson_id
        for lesson_id in curriculum.ordered_ids:
            if not self.is_completed(lesson_id):
                return lesson_id
        return None

    def level_progress(self, curriculum: Curriculum, level_number: int) -> tuple[int, int]:
        level = next(lv for lv in curriculum.levels if lv.number == level_number)
        done = sum(1 for i in level.lesson_ids if self.is_completed(i))
        return done, len(level.lesson_ids)

    def overall_progress(self, curriculum: Curriculum) -> tuple[int, int]:
        done = sum(1 for i in curriculum.ordered_ids if self.is_completed(i))
        return done, len(curriculum.ordered_ids)

    def average_quiz_score(self) -> float | None:
        scores = list(self.data.quiz_best.values())
        return sum(scores) / len(scores) if scores else None
