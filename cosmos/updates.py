"""Checking whether a newer Cosmos has been released (E13).

Three rules, and they are the whole design:

* **Opt in.** The check is off until somebody turns it on, and turning it on is a
  question the app asks once, in plain language, with "not now" as the default.
* **No telemetry.** The request is a plain GET for a public release listing. Nothing
  about the learner, the machine or their progress is sent, and there is no
  identifier of any kind — not even a count.
* **It never blocks.** The check runs on a worker thread, at most once a day, and a
  failure is silent. An app that cannot start because a server is down is worse than
  an app one version behind.

The network code lives in :func:`fetch_latest`; everything else here is pure logic so
it can be tested without touching the network.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from urllib.request import Request, urlopen

RELEASES_URL = "https://api.github.com/repos/salihyesil59/cosmos/releases/latest"
RELEASE_PAGE = "https://github.com/salihyesil59/cosmos/releases/latest"
TIMEOUT_SECONDS = 6.0
CHECK_EVERY_DAYS = 1

_VERSION = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?")


def parse_version(text: str) -> tuple[int, int, int]:
    """Turn "v1.4" or "1.4.2-beta" into a comparable triple. Unparseable is (0, 0, 0)."""
    match = _VERSION.search(text or "")
    if not match:
        return (0, 0, 0)
    return tuple(int(part) if part else 0 for part in match.groups())        # type: ignore[return-value]


def is_newer(candidate: str, current: str) -> bool:
    return parse_version(candidate) > parse_version(current)


@dataclass(frozen=True)
class Release:
    version: str
    url: str
    notes: str = ""

    @property
    def short_notes(self) -> str:
        """The first paragraph, trimmed — release notes can be very long."""
        first = (self.notes or "").strip().split("\n\n")[0].strip()
        return first if len(first) <= 400 else first[:397] + "…"


def should_check(enabled: bool, last_checked: str, today: date | None = None) -> bool:
    """True if the app may look today. Off means never; otherwise once a day."""
    if not enabled:
        return False
    today = today or date.today()
    try:
        previous = date.fromisoformat(last_checked)
    except (TypeError, ValueError):
        return True
    return today - previous >= timedelta(days=CHECK_EVERY_DAYS)


def fetch_latest(url: str = RELEASES_URL, timeout: float = TIMEOUT_SECONDS) -> Release | None:
    """Ask the release listing what the newest version is. None on any failure.

    This is the only function here that touches the network, and it sends nothing but
    the request itself: no query string, no identifier, no user agent beyond the name
    of the app.
    """
    request = Request(url, headers={"Accept": "application/vnd.github+json",
                                    "User-Agent": "Cosmos"})
    try:
        with urlopen(request, timeout=timeout) as response:      # noqa: S310 (fixed https URL)
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:            # network, DNS, JSON, anything: staying quiet is correct
        return None
    version = str(payload.get("tag_name") or payload.get("name") or "").strip()
    if not version:
        return None
    return Release(version=version,
                   url=str(payload.get("html_url") or RELEASE_PAGE),
                   notes=str(payload.get("body") or ""))


def check(current_version: str, url: str = RELEASES_URL) -> Release | None:
    """The newest release, but only if it is newer than what is running."""
    latest = fetch_latest(url)
    if latest is None or not is_newer(latest.version, current_version):
        return None
    return latest
