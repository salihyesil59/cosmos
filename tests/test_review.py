"""Spaced repetition (G16): the Leitner schedule and the deck in the progress store."""

from datetime import date, timedelta

import pytest

from cosmos import review
from cosmos.progress import ProgressStore

DAY0 = date(2026, 3, 1)


@pytest.fixture
def store(tmp_path):
    return ProgressStore(tmp_path / "p.json")


def test_card_ids_round_trip():
    assert review.card_id("L1.2", 3) == "L1.2#3"
    assert review.split_card_id("L1.2#3") == ("L1.2", 3)
    assert review.split_card_id(review.card_id("L7.5", 0)) == ("L7.5", 0)


def test_a_right_answer_on_a_new_question_creates_nothing():
    assert review.after_answer(None, True, DAY0) is None


def test_a_wrong_answer_brings_the_question_back_tomorrow():
    entry = review.after_answer(None, False, DAY0)
    assert entry["box"] == 1 and entry["lapses"] == 1
    assert date.fromisoformat(entry["due"]) == DAY0 + timedelta(days=1)


def test_the_intervals_grow_and_the_card_finally_leaves():
    entry = review.after_answer(None, False, DAY0)
    waits = []
    today = DAY0
    for _ in range(review.MAX_BOX):
        today = date.fromisoformat(entry["due"])
        entry = review.after_answer(entry, True, today)
        if entry is None:
            break
        waits.append((date.fromisoformat(entry["due"]) - today).days)
    assert entry is None, "a card that passes the last box is learned and leaves the deck"
    assert waits == list(review.BOXES[1:])
    assert waits == sorted(waits), "each interval must be longer than the one before"


def test_a_lapse_sends_the_card_back_to_the_start():
    entry = {"box": 4, "due": DAY0.isoformat(), "lapses": 1}
    after = review.after_answer(entry, False, DAY0)
    assert after["box"] == 1 and after["lapses"] == 2
    assert date.fromisoformat(after["due"]) == DAY0 + timedelta(days=1)


def test_due_and_deck_ordering():
    deck = {
        "L1.1#0": {"box": 1, "due": (DAY0 - timedelta(days=3)).isoformat(), "lapses": 2},
        "L1.2#1": {"box": 2, "due": DAY0.isoformat(), "lapses": 1},
        "L1.3#2": {"box": 3, "due": (DAY0 + timedelta(days=5)).isoformat(), "lapses": 1},
    }
    assert [c.id for c in review.deck(deck, DAY0)] == ["L1.1#0", "L1.2#1", "L1.3#2"]
    assert [c.id for c in review.due(deck, DAY0)] == ["L1.1#0", "L1.2#1"]
    assert review.due(deck, DAY0)[0].days_late(DAY0) == 3
    assert review.due(deck, DAY0 - timedelta(days=10)) == []


def test_the_schedule_puts_everything_overdue_on_today():
    deck = {
        "L1.1#0": {"box": 1, "due": (DAY0 - timedelta(days=9)).isoformat(), "lapses": 1},
        "L1.2#1": {"box": 1, "due": (DAY0 - timedelta(days=1)).isoformat(), "lapses": 1},
        "L1.3#2": {"box": 2, "due": (DAY0 + timedelta(days=3)).isoformat(), "lapses": 1},
        "L1.4#0": {"box": 5, "due": (DAY0 + timedelta(days=99)).isoformat(), "lapses": 1},
    }
    rows = review.upcoming(deck, DAY0)
    assert len(rows) == review.HORIZON_DAYS
    assert rows[0] == (DAY0, 2)                              # both overdue cards land on today
    assert dict(rows)[DAY0 + timedelta(days=3)] == 1
    assert dict(rows)[DAY0 + timedelta(days=13)] == 1        # beyond the horizon, held at the last day
    assert sum(count for _d, count in rows) == len(deck)


def test_summary():
    deck = {
        "L1.1#0": {"box": 1, "due": DAY0.isoformat(), "lapses": 3},
        "L1.1#4": {"box": 2, "due": (DAY0 + timedelta(days=2)).isoformat(), "lapses": 1},
    }
    report = review.summary(deck, DAY0)
    assert report == {"total": 2, "due": 1, "lessons": 1, "lapses": 4,
                      "next_due": DAY0 + timedelta(days=2)}
    assert review.summary({}, DAY0)["next_due"] is None


# ------------------------------------------------------------------ the store
def test_the_store_keeps_the_deck(store):
    assert store.record_question("L1.2", 3, False, DAY0) is True
    # Missing it a second time is a second lapse, but the card is already at the start.
    assert store.record_question("L1.2", 3, False, DAY0) is True
    assert store.data.review["L1.2#3"]["lapses"] == 2
    assert store.data.review["L1.2#3"]["box"] == 1
    # A right answer on a question that never entered the deck changes nothing.
    assert store.record_question("L9.9", 0, True, DAY0) is False
    assert [c.id for c in store.due_reviews(DAY0)] == []
    assert [c.id for c in store.due_reviews(DAY0 + timedelta(days=1))] == ["L1.2#3"]
    assert store.review_summary(DAY0)["total"] == 1

    reloaded = ProgressStore(store.path)
    assert reloaded.data.review == store.data.review


def test_learning_a_card_counts_towards_the_badge(store):
    store.record_question("L1.2", 3, False, DAY0)
    today = DAY0
    for _ in range(review.MAX_BOX):
        today += timedelta(days=40)
        store.record_question("L1.2", 3, True, today)
    assert store.data.review == {}
    assert store.data.review_learned == 1
    # A right answer on a question that is not in the deck must not count again.
    store.record_question("L1.2", 3, True, today)
    assert store.data.review_learned == 1


def test_clearing_a_session_counts_and_forgetting_empties_the_deck(store):
    assert store.record_review_session(3, 2) is False
    assert store.record_review_session(0, 0) is False
    assert store.record_review_session(3, 3) is True
    assert store.data.reviews_cleared == 1

    for index in range(3):
        store.record_question("L1.2", index, False, DAY0)
    store.record_question("L5.1", 0, False, DAY0)
    assert store.forget_reviews("L1.2") == 3
    assert list(store.data.review) == ["L5.1#0"]
    assert store.forget_reviews() == 1
    assert store.data.review == {}


def test_reset_keeps_the_settings_but_drops_the_deck(store):
    store.data.font_scale = 1.3
    store.data.language = "tr"
    store.record_question("L1.2", 3, False, DAY0)
    store.reset()
    assert store.data.review == {}
    assert store.data.font_scale == 1.3 and store.data.language == "tr"
