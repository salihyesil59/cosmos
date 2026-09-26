"""Multiple-choice quiz with immediate, explained feedback.

The same widget runs two things: the quiz at the end of a lesson, and a
spaced-repetition session (G16) that mixes questions from every lesson whose cards
have fallen due. Only the framing differs, so both build a list of :class:`QuizItem` and run it.
"""

from __future__ import annotations

from dataclasses import dataclass

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

from cosmos.content.models import Lesson, QuizQuestion
from cosmos.gui import nav_icons
from cosmos.gui.widgets.common import Banner, muted_label, title_label
from cosmos.i18n import tr
from cosmos.progress import PASS_SCORE


@dataclass(frozen=True)
class QuizItem:
    """One question, and where it came from."""

    lesson_id: str
    index: int                 # its position in that lesson's quiz
    question: QuizQuestion
    source: str = ""           # shown in review mode, where the questions are mixed


class QuizWidget(QWidget):
    finished = Signal(float)              # score between 0 and 1
    answered_question = Signal(str, int, bool)   # lesson id, question index, correct
    nextLessonRequested = Signal()
    reviewRequested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.lesson: Lesson | None = None
        self.items: list[QuizItem] = []
        self.review_mode = False
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
        self.intro_title = title_label(tr("Check your understanding"))
        il.addWidget(self.intro_title)
        self.intro_text = muted_label("")
        il.addWidget(self.intro_text)
        self.best_label = QLabel()
        il.addWidget(self.best_label)
        self.start_button = QPushButton(tr("Start the quiz"))
        self.start_button.setProperty("role", "primary")
        self.start_button.clicked.connect(self.start)
        il.addWidget(self.start_button, 0, Qt.AlignLeft)
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
        self.source_label = muted_label("")
        ql.addWidget(self.source_label)
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
        self.check = QPushButton(tr("Check answer"))
        self.check.setProperty("role", "primary")
        self.check.clicked.connect(self.check_answer)
        self.next_btn = QPushButton(tr("Next question"))
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
        retry = QPushButton(tr("Try again"))
        retry.clicked.connect(self.start)
        self.retry_button = retry
        review = QPushButton(tr("Review the lesson"))
        review.clicked.connect(self.reviewRequested)
        self.review_button = review
        self.next_lesson = QPushButton(tr("Next lesson"))
        self.next_lesson.setProperty("role", "primary")
        self.next_lesson.setLayoutDirection(Qt.RightToLeft)     # the arrow after the words
        nav_icons.set_glyph(self.next_lesson, "forward", 14)
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
        """The quiz at the end of a lesson."""
        self.lesson = lesson
        self.review_mode = False
        self.items = [QuizItem(lesson.id, i, q) for i, q in enumerate(lesson.quiz)]
        n = len(self.items)
        self.intro_title.setText(tr("Check your understanding"))
        self.start_button.setText(tr("Start the quiz"))
        self.intro_text.setText(
            tr("This quiz has {count} questions about “{lesson}”. After each answer you will see an "
               "explanation. Score at least {score} to complete the lesson; you can retry as often as "
               "you like.").format(count=n, lesson=lesson.title, score=f"{PASS_SCORE:.0%}")
        )
        self.best_label.setText(tr("Your best score so far: <b>{score}</b>").format(score=f"{best:.0%}")
                                if best is not None else "")
        self.stack.setCurrentIndex(0)

    def load_review(self, items: list[QuizItem]) -> None:
        """A spaced-repetition session: questions from any lesson, due today."""
        self.lesson = None
        self.review_mode = True
        self.items = list(items)
        self.intro_title.setText(tr("Time to review"))
        self.start_button.setText(tr("Start the review"))
        self.intro_text.setText(
            tr("{count} question(s) you once got wrong are due today, from {lessons} lesson(s). Answer one "
               "correctly and it comes back later still; get it wrong and it starts again tomorrow.")
            .format(count=len(self.items), lessons=len({i.lesson_id for i in self.items}))
        )
        self.best_label.setText("")
        self.stack.setCurrentIndex(0)

    def start(self) -> None:
        if not self.items:
            return
        self.index = 0
        self.correct = 0
        self.stack.setCurrentIndex(1)
        self._show_question()

    # ------------------------------------------------------------ internals
    def _show_question(self) -> None:
        item = self.items[self.index]
        q = item.question
        n = len(self.items)
        self.answered = False
        self.source_label.setText(item.source)
        self.source_label.setVisible(bool(item.source))
        self.counter.setText(tr("Question {number} of {total}").format(number=self.index + 1, total=n))
        self.score_label.setText(tr("Correct so far: {count}").format(count=self.correct))
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
        item = self.items[self.index]
        q = item.question
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
            self.feedback.set_message("success", tr("<b>Correct!</b>") + f" {q.explanation}")
        else:
            self.feedback.set_message(
                "danger", tr("<b>Not quite.</b> The right answer is <b>{answer}</b>.").format(answer=right)
                + f"<br>{q.explanation}"
            )
        self.feedback.show()
        self.score_label.setText(tr("Correct so far: {count}").format(count=self.correct))
        self.check.hide()
        self.answered_question.emit(item.lesson_id, item.index, ok)
        last = self.index == len(self.items) - 1
        self.next_btn.setText(tr("See results") if last else tr("Next question"))
        self.next_btn.show()
        self.next_btn.setFocus()

    def next_question(self) -> None:
        if self.index + 1 < len(self.items):
            self.index += 1
            self._show_question()
            return
        n = len(self.items)
        score = self.correct / n
        self.result_title.setText(tr("You scored {correct} / {total} ({score})")
                                  .format(correct=self.correct, total=n, score=f"{score:.0%}"))
        if self.review_mode:
            self._finish_review(score)
        else:
            self._finish_quiz(score)
        self.stack.setCurrentIndex(2)
        self.finished.emit(score)

    def _finish_quiz(self, score: float) -> None:
        passed = score >= PASS_SCORE
        if passed:
            self.result_banner.set_message(
                "success", tr("<b>Lesson complete!</b> Great work. The next lessons that build on this one "
                              "are now ready.")
            )
        else:
            self.result_banner.set_message(
                "warning",
                tr("You need {score} to complete the lesson. Review the explanations, re-read the parts that "
                   "felt unclear, and try again.").format(score=f"{PASS_SCORE:.0%}"),
            )
        self.next_lesson.setVisible(passed)
        self.retry_button.setVisible(True)
        self.review_button.setVisible(True)

    def _finish_review(self, score: float) -> None:
        missed = len(self.items) - self.correct
        if missed:
            self.result_banner.set_message(
                "info",
                tr("<b>Review done.</b> {count} question(s) go back to the start and return tomorrow; the "
                   "rest have moved further out.").format(count=missed))
        else:
            self.result_banner.set_message(
                "success",
                tr("<b>All of them.</b> Every card moved up a box, and the ones that passed the last box "
                   "have left the deck for good."))
        self.next_lesson.setVisible(False)
        self.retry_button.setVisible(False)
        self.review_button.setVisible(False)
