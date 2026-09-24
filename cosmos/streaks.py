"""A study streak and a gentle daily goal (G23).

Every time the learner does something that makes them think — answers a quiz
question, reviews a card, turns a flashcard, tries a worked problem, solves a
simulator challenge — one step is counted for that day. Two numbers come out of
that log:

* **the daily goal**: steps today against a target the learner chooses (or none);
* **the streak**: how many days in a row they have studied at all.

The streak is deliberately forgiving. A single day off between two study days does
not break it — life happens — although the day off is not counted either. Two days
off in a row start it again. The point is a habit, not a punishment.

Pure logic: no Qt, no storage. The log lives in ``UserData.activity`` as
``{"2026-09-24": 12, ...}``.
"""

from __future__ import annotations

from datetime import date, timedelta

GOALS = (0, 5, 10, 20, 40)           # steps per day; 0 switches the goal off
DEFAULT_GOAL = 10
GRACE_DAYS = 1                       # days off that do not break a streak
KEEP_DAYS = 400                      # the log is trimmed to about a year


def record(activity: dict[str, int], today: date, steps: int = 1) -> dict[str, int]:
    """The log with ``steps`` more on ``today``, and anything older than a year dropped."""
    key = today.isoformat()
    out = {k: v for k, v in activity.items() if _parse(k) and _parse(k) > today - timedelta(days=KEEP_DAYS)}
    out[key] = out.get(key, 0) + steps
    return out


def _parse(value: str) -> date | None:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def active_days(activity: dict[str, int]) -> list[date]:
    days = [_parse(k) for k, v in activity.items() if v > 0]
    return sorted(d for d in days if d is not None)


def _runs(days: list[date]) -> list[tuple[date, date, int]]:
    """Streaks as (first day, last day, days studied), allowing the grace gap."""
    runs: list[tuple[date, date, int]] = []
    for day in days:
        if runs and (day - runs[-1][1]).days <= GRACE_DAYS + 1:
            first, _last, count = runs[-1]
            runs[-1] = (first, day, count + 1)
        else:
            runs.append((day, day, 1))
    return runs


def current_streak(activity: dict[str, int], today: date) -> int:
    """Days studied in the streak that is still alive today (0 if it has lapsed)."""
    runs = _runs([d for d in active_days(activity) if d <= today])
    if not runs:
        return 0
    _first, last, count = runs[-1]
    return count if (today - last).days <= GRACE_DAYS else 0


def longest_streak(activity: dict[str, int]) -> int:
    return max((count for _f, _l, count in _runs(active_days(activity))), default=0)


def at_risk(activity: dict[str, int], today: date) -> bool:
    """True if there is a streak that ends unless the learner studies today."""
    return current_streak(activity, today) > 0 and activity.get(today.isoformat(), 0) == 0


def today_steps(activity: dict[str, int], today: date) -> int:
    return int(activity.get(today.isoformat(), 0))


def week(activity: dict[str, int], today: date) -> list[tuple[date, int]]:
    """The last seven days, oldest first, with their steps."""
    return [(today - timedelta(days=i), int(activity.get((today - timedelta(days=i)).isoformat(), 0)))
            for i in range(6, -1, -1)]
