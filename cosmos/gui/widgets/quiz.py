"""Multiple-choice quiz with immediate, explained feedback."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cosmos.content.models import Lesson
from cosmos.gui.widgets.common import Banner, muted_label, title_label
from cosmos.progress import PASS_SCORE


class QuizWidget(QWidget):
    finished = Signal(float)       # score between 0 and 1
    nextLessonRequested = Signal()
    reviewRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.lesson: Lesson | None = None
        self.index = 0
        self.correct = 0
        self.answered = False

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 18, 24, 18)
        self.stack = QStackedWidget()
        root.addWidget(self.stack)

        # --- intro page
        intro = QWidget()
        il = QVBoxLayout(intro)
        il.addWidget(title_label("Check your understanding"))
        self.intro_text = muted_label("")
        il.addWidget(self.intro_text)
        self.best_label = QLabel()
        il.addWidget(self.best_label)
        start = QPushButton("Start the quiz")
        start.setProperty("role", "primary")
        start.clicked.connect(self.start)
        il.addWidget(start, 0, Qt.AlignLeft)
        il.addStretch(1)
        self.stack.addWidget(intro)

        # --- question page
        qpage = QWidget()
        ql = QVBoxLayout(qpage)
        head = QHBoxLayout()
        self.counter = muted_label("")
        head.addWidget(self.counter)
        head.addStretch(1)
        self.score_label = muted_label("")
        head.addWidget(self.score_label)
        ql.addLayout(head)
        self.progress = QProgressBar()
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        ql.addWidget(self.progress)
        self.prompt = title_label("", "subtitle")
        self.prompt.setTextFormat(Qt.PlainText)
        ql.addWidget(self.prompt)
        self.choices_host = QVBoxLayout()
        self.choices_host.setSpacing(8)
        ql.addLayout(self.choices_host)
        self.group = QButtonGroup(self)
        self.group.buttonClicked.connect(lambda _b: self.check.setEnabled(not self.answered))
        self.feedback = Banner("info")
        self.feedback.hide()
        ql.addWidget(self.feedback)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.check = QPushButton("Check answer")
        self.check.setProperty("role", "primary")
        self.check.clicked.connect(self.check_answer)
        self.next_btn = QPushButton("Next question")
        self.next_btn.setProperty("role", "primary")
        self.next_btn.clicked.connect(self.next_question)
        buttons.addWidget(self.check)
        buttons.addWidget(self.next_btn)
        ql.addLayout(buttons)
        ql.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(qpage)
        self.stack.addWidget(scroll)

        # --- result page
        rpage = QWidget()
        rl = QVBoxLayout(rpage)
        self.result_title = title_label("")
        self.result_banner = Banner("success")
        rl.addWidget(self.result_title)
        rl.addWidget(self.result_banner)
        rb = QHBoxLayout()
        retry = QPushButton("Try again")
        retry.clicked.connect(self.start)
        review = QPushButton("Review the lesson")
        review.clicked.connect(self.reviewRequested)
        self.next_lesson = QPushButton("Next lesson ▶")
        self.next_lesson.setProperty("role", "primary")
        self.next_lesson.clicked.connect(self.nextLessonRequested)
        rb.addWidget(retry)
        rb.addWidget(review)
        rb.addStretch(1)
        rb.addWidget(self.next_lesson)
        rl.addLayout(rb)
        rl.addStretch(1)
        self.stack.addWidget(rpage)

    # ----------------------------------------------------------------- api
    def load(self, lesson: Lesson, best: float | None) -> None:
        self.lesson = lesson
        n = len(lesson.quiz)
        self.intro_text.setText(
            f"This quiz has {n} questions about “{lesson.title}”. After each answer you will see an "
            f"explanation. Score at least {PASS_SCORE:.0%} to complete the lesson; you can retry "
            "as often as you like."
        )
        self.best_label.setText(f"Your best score so far: <b>{best:.0%}</b>" if best is not None else "")
        self.stack.setCurrentIndex(0)

    def start(self) -> None:
        if not self.lesson or not self.lesson.quiz:
            return
        self.index = 0
        self.correct = 0
        self.stack.setCurrentIndex(1)
        self._show_question()

    # ------------------------------------------------------------ internals
    def _show_question(self) -> None:
        q = self.lesson.quiz[self.index]
        n = len(self.lesson.quiz)
        self.answered = False
        self.counter.setText(f"Question {self.index + 1} of {n}")
        self.score_label.setText(f"Correct so far: {self.correct}")
        self.progress.setRange(0, n)
        self.progress.setValue(self.index)
        self.prompt.setText(q.prompt)
        for button in self.group.buttons():
            self.group.removeButton(button)
            button.hide()
            button.deleteLater()
        for i, choice in enumerate(q.choices):
            rb = QRadioButton(choice)
            rb.setStyleSheet("QRadioButton { padding: 6px; }")
            self.group.addButton(rb, i)
            self.choices_host.addWidget(rb)
        self.feedback.hide()
        self.check.setEnabled(False)
        self.check.show()
        self.next_btn.hide()

    def check_answer(self) -> None:
        q = self.lesson.quiz[self.index]
        chosen = self.group.checkedId()
        if chosen < 0:
            return
        self.answered = True
        ok = chosen == q.answer
        self.correct += int(ok)
        for button in self.group.buttons():
            button.setEnabled(False)
        right = q.choices[q.answer]
        if ok:
            self.feedback.set_message("success", f"<b>Correct!</b> {q.explanation}")
        else:
            self.feedback.set_message(
                "danger", f"<b>Not quite.</b> The right answer is <b>{right}</b>.<br>{q.explanation}"
            )
        self.feedback.show()
        self.score_label.setText(f"Correct so far: {self.correct}")
        self.check.hide()
        last = self.index == len(self.lesson.quiz) - 1
        self.next_btn.setText("See results" if last else "Next question")
        self.next_btn.show()
        self.next_btn.setFocus()

    def next_question(self) -> None:
        if self.index + 1 < len(self.lesson.quiz):
            self.index += 1
            self._show_question()
            return
        n = len(self.lesson.quiz)
        score = self.correct / n
        passed = score >= PASS_SCORE
        self.result_title.setText(f"You scored {self.correct} / {n} ({score:.0%})")
        if passed:
            self.result_banner.set_message(
                "success", "<b>Lesson complete!</b> Great work. The next lessons that build on this one are now ready."
            )
        else:
            self.result_banner.set_message(
                "warning",
                f"You need {PASS_SCORE:.0%} to complete the lesson. Review the explanations, "
                "re-read the parts that felt unclear, and try again.",
            )
        self.next_lesson.setVisible(passed)
        self.stack.setCurrentIndex(2)
        self.finished.emit(score)
