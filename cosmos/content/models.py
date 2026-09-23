"""Plain data classes describing course content."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class QuizQuestion:
    prompt: str
    choices: list[str]
    answer: int
    explanation: str


@dataclass(frozen=True)
class Lesson:
    id: str
    title: str
    level: int
    summary: str
    body: str
    minutes: int = 10
    prerequisites: list[str] = field(default_factory=list)
    simulators: list[str] = field(default_factory=list)
    objectives: list[str] = field(default_factory=list)
    quiz: list[QuizQuestion] = field(default_factory=list)

    @property
    def file_stem(self) -> str:
        return self.id.replace(".", "_")


@dataclass(frozen=True)
class Level:
    number: int
    title: str
    description: str
    lesson_ids: list[str]


@dataclass(frozen=True)
class Formula:
    """One entry of the formula sheet on the Reference page."""

    id: str
    group: str
    title: str
    formula: str          # mathtext source, without the surrounding $$
    symbols: str
    description: str
    lesson: str | None = None


@dataclass(frozen=True)
class Challenge:
    """One step of a guided challenge inside a simulator (G8)."""

    id: str
    simulator: str
    task: str
    hint: str
    success: str
    check: list[dict]

    @property
    def key(self) -> str:
        return f"{self.simulator}/{self.id}"


@dataclass(frozen=True)
class Problem:
    """A worked numeric exercise with a checked answer (G15)."""

    id: str
    level: int
    lesson: str
    title: str
    statement: str
    answer: float
    unit: str = ""
    tolerance: float = 0.02          # relative
    difficulty: int = 1              # 1 to 3
    hints: list[str] = field(default_factory=list)
    solution: str = ""
    simulator: str | None = None


@dataclass(frozen=True)
class ProblemSet:
    level: int
    title: str
    intro: str
    problems: list[Problem]


@dataclass(frozen=True)
class HistoryEvent:
    """A dated milestone on the history-of-cosmology timeline (G12)."""

    year: int
    title: str
    who: str
    description: str
    kind: str            # idea | theory | observation | problem
    lesson: str | None = None


@dataclass(frozen=True)
class Scientist:
    name: str
    years: str
    contribution: str
    story: str
    lessons: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TeacherNote:
    """What a teacher should watch for in one lesson (G19)."""

    lesson: str
    misconception: str
    discussion: str
    demonstrate: str

    def markdown(self, labels: dict[str, str] | None = None) -> str:
        """The note as Markdown, for the Guide panel and for printing."""
        names = labels or {"misconception": "Common misconception",
                           "discussion": "Discussion question",
                           "demonstrate": "Show them"}
        return "\n\n".join(
            f"**{names[field]}.** {getattr(self, field)}"
            for field in ("misconception", "discussion", "demonstrate"))


@dataclass(frozen=True)
class GlossaryTerm:
    key: str
    term: str
    definition: str
    see_also: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
