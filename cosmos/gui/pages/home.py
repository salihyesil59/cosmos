"""Home page: welcome, where to continue, level overview."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.widgets.common import FlowLayout, card, centred, muted_label, title_label
from cosmos.gui.widgets.common import labelled_row
from cosmos.i18n import tr, tr_noop
from cosmos import streaks

GUIDE = tr_noop("""
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
- **Review** (Ctrl+Shift+R) brings back every quiz question you got wrong — the
  next day, then after 3, 7, 16 and 35 days, until it sticks.
- **History** tells the story from Copernicus to the latest surveys, with cards
  for the scientists.
- **Badges** on the Progress page mark what you have achieved.
- **Today** counts your study steps — quiz questions, reviews, flashcards, problems
  and challenges — against a daily goal you choose, and keeps a streak of the days
  you studied. One day off does not break the streak; two in a row do.

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
- **Theme** (Ctrl+T) cycles dark, light and a high-contrast scheme.
- **Text size** under *View* scales the whole interface (Ctrl++ / Ctrl+- / Ctrl+0).
- **Tour** replays the guided introduction.
- Every control with a **?** button has a detailed explanation.

### Without a mouse

Every command has a keyboard shortcut; *Help → Keyboard shortcuts* lists them all.
**Tab** moves between controls, **F6** jumps between the lesson list, the page and
the side panels, and whatever has the keyboard is drawn with a clear outline.
""")


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
        scroll.setWidget(centred(host))
        self.layout_ = QVBoxLayout(host)
        self.layout_.setContentsMargins(28, 22, 28, 22)
        self.layout_.setSpacing(16)

        # Hero
        hero = card()
        hl = QVBoxLayout(hero)
        hl.setContentsMargins(24, 20, 24, 20)
        hl.addWidget(title_label(tr("Welcome to Cosmos")))
        hl.addWidget(
            muted_label(tr("An interactive course in cosmology — the science of the universe as a whole. Start "
                           "with how big the universe is and how we measure it, and work your way up to the "
                           "expanding universe, dark matter, dark energy and the first minutes after the Big Bang."))
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
        tour = QPushButton(tr("Take the guided tour"))
        tour.clicked.connect(lambda: ctx.navigate("action:tour"))
        row.addWidget(self.continue_btn)
        row.addWidget(tour)
        row.addStretch(1)
        hl.addLayout(row)
        hl.addWidget(self.continue_hint)
        self.review_btn = QPushButton()
        self.review_btn.setToolTip(tr("Questions you got wrong, brought back just before you would "
                                      "forget them (Ctrl+Shift+R)"))
        self.review_btn.clicked.connect(lambda: ctx.navigate("review"))
        row.insertWidget(1, self.review_btn)
        self.layout_.addWidget(hero)

        # G23: today's steps, the goal and the streak
        today = card()
        today.setObjectName("studyCard")
        tl = QHBoxLayout(today)
        tl.setContentsMargins(20, 14, 20, 14)
        left = QVBoxLayout()
        self.streak_label = title_label("", "subtitle")
        left.addWidget(self.streak_label)
        self.goal_label = QLabel()
        self.goal_label.setTextFormat(Qt.RichText)
        left.addWidget(self.goal_label)
        self.goal_bar = QProgressBar()
        self.goal_bar.setTextVisible(False)
        self.goal_bar.setFixedHeight(8)
        left.addWidget(self.goal_bar)
        self.week_label = muted_label("")
        left.addWidget(self.week_label)
        tl.addLayout(left, 1)
        self.goal_combo = QComboBox()
        for steps in streaks.GOALS:
            self.goal_combo.addItem(tr("No daily goal") if steps == 0
                                    else tr("{steps} steps a day").format(steps=steps), steps)
        self.goal_combo.currentIndexChanged.connect(self._goal_changed)
        tl.addWidget(labelled_row(tr("Daily goal"), self.goal_combo, (
            tr("What counts as a step"),
            tr("Every quiz question you answer, every review and flashcard, every attempt at a worked "
               "problem and every simulator challenge you solve. Ten a day is about fifteen minutes."))),
            0, Qt.AlignTop)
        self.layout_.addWidget(today)

        # Levels
        self.layout_.addWidget(title_label(tr("Course levels"), "subtitle"))
        self.levels_grid = QGridLayout()
        self.levels_grid.setSpacing(12)
        self.levels_grid.setColumnStretch(0, 1)
        self.levels_grid.setColumnStretch(1, 1)
        self.layout_.addLayout(self.levels_grid)
        self.level_widgets = []
        for i, level in enumerate(ctx.curriculum.levels):
            c = card()
            c.setObjectName(f"levelCard{level.number}")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 14, 16, 14)
            badge = QLabel(tr("LEVEL {number}").format(number=level.number))
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
            btn = QPushButton(tr("Open level"))
            first = level.lesson_ids[0]
            btn.clicked.connect(lambda _=False, lv=level: self._open_level(lv))
            btn.setToolTip(tr("Opens the first unfinished lesson of this level (starts at {lesson}).")
                           .format(lesson=first))
            cl.addStretch(1)
            cl.addWidget(btn, 0, Qt.AlignLeft)
            self.levels_grid.addWidget(c, i // 2, i % 2)
            self.level_widgets.append((level, bar, status))

        # Simulators
        self.layout_.addWidget(title_label(tr("Simulators"), "subtitle"))
        self.layout_.addWidget(
            muted_label(tr("Hands-on tools to explore the ideas from the lessons. You can open them at any time."))
        )
        sims = FlowLayout(spacing=8)
        for info in SIMULATORS.values():
            # "&" would otherwise become a keyboard mnemonic and vanish from the label.
            btn = QPushButton(tr(info.title).replace("&", "&&"))
            btn.setIcon(nav_icons.text_icon(info.icon, size=16))
            btn.setProperty("symbol", info.icon)        # so a theme change can redraw it
            btn.setStyleSheet("QPushButton { text-align: left; padding: 9px 12px; }")
            # One line each, with the tagline in the tooltip: 29 two-line buttons made
            # a wall of text on the page a learner sees first (D1).
            btn.setToolTip(f"<b>{tr(info.tagline)}</b><br>{tr(info.description)}")
            btn.clicked.connect(lambda _=False, sid=info.id: ctx.navigate(f"sim:{sid}"))
            sims.addWidget(btn)
        self.layout_.addLayout(sims)
        self.layout_.addStretch(1)

        ctx.signals.progressChanged.connect(self.refresh)
        self.refresh()

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    def refresh(self) -> None:
        cur, store = self.ctx.curriculum, self.ctx.store
        done, total = store.overall_progress(cur)
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(done)
        self.progress_label.setText(
            tr("Course progress: <b>{done}</b> of {total} lessons completed").format(done=done, total=total))
        nxt = store.next_recommended(cur)
        if nxt is None:
            self.continue_btn.setText(tr("Review the course"))
            self.continue_hint.setText(tr("You have completed every lesson. Congratulations!"))
            self._next = cur.ordered_ids[0]
        else:
            lesson = cur.lessons[nxt]
            verb = tr("Start learning") if done == 0 else tr("Continue learning")
            self.continue_btn.setText(f"▶  {verb}: {lesson.id} {lesson.title}")
            self.continue_hint.setText(lesson.summary)
            self._next = nxt
        self._refresh_today()
        # G16: only offer a review when there is one to do.
        due = len(store.due_reviews())
        self.review_btn.setVisible(bool(due))
        self.review_btn.setText("🔁  " + tr("Review {count} question(s)").format(count=due))
        for level, bar, status in self.level_widgets:
            d, t = store.level_progress(cur, level.number)
            bar.setRange(0, t)
            bar.setValue(d)
            status.setText(tr("{done} of {total} lessons completed").format(done=d, total=t))

    def _refresh_today(self) -> None:
        info = self.ctx.store.study_summary()
        streak, steps, goal = info["streak"], info["today"], info["goal"]
        if streak:
            self.streak_label.setText("🔥 " + tr("{days}-day streak").format(days=streak))
        else:
            self.streak_label.setText(tr("Start a streak today"))
        if goal:
            self.goal_bar.setVisible(True)
            self.goal_bar.setRange(0, goal)
            self.goal_bar.setValue(min(steps, goal))
            text = tr("Today: <b>{steps}</b> of {goal} steps").format(steps=steps, goal=goal)
            if info["goal_met"]:
                text += " — " + tr("goal reached ✓")
        else:
            self.goal_bar.setVisible(False)
            text = tr("Today: <b>{steps}</b> steps").format(steps=steps)
        if info["at_risk"]:
            text += "<br>" + tr("Study a little today to keep your streak going.")
        self.goal_label.setText(text)
        marks = " ".join(("●" if count else "○") for _day, count in info["week"])
        self.week_label.setText(tr("Last seven days: {marks}   Longest streak: {longest} days")
                                .format(marks=marks, longest=info["longest"]))
        index = self.goal_combo.findData(goal)
        if index < 0:
            self.goal_combo.addItem(tr("{steps} steps a day").format(steps=goal), goal)
            index = self.goal_combo.count() - 1
        self.goal_combo.blockSignals(True)
        self.goal_combo.setCurrentIndex(index)
        self.goal_combo.blockSignals(False)

    def _goal_changed(self, _index: int) -> None:
        self.ctx.store.set_daily_goal(self.goal_combo.currentData())
        self._refresh_today()

    def _continue(self) -> None:
        self.ctx.navigate(f"lesson:{self._next}")

    def _open_level(self, level) -> None:
        target = next((i for i in level.lesson_ids if not self.ctx.store.is_completed(i)), level.lesson_ids[0])
        self.ctx.navigate(f"lesson:{target}")
