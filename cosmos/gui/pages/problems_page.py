"""Worked problem sets (G15): numeric exercises with checked answers, hints and solutions."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from cosmos.content.loader import load_problems
from cosmos.content.models import Problem
from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.widgets.common import Banner, muted_label, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr, tr_noop
from cosmos.problems import Verdict, check_answer, format_answer

PROBLEM_ROLE = Qt.UserRole

GUIDE = tr_noop("""
## Problem sets

One set of worked problems for every level of the course. Each problem asks for a
single number, and the app checks it.

### How to work a problem

1. Read the statement and note the **unit** the answer must be given in.
2. Work it out on paper or with a calculator. Some problems point to a simulator
   that computes the hard part for you.
3. Type the number and press **Check** (or Enter). Scientific notation works:
   `5.6e11`, `5.6×10^11` and `5,6` are all understood.
4. Stuck? **Show a hint** reveals the next step. After your first attempt you can
   open the **worked solution**.

### What the feedback means

- **Correct** — within the tolerance of the problem, usually 2%.
- **Close** — probably rounding, or a value taken from a slightly different step.
- **Wrong power of ten** — the digits are right: check the units.
- **Wrong sign** — the size is right, the direction is not.

Solved problems stay ticked, and badges reward solving a whole set and getting
answers right at the first attempt.
""")

VERDICT_TEXT = {
    Verdict.CLOSE: ("warning", tr_noop("<b>Close, but not within the tolerance.</b> Check your rounding and "
                                       "the value of each constant.")),
    Verdict.POWER_OF_TEN: ("warning", tr_noop("<b>The digits look right, but the answer is off by a factor of "
                                              "10^{factor}.</b> Check the unit conversions.")),
    Verdict.SIGN: ("warning", tr_noop("<b>The size is right, but the sign is not.</b>")),
    Verdict.WRONG: ("danger", tr_noop("<b>Not yet.</b> Try again, or reveal a hint.")),
    Verdict.INVALID: ("warning", tr_noop("Please type a number, for example 4.25 or 5.6e11.")),
}


def stars(difficulty: int) -> str:
    return "★" * difficulty + "☆" * (3 - difficulty)


class ProblemsPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.sets = load_problems()
        self.problems: dict[str, Problem] = {p.id: p for s in self.sets for p in s.problems}
        self.order = list(self.problems)
        self.current: Problem | None = None
        self.hints_shown = 0
        self.solution_shown = False

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(8)
        root.addWidget(title_label(tr("Problem sets")))
        self.summary = muted_label("")
        root.addWidget(self.summary)

        split = QSplitter(Qt.Horizontal)
        split.setChildrenCollapsible(False)
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(260)
        self.tree.itemClicked.connect(self._on_item)
        self.tree.itemActivated.connect(self._on_item)
        split.addWidget(self.tree)

        detail = QWidget()
        dl = QVBoxLayout(detail)
        dl.setContentsMargins(12, 0, 0, 0)
        dl.setSpacing(6)
        self.kicker = muted_label("")
        self.title = title_label("", "subtitle")
        dl.addWidget(self.kicker)
        dl.addWidget(self.title)
        links = QHBoxLayout()
        self.lesson_btn = QPushButton()
        self.lesson_btn.setToolTip(tr("The lesson that explains the physics behind this problem."))
        self.lesson_btn.clicked.connect(lambda: self.current and ctx.navigate(f"lesson:{self.current.lesson}"))
        self.sim_btn = QPushButton()
        self.sim_btn.setToolTip(tr("A simulator that can compute or visualise part of the answer."))
        self.sim_btn.clicked.connect(
            lambda: self.current and self.current.simulator and ctx.navigate(f"sim:{self.current.simulator}"))
        links.addWidget(self.lesson_btn)
        links.addWidget(self.sim_btn)
        links.addStretch(1)
        dl.addLayout(links)

        self.view = RichBrowser(font_pt=11.0)
        self.view.lessonRequested.connect(lambda i: ctx.navigate(f"lesson:{i}"))
        self.view.simulatorRequested.connect(lambda s: ctx.navigate(f"sim:{s}"))
        self.view.glossaryRequested.connect(ctx.signals.glossaryRequested)
        dl.addWidget(self.view, 1)

        answer_row = QHBoxLayout()
        answer_row.addWidget(QLabel(tr("Your answer:")))
        self.answer = QLineEdit()
        self.answer.setPlaceholderText(tr("a number, e.g. 4.25 or 5.6e11"))
        self.answer.returnPressed.connect(self.check)
        answer_row.addWidget(self.answer, 1)
        self.unit = QLabel()
        answer_row.addWidget(self.unit)
        self.check_btn = QPushButton(tr("✓  Check"))
        self.check_btn.setProperty("role", "primary")
        self.check_btn.clicked.connect(self.check)
        answer_row.addWidget(self.check_btn)
        dl.addLayout(answer_row)

        self.feedback = Banner("info", "")
        self.feedback.hide()
        dl.addWidget(self.feedback)

        buttons = QHBoxLayout()
        self.hint_btn = QPushButton()
        self.hint_btn.clicked.connect(self.show_hint)
        self.solution_btn = QPushButton(tr("Show the worked solution"))
        self.solution_btn.clicked.connect(self.show_solution)
        self.prev_btn = QPushButton(tr("◀ Previous"))
        self.prev_btn.clicked.connect(lambda: self._step(-1))
        self.next_btn = QPushButton(tr("Next ▶"))
        self.next_btn.clicked.connect(lambda: self._step(1))
        for w in (self.hint_btn, self.solution_btn):
            buttons.addWidget(w)
        buttons.addStretch(1)
        buttons.addWidget(self.prev_btn)
        buttons.addWidget(self.next_btn)
        dl.addLayout(buttons)

        split.addWidget(detail)
        split.setStretchFactor(1, 1)
        split.setSizes([300, 800])
        root.addWidget(split, 1)

        ctx.signals.progressChanged.connect(self.refresh)
        self.refresh()
        self.select(self._first_unsolved())

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    # ------------------------------------------------------------------ api
    def refresh(self) -> None:
        store = self.ctx.store
        solved = sum(1 for pid in self.problems if store.is_problem_solved(pid))
        self.summary.setText(tr("{solved} of {total} problems solved, in {sets} sets — one for every level.")
                             .format(solved=solved, total=len(self.problems), sets=len(self.sets)))
        current = self.current.id if self.current else None
        self.tree.blockSignals(True)
        self.tree.clear()
        levels = {lv.number: lv for lv in self.ctx.curriculum.levels}
        for problem_set in self.sets:
            done = sum(1 for p in problem_set.problems if store.is_problem_solved(p.id))
            level = levels.get(problem_set.level)
            label = tr("Level {number} · {title}").format(number=problem_set.level, title=problem_set.title)
            top = QTreeWidgetItem([f"{label}  ({done}/{len(problem_set.problems)})"])
            top.setToolTip(0, problem_set.intro + (f"\n\n{level.title}" if level else ""))
            font = top.font(0)
            font.setBold(True)
            top.setFont(0, font)
            self.tree.addTopLevelItem(top)
            for problem in problem_set.problems:
                mark = "✓" if store.is_problem_solved(problem.id) else "○"
                item = QTreeWidgetItem([f"{mark}  {problem.title}   {stars(problem.difficulty)}"])
                item.setData(0, PROBLEM_ROLE, problem.id)
                item.setToolTip(0, tr("Difficulty {stars} · lesson {lesson}")
                                .format(stars=stars(problem.difficulty), lesson=problem.lesson))
                top.addChild(item)
                if problem.id == current:
                    self.tree.setCurrentItem(item)
            top.setExpanded(True)
        self.tree.blockSignals(False)

    def select(self, problem_id: str) -> None:
        if problem_id not in self.problems:
            return
        self.current = problem = self.problems[problem_id]
        self.hints_shown = 0
        self.solution_shown = False
        index = self.order.index(problem_id)
        in_set = next(s for s in self.sets if s.level == problem.level).problems
        self.kicker.setText(tr("LEVEL {level} · PROBLEM {number} OF {total}")
                            .format(level=problem.level, number=in_set.index(problem) + 1, total=len(in_set))
                            + "   " + stars(problem.difficulty))
        self.title.setText(problem.title)
        lesson = self.ctx.curriculum.lessons.get(problem.lesson)
        self.lesson_btn.setText("📖  " + (f"{problem.lesson} {lesson.title}" if lesson else problem.lesson))
        has_simulator = problem.simulator in SIMULATORS
        self.sim_btn.setVisible(has_simulator)
        if has_simulator:
            info = SIMULATORS[problem.simulator]
            self.sim_btn.setText(f"{info.icon}  {tr(info.title)}".replace("&", "&&"))
        self.unit.setText(problem.unit)
        self.answer.clear()
        self.feedback.hide()
        self.prev_btn.setEnabled(index > 0)
        self.next_btn.setEnabled(index < len(self.order) - 1)
        for i in range(self.tree.topLevelItemCount()):
            top = self.tree.topLevelItem(i)
            for j in range(top.childCount()):
                if top.child(j).data(0, PROBLEM_ROLE) == problem_id:
                    self.tree.setCurrentItem(top.child(j))
        self._render()
        if self.ctx.store.is_problem_solved(problem_id):
            self.feedback.set_message("success", tr("<b>Solved.</b> You can still try it again or read the "
                                                    "worked solution."))
            self.feedback.show()

    def check(self) -> None:
        problem = self.current
        if problem is None:
            return
        result = check_answer(self.answer.text(), problem.answer, problem.tolerance)
        if result.verdict is Verdict.INVALID:
            kind, text = VERDICT_TEXT[Verdict.INVALID]
            self.feedback.set_message(kind, tr(text))
            self.feedback.show()
            return
        first_time = self.ctx.store.record_problem_attempt(problem.id, result.correct)
        if result.correct:
            attempts = self.ctx.store.data.problems_solved.get(problem.id, 1)
            message = tr("<b>Correct!</b> The answer is {answer} {unit}.").format(
                answer=format_answer(problem.answer), unit=problem.unit)
            if first_time and attempts == 1:
                message += " " + tr("First try!")
            self.feedback.set_message("success", message)
        else:
            kind, text = VERDICT_TEXT[result.verdict]
            self.feedback.set_message(kind, tr(text).format(factor=f"{result.factor:+d}"))
        self.feedback.show()
        self._update_buttons()
        if first_time:
            self.ctx.signals.progressChanged.emit()

    def show_hint(self) -> None:
        if self.current and self.hints_shown < len(self.current.hints):
            self.hints_shown += 1
            self._render()

    def show_solution(self) -> None:
        if self.current:
            self.solution_shown = True
            self._render()
            self.view.scroll_to_end()

    def solution_available(self) -> bool:
        problem = self.current
        if problem is None:
            return False
        tried = self.ctx.store.data.problem_attempts.get(problem.id, 0) > 0
        return tried or self.hints_shown >= len(problem.hints)

    # -------------------------------------------------------------- private
    def _render(self) -> None:
        problem = self.current
        lines = [problem.statement, ""]
        for i, hint in enumerate(problem.hints[:self.hints_shown], 1):
            lines += [":::tip " + tr("Hint {number}").format(number=i), hint, ":::", ""]
        if self.solution_shown:
            lines += ["### " + tr("Worked solution"), "", problem.solution, "",
                      "**" + tr("Answer: {answer} {unit}").format(answer=format_answer(problem.answer),
                                                                   unit=problem.unit) + "**"]
        self.view.set_markdown_content("\n".join(lines))
        self._update_buttons()

    def _update_buttons(self) -> None:
        problem = self.current
        left = len(problem.hints) - self.hints_shown
        self.hint_btn.setText(tr("Show a hint ({count} left)").format(count=left))
        self.hint_btn.setEnabled(left > 0)
        available = self.solution_available()
        self.solution_btn.setEnabled(available and not self.solution_shown)
        self.solution_btn.setToolTip("" if available else
                                     tr("Try an answer (or use every hint) first — the solution teaches more "
                                        "once you have struggled with the problem."))

    def _on_item(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        problem_id = item.data(0, PROBLEM_ROLE)
        if problem_id:
            self.select(problem_id)
        else:
            item.setExpanded(not item.isExpanded())

    def _step(self, delta: int) -> None:
        if self.current:
            index = self.order.index(self.current.id) + delta
            if 0 <= index < len(self.order):
                self.select(self.order[index])

    def _first_unsolved(self) -> str:
        return next((pid for pid in self.order if not self.ctx.store.is_problem_solved(pid)), self.order[0])

    def problems_for_lesson(self, lesson_id: str) -> list[Problem]:
        return [p for p in self.problems.values() if p.lesson == lesson_id]
