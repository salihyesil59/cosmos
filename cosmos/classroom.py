"""Classroom mode (G19): a progress report a teacher can actually read.

The app already records everything a teacher would want to know — which lessons are
finished, what the quiz scores were, which simulator challenges and worked problems
were solved, what is waiting in the review deck. This module turns that into prose
and a few tables, with no Qt involved, so the same text can go on screen, into a
Markdown file or onto paper.

Nothing here leaves the machine. The report is written when someone asks for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime

from cosmos.content.loader import Curriculum, load_challenges, load_problems

# A score this far below the pass mark, on a lesson marked complete, is worth a look.
SHAKY_SCORE = 0.85


@dataclass
class LevelReport:
    number: int
    title: str
    completed: int
    total: int
    average_score: float | None
    weakest: list[tuple[str, str, float]] = field(default_factory=list)   # id, title, score

    @property
    def fraction(self) -> float:
        return self.completed / self.total if self.total else 0.0


@dataclass
class Report:
    generated: date
    lessons_done: int
    lessons_total: int
    average_score: float | None
    perfect_quizzes: int
    challenges_done: int
    challenges_total: int
    problems_solved: int
    problems_total: int
    first_try_problems: int
    badges: int
    badges_total: int
    review_due: int
    review_total: int
    review_learned: int
    minutes_of_lessons: int
    levels: list[LevelReport] = field(default_factory=list)
    shaky: list[tuple[str, str, float]] = field(default_factory=list)
    unopened_simulators: list[str] = field(default_factory=list)
    last_activity: str = ""

    @property
    def fraction(self) -> float:
        return self.lessons_done / self.lessons_total if self.lessons_total else 0.0


def build(store, curriculum: Curriculum, today: date | None = None) -> Report:
    """Everything the report needs, read out of the progress store."""
    from cosmos.achievements import ACHIEVEMENTS
    from cosmos.gui.simulators.registry import SIMULATORS

    today = today or date.today()
    data = store.data
    scores = data.quiz_best

    levels = []
    for level in curriculum.levels:
        done = sum(1 for i in level.lesson_ids if store.is_completed(i))
        marks = [scores[i] for i in level.lesson_ids if i in scores]
        weakest = sorted(
            ((i, curriculum.lessons[i].title, scores[i]) for i in level.lesson_ids if i in scores),
            key=lambda row: row[2])[:3]
        levels.append(LevelReport(
            number=level.number, title=level.title, completed=done, total=len(level.lesson_ids),
            average_score=sum(marks) / len(marks) if marks else None, weakest=weakest))

    shaky = sorted(
        ((i, curriculum.lessons[i].title, score) for i, score in scores.items()
         if i in curriculum.lessons and store.is_completed(i) and score < SHAKY_SCORE),
        key=lambda row: row[2])

    problems = [p for s in load_problems() for p in s.problems]
    challenges_total = sum(len(steps) for steps in load_challenges().values())
    minutes = sum(curriculum.lessons[i].minutes for i in data.completed if i in curriculum.lessons)
    last = max(data.completed.values(), default="")
    return Report(
        generated=today,
        lessons_done=sum(1 for i in curriculum.ordered_ids if store.is_completed(i)),
        lessons_total=len(curriculum.ordered_ids),
        average_score=store.average_quiz_score(),
        perfect_quizzes=sum(1 for v in scores.values() if v >= 0.999),
        challenges_done=len(data.challenges_done),
        challenges_total=challenges_total,
        problems_solved=len(data.problems_solved),
        problems_total=len(problems),
        first_try_problems=sum(1 for n in data.problems_solved.values() if n == 1),
        badges=len(data.achievements),
        badges_total=len(ACHIEVEMENTS),
        review_due=len(store.due_reviews(today)),
        review_total=len(data.review),
        review_learned=data.review_learned,
        minutes_of_lessons=minutes,
        levels=levels,
        shaky=shaky,
        unopened_simulators=[k for k in SIMULATORS if k not in data.simulators_opened],
        last_activity=_readable(last),
    )


def _readable(stamp: str) -> str:
    try:
        return datetime.fromisoformat(stamp).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return ""


def _percent(value: float | None) -> str:
    return f"{value:.0%}" if value is not None else "—"


def markdown(report: Report, labels: dict[str, str] | None = None) -> str:
    """The report as Markdown: a summary, a table per level, and what to look at."""
    t = labels or {}

    def label(key: str, default: str) -> str:
        return t.get(key, default)

    lines = [
        f"# {label('title', 'Progress report')}",
        "",
        f"*{label('generated', 'Generated')} {report.generated.isoformat()}*",
        "",
        "## " + label("summary", "Summary"),
        "",
        f"- **{label('lessons', 'Lessons completed')}:** {report.lessons_done} / "
        f"{report.lessons_total} ({report.fraction:.0%}), "
        f"{label('reading', 'about {minutes} minutes of reading').format(minutes=report.minutes_of_lessons)}",
        f"- **{label('average', 'Average quiz score')}:** {_percent(report.average_score)}"
        f"  ·  {report.perfect_quizzes} {label('perfect', 'perfect')}",
        f"- **{label('challenges', 'Simulator challenges')}:** {report.challenges_done} / "
        f"{report.challenges_total}",
        f"- **{label('problems', 'Worked problems')}:** {report.problems_solved} / "
        f"{report.problems_total}  ·  {report.first_try_problems} "
        f"{label('first_try', 'at the first attempt')}",
        f"- **{label('badges', 'Badges')}:** {report.badges} / {report.badges_total}",
        f"- **{label('review', 'Review deck')}:** {report.review_total} "
        f"{label('waiting', 'waiting')}, {report.review_due} {label('due', 'due today')}, "
        f"{report.review_learned} {label('learned', 'learned for good')}",
    ]
    if report.last_activity:
        lines.append(f"- **{label('last', 'Last lesson completed')}:** {report.last_activity}")

    lines += ["", "## " + label("by_level", "By level"), "",
              "| " + " | ".join([label("level", "Level"), label("lessons_short", "Lessons"),
                                 label("average_short", "Average quiz")]) + " |",
              "|---|---|---|"]
    for level in report.levels:
        lines.append(f"| {level.number} · {level.title} | {level.completed} / {level.total} "
                     f"| {_percent(level.average_score)} |")

    if report.shaky:
        lines += ["", "## " + label("attention", "Worth going over again"), "",
                  label("shaky_intro",
                        "Completed, but only just. A pass at 70% leaves plenty unlearned."), ""]
        lines += [f"- **{lesson_id}** {title} — {score:.0%}" for lesson_id, title, score in report.shaky]

    if report.unopened_simulators:
        lines += ["", "## " + label("unopened", "Simulators not yet opened"), "",
                  ", ".join(report.unopened_simulators)]

    lines += ["", "---", "",
              label("footer",
                    "Everything in this report is read from this computer only. Nothing was uploaded.")]
    return "\n".join(lines)
