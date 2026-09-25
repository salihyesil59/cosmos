"""History page (G12): the timeline of discoveries and the people behind them."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from cosmos.content.loader import load_history
from cosmos.gui.context import AppContext
from cosmos.gui.theme import theme
from cosmos.gui.widgets.common import card, muted_label, title_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr, tr_noop

GUIDE = tr_noop("""
## The history of cosmology

Cosmology went from philosophy to precision science in four centuries. This page
follows that road.

- **Timeline** lists the milestones in order, from Copernicus to the latest
  results. The coloured tag says what kind of step it was: an **idea**, a piece
  of **theory**, an **observation**, or an open **problem**.
- **Scientists** collects the people. Click a card to read what they did and
  which lessons build on their work.
- The search box filters both, by name, year or keyword.

Every entry links to the lesson where the physics is explained, so the history
and the science stay together.
""")

KIND_LABELS = {
    "idea": (tr_noop("Idea"), "accent2"),
    "theory": (tr_noop("Theory"), "accent"),
    "observation": (tr_noop("Observation"), "success"),
    "problem": (tr_noop("Open problem"), "danger"),
}


class HistoryPage(QWidget):
    def __init__(self, ctx: AppContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.events, self.scientists = load_history()

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 14, 20, 12)
        root.setSpacing(8)
        root.addWidget(title_label(tr("The history of cosmology")))
        root.addWidget(muted_label(
            tr("{events} milestones between {first} and {last}, and {people} of the people behind them.")
            .format(events=len(self.events), first=self.events[0].year, last=self.events[-1].year,
                    people=len(self.scientists))))
        self.search = QLineEdit()
        self.search.setPlaceholderText(tr("Filter by name, year or keyword…  (e.g. Hubble, 1998, dark matter)"))
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(self._refresh)
        root.addWidget(self.search)

        self.tabs = QTabWidget()
        root.addWidget(self.tabs, 1)

        timeline_host = QWidget()
        tl = QVBoxLayout(timeline_host)
        tl.setContentsMargins(0, 8, 0, 0)
        self.timeline_scroll = QScrollArea()
        self.timeline_scroll.setProperty("scrolls_sideways", True)   # it is a timeline
        self.timeline_scroll.setWidgetResizable(True)
        inner = QWidget()
        self.timeline_layout = QVBoxLayout(inner)
        self.timeline_layout.setContentsMargins(0, 0, 10, 0)
        self.timeline_layout.setSpacing(8)
        self.timeline_scroll.setWidget(inner)
        tl.addWidget(self.timeline_scroll)
        self.timeline_count = muted_label("")
        tl.addWidget(self.timeline_count)
        self.tabs.addTab(timeline_host, "🕰  " + tr("Timeline"))

        people_host = QWidget()
        pl = QHBoxLayout(people_host)
        pl.setContentsMargins(0, 8, 0, 0)
        people_scroll = QScrollArea()
        people_scroll.setWidgetResizable(True)
        cards_host = QWidget()
        self.people_grid = QGridLayout(cards_host)
        self.people_grid.setSpacing(8)
        people_scroll.setWidget(cards_host)
        pl.addWidget(people_scroll, 3)
        self.person_view = RichBrowser(font_pt=11.0)
        self.person_view.lessonRequested.connect(lambda i: ctx.navigate(f"lesson:{i}"))
        self.person_view.glossaryRequested.connect(ctx.signals.glossaryRequested)
        pl.addWidget(self.person_view, 2)
        self.tabs.addTab(people_host, "👩‍🔬  " + tr("Scientists"))

        self._refresh()
        if self.scientists:
            self.show_scientist(self.scientists[0])

    def guide_markdown(self) -> str:
        return tr(GUIDE)

    # ------------------------------------------------------------------ api
    def matching_events(self, needle: str = "") -> list:
        needle = needle.strip().lower()
        if not needle:
            return list(self.events)
        return [e for e in self.events
                if needle in f"{e.year} {e.title} {e.who} {e.description} {e.kind}".lower()]

    def matching_scientists(self, needle: str = "") -> list:
        needle = needle.strip().lower()
        if not needle:
            return list(self.scientists)
        return [s for s in self.scientists
                if needle in f"{s.name} {s.years} {s.contribution} {s.story}".lower()]

    def show_scientist(self, scientist) -> None:
        cur = self.ctx.curriculum
        lines = [f"# {scientist.name}", "", f"*{scientist.years}*", "",
                 f"**{scientist.contribution}**", "", scientist.story, ""]
        lessons = [lid for lid in scientist.lessons if lid in cur.lessons]
        if lessons:
            lines += ["**Where the course builds on this work:**", ""]
            lines += [f"- [{lid} {cur.lessons[lid].title}](lesson:{lid})" for lid in lessons]
        related = [e for e in self.events if scientist.name.split()[-1] in e.who]
        if related:
            lines += ["", "**On the timeline:**", ""]
            lines += [f"- {e.year} — {e.title}" for e in related]
        self.person_view.set_markdown_content("\n".join(lines))

    # -------------------------------------------------------------- private
    def _refresh(self, *_args) -> None:
        needle = self.search.text()
        self._fill_timeline(self.matching_events(needle))
        self._fill_people(self.matching_scientists(needle))

    @staticmethod
    def _clear(layout) -> None:
        while layout.count():
            widget = layout.takeAt(0).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _fill_timeline(self, events) -> None:
        self._clear(self.timeline_layout)
        p = theme().palette
        decade = None
        for event in events:
            century = event.year // 100 * 100
            if century != decade:
                decade = century
                self.timeline_layout.addWidget(title_label(f"{century}s", "subtitle"))
            self.timeline_layout.addWidget(self._event_card(event, p))
        self.timeline_layout.addStretch(1)
        self.timeline_count.setText(tr("{n} milestones shown").format(n=len(events)))

    def _event_card(self, event, palette) -> QWidget:
        label, colour_attr = KIND_LABELS.get(event.kind, KIND_LABELS["idea"])
        colour = getattr(palette, colour_attr)
        frame = card()
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)
        year = QLabel(str(event.year))
        year.setStyleSheet(f"color: {colour}; font-size: 16pt; font-weight: 600;")
        year.setFixedWidth(64)
        year.setAlignment(Qt.AlignTop)
        layout.addWidget(year)
        text = QVBoxLayout()
        text.setSpacing(2)
        head = QLabel(f"<b>{event.title}</b> &nbsp;<span style='color:{colour}'>{tr(label)}</span>")
        head.setTextFormat(Qt.RichText)
        head.setWordWrap(True)
        text.addWidget(head)
        text.addWidget(muted_label(event.who))
        body = QLabel(event.description)
        body.setWordWrap(True)
        text.addWidget(body)
        layout.addLayout(text, 1)
        if event.lesson in self.ctx.curriculum.lessons:
            lesson = self.ctx.curriculum.lessons[event.lesson]
            button = QPushButton(f"{event.lesson} ▶")
            button.setToolTip(tr("Open {lesson}").format(lesson=f"{event.lesson} {lesson.title}"))
            button.clicked.connect(lambda _=False, lid=event.lesson: self.ctx.navigate(f"lesson:{lid}"))
            layout.addWidget(button, 0, Qt.AlignTop)
        return frame

    def _fill_people(self, scientists) -> None:
        self._clear(self.people_grid)
        for i, scientist in enumerate(scientists):
            frame = card()
            layout = QVBoxLayout(frame)
            layout.setContentsMargins(12, 10, 12, 10)
            layout.setSpacing(3)
            name = QLabel(f"<b>{scientist.name}</b>")
            name.setTextFormat(Qt.RichText)
            name.setWordWrap(True)
            layout.addWidget(name)
            layout.addWidget(muted_label(scientist.years))
            contribution = QLabel(scientist.contribution)
            contribution.setWordWrap(True)
            layout.addWidget(contribution)
            read = QPushButton(tr("Read more"))
            read.setProperty("role", "link")
            read.clicked.connect(lambda _=False, s=scientist: self.show_scientist(s))
            layout.addWidget(read, 0, Qt.AlignLeft)
            self.people_grid.addWidget(frame, i // 2, i % 2)
