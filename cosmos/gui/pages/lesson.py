"""Lesson page: content, related simulators and the quiz."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget

from cosmos.content.models import Lesson
from cosmos.gui.context import AppContext
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.widgets.common import Banner, muted_label, title_label
from cosmos.gui.widgets.quiz import QuizWidget
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.progress import LessonStatus


class LessonPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.lesson: Lesson | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        self.badge = QLabel()
        self.badge.setProperty("role", "badge")
        head.addWidget(self.badge)
        self.status = muted_label("")
        head.addWidget(self.status)
        head.addStretch(1)
        self.minutes = muted_label("")
        head.addWidget(self.minutes)
        root.addLayout(head)
        self.title = title_label("")
        root.addWidget(self.title)
        self.summary = muted_label("")
        root.addWidget(self.summary)

        self.prereq_banner = Banner("warning")
        self.prereq_banner.label.linkActivated.connect(ctx.navigate)
        root.addWidget(self.prereq_banner)

        self.tabs = QTabWidget()
        self.tabs.setObjectName("lessonTabs")
        self.browser = RichBrowser(font_pt=11.5)
        self.browser.setObjectName("lessonBrowser")
        self.browser.glossaryRequested.connect(ctx.signals.glossaryRequested)
        self.browser.simulatorRequested.connect(lambda s: ctx.navigate(f"sim:{s}"))
        self.browser.lessonRequested.connect(lambda i: ctx.navigate(f"lesson:{i}"))
        self.quiz = QuizWidget()
        self.quiz.finished.connect(self._quiz_finished)
        self.quiz.nextLessonRequested.connect(self._go_next)
        self.quiz.reviewRequested.connect(lambda: self.tabs.setCurrentIndex(0))
        self.tabs.addTab(self.browser, "📖  Lesson")
        self.tabs.addTab(self.quiz, "✎  Quiz")
        root.addWidget(self.tabs, 1)

        nav = QHBoxLayout()
        self.prev_btn = QPushButton("◀ Previous lesson")
        self.prev_btn.clicked.connect(self._go_prev)
        nav.addWidget(self.prev_btn)
        self.sim_buttons = QHBoxLayout()
        nav.addStretch(1)
        nav.addLayout(self.sim_buttons)
        nav.addStretch(1)
        self.quiz_btn = QPushButton("Take the quiz ▶")
        self.quiz_btn.setObjectName("quizButton")
        self.quiz_btn.setProperty("role", "primary")
        self.quiz_btn.clicked.connect(self._open_quiz)
        nav.addWidget(self.quiz_btn)
        self.next_btn = QPushButton("Next lesson ▶")
        self.next_btn.clicked.connect(self._go_next)
        nav.addWidget(self.next_btn)
        root.addLayout(nav)

        self.tabs.currentChanged.connect(self._tab_changed)

    # ------------------------------------------------------------------ api
    def load(self, lesson_id: str) -> None:
        cur, store = self.ctx.curriculum, self.ctx.store
        lesson = cur.lessons[lesson_id]
        self.lesson = lesson
        level = cur.level_of(lesson_id)
        self.badge.setText(f"LEVEL {level.number} · {level.title.upper()}")
        self.title.setText(f"{lesson.id}  {lesson.title}")
        self.summary.setText(lesson.summary)
        self.minutes.setText(f"≈ {lesson.minutes} min read")
        self._refresh_status()

        body = self._compose_body(lesson)
        self.browser.set_markdown_content(body)
        self.browser.scroll_to_top()
        self.quiz.load(lesson, store.data.quiz_best.get(lesson_id))
        self.tabs.setCurrentIndex(0)

        while self.sim_buttons.count():
            item = self.sim_buttons.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        for sid in lesson.simulators:
            info = SIMULATORS[sid]
            btn = QPushButton(f"{info.icon} {info.title}")
            btn.setToolTip(f"Open the {info.title}: {info.tagline}")
            btn.clicked.connect(lambda _=False, s=sid: self.ctx.navigate(f"sim:{s}"))
            self.sim_buttons.addWidget(btn)

        self.prev_btn.setEnabled(cur.previous_lesson(lesson_id) is not None)
        self.next_btn.setEnabled(cur.next_lesson(lesson_id) is not None)
        store.mark_opened("lesson", lesson_id)

    def _compose_body(self, lesson: Lesson) -> str:
        parts = []
        if lesson.objectives:
            items = "\n".join(f"- {o}" for o in lesson.objectives)
            parts.append(f":::key In this lesson you will learn\n{items}\n:::\n")
        parts.append(lesson.body)
        nxt = self.ctx.curriculum.next_lesson(lesson.id)
        tail = "\n\n---\n\n**Finished reading?** Open the **Quiz** tab to check your understanding"
        if nxt:
            tail += f", then continue with [{nxt.id} {nxt.title}](lesson:{nxt.id})."
        else:
            tail += "."
        parts.append(tail)
        return "\n".join(parts)

    def _refresh_status(self) -> None:
        if not self.lesson:
            return
        cur, store = self.ctx.curriculum, self.ctx.store
        status = store.status(cur, self.lesson.id)
        best = store.data.quiz_best.get(self.lesson.id)
        text = {
            LessonStatus.COMPLETED: "✓ Completed",
            LessonStatus.READY: "● Ready to learn",
            LessonStatus.NOT_READY: "○ Prerequisites missing",
        }[status]
        if best is not None:
            text += f" · best quiz score {best:.0%}"
        self.status.setText(text)
        missing = store.missing_prerequisites(cur, self.lesson.id)
        if missing:
            links = ", ".join(
                f'<a href="lesson:{m}" style="color:inherit;"><b>{m} {cur.lessons[m].title}</b></a>' for m in missing
            )
            self.prereq_banner.set_message(
                "warning",
                f"This lesson builds on {links}. You can read it now, but it will be easier after "
                "completing those first.",
            )
            self.prereq_banner.show()
        else:
            self.prereq_banner.hide()

    def guide_markdown(self) -> str:
        if not self.lesson:
            return ""
        lesson = self.lesson
        cur = self.ctx.curriculum
        lines = [f"## {lesson.id} {lesson.title}", "", lesson.summary, "", "### How to study this lesson", ""]
        lines += [
            "1. Read the lesson from top to bottom. Formulas are explained in words right after they appear.",
            "2. Click the coloured glossary terms to see definitions here without losing your place.",
            "3. When you see a **Try it** box, open the simulator, experiment, then come back.",
            "4. Finish with the **Quiz** tab. Every answer comes with an explanation.",
            "",
        ]
        if lesson.prerequisites:
            lines.append("### Builds on")
            lines += [f"- [{p} {cur.lessons[p].title}](lesson:{p})" for p in lesson.prerequisites]
            lines.append("")
        if lesson.simulators:
            lines.append("### Related simulators")
            lines += [f"- [{SIMULATORS[s].title}](sim:{s}): {SIMULATORS[s].tagline}" for s in lesson.simulators]
            lines.append("")
        followers = [lid for lid, les in cur.lessons.items() if lesson.id in les.prerequisites]
        if followers:
            lines.append("### Leads to")
            lines += [f"- [{f} {cur.lessons[f].title}](lesson:{f})" for f in followers]
        return "\n".join(lines)

    # ------------------------------------------------------------ handlers
    def _open_quiz(self) -> None:
        self.tabs.setCurrentIndex(1)

    def _tab_changed(self, index: int) -> None:
        self.quiz_btn.setVisible(index == 0)

    def _quiz_finished(self, score: float) -> None:
        if not self.lesson:
            return
        self.ctx.store.record_quiz(self.lesson.id, score)
        self._refresh_status()
        self.ctx.signals.progressChanged.emit()

    def _go_next(self) -> None:
        nxt = self.ctx.curriculum.next_lesson(self.lesson.id)
        if nxt:
            self.ctx.navigate(f"lesson:{nxt.id}")

    def _go_prev(self) -> None:
        prev = self.ctx.curriculum.previous_lesson(self.lesson.id)
        if prev:
            self.ctx.navigate(f"lesson:{prev.id}")
