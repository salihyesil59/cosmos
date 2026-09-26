"""Shared application state handed to pages."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal

from cosmos.content.loader import Curriculum
from cosmos.content.models import GlossaryTerm
from cosmos.progress import ProgressStore


class AppSignals(QObject):
    navigate = Signal(str)          # route string, e.g. "lesson:L1.2"
    progressChanged = Signal()
    glossaryRequested = Signal(str)  # show a term in the Guide panel
    guideRequested = Signal()        # V3: open the Guide panel at the page it already holds
    notesChanged = Signal()          # a note or bookmark was added, edited or removed
    achievementsUnlocked = Signal(list)  # ids of achievements earned just now
    statusMessage = Signal(str)     # a line for the status bar, from any page
    updateFound = Signal(str, str, str, bool)   # E13: version, url, notes, asked-for-it


@dataclass
class AppContext:
    curriculum: Curriculum
    glossary: dict[str, GlossaryTerm]
    store: ProgressStore
    signals: AppSignals
    plugins: object = None          # E14: what the plugins folder produced, if anything

    def navigate(self, route: str) -> None:
        self.signals.navigate.emit(route)
