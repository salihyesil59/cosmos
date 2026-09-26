"""A flashcard session for glossary terms (G22).

The card shows a term; the learner tries to recall what it means, turns the card
over and says honestly whether they knew it. That self-judgement drives the same
spaced-repetition boxes as the quiz review: "I knew it" moves the card on, "I did
not" sends it back to tomorrow.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cosmos.gui import nav_icons
from cosmos.gui.widgets.common import card, muted_label, title_label
from cosmos.i18n import tr


@dataclass(frozen=True)
class Flashcard:
    key: str
    term: str
    definition: str
    related: str = ""          # names of related terms, for a nudge after turning over


class FlashcardSession(QWidget):
    answered = Signal(str, bool)          # glossary key, knew it
    finished = Signal(int, int)           # cards seen, cards known
    back = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.cards: list[Flashcard] = []
        self.position = 0
        self.known = 0
        self.revealed = False

        self.setFocusPolicy(Qt.StrongFocus)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        self.counter = muted_label("")
        root.addWidget(self.counter)

        self.face = card()
        face = QVBoxLayout(self.face)
        face.setContentsMargins(28, 24, 28, 24)
        face.setSpacing(12)
        self.term_label = title_label("")
        self.term_label.setAlignment(Qt.AlignCenter)
        self.term_label.setWordWrap(True)
        face.addWidget(self.term_label)
        self.prompt = muted_label(tr("What does it mean? Say it to yourself, then turn the card over."))
        self.prompt.setAlignment(Qt.AlignCenter)
        face.addWidget(self.prompt)
        self.definition = QLabel()
        self.definition.setWordWrap(True)
        self.definition.setAlignment(Qt.AlignCenter)
        self.definition.setTextFormat(Qt.RichText)
        self.definition.setTextInteractionFlags(Qt.TextSelectableByMouse)
        face.addWidget(self.definition)
        root.addWidget(self.face, 1)

        buttons = QHBoxLayout()
        self.reveal_btn = QPushButton(tr("Turn the card over (Space)"))
        self.reveal_btn.setProperty("role", "primary")
        self.reveal_btn.clicked.connect(self.reveal)
        self.missed_btn = QPushButton(tr("I did not know it (1)"))
        nav_icons.set_glyph(self.missed_btn, "cross", 14)
        self.missed_btn.setToolTip(tr("It comes back tomorrow."))
        self.missed_btn.clicked.connect(lambda: self.judge(False))
        self.knew_btn = QPushButton(tr("I knew it (2)"))
        nav_icons.set_glyph(self.knew_btn, "check", 14)
        self.knew_btn.setToolTip(tr("It comes back later: 3 days, a week, 16 days, 35 days, then never."))
        self.knew_btn.clicked.connect(lambda: self.judge(True))
        self.back_btn = QPushButton(tr("Back to the review page"))
        self.back_btn.clicked.connect(self.back.emit)
        buttons.addStretch(1)
        for button in (self.reveal_btn, self.missed_btn, self.knew_btn, self.back_btn):
            buttons.addWidget(button)
        buttons.addStretch(1)
        root.addLayout(buttons)

    # ------------------------------------------------------------------ api
    def load(self, cards: list[Flashcard]) -> None:
        self.cards = list(cards)
        self.position = 0
        self.known = 0
        self._show()

    @property
    def done(self) -> bool:
        return self.position >= len(self.cards)

    def reveal(self) -> None:
        if self.done or self.revealed:
            return
        self.revealed = True
        current = self.cards[self.position]
        text = current.definition
        if current.related:
            text += "<br><br><span style='font-size:small'>" + tr("See also: {terms}").format(
                terms=current.related) + "</span>"
        self.definition.setText(text)
        self._sync_buttons()

    def judge(self, knew_it: bool) -> None:
        if self.done or not self.revealed:
            return
        current = self.cards[self.position]
        self.known += int(knew_it)
        self.position += 1
        self.answered.emit(current.key, knew_it)
        if self.done:
            self.finished.emit(len(self.cards), self.known)
        self._show()

    def keyPressEvent(self, event) -> None:  # noqa: N802 (Qt override)
        """Space or Enter turns the card over, 1 and 2 judge it: no mouse needed."""
        key = event.key()
        if key in (Qt.Key_Space, Qt.Key_Return, Qt.Key_Enter) and not self.revealed:
            self.reveal()
        elif key == Qt.Key_1:
            self.judge(False)
        elif key == Qt.Key_2:
            self.judge(True)
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    # ------------------------------------------------------------- display
    def _show(self) -> None:
        self.revealed = False
        self.definition.setText("")
        if self.done:
            self.counter.setText("")
            self.term_label.setText(tr("All done"))
            self.prompt.setText(tr("You knew {known} of {total}. The ones you missed come back tomorrow.")
                                .format(known=self.known, total=len(self.cards)))
        else:
            self.counter.setText(tr("Card {number} of {total}").format(number=self.position + 1,
                                                                        total=len(self.cards)))
            self.term_label.setText(self.cards[self.position].term)
            self.prompt.setText(tr("What does it mean? Say it to yourself, then turn the card over."))
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        self.reveal_btn.setVisible(not self.done and not self.revealed)
        self.missed_btn.setVisible(not self.done and self.revealed)
        self.knew_btn.setVisible(not self.done and self.revealed)
        self.back_btn.setVisible(self.done)
        # Hidden buttons are disabled too, so only the visible ones answer to their keys.
        self.reveal_btn.setEnabled(not self.done and not self.revealed)
        self.missed_btn.setEnabled(not self.done and self.revealed)
        self.knew_btn.setEnabled(not self.done and self.revealed)
        self.back_btn.setEnabled(self.done)
        # The session keeps the focus, so the number keys always reach it.
        self.setFocus()
