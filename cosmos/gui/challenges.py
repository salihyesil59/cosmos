"""Checking guided simulator challenges against what the learner actually did (G8)."""

from __future__ import annotations

from cosmos.content.models import Challenge

NUMERIC_KEYS = ("min", "max")


def condition_met(condition: dict, state: dict) -> bool:
    """Is one condition of a challenge satisfied by the simulator's state?"""
    if condition["field"] not in state:
        return False
    value = state[condition["field"]]
    for key, wanted in condition.items():
        if key == "field":
            continue
        if key in NUMERIC_KEYS:
            try:
                number = float(value)
            except (TypeError, ValueError):
                return False
            if key == "min" and number < float(wanted):
                return False
            if key == "max" and number > float(wanted):
                return False
        elif key == "equals":
            if str(value).strip().lower() != str(wanted).strip().lower():
                return False
        elif key == "contains":
            if str(wanted).lower() not in str(value).lower():
                return False
        elif key == "is_true":
            if bool(value) is not bool(wanted):
                return False
        elif key == "is_false":
            if bool(value) is bool(wanted):
                return False
        else:
            raise ValueError(f"unknown challenge condition {key!r}")
    return True


def challenge_met(challenge: Challenge, state: dict) -> bool:
    return all(condition_met(c, state) for c in challenge.check)


def unmet_fields(challenge: Challenge, state: dict) -> list[str]:
    """Fields that still do not match, used to nudge the learner."""
    return [c["field"] for c in challenge.check if not condition_met(c, state)]
