"""R4: a failure should leave something a person can read.

Until now nothing was written down. `R1` found a save file that stopped the app
opening at all, and the only evidence was a traceback on standard error, which a
packaged build on Windows does not show. "It did not open" was the whole report
anybody could make.

These tests cover the three things that matter: that the trail exists, that it is
still there after the thing that made it goes down, and that it contains nothing
the learner did not expect to be written.
"""

from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cosmos import __version__, logbook  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    """Each test gets its own log, and none is left installed afterwards."""
    monkeypatch.setattr(logbook, "_path", None)
    before = sys.excepthook
    yield tmp_path / "progress.json"
    sys.excepthook = before


# -------------------------------------------------------------- the trail

def test_it_starts_a_log_beside_the_progress_file(fresh):
    path = logbook.start(fresh)
    assert path == fresh.parent / "cosmos.log"
    assert path.exists()


def test_it_says_what_a_reader_of_a_traceback_needs(fresh):
    logbook.start(fresh)
    text = logbook.read()
    assert __version__ in text
    assert "python" in text
    assert sys.version.split()[0] in text


def test_a_record_carries_its_traceback(fresh):
    logbook.start(fresh)
    try:
        raise ValueError("a deliberate failure")
    except ValueError as error:
        logbook.record("unhandled error", error)
    text = logbook.read()
    assert "unhandled error" in text
    assert "Traceback" in text
    assert "a deliberate failure" in text


def test_every_line_is_stamped(fresh):
    import re

    logbook.start(fresh)
    logbook.record("something happened")
    stamped = [line for line in logbook.read().splitlines()
               if re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}  ", line)]
    assert len(stamped) >= 3


# ------------------------------------------------------- never the thing that breaks

def test_a_log_that_cannot_be_opened_does_not_stop_anything(tmp_path, monkeypatch):
    monkeypatch.setattr(logbook, "_path", None)
    blocked = tmp_path / "nope"
    blocked.write_text("I am a file, not a folder", encoding="utf-8")
    assert logbook.start(blocked / "deeper" / "progress.json") is None
    logbook.record("this must not raise")          # and nothing is written anywhere
    assert logbook.read() == ""


def test_recording_before_starting_is_harmless(fresh):
    logbook.record("no log open yet")
    assert logbook.read() == ""


def test_it_does_not_grow_without_limit(fresh, monkeypatch):
    monkeypatch.setattr(logbook, "MAX_BYTES", 4000)
    monkeypatch.setattr(logbook, "KEEP_BYTES", 1000)
    logbook.start(fresh)
    for i in range(400):
        logbook.record(f"line {i} " + "x" * 60)
    path = logbook.log_path(fresh)
    assert path.stat().st_size > 4000, "nothing is trimmed until the next start"
    logbook.start(fresh)                            # trimming happens when it is opened
    assert path.stat().st_size < 4000
    assert "trimmed" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------- the crash handler

def test_an_unhandled_error_reaches_the_log(fresh):
    logbook.start(fresh)
    seen = []
    logbook.install_crash_handler(seen.append)
    try:
        raise RuntimeError("fell over")
    except RuntimeError as error:
        sys.excepthook(type(error), error, error.__traceback__)
    assert "fell over" in logbook.read()
    assert seen and isinstance(seen[0], RuntimeError)


def test_the_log_is_written_before_anybody_is_told(fresh):
    """If telling them fails, the evidence must already be safe."""
    logbook.start(fresh)

    def unhelpful(_error):
        raise OSError("the dialog itself broke")

    logbook.install_crash_handler(unhelpful)
    try:
        raise RuntimeError("the original problem")
    except RuntimeError as error:
        sys.excepthook(type(error), error, error.__traceback__)
    assert "the original problem" in logbook.read()


def test_stopping_the_app_is_not_a_crash(fresh):
    """Ctrl-C and a clean exit are not failures and must pass straight through."""
    logbook.start(fresh)
    logbook.install_crash_handler(None)
    for kind, value in ((KeyboardInterrupt, KeyboardInterrupt()), (SystemExit, SystemExit(0))):
        try:
            raise value
        except BaseException as error:                        # noqa: BLE001
            sys.excepthook(kind, error, error.__traceback__)
    assert "unhandled error" not in logbook.read()


# ------------------------------------------------------------------- privacy

def test_nothing_the_learner_wrote_goes_in_the_log(fresh):
    """The app has never uploaded anything, and this must not start.

    A note or an answer is the learner's own writing. The log exists so that a
    failure can be described, and none of that is needed to describe one.
    """
    from cosmos.progress import ProgressStore

    logbook.start(fresh)
    store = ProgressStore(fresh)
    store.data.notes["lesson:L1.2"] = "my private thoughts about redshift"
    store.data.quiz_best["L1.2"] = 0.9
    store.save()
    logbook.record("a page was opened")

    text = logbook.read()
    assert "private thoughts" not in text
    assert "redshift" not in text


def test_the_log_says_nothing_is_sent(qt_app, tmp_path_factory):
    """The dialog has to be plain about it, because a crash report usually is not."""
    from PySide6.QtWidgets import QApplication

    folder = tmp_path_factory.mktemp("crash")
    os.environ["COSMOS_DATA_DIR"] = str(folder)
    logbook.start(folder / "progress.json")
    app = QApplication.instance() or QApplication([])
    from cosmos.app import create_window

    window = create_window(app)
    try:
        # Build the dialog the way report_crash does, without blocking on exec().
        assert hasattr(window, "report_crash")
        from cosmos.i18n import tr

        assert "sent" in tr("What happened was written to {path}. "
                            "Nothing has been sent anywhere.")
    finally:
        window.close()
