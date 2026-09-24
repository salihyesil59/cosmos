"""Backing up and restoring progress (G21)."""

import json

import pytest

from cosmos import progress
from cosmos.progress import BackupError, ProgressStore


def learner(tmp_path, name="p.json") -> ProgressStore:
    store = ProgressStore(tmp_path / name)
    store.record_quiz("L0.1", 0.9)
    store.record_challenge("S1", "cmb-age")
    store.set_note("lesson:L0.1", "Parsecs are defined by parallax.")
    store.toggle_bookmark("lesson:L0.2")
    store.record_question("L0.1", 2, correct=False)
    return store


def test_a_backup_restores_everything_learned(tmp_path):
    old = learner(tmp_path)
    old.export_backup(tmp_path / "backup.json")

    fresh = ProgressStore(tmp_path / "other.json")
    fresh.data.theme, fresh.data.language, fresh.data.font_scale = "light", "tr", 1.4
    fresh.import_backup(tmp_path / "backup.json")

    assert fresh.is_completed("L0.1")
    assert fresh.is_challenge_done("S1", "cmb-age")
    assert fresh.note("lesson:L0.1") == "Parsecs are defined by parallax."
    assert fresh.is_bookmarked("lesson:L0.2")
    assert fresh.data.review == old.data.review
    # The display settings of this computer are kept.
    assert (fresh.data.theme, fresh.data.language, fresh.data.font_scale) == ("light", "tr", 1.4)
    # And the restore was saved to disk.
    assert ProgressStore(tmp_path / "other.json").is_completed("L0.1")


def test_the_backup_file_says_what_it_is(tmp_path):
    learner(tmp_path).export_backup(tmp_path / "backup.json")
    payload = json.loads((tmp_path / "backup.json").read_text(encoding="utf-8"))
    assert payload["app"] == "Cosmos" and payload["format"] == progress.BACKUP_FORMAT
    assert payload["exported"] and payload["data"]["completed"]


def test_a_plain_progress_file_is_accepted(tmp_path):
    old = learner(tmp_path)
    fresh = ProgressStore(tmp_path / "other.json")
    fresh.import_backup(old.path)
    assert fresh.is_completed("L0.1")


@pytest.mark.parametrize("content, reason", [
    ("not json at all", progress.NOT_JSON),
    ("[1, 2, 3]", progress.NOT_A_BACKUP),
    ('{"hello": "world"}', progress.NOT_A_BACKUP),
    ('{"app": "Other", "format": 1, "data": {"completed": {}}}', progress.NOT_A_BACKUP),
    ('{"app": "Cosmos", "format": 99, "data": {"completed": {}}}', progress.TOO_NEW),
    ('{"app": "Cosmos", "format": 1, "data": {"completed": "yes"}}', progress.DAMAGED),
])
def test_a_bad_file_changes_nothing(tmp_path, content, reason):
    store = learner(tmp_path)
    before = json.loads(store.path.read_text(encoding="utf-8"))
    bad = tmp_path / "bad.json"
    bad.write_text(content, encoding="utf-8")
    with pytest.raises(BackupError) as error:
        store.import_backup(bad)
    assert str(error.value) == reason
    assert json.loads(store.path.read_text(encoding="utf-8")) == before
    assert store.is_completed("L0.1")


def test_every_refusal_can_be_translated():
    from cosmos.gui import labels

    assert set(progress.BACKUP_ERRORS) <= set(labels.BACKUP_ERRORS)
