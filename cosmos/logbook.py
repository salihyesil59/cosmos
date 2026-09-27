"""A trail a failure can be described from (`R4`).

Until now nothing was written down. When the app fell over — and `R1` found a
save file that made it fall over before the window ever appeared — there was a
traceback on standard error, which a packaged build on Windows does not even
show, and then nothing. Somebody could say "it did not open", and that was the
whole of the evidence.

So there is a log beside the progress file, and an unhandled exception is written
to it before the app goes down.

**What is not in it.** Nothing the learner wrote: not a note, not an answer, not
a search. Nothing about the computer beyond the operating system and the versions
needed to read a traceback. Nothing leaves the machine — there is no uploading
here and never has been, and this does not add any. It is a file on disk that a
person can read, and send if they choose to.
"""

from __future__ import annotations

import datetime as _datetime
import platform
import sys
import traceback
from pathlib import Path

from cosmos import APP_NAME, __version__

#: Keep the file small enough to open in a text editor and to paste into a report.
MAX_BYTES = 256 * 1024

#: How much is kept when it is trimmed: the tail, because that is where the
#: failure is.
KEEP_BYTES = 64 * 1024

_path: Path | None = None


def log_path(data_file: Path | str) -> Path:
    """Beside the progress file, where somebody can find it."""
    return Path(data_file).parent / "cosmos.log"


def start(data_file: Path | str) -> Path | None:
    """Open the log and write what a reader of a traceback needs to know."""
    global _path
    path = log_path(data_file)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _trim(path)
        _path = path
    except OSError:
        _path = None                      # a log is never worth failing to start over
        return None
    record(f"{APP_NAME} {__version__} starting")
    record(f"python {sys.version.split()[0]} on {platform.platform()}")
    return path


def current() -> Path | None:
    """Where the log is, once it has been opened."""
    return _path


def record(message: str, error: BaseException | None = None) -> None:
    """Append one line, and a traceback if there is one."""
    if _path is None:
        return
    stamp = _datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [f"{stamp}  {message}"]
    if error is not None:
        lines += ["".join(traceback.format_exception(type(error), error,
                                                     error.__traceback__)).rstrip()]
    try:
        with open(_path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    except OSError:
        pass                              # logging must never be the thing that breaks


def read(limit: int = 8000) -> str:
    """The end of the log, for showing somebody what just happened."""
    if _path is None or not _path.exists():
        return ""
    try:
        text = _path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text if len(text) <= limit else "…\n" + text[-limit:]


def _trim(path: Path) -> None:
    """Keep the tail when the file has grown past what anybody would read."""
    try:
        if path.exists() and path.stat().st_size > MAX_BYTES:
            tail = path.read_text(encoding="utf-8", errors="replace")[-KEEP_BYTES:]
            path.write_text("…earlier entries trimmed…\n" + tail, encoding="utf-8")
    except OSError:
        pass


def install_crash_handler(on_crash=None) -> None:
    """Write down an unhandled exception before the app goes down (`R4`).

    ``on_crash`` is given the exception so the window can say something; if it
    fails in its turn, that is swallowed, because the one job here is that the
    original failure reaches the log.
    """
    previous = sys.excepthook

    def handler(kind, value, tb):
        if issubclass(kind, (KeyboardInterrupt, SystemExit)):
            previous(kind, value, tb)     # not failures; let them through untouched
            return
        record("unhandled error", value)
        if on_crash is not None:
            try:
                on_crash(value)
            except Exception:             # noqa: BLE001 - never mask the real one
                pass
        previous(kind, value, tb)

    sys.excepthook = handler
