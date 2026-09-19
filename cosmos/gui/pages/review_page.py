"""Review page (G16): the quiz questions you got wrong, brought back on a schedule."""

from __future__ import annotations

from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from cosmos import review
from cosmos.gui.context import AppContext
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import card, muted_label, title_label
from cosmos.gui.widgets.quiz import QuizItem, QuizWidget
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## Review

Getting a quiz question wrong and moving on teaches very little. Every question you
miss is kept here and brought back later, which is the one study technique that has
survived a century of testing.

- A missed question comes back **tomorrow**.
- Answer it correctly and the wait grows: 3 days, then a week, then 16 days, then 35.
- Get it wrong again and it goes back to the start.
- A question you have answered correctly five times in a row has been learned, and
  leaves the deck for good.

Reviews take a couple of minutes. Doing them on the day they fall due is what makes
the method work — the whole point is to be asked just as you are about to forget.
""")


class ReviewPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self._items: list[QuizItem] = []

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(8)

        head = QHBoxLayout()
        heading = QVBoxLayout()
        heading.addWidget(title_label(tr("Review")))
        self.subtitle = muted_label("")
        heading.addWidget(self.subtitle)
        head.addLayout(heading, 1)
        self.forget_btn = QPushButton(tr("Empty the deck…"))
        self.forget_btn.setToolTip(tr("Remove every question from the review deck. Your quiz scores and "
                                      "completed lessons are not affected."))
        self.forget_btn.clicked.connect(self._forget)
        head.addWidget(self.forget_btn, 0, Qt.AlignTop)
        root.addLayout(head)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # --- overview
        overview = QWidget()
        ol = QVBoxLayout(overview)
        ol.setContentsMargins(0, 0, 0, 0)
        self.banner_card = card()
        bl = QVBoxLayout(self.banner_card)
        self.due_label = title_label("", "subtitle")
        self.due_label.setWordWrap(True)
        bl.addWidget(self.due_label)
        self.due_detail = muted_label("")
        self.due_detail.setWordWrap(True)
        bl.addWidget(self.due_detail)
        self.start_btn = QPushButton(tr("Start the review ▶"))
        self.start_btn.setProperty("role", "primary")
        self.start_btn.clicked.connect(self.start)
        bl.addWidget(self.start_btn, 0, Qt.AlignLeft)
        ol.addWidget(self.banner_card)

        self.schedule_card = card()
        sl = QVBoxLayout(self.schedule_card)
        sl.addWidget(title_label(tr("The next two weeks"), "subtitle"))
        self.schedule_grid = QGridLayout()
        self.schedule_grid.setHorizontalSpacing(4)
        sl.addLayout(self.schedule_grid)
        ol.addWidget(self.schedule_card)

        self.deck_card = card()
        dl = QVBoxLayout(self.deck_card)
        dl.addWidget(title_label(tr("What is in the deck"), "subtitle"))
        self.deck_host = QVBoxLayout()
        self.deck_host.setSpacing(4)
        dl.addLayout(self.deck_host)
        ol.addWidget(self.deck_card)
        ol.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(overview)
        scroll.setFrameShape(QFrame.NoFrame)
        self.stack.addWidget(scroll)

        # --- the session itself
        self.quiz = QuizWidget()
        self.quiz.answered_question.connect(self._answered)
        self.quiz.finished.connect(self._session_finished)
        self.stack.addWidget(self.quiz)

    # ------------------------------------------------------------- content
    def today(self) -> date:
        return date.today()

    def refresh(self) -> None:
        self.stack.setCurrentIndex(0)
        today = self.today()
        store = self.ctx.store
        report = store.review_summary(today)
        cards = review.deck(store.data.review, today)
        self._items = self._to_items(store.due_reviews(today))

        self.subtitle.setText(
            tr("Questions you got wrong, brought back just before you would forget them.")
            if cards else tr("Nothing here yet — and that is a good sign."))
        self.forget_btn.setVisible(bool(cards))

        if self._items:
            self.due_label.setText(tr("{count} question(s) are due today").format(count=len(self._items)))
            self.due_detail.setText(
                tr("From {lessons} lesson(s). It should take about {minutes} minute(s).")
                .format(lessons=len({i.lesson_id for i in self._items}),
                        minutes=max(1, round(len(self._items) * 0.4))))
        elif cards:
            when = report["next_due"]
            self.due_label.setText(tr("Nothing due today"))
            self.due_detail.setText(
                tr("{total} question(s) are waiting; the next one comes back on {date}.")
                .format(total=report["total"], date=when.isoformat() if when else "—"))
        else:
            self.due_label.setText(tr("The deck is empty"))
            self.due_detail.setText(
                tr("Any quiz question you answer wrongly is kept here and asked again tomorrow, then at "
                   "growing intervals until you have it for good."))
        self.start_btn.setVisible(bool(self._items))
        self._fill_schedule(today)
        self._fill_deck(cards, today)

    def _to_items(self, cards: list[review.Card]) -> list[QuizItem]:
        """Turn cards into questions, skipping any whose lesson or question has moved."""
        items = []
        for entry in cards:
            lesson = self.ctx.curriculum.lessons.get(entry.lesson_id)
            if lesson is None or entry.index >= len(lesson.quiz):
                continue
            items.append(QuizItem(entry.lesson_id, entry.index, lesson.quiz[entry.index],
                                  source=f"{entry.lesson_id} · {lesson.title}"))
        return items

    def _fill_schedule(self, today: date) -> None:
        while self.schedule_grid.count():
            self.schedule_grid.takeAt(0).widget().deleteLater()
        rows = review.upcoming(self.ctx.store.data.review, today)
        peak = max((count for _d, count in rows), default=0)
        p = theme().palette
        for column, (day, count) in enumerate(rows):
            bar = QLabel("▉" if count else "·")
            bar.setAlignment(Qt.AlignCenter)
            strength = 0.25 + 0.75 * (count / peak) if peak else 0.0
            colour = p.mix(p.accent, strength) if count else p.border
            bar.setStyleSheet(f"color: {colour}; font-size: {8 + int(14 * (count / peak) if peak else 0)}pt;")
            bar.setToolTip(tr("{count} question(s) due on {date}")
                           .format(count=count, date=day.isoformat()))
            number = muted_label(str(count) if count else "")
            number.setAlignment(Qt.AlignCenter)
            label = muted_label(tr("today") if column == 0 else str(day.day))
            label.setAlignment(Qt.AlignCenter)
            self.schedule_grid.addWidget(bar, 0, column)
            self.schedule_grid.addWidget(number, 1, column)
            self.schedule_grid.addWidget(label, 2, column)

    def _fill_deck(self, cards: list[review.Card], today: date) -> None:
        while self.deck_host.count():
            self.deck_host.takeAt(0).widget().deleteLater()
        if not cards:
            self.deck_host.addWidget(muted_label(tr("No questions are waiting.")))
            self.deck_card.setVisible(True)
            return
        for entry in cards[:40]:
            lesson = self.ctx.curriculum.lessons.get(entry.lesson_id)
            title = lesson.title if lesson else entry.lesson_id
            when = (tr("due today") if entry.is_due(today)
                    else tr("in {days} day(s)").format(days=(entry.due - today).days))
            row = QLabel(f"<b>{entry.lesson_id}</b> · {title} — "
                         + tr("question {number}, box {box} of {boxes}, {when}")
                         .format(number=entry.index + 1, box=entry.box, boxes=review.MAX_BOX, when=when))
            row.setWordWrap(True)
            row.setTextFormat(Qt.RichText)
            self.deck_host.addWidget(row)
        if len(cards) > 40:
            self.deck_host.addWidget(muted_label(tr("… and {count} more.").format(count=len(cards) - 40)))

    # ------------------------------------------------------------ handlers
    def start(self) -> None:
        if not self._items:
            return
        self.quiz.load_review(self._items)
        self.quiz.start()
        self.stack.setCurrentIndex(1)

    def _answered(self, lesson_id: str, index: int, correct: bool) -> None:
        self.ctx.store.record_question(lesson_id, index, correct, self.today())

    def _session_finished(self, score: float) -> None:
        self.ctx.store.record_review_session(len(self.quiz.items), self.quiz.correct)
        self.ctx.signals.progressChanged.emit()

    def _forget(self) -> None:
        answer = QMessageBox.question(
            self, tr("Empty the review deck?"),
            tr("This removes every question waiting for review. Your quiz scores, completed lessons and "
               "badges are not affected."))
        if answer == QMessageBox.Yes:
            self.ctx.store.forget_reviews()
            self.ctx.signals.progressChanged.emit()
            self.refresh()

    def guide_markdown(self) -> str:
        return tr(GUIDE)
