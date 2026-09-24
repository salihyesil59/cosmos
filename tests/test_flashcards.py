"""Glossary flashcards (G22): the deck, its schedule and the terms of a lesson."""

from datetime import date, timedelta

from cosmos import review
from cosmos.content.loader import load_curriculum, load_glossary
from cosmos.progress import ProgressStore

DAY = date(2026, 3, 1)


def test_a_new_term_is_due_at_once(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    assert store.add_flashcards(["parsec", "redshift"], DAY) == 2
    assert store.add_flashcards(["parsec"], DAY) == 0           # already there
    assert [c.term for c in store.due_flashcards(DAY)] == ["parsec", "redshift"]
    assert store.has_flashcard("parsec")
    assert ProgressStore(tmp_path / "p.json").has_flashcard("redshift")   # saved


def test_the_same_boxes_as_the_quiz_review(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    store.add_flashcards(["parsec"], DAY)
    day = DAY
    for gap in review.BOXES[:-1]:
        assert store.record_flashcard("parsec", True, day) is False
        assert store.data.flashcards["parsec"]["due"] == (day + timedelta(days=review.BOXES[
            store.data.flashcards["parsec"]["box"] - 1])).isoformat()
        day += timedelta(days=gap)
    assert store.record_flashcard("parsec", True, day) is True       # past the last box: learned
    assert not store.has_flashcard("parsec") and store.data.terms_learned == 1


def test_a_missed_term_comes_back_tomorrow(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    store.add_flashcards(["parsec"], DAY)
    store.record_flashcard("parsec", True, DAY)
    store.record_flashcard("parsec", False, DAY + timedelta(days=3))
    entry = store.data.flashcards["parsec"]
    assert entry["box"] == 1 and entry["lapses"] == 1
    assert entry["due"] == (DAY + timedelta(days=4)).isoformat()
    assert store.due_flashcards(DAY + timedelta(days=3)) == []
    assert store.record_flashcard("not-in-deck", True, DAY) is False


def test_removing_and_emptying(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    store.add_flashcards(["parsec", "redshift", "hubble-time"], DAY)
    assert store.remove_flashcard("parsec") and not store.remove_flashcard("parsec")
    assert store.forget_flashcards() == 2 and store.data.flashcards == {}


def test_flashcards_travel_in_a_backup(tmp_path):
    store = ProgressStore(tmp_path / "p.json")
    store.add_flashcards(["parsec"], DAY)
    store.export_backup(tmp_path / "b.json")
    other = ProgressStore(tmp_path / "o.json")
    other.import_backup(tmp_path / "b.json")
    assert other.has_flashcard("parsec")


def test_the_terms_of_a_lesson():
    curriculum, glossary = load_curriculum(), load_glossary()
    lesson = curriculum.lessons["L0.2"]
    terms = review.lesson_terms(lesson.body, lesson.id, glossary)
    assert terms and all(key in glossary for key in terms)
    assert len(terms) == len(set(terms))
    assert "parsec" in terms
    # Every lesson with glossary links offers some terms.
    for lesson in curriculum.lessons.values():
        if "[[" in lesson.body:
            assert review.lesson_terms(lesson.body, lesson.id, glossary), lesson.id


def test_a_badge_for_learned_terms(tmp_path):
    from cosmos.achievements import BY_ID

    store = ProgressStore(tmp_path / "p.json")
    curriculum = load_curriculum()
    assert not BY_ID["lexicon"].is_earned(store, curriculum)
    store.data.terms_learned = 10
    assert BY_ID["lexicon"].is_earned(store, curriculum)
