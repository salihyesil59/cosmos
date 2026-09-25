"""Learner progress: persistence and recommendations (GUI independent)."""

from __future__ import annotations

import enum
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
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
    problems_solved: dict[str, int] = field(default_factory=dict)   # problem id -> attempts it took
    problem_attempts: dict[str, int] = field(default_factory=dict)  # problem id -> attempts so far
    pages_seen: list[str] = field(default_factory=list)             # route kinds the learner has visited
    review: dict[str, dict] = field(default_factory=dict)           # "L1.2#3" -> spaced-repetition card
    review_learned: int = 0                                         # cards that left the deck for good
    reviews_cleared: int = 0                                        # review sessions answered in full
    flashcards: dict[str, dict] = field(default_factory=dict)       # G22: glossary key -> review card
    terms_learned: int = 0                                          # flashcards that left the deck for good
    activity: dict[str, int] = field(default_factory=dict)          # G23: ISO date -> study steps that day
    daily_goal: int = 10                                            # G23: steps per day; 0 = no goal
    font_scale: float = 1.0                                         # interface text size, 0.8 to 1.6
    classroom: bool = False                                         # G19: show teacher notes in lessons
    update_check: str = "ask"                                       # E13: "ask", "on" or "off"
    update_last_checked: str = ""                                   # ISO date of the last look
    achievements: dict[str, str] = field(default_factory=dict)      # achievement id -> ISO timestamp
    panels_open: list[str] = field(default_factory=list)            # side panels left open: "guide", "notes", "tutor"
    nav_hidden: bool = False                                        # the navigation list is folded away (Ctrl+B)
    window_geometry: str = ""                                       # base64 QMainWindow.saveGeometry()
    window_layout: str = ""                                         # base64 QMainWindow.saveState()

    @classmethod
    def from_dict(cls, data: dict) -> UserData:
        known = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**known)


BACKUP_APP = "Cosmos"
BACKUP_FORMAT = 1
# Settings that belong to a computer rather than to a learner: a restored backup keeps
# whatever this machine already uses.
_DEVICE_FIELDS = ("theme", "language", "font_scale", "update_check", "update_last_checked",
                  "panels_open", "nav_hidden", "window_geometry", "window_layout")
_RECORD_FIELDS = ("quiz_best", "completed", "lessons_opened", "simulators_opened", "notes",
                  "bookmarks", "challenges_done", "problems_solved", "review", "achievements", "flashcards")


class BackupError(ValueError):
    """A file chosen for restoring is not a usable Cosmos backup."""


# Why a restore was refused; cosmos.gui.labels marks these for translation.
NOT_JSON = "The file is not valid JSON."
NOT_A_BACKUP = "The file does not contain a Cosmos backup."
TOO_NEW = "The backup was made by a newer version of Cosmos."
DAMAGED = "The backup is damaged."
BACKUP_ERRORS = (NOT_JSON, NOT_A_BACKUP, TOO_NEW, DAMAGED)


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
                             bookmarks=list(kept.bookmarks), language=kept.language,
                             font_scale=kept.font_scale, classroom=kept.classroom,
                             update_check=kept.update_check, daily_goal=kept.daily_goal,
                             panels_open=list(kept.panels_open), nav_hidden=kept.nav_hidden,
                             window_geometry=kept.window_geometry, window_layout=kept.window_layout)
        self.save()

    # ------------------------------------------------------ backup (G21)
    def export_backup(self, path: Path, now: datetime | None = None) -> None:
        """Write the whole learning record, notes included, to one portable file."""
        stamp = (now or datetime.now()).isoformat(timespec="seconds")
        payload = {"app": BACKUP_APP, "format": BACKUP_FORMAT, "exported": stamp,
                   "data": asdict(self.data)}
        Path(path).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def import_backup(self, path: Path) -> UserData:
        """Replace the learning record with a backup; returns the restored data.

        The display settings of this computer (theme, language, text size, update
        check) stay as they are: a backup carries what was learned, not how the
        screen looked. A plain ``progress.json`` is accepted too. Raises
        :class:`BackupError` if the file is not a Cosmos backup.
        """
        try:
            raw = json.loads(Path(path).read_text(encoding="utf-8"))
        except OSError as error:
            raise BackupError(str(error)) from error
        except ValueError as error:
            raise BackupError(NOT_JSON) from error
        if not isinstance(raw, dict):
            raise BackupError(NOT_A_BACKUP)
        if "data" in raw:
            if raw.get("app") != BACKUP_APP:
                raise BackupError(NOT_A_BACKUP)
            if not isinstance(raw.get("format"), int) or raw["format"] > BACKUP_FORMAT:
                raise BackupError(TOO_NEW)
            raw = raw["data"]
        if not isinstance(raw, dict) or not set(raw) & set(_RECORD_FIELDS):
            raise BackupError(NOT_A_BACKUP)
        default = UserData()
        for name, value in raw.items():
            expected = type(getattr(default, name, None))
            if name in UserData.__dataclass_fields__ and not isinstance(value, expected):
                if not (expected is float and isinstance(value, int)):
                    raise BackupError(DAMAGED)
        restored = UserData.from_dict(raw)
        for name in _DEVICE_FIELDS:
            setattr(restored, name, getattr(self.data, name))
        restored.tour_completed = True
        self.data = restored
        self.save()
        return restored

    # ------------------------------------------------ streak and goal (G23)
    def _step(self, today=None, steps: int = 1) -> None:
        """Count study steps for a day. The caller saves."""
        from cosmos import streaks

        self.data.activity = streaks.record(self.data.activity, today or date.today(), steps)

    def study_summary(self, today=None) -> dict:
        """What the home page shows: steps today, the goal, and the streak."""
        from cosmos import streaks

        day = today or date.today()
        activity = self.data.activity
        steps = streaks.today_steps(activity, day)
        goal = self.data.daily_goal
        return {
            "today": steps,
            "goal": goal,
            "goal_met": goal > 0 and steps >= goal,
            "streak": streaks.current_streak(activity, day),
            "longest": streaks.longest_streak(activity),
            "at_risk": streaks.at_risk(activity, day),
            "week": streaks.week(activity, day),
        }

    def set_daily_goal(self, steps: int) -> None:
        self.data.daily_goal = max(int(steps), 0)
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
        self._step()
        self.save()
        return True

    def is_challenge_done(self, simulator_id: str, challenge_id: str) -> bool:
        return f"{simulator_id}/{challenge_id}" in self.data.challenges_done

    def record_problem_attempt(self, problem_id: str, correct: bool) -> bool:
        """Count an attempt at a worked problem; returns True the first time it is solved."""
        if problem_id in self.data.problems_solved:
            return False
        attempts = self.data.problem_attempts.get(problem_id, 0) + 1
        self.data.problem_attempts[problem_id] = attempts
        self._step()
        if correct:
            self.data.problems_solved[problem_id] = attempts
        self.save()
        return correct

    def is_problem_solved(self, problem_id: str) -> bool:
        return problem_id in self.data.problems_solved

    # -------------------------------------------------- spaced repetition
    def record_question(self, lesson_id: str, index: int, correct: bool, today=None) -> bool:
        """Update the review deck after one quiz question. True if the card changed.

        A question answered wrongly joins the deck (or drops back to the first box).
        Answering a card correctly promotes it, and a card that passes the last box
        has been learned and leaves.
        """
        from cosmos import review

        identifier = review.card_id(lesson_id, index)
        before = self.data.review.get(identifier)
        after = review.after_answer(before, correct, today or date.today())
        self._step(today)
        if after == before:
            self.save()
            return False
        if after is None:
            self.data.review.pop(identifier, None)
            if before is not None:
                self.data.review_learned += 1     # it passed the last box and is learned
        else:
            self.data.review[identifier] = after
        self.save()
        return True

    def record_review_session(self, total: int, correct: int) -> bool:
        """Count a review session. True if every question that was due came back right."""
        cleared = total > 0 and correct == total
        if cleared:
            self.data.reviews_cleared += 1
            self.save()
        return cleared

    def due_reviews(self, today=None) -> list:
        """Cards that should be reviewed now, oldest first."""
        from cosmos import review

        return review.due(self.data.review, today or date.today())

    def review_summary(self, today=None) -> dict:
        from cosmos import review

        return review.summary(self.data.review, today or date.today())

    def forget_reviews(self, lesson_id: str | None = None) -> int:
        """Drop cards from the deck; all of them, or only one lesson's."""
        from cosmos import review

        doomed = [k for k in self.data.review
                  if lesson_id is None or review.split_card_id(k)[0] == lesson_id]
        for key in doomed:
            del self.data.review[key]
        if doomed:
            self.save()
        return len(doomed)

    # ------------------------------------------------ flashcards (G22)
    def add_flashcards(self, keys, today=None) -> int:
        """Put glossary terms in the flashcard deck; returns how many were new."""
        from cosmos import review

        stamp = today or date.today()
        added = 0
        for key in keys:
            if key not in self.data.flashcards:
                self.data.flashcards[key] = review.new_term(stamp)
                added += 1
        if added:
            self.save()
        return added

    def remove_flashcard(self, key: str) -> bool:
        if self.data.flashcards.pop(key, None) is None:
            return False
        self.save()
        return True

    def has_flashcard(self, key: str) -> bool:
        return key in self.data.flashcards

    def record_flashcard(self, key: str, knew_it: bool, today=None) -> bool:
        """Move a flashcard after the learner has judged their answer. True if it was learned."""
        from cosmos import review

        before = self.data.flashcards.get(key)
        if before is None:
            return False
        after = review.after_answer(before, knew_it, today or date.today())
        self._step(today)
        if after is None:
            del self.data.flashcards[key]
            self.data.terms_learned += 1
        else:
            self.data.flashcards[key] = after
        self.save()
        return after is None

    def due_flashcards(self, today=None) -> list:
        from cosmos import review

        return review.terms_due(self.data.flashcards, today or date.today())

    def forget_flashcards(self) -> int:
        count = len(self.data.flashcards)
        if count:
            self.data.flashcards.clear()
            self.save()
        return count

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
