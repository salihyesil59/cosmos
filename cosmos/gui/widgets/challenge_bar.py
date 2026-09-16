"""The challenge strip shown above a simulator (G8)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from cosmos.content.models import Challenge
from cosmos.gui.challenges import challenge_met, unmet_fields
from cosmos.gui.context import AppContext
from cosmos.gui.widgets.common import Banner, card, muted_label


class ChallengeBar(QWidget):
    """Walks the learner through the challenges of one simulator."""

    solved = Signal(str)          # challenge key, the first time it is solved

    def __init__(self, ctx: AppContext, simulator, challenges: list[Challenge], parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.simulator = simulator
        self.challenges = challenges
        self.index = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        frame = card()
        frame.setObjectName("challengeBar")
        outer.addWidget(frame)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        head = QHBoxLayout()
        self.heading = QLabel()
        self.heading.setProperty("role", "subtitle")
        head.addWidget(self.heading)
        head.addStretch(1)
        self.progress = muted_label("")
        head.addWidget(self.progress)
        prev_btn = QPushButton("◀")
        prev_btn.setToolTip("Previous challenge")
        prev_btn.setMaximumWidth(36)
        prev_btn.clicked.connect(lambda: self.go(self.index - 1))
        next_btn = QPushButton("▶")
        next_btn.setToolTip("Next challenge")
        next_btn.setMaximumWidth(36)
        next_btn.clicked.connect(lambda: self.go(self.index + 1))
        head.addWidget(prev_btn)
        head.addWidget(next_btn)
        layout.addLayout(head)

        self.task = QLabel()
        self.task.setWordWrap(True)
        self.task.setTextFormat(Qt.RichText)
        layout.addWidget(self.task)

        row = QHBoxLayout()
        self.check_btn = QPushButton("✓  Check my answer")
        self.check_btn.setProperty("role", "primary")
        self.check_btn.setToolTip("Look at the current settings of the simulator and see whether they "
                                  "solve the challenge.")
        self.check_btn.clicked.connect(self.check)
        self.hint_btn = QPushButton("Show a hint")
        self.hint_btn.clicked.connect(self.show_hint)
        row.addWidget(self.check_btn)
        row.addWidget(self.hint_btn)
        row.addStretch(1)
        layout.addLayout(row)

        self.feedback = Banner("info")
        self.feedback.hide()
        layout.addWidget(self.feedback)
        self.go(self._first_unsolved())

    # ------------------------------------------------------------------ api
    @property
    def current(self) -> Challenge:
        return self.challenges[self.index]

    def _first_unsolved(self) -> int:
        for i, challenge in enumerate(self.challenges):
            if not self.ctx.store.is_challenge_done(challenge.simulator, challenge.id):
                return i
        return 0

    def go(self, index: int) -> None:
        self.index = index % len(self.challenges)
        challenge = self.current
        done = self.ctx.store.is_challenge_done(challenge.simulator, challenge.id)
        solved = sum(1 for c in self.challenges
                     if self.ctx.store.is_challenge_done(c.simulator, c.id))
        marks = "".join("●" if self.ctx.store.is_challenge_done(c.simulator, c.id) else "○"
                        for c in self.challenges)
        self.heading.setText(f"🎯  Challenge {self.index + 1} of {len(self.challenges)}")
        self.progress.setText(f"{marks}   {solved} of {len(self.challenges)} solved")
        self.task.setText(challenge.task)
        self.feedback.hide()
        if done:
            self.feedback.set_message("success", f"<b>Solved.</b> {challenge.success}")
            self.feedback.show()

    def show_hint(self) -> None:
        self.feedback.set_message("info", f"<b>Hint.</b> {self.current.hint}")
        self.feedback.show()

    def check(self) -> bool:
        challenge = self.current
        state = self.simulator.state()
        if challenge_met(challenge, state):
            first_time = self.ctx.store.record_challenge(challenge.simulator, challenge.id)
            if first_time:
                self.solved.emit(challenge.key)
            self.go(self.index)              # refresh the marks, keeping the learner on this challenge
            message = f"<b>Solved!</b> {challenge.success}"
            if any(not self.ctx.store.is_challenge_done(c.simulator, c.id) for c in self.challenges):
                message += " Press ▶ for the next challenge."
            self.feedback.set_message("success", message)
            self.feedback.show()
            return True
        missing = unmet_fields(challenge, state)
        detail = f" Look again at: {', '.join(missing)}." if missing else ""
        self.feedback.set_message("warning", "<b>Not yet.</b> The simulator is not in the state the "
                                             "challenge asks for." + detail)
        self.feedback.show()
        return False
