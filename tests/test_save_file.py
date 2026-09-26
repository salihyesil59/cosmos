"""R1: a save file written badly must not stop the app opening.

A `progress.json` with a value of the wrong type — a list where a dictionary
belongs — used to take the whole app down on start-up with an AttributeError.
That is a file written half way through a save, or restored from a version that
spelled something differently, and the app would not open at all. Losing one
setting is a far smaller thing than losing the app.
"""

from __future__ import annotations

import json
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cosmos.progress import ProgressStore, UserData  # noqa: E402


def written(tmp_path, payload) -> ProgressStore:
    path = tmp_path / "progress.json"
    path.write_text(json.dumps(payload) if not isinstance(payload, str) else payload,
                    encoding="utf-8")
    return ProgressStore(path)


# ------------------------------------------------------------- reading a file

def test_a_missing_file_is_a_first_run(tmp_path):
    store = ProgressStore(tmp_path / "nothing-here.json")
    assert store.data == UserData()
    assert store.dropped == []
    assert store.damaged_copy is None


def test_a_good_file_is_read_whole(tmp_path):
    store = written(tmp_path, {"theme": "light", "completed": {"L1.1": "2026-01-01"},
                               "font_scale": 1.4, "review_learned": 3})
    assert store.data.theme == "light"
    assert store.data.completed == {"L1.1": "2026-01-01"}
    assert store.data.font_scale == 1.4
    assert store.dropped == []


def test_a_value_of_the_wrong_type_is_left_out_rather_than_kept(tmp_path):
    store = written(tmp_path, {"completed": "not a dictionary", "theme": "light"})
    assert store.data.completed == {}, "the bad value reached the app"
    assert store.data.theme == "light", "a good value was thrown away with the bad one"
    assert store.dropped == ["completed"]


@pytest.mark.parametrize("field, bad", [
    ("completed", []), ("quiz_best", 42), ("bookmarks", 5), ("notes", "text"),
    ("review", []), ("theme", 7), ("tour_completed", "yes"), ("font_scale", "big"),
    ("review_learned", 1.5), ("daily_goal", None),
])
def test_every_kind_of_wrong_value_is_survived(tmp_path, field, bad):
    store = written(tmp_path, {field: bad})
    assert field in store.dropped
    assert getattr(store.data, field) == getattr(UserData(), field)


def test_a_whole_number_is_still_a_font_scale(tmp_path):
    """JSON has no float type of its own; 1 is a perfectly good scale."""
    store = written(tmp_path, {"font_scale": 1})
    assert store.data.font_scale == 1
    assert store.dropped == []


def test_true_is_not_a_number(tmp_path):
    """bool is a subclass of int in Python, and a daily goal of True is nonsense."""
    store = written(tmp_path, {"daily_goal": True})
    assert "daily_goal" in store.dropped


def test_unknown_fields_are_ignored_quietly(tmp_path):
    """A file from a newer version should not be reported as damaged."""
    store = written(tmp_path, {"theme": "light", "something_new": 1})
    assert store.data.theme == "light"
    assert store.dropped == []


def test_a_file_that_is_not_json_at_all(tmp_path):
    store = written(tmp_path, "{ this is not json")
    assert store.data == UserData()


def test_a_file_that_is_not_even_a_record(tmp_path):
    store = written(tmp_path, [1, 2, 3])
    assert store.data == UserData()
    assert store.dropped


# --------------------------------------------------------- keeping the pieces

def test_an_unreadable_file_is_put_aside_not_written_over(tmp_path):
    """It is the only copy of somebody's progress; the next save would destroy it."""
    store = written(tmp_path, "{ half a file")
    assert store.damaged_copy is not None
    assert store.damaged_copy.exists()
    assert store.damaged_copy.read_text(encoding="utf-8") == "{ half a file"
    store.data.theme = "light"
    store.save()
    assert store.damaged_copy.read_text(encoding="utf-8") == "{ half a file"
    assert json.loads(store.path.read_text(encoding="utf-8"))["theme"] == "light"


# ------------------------------------------------------------- what it tells you

def test_the_window_opens_on_a_broken_file_and_says_so(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    folder = tmp_path_factory.mktemp("broken")
    (folder / "progress.json").write_text(
        json.dumps({"completed": "not a dictionary", "bookmarks": 5, "theme": "light"}),
        encoding="utf-8")
    os.environ["COSMOS_DATA_DIR"] = str(folder)
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    window = create_window(app)
    try:
        window.show()
        app.processEvents()
        window.navigate("progress")
        app.processEvents()
        assert window.ctx.store.dropped == ["completed", "bookmarks"]
        assert "could not be read" in window.statusBar().currentMessage()
        assert window.ctx.store.data.theme == "light"
    finally:
        window.close()


def test_the_window_says_when_the_whole_file_was_unreadable(tmp_path_factory):
    from PySide6.QtWidgets import QApplication

    folder = tmp_path_factory.mktemp("unreadable")
    (folder / "progress.json").write_text("{ not json", encoding="utf-8")
    os.environ["COSMOS_DATA_DIR"] = str(folder)
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    window = create_window(app)
    try:
        window.show()
        app.processEvents()
        message = window.statusBar().currentMessage()
        assert "progress.damaged.json" in message
    finally:
        window.close()
