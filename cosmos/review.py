"""Spaced repetition: bringing back the quiz questions you got wrong (G16).

Getting a question wrong once and moving on teaches very little. The fix is old and
well tested: see the question again tomorrow, and if you get it right, again in three
days, then a week later, then a fortnight. Each correct answer moves the card up a
box and pushes the next review further out; a wrong answer sends it back to the
first box. A card that survives the last box has been learned and leaves the deck.

This module is the scheduling logic only — no Qt, no storage. The deck lives in
:class:`cosmos.progress.UserData` as ``review``, a mapping from card id to a small
record, and :class:`cosmos.progress.ProgressStore` is what writes to it.

Glossary flashcards (G22) use exactly the same boxes and the same records. They live
in a deck of their own, ``flashcards``, keyed by glossary term, because they get into
it differently: a quiz question joins when you get it wrong, a term when you choose to
learn it — and then it is due at once, since you have not seen it as a card yet.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

# Days to wait before showing a card again, one entry per box. A card in the last
# box has been answered correctly four times in a row and is retired.
BOXES: tuple[int, ...] = (1, 3, 7, 16, 35)
MAX_BOX = len(BOXES)
HORIZON_DAYS = 14                     # how far ahead the review page looks


def card_id(lesson_id: str, index: int) -> str:
    """One question of one lesson, as a single string key."""
    return f"{lesson_id}#{index}"


def split_card_id(identifier: str) -> tuple[str, int]:
    lesson_id, _, index = identifier.rpartition("#")
    return lesson_id, int(index)


def due_date(box: int, today: date) -> date:
    """When a card in ``box`` should next be seen."""
    return today + timedelta(days=BOXES[min(max(box, 1), MAX_BOX) - 1])


@dataclass(frozen=True)
class Card:
    """A question waiting in the deck."""

    lesson_id: str
    index: int
    box: int
    due: date
    lapses: int

    @property
    def id(self) -> str:
        return card_id(self.lesson_id, self.index)

    def is_due(self, today: date) -> bool:
        return self.due <= today

    def days_late(self, today: date) -> int:
        return max((today - self.due).days, 0)


def _to_date(value: str, fallback: date) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return fallback


def to_card(identifier: str, entry: dict, today: date) -> Card:
    lesson_id, index = split_card_id(identifier)
    return Card(
        lesson_id=lesson_id,
        index=index,
        box=int(entry.get("box", 1)),
        due=_to_date(entry.get("due", ""), today),
        lapses=int(entry.get("lapses", 1)),
    )


def after_answer(entry: dict | None, correct: bool, today: date) -> dict | None:
    """The new record for a card after it has been answered.

    A wrong answer puts the card in box 1 and counts a lapse. A correct answer moves
    it up one box; past the last box it is learned and ``None`` retires it from the
    deck. Answering correctly a question that is not in the deck changes nothing.
    """
    if entry is None:
        if correct:
            return None
        return {"box": 1, "due": due_date(1, today).isoformat(), "lapses": 1,
                "seen": today.isoformat()}
    if not correct:
        return {"box": 1, "due": due_date(1, today).isoformat(),
                "lapses": int(entry.get("lapses", 0)) + 1, "seen": today.isoformat()}
    box = int(entry.get("box", 1)) + 1
    if box > MAX_BOX:
        return None
    return {"box": box, "due": due_date(box, today).isoformat(),
            "lapses": int(entry.get("lapses", 0)), "seen": today.isoformat()}


def deck(review: dict[str, dict], today: date) -> list[Card]:
    """Every card in the deck, soonest due first."""
    cards = [to_card(identifier, entry, today) for identifier, entry in review.items()]
    return sorted(cards, key=lambda c: (c.due, c.lesson_id, c.index))


def due(review: dict[str, dict], today: date) -> list[Card]:
    """The cards that should be reviewed now, the most overdue first."""
    ready = [c for c in deck(review, today) if c.is_due(today)]
    return sorted(ready, key=lambda c: (c.due, c.box, c.lesson_id, c.index))


def upcoming(review: dict[str, dict], today: date, days: int = HORIZON_DAYS) -> list[tuple[date, int]]:
    """How many cards fall due on each of the next ``days`` days.

    Anything already overdue is counted on the first day, which is where it belongs:
    the deck does not forget.
    """
    counts = {today + timedelta(days=i): 0 for i in range(days)}
    horizon = today + timedelta(days=days - 1)
    for card in deck(review, today):
        when = min(max(card.due, today), horizon)
        if when in counts:
            counts[when] += 1
    return sorted(counts.items())


def summary(review: dict[str, dict], today: date) -> dict:
    """The numbers the review page and the toolbar badge show."""
    cards = deck(review, today)
    ready = [c for c in cards if c.is_due(today)]
    return {
        "total": len(cards),
        "due": len(ready),
        "lessons": len({c.lesson_id for c in cards}),
        "lapses": sum(c.lapses for c in cards),
        "next_due": min((c.due for c in cards if not c.is_due(today)), default=None),
    }


# ------------------------------------------------------------ flashcards (G22)
@dataclass(frozen=True)
class TermCard:
    """A glossary term waiting in the flashcard deck."""

    term: str
    box: int
    due: date
    lapses: int

    def is_due(self, today: date) -> bool:
        return self.due <= today


def new_term(today: date) -> dict:
    """The record of a term that has just been added: in the first box, due today."""
    return {"box": 1, "due": today.isoformat(), "lapses": 0, "seen": ""}


def term_deck(flashcards: dict[str, dict], today: date) -> list[TermCard]:
    cards = [TermCard(term=key, box=int(entry.get("box", 1)), due=_to_date(entry.get("due", ""), today),
                      lapses=int(entry.get("lapses", 0)))
             for key, entry in flashcards.items()]
    return sorted(cards, key=lambda c: (c.due, c.box, c.term))


def terms_due(flashcards: dict[str, dict], today: date) -> list[TermCard]:
    return [c for c in term_deck(flashcards, today) if c.is_due(today)]


def lesson_terms(body: str, lesson_id: str, glossary: dict) -> list[str]:
    """The glossary terms a lesson uses or explains, in the order they first appear."""
    import re

    keys = []
    for key in re.findall(r"\[\[([\w-]+)", body):
        if key in glossary and key not in keys:
            keys.append(key)
    for key, term in glossary.items():
        if lesson_id in getattr(term, "lessons", ()) and key not in keys:
            keys.append(key)
    return keys

