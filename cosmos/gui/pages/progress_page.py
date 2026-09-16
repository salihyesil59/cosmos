"""Progress overview and the prerequisite map."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cosmos.achievements import ACHIEVEMENTS
from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.theme import repolish
from cosmos.gui.widgets.common import card, muted_label, title_label
from cosmos.gui.widgets.prereq_map import PrerequisiteMap
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Your progress

### Reading the map

- Each box is a lesson; columns are levels.
- **Green ✓** lessons are completed (quiz score of at least 70%).
- **Blue ●** lessons are ready: all their prerequisites are done.
- **Grey ○** lessons still have missing prerequisites.
- Lines connect a lesson to the lessons that build on it. Solid green lines are
  prerequisites you have already completed.

Click any box to open that lesson. Drag the map to move around.

### Badges

Badges are earned by learning, not by clicking: finish lessons, score full marks,
explore the simulators and solve their challenges. Locked badges show how far
along you are.

### Resetting

**Reset progress** clears quiz scores, completed lessons, challenges and badges.
Your notes, bookmarks and settings are kept.
""")


class ProgressPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(10)
        head = QHBoxLayout()
        head.addWidget(title_label(tr("Your progress")))
        head.addStretch(1)
        reset = QPushButton(tr("Reset progress…"))
        reset.clicked.connect(self._reset)
        head.addWidget(reset)
        root.addLayout(head)

        stats = QHBoxLayout()
        self.stat_values = {}
        for key, label in [
            ("lessons", tr("Lessons completed")),
            ("quiz", tr("Average best quiz score")),
            ("sims", tr("Simulators explored")),
            ("next", tr("Recommended next")),
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

        root.addWidget(title_label(tr("Badges"), "subtitle"))
        self.badge_summary = muted_label("")
        root.addWidget(self.badge_summary)
        badge_scroll = QScrollArea()
        badge_scroll.setWidgetResizable(True)
        badge_scroll.setFixedHeight(250)
        badge_host = QWidget()
        self.badge_grid = QGridLayout(badge_host)
        self.badge_grid.setSpacing(8)
        badge_scroll.setWidget(badge_host)
        root.addWidget(badge_scroll)
        self.badge_widgets = {}
        for i, achievement in enumerate(ACHIEVEMENTS):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(12, 8, 12, 8)
            cl.setSpacing(2)
            title = QLabel(f"{achievement.icon}  {tr(achievement.title)}")
            title.setWordWrap(True)
            cl.addWidget(title)
            text = muted_label(tr(achievement.description))
            cl.addWidget(text)
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(6)
            cl.addWidget(bar)
            status = muted_label("")
            cl.addWidget(status)
            self.badge_grid.addWidget(c, i // 4, i % 4)
            self.badge_widgets[achievement.id] = (c, title, bar, status)

        root.addWidget(title_label(tr("Lesson map"), "subtitle"))
        root.addWidget(muted_label(tr("Click a lesson to open it. Arrows show which lessons build on which.")))
        self.map = PrerequisiteMap(ctx)
        self.map.setObjectName("prereqMap")
        self.map.lessonClicked.connect(lambda lid: ctx.navigate(f"lesson:{lid}"))
        root.addWidget(self.map, 1)
        ctx.signals.progressChanged.connect(self.refresh)
        self.refresh()

    def guide_markdown(self) -> str:
        return tr(GUIDE)

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
        self._refresh_badges()

    def _refresh_badges(self) -> None:
        cur, store = self.ctx.curriculum, self.ctx.store
        earned = 0
        for achievement in ACHIEVEMENTS:
            done, goal = achievement.state(store, cur)
            unlocked = achievement.id in store.data.achievements or done >= goal
            frame, title, bar, status = self.badge_widgets[achievement.id]
            bar.setRange(0, max(goal, 1))
            bar.setValue(done)
            bar.setVisible(not unlocked)
            frame.setProperty("earned", "yes" if unlocked else "no")
            title.setEnabled(unlocked)
            when = store.data.achievements.get(achievement.id, "")
            status.setText(tr("Earned {date}").format(date=when[:10]) if unlocked and when else
                           (tr("Earned") if unlocked else f"{done} / {goal}"))
            repolish(frame)
            earned += int(unlocked)
        self.badge_summary.setText(tr("{earned} of {total} badges earned")
                                   .format(earned=earned, total=len(ACHIEVEMENTS)))

    def _reset(self) -> None:
        answer = QMessageBox.question(
            self,
            tr("Reset progress"),
            tr("Clear all quiz scores, completed lessons, challenges and badges? Your notes and "
               "bookmarks are kept. This cannot be undone."),
        )
        if answer == QMessageBox.Yes:
            self.ctx.store.reset()
            self.ctx.signals.progressChanged.emit()
