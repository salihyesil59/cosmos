"""G23: the study streak, the daily goal and what counts as a step."""

from datetime import date, timedelta

from cosmos import streaks
from cosmos.progress import ProgressStore

DAY = date(2026, 9, 1)


def log(*offsets, steps=3):
    return {(DAY + timedelta(days=o)).isoformat(): steps for o in offsets}


def test_consecutive_days_make_a_streak():
    activity = log(0, 1, 2, 3)
    assert streaks.current_streak(activity, DAY + timedelta(days=3)) == 4
    assert streaks.longest_streak(activity) == 4


def test_one_day_off_is_forgiven_two_are_not():
    forgiven = log(0, 1, 3, 4)                      # day 2 off
    assert streaks.current_streak(forgiven, DAY + timedelta(days=4)) == 4
    broken = log(0, 1, 4, 5)                        # days 2 and 3 off
    assert streaks.current_streak(broken, DAY + timedelta(days=5)) == 2
    assert streaks.longest_streak(broken) == 2


def test_a_streak_survives_until_the_grace_day_is_over():
    activity = log(0, 1, 2)
    assert streaks.current_streak(activity, DAY + timedelta(days=3)) == 3     # not yet studied today
    assert streaks.at_risk(activity, DAY + timedelta(days=3))
    assert streaks.current_streak(activity, DAY + timedelta(days=4)) == 0     # two days off: gone
    assert not streaks.at_risk(activity, DAY + timedelta(days=2))


def test_the_log_is_trimmed_and_the_week_is_listed():
    old = {"2020-01-01": 5, "not a date": 3}
    activity = streaks.record(old, DAY, 2)
    assert activity == {DAY.isoformat(): 2}
    activity = streaks.record(activity, DAY, 1)
    assert streaks.today_steps(activity, DAY) == 3
    week = streaks.week(activity, DAY)
    assert len(week) == 7 and week[-1] == (DAY, 3) and week[0][1] == 0


def test_every_kind_of_study_counts(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    store.record_question("L0.1", 0, True, DAY)        # correct and not in the deck: still a step
    store.record_question("L0.1", 1, False, DAY)
    store.add_flashcards(["parsec"], DAY)
    store.record_flashcard("parsec", True, DAY)
    store.record_problem_attempt("p0-proxima", False)
    store.record_challenge("S1", "cmb-age")
    assert store.data.activity[DAY.isoformat()] == 3       # two questions and a flashcard
    assert sum(store.data.activity.values()) == 5          # the problem and challenge count on the real day
    assert ProgressStore(tmp_path / "p.json").data.activity == store.data.activity   # saved


def test_the_goal(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    assert store.data.daily_goal == streaks.DEFAULT_GOAL
    store.set_daily_goal(5)
    for index in range(5):
        store.record_question("L0.2", index, True, DAY)
    info = store.study_summary(DAY)
    assert info["today"] == 5 and info["goal_met"] and info["streak"] == 1
    store.set_daily_goal(0)
    assert not store.study_summary(DAY)["goal_met"]
    store.reset()
    assert store.data.daily_goal == 0 and store.data.activity == {}


def test_a_badge_for_a_week(tmp_path):
    from cosmos.achievements import BY_ID
    from cosmos.content.loader import load_curriculum

    store = ProgressStore(tmp_path / "p.json")
    store.data.activity = log(0, 1, 2, 4, 5, 6)           # six days studied: not yet
    assert not BY_ID["streak-week"].is_earned(store, load_curriculum())
    store.data.activity = log(0, 1, 2, 4, 5, 6, 7)
    assert BY_ID["streak-week"].is_earned(store, load_curriculum())
