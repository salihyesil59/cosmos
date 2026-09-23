"""The application icon, shared by the window and the packaged executable."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

ICON_PATH = Path(__file__).resolve().parent / "resources" / "cosmos.ico"


def app_icon() -> QIcon:
    """The Cosmos icon, or an empty icon if the file is missing."""
    return QIcon(str(ICON_PATH)) if ICON_PATH.exists() else QIcon()
