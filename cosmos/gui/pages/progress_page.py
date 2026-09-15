"""Progress overview and the prerequisite map."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.widgets.common import card, muted_label, title_label
from cosmos.gui.widgets.prereq_map import PrerequisiteMap

GUIDE = """
## Your progress

### Reading the map

- Each box is a lesson; columns are levels.
- **Green ✓** lessons are completed (quiz score of at least 70%).
- **Blue ●** lessons are ready: all their prerequisites are done.
- **Grey ○** lessons still have missing prerequisites.
- Lines connect a lesson to the lessons that build on it. Solid green lines are
  prerequisites you have already completed.

Click any box to open that lesson. Drag the map to move around.

### Resetting

**Reset progress** clears quiz scores and completed lessons. Your theme and
settings are kept.
"""


class ProgressPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(title_label("Your progress"))
        head.addStretch(1)
        reset = QPushButton("Reset progress…")
        reset.clicked.connect(self._reset)
        head.addWidget(reset)
        root.addLayout(head)

        stats = QHBoxLayout()
        self.stat_values = {}
        for key, label in [
            ("lessons", "Lessons completed"),
            ("quiz", "Average best quiz score"),
            ("sims", "Simulators explored"),
            ("next", "Recommended next"),
        ]:
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(14, 10, 14, 10)
            value = QLabel("–")
            value.setProperty("role", "value")
            cl.addWidget(value)
            cl.addWidget(muted_label(label))
            stats.addWidget(c, 1)
            self.stat_values[key] = value
        root.addLayout(stats)

        root.addWidget(title_label("Lesson map", "subtitle"))
        root.addWidget(muted_label("Click a lesson to open it. Arrows show which lessons build on which."))
        self.map = PrerequisiteMap(ctx)
        self.map.setObjectName("prereqMap")
        self.map.lessonClicked.connect(lambda lid: ctx.navigate(f"lesson:{lid}"))
        root.addWidget(self.map, 1)
        ctx.signals.progressChanged.connect(self.refresh)
        self.refresh()

    def guide_markdown(self) -> str:
        return GUIDE

    def refresh(self) -> None:
        cur, store = self.ctx.curriculum, self.ctx.store
        done, total = store.overall_progress(cur)
        self.stat_values["lessons"].setText(f"{done} / {total}")
        avg = store.average_quiz_score()
        self.stat_values["quiz"].setText("–" if avg is None else f"{avg:.0%}")
        explored = len([s for s in store.data.simulators_opened if s in SIMULATORS])
        self.stat_values["sims"].setText(f"{explored} / {len(SIMULATORS)}")
        nxt = store.next_recommended(cur)
        self.stat_values["next"].setText(nxt or "All done!")

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset progress",
            "Clear all quiz scores and completed lessons? This cannot be undone.",
        )
        if answer == QMessageBox.Yes:
            self.ctx.store.reset()
            self.ctx.signals.progressChanged.emit()
