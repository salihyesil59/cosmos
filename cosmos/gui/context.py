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
    notesChanged = Signal()          # a note or bookmark was added, edited or removed
    achievementsUnlocked = Signal(list)  # ids of achievements earned just now


@dataclass
class AppContext:
    curriculum: Curriculum
    glossary: dict[str, GlossaryTerm]
    store: ProgressStore
    signals: AppSignals

    def navigate(self, route: str) -> None:
        self.signals.navigate.emit(route)
