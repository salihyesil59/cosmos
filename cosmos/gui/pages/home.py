"""Home page: welcome, where to continue, level overview."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.widgets.common import card, muted_label, title_label

GUIDE = """
## Welcome to Cosmos

This panel is your **Guide**. It always explains the page you are on and gives
tips on what to do next. Click any [[cosmology|highlighted term]] to see its
definition here.

### How the course works

1. Lessons are grouped into **levels**, from everyday ideas to the physics of the
   early universe.
2. Each lesson ends with a short **quiz**. Score 70% or more to complete it.
3. Lessons that build on others list their **prerequisites**. You can open any
   lesson at any time, but the recommended order helps.
4. **Simulators** let you experiment with the ideas. Lessons link to them with
   *Try it* boxes.

### Where to start

Press **Continue learning** on the home page. It always points to the next lesson
you are ready for.

### More to explore

- **Challenges** inside many simulators give you a concrete task and check your
  answer.
- **History** tells the story from Copernicus to the latest surveys, with cards
  for the scientists.
- **Badges** on the Progress page mark what you have achieved.

### Optional help

- **Tutor** (F3) can answer questions about the page you are on. It is off until
  you paste your own API key, and nothing is sent until you press **Ask**.

### Finding things again

- **Search** (Ctrl+F) looks through every lesson, glossary term, simulator and
  formula at once.
- **Reference** (Ctrl+R) is the formula sheet, with constants, unit conversions
  and the parameters of every model.
- **Notes** is your private notebook: one note per page, plus bookmarks
  (Ctrl+D). Everything stays on this computer.

### Handy controls

- **Back / Forward** in the toolbar move through pages you visited.
- **Theme** switches between dark and light.
- **Tour** replays the guided introduction.
- Every control with a **?** button has a detailed explanation.
"""


class HomePage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        host = QWidget()
        scroll.setWidget(host)
        self.layout_ = QVBoxLayout(host)
        self.layout_.setContentsMargins(28, 22, 28, 22)
        self.layout_.setSpacing(16)

        # Hero
        hero = card()
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.addWidget(title_label("Welcome to Cosmos"))
        hl.addWidget(
            muted_label(
                "An interactive course in cosmology — the science of the universe as a whole. Start "
                "with how big the universe is and how we measure it, and work your way up to the "
                "expanding universe, dark matter, dark energy and the first minutes after the Big Bang."
            )
        )
        self.progress_label = QLabel()
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(10)
        hl.addWidget(self.progress_label)
        hl.addWidget(self.progress_bar)
        row = QHBoxLayout()
        self.continue_btn = QPushButton()
        self.continue_btn.setObjectName("continueButton")
        self.continue_btn.setProperty("role", "primary")
        self.continue_btn.setMinimumHeight(38)
        self.continue_btn.clicked.connect(self._continue)
        self.continue_hint = muted_label("")
        tour = QPushButton("Take the guided tour")
        tour.clicked.connect(lambda: ctx.navigate("action:tour"))
        row.addWidget(self.continue_btn)
        row.addWidget(tour)
        row.addStretch(1)
        hl.addLayout(row)
        hl.addWidget(self.continue_hint)
        self.layout_.addWidget(hero)

        # Levels
        self.layout_.addWidget(title_label("Course levels", "subtitle"))
        self.levels_grid = QGridLayout()
        self.levels_grid.setSpacing(12)
        self.layout_.addLayout(self.levels_grid)
        self.level_widgets = []
        for i, level in enumerate(ctx.curriculum.levels):
            c = card()
            c.setObjectName(f"levelCard{level.number}")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 14, 16, 14)
            badge = QLabel(f"LEVEL {level.number}")
            badge.setProperty("role", "badge")
            cl.addWidget(badge, 0, Qt.AlignLeft)
            cl.addWidget(title_label(level.title, "subtitle"))
            cl.addWidget(muted_label(level.description))
            bar = QProgressBar()
            bar.setTextVisible(False)
            bar.setFixedHeight(8)
            status = muted_label("")
            cl.addWidget(bar)
            cl.addWidget(status)
            btn = QPushButton("Open level")
            first = level.lesson_ids[0]
            btn.clicked.connect(lambda _=False, lv=level: self._open_level(lv))
            btn.setToolTip(f"Opens the first unfinished lesson of this level (starts at {first}).")
            cl.addStretch(1)
            cl.addWidget(btn, 0, Qt.AlignLeft)
            self.levels_grid.addWidget(c, i // 2, i % 2)
            self.level_widgets.append((level, bar, status))

        # Simulators
        self.layout_.addWidget(title_label("Simulators", "subtitle"))
        self.layout_.addWidget(
            muted_label("Hands-on tools to explore the ideas from the lessons. You can open them at any time.")
        )
        sims = QGridLayout()
        sims.setSpacing(10)
        for i, info in enumerate(SIMULATORS.values()):
            # "&" would otherwise become a keyboard mnemonic and vanish from the label.
            btn = QPushButton(f"{info.icon}  {info.title}\n{info.tagline}".replace("&", "&&"))
            btn.setStyleSheet("QPushButton { text-align: left; padding: 10px 14px; }")
            btn.setToolTip(info.description)
            btn.clicked.connect(lambda _=False, sid=info.id: ctx.navigate(f"sim:{sid}"))
            sims.addWidget(btn, i // 2, i % 2)
        self.layout_.addLayout(sims)
        self.layout_.addStretch(1)

        ctx.signals.progressChanged.connect(self.refresh)
        self.refresh()

    def guide_markdown(self) -> str:
        return GUIDE

    def refresh(self) -> None:
        cur, store = self.ctx.curriculum, self.ctx.store
        done, total = store.overall_progress(cur)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(done)
        self.progress_label.setText(f"Course progress: <b>{done}</b> of {total} lessons completed")
        nxt = store.next_recommended(cur)
        if nxt is None:
            self.continue_btn.setText("Review the course")
            self.continue_hint.setText("You have completed every lesson. Congratulations!")
            self._next = cur.ordered_ids[0]
        else:
            lesson = cur.lessons[nxt]
            verb = "Start learning" if done == 0 else "Continue learning"
            self.continue_btn.setText(f"▶  {verb}: {lesson.id} {lesson.title}")
            self.continue_hint.setText(lesson.summary)
            self._next = nxt
        for level, bar, status in self.level_widgets:
            d, t = store.level_progress(cur, level.number)
            bar.setRange(0, t)
            bar.setValue(d)
            status.setText(f"{d} of {t} lessons completed")

    def _continue(self) -> None:
        self.ctx.navigate(f"lesson:{self._next}")

    def _open_level(self, level) -> None:
        target = next((i for i in level.lesson_ids if not self.ctx.store.is_completed(i)), level.lesson_ids[0])
        self.ctx.navigate(f"lesson:{target}")
