"""Simulator hub and the frame that hosts one simulator."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from cosmos.content.loader import load_challenges, load_formulas
from cosmos.gui import nav_icons
from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import GROUP_ORDER, SIMULATORS, SimulatorInfo
from cosmos.gui.widgets.challenge_bar import ChallengeBar
from cosmos.gui.widgets.common import card, centred, muted_label, scrolling_page, title_label
from cosmos.i18n import tr, tr_noop

HUB_GUIDE = tr_noop("""
## Simulators

Simulators are small laboratories. Each one focuses on a single idea from the
course and lets you change the parameters yourself.

### Tips

- Every simulator has a **How to use** section in this panel once you open it.
- Hover over any control to see a short explanation; click **?** for more.
- Plots can be saved as images, and data can be exported as CSV files.
- Nothing you do in a simulator can break anything: experiment freely!
""")


class SimulatorHubPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        outer.addWidget(scroll)
        host = QWidget()
        scroll.setWidget(centred(host))
        layout = QVBoxLayout(host)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.addWidget(title_label(tr("Simulators")))
        layout.addWidget(muted_label(tr("Choose a simulator. Each card lists the lessons it supports.")))
        for name in GROUP_ORDER:
            members = [info for info in SIMULATORS.values() if info.group == name]
            if members:
                layout.addSpacing(6)
                layout.addWidget(title_label(tr(name), "subtitle"))
                layout.addLayout(self._cards(ctx, members))

    def _cards(self, ctx: AppContext, members: list[SimulatorInfo]) -> QGridLayout:
        grid = QGridLayout()
        grid.setSpacing(14)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        for i, info in enumerate(members):
            c = card()
            cl = QVBoxLayout(c)
            cl.setContentsMargins(16, 14, 16, 14)
            # The simulator's own symbol, drawn on the icons' grid rather than pasted
            # into the words, so it sits on the same baseline and follows the theme (D3).
            head = QHBoxLayout()
            head.setSpacing(8)
            mark = QLabel()
            nav_icons.set_label_symbol(mark, info.icon, 20)
            head.addWidget(mark, 0, Qt.AlignVCenter)
            head.addWidget(title_label(f"{info.id} · {tr(info.title)}", "subtitle"), 1)
            cl.addLayout(head)
            cl.addWidget(muted_label(tr(info.description)))
            lessons = ", ".join(info.lessons)
            cl.addWidget(muted_label(tr("Supports lessons: {lessons}").format(lessons=lessons)))
            btn = QPushButton(tr("Open simulator"))
            btn.setProperty("role", "primary")
            btn.clicked.connect(lambda _=False, sid=info.id: ctx.navigate(f"sim:{sid}"))
            cl.addStretch(1)
            cl.addWidget(btn, 0, Qt.AlignLeft)
            grid.addWidget(c, i // 2, i % 2)
        return grid

    def guide_markdown(self) -> str:
        return tr(HUB_GUIDE)


class SimulatorHostPage(QWidget):
    """Header with title and description plus the simulator itself."""

    def __init__(self, ctx: AppContext, info: SimulatorInfo, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx, self.info = ctx, info
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        body = QWidget()
        outer.addWidget(scrolling_page(body))
        root = QVBoxLayout(body)
        root.setContentsMargins(16, 12, 16, 10)
        root.setSpacing(6)
        head = QHBoxLayout()
        badge = QLabel(tr("SIMULATOR") + f" {info.id}")
        badge.setProperty("role", "badge")
        head.addWidget(badge)
        head.addStretch(1)
        if info.method:
            # V3: a learner reading a number off this page cannot tell a textbook
            # formula from a fit, or an exact answer from one good to fifteen per
            # cent. The button says which, without putting it in their way.
            how = QPushButton(tr("How this is computed"))
            how.setProperty("role", "link")
            how.setToolTip(tr("The formulas behind this simulator, and what they leave out"))
            how.clicked.connect(self._show_method)
            head.addWidget(how)
        root.addLayout(head)
        heading = QHBoxLayout()
        heading.setSpacing(10)
        mark = QLabel()
        nav_icons.set_label_symbol(mark, info.icon, 30)
        heading.addWidget(mark, 0, Qt.AlignVCenter)
        heading.addWidget(title_label(tr(info.title)), 1)
        root.addLayout(heading)
        root.addWidget(muted_label(tr(info.description)))
        self.simulator = info.create()
        self.challenges = load_challenges().get(info.id, [])
        self.challenge_bar = None
        if self.challenges:
            self.challenge_bar = ChallengeBar(ctx, self.simulator, self.challenges)
            self.challenge_bar.solved.connect(self._challenge_solved)
            root.addWidget(self.challenge_bar)
        root.addWidget(self.simulator, 1)

    def _challenge_solved(self, _key: str) -> None:
        self.ctx.signals.progressChanged.emit()

    def _show_method(self) -> None:
        """Open the Guide panel at the method, rather than a popup of its own.

        The panel already renders formulas and links to the lessons that derive
        them, and it is where the rest of this simulator's help lives.
        """
        self.ctx.signals.guideRequested.emit()

    def method_markdown(self) -> list[str]:
        """V3: the formulas behind this simulator, and what they leave out."""
        method = self.info.method
        if method is None:
            return []
        formulas = {f.id: f for f in load_formulas()}
        # The note itself is formula-sheet material — it names equations and cites
        # papers — so it stays in English like the formula sheet and the glossary.
        # The headings around it are translated.
        lines = ["", "### " + tr("How this is computed"), "", method.summary, ""]
        for formula_id in method.formulas:
            formula = formulas.get(formula_id)
            if formula is None:
                continue
            lines += [f"**{formula.title}**", "", f"$${formula.formula}$$", ""]
        if method.reference:
            lines += [f"**{tr('Follows')}:** {method.reference}", ""]
        if method.approximations:
            lines += [tr("**What it leaves out**"), ""]
            lines += [f"- {a}" for a in method.approximations]
        lines += ["", tr("Every check the physics engine has to pass is listed under "
                         "[Reference → Data & methods](reference:data)."), ""]
        return lines

    def guide_markdown(self) -> str:
        info = self.info
        cur = self.ctx.curriculum
        lines = [f"## {tr(info.title)}", "", tr(info.description), ""]
        lines += self.method_markdown()
        lines += ["### " + tr("How to use"), ""]
        lines += [f"{i}. {tr(step)}" for i, step in enumerate(info.how_to_use, 1)]
        lines += ["", "### " + tr("Things to try"), ""]
        lines += [f"- {tr(t)}" for t in info.things_to_try]
        lessons = [lid for lid in info.lessons if lid in cur.lessons]
        if lessons:
            lines += ["", "### " + tr("Related lessons"), ""]
            lines += [f"- [{lid} {cur.lessons[lid].title}](lesson:{lid})" for lid in lessons]
        if self.challenges:
            solved = sum(1 for c in self.challenges
                         if self.ctx.store.is_challenge_done(c.simulator, c.id))
            lines += ["", "### " + tr("Challenges"), "",
                      tr("This simulator has {total} guided challenges ({solved} solved). Read the task at "
                         "the top, set the controls, then press **Check my answer**.")
                      .format(total=len(self.challenges), solved=solved)]
        extra = getattr(self.simulator, "guide_extra", None)
        if extra:
            lines += ["", extra()]
        return "\n".join(lines)
