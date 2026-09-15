"""Load course content from Markdown and YAML files."""

from __future__ import annotations

import functools
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from cosmos.content.models import GlossaryTerm, Lesson, Level, QuizQuestion

CONTENT_DIR = Path(__file__).resolve().parent
_FRONT_MATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Curriculum:
    levels: list[Level]
    lessons: dict[str, Lesson]  # ordered: follows the course sequence

    @property
    def ordered_ids(self) -> list[str]:
        return list(self.lessons)

    def level_of(self, lesson_id: str) -> Level:
        return next(lv for lv in self.levels if lesson_id in lv.lesson_ids)

    def next_lesson(self, lesson_id: str) -> Lesson | None:
        ids = self.ordered_ids
        i = ids.index(lesson_id)
        return self.lessons[ids[i + 1]] if i + 1 < len(ids) else None

    def previous_lesson(self, lesson_id: str) -> Lesson | None:
        ids = self.ordered_ids
        i = ids.index(lesson_id)
        return self.lessons[ids[i - 1]] if i > 0 else None


def parse_lesson(text: str, lesson_id: str) -> tuple[dict, str]:
    match = _FRONT_MATTER.match(text.replace("\r\n", "\n"))
    if not match:
        raise ValueError(f"lesson {lesson_id} has no YAML front matter")
    meta = yaml.safe_load(match.group(1)) or {}
    return meta, match.group(2)


def _load_quiz(stem: str) -> list[QuizQuestion]:
    path = CONTENT_DIR / "quizzes" / f"{stem}.yaml"
    if not path.exists():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    return [
        QuizQuestion(
            prompt=q["question"].strip(),
            choices=[str(c) for c in q["choices"]],
            answer=int(q["answer"]),
            explanation=q["explanation"].strip(),
        )
        for q in data
    ]


@functools.cache
def load_curriculum() -> Curriculum:
    spec = yaml.safe_load((CONTENT_DIR / "curriculum.yaml").read_text(encoding="utf-8"))
    levels: list[Level] = []
    lessons: dict[str, Lesson] = {}
    for lv in spec["levels"]:
        ids = list(lv["lessons"])
        levels.append(Level(lv["number"], lv["title"], lv["description"].strip(), ids))
        for lesson_id in ids:
            stem = lesson_id.replace(".", "_")
            text = (CONTENT_DIR / "lessons" / f"{stem}.md").read_text(encoding="utf-8")
            meta, body = parse_lesson(text, lesson_id)
            if meta.get("id") != lesson_id:
                raise ValueError(f"{stem}.md declares id {meta.get('id')!r}, expected {lesson_id!r}")
            lessons[lesson_id] = Lesson(
                id=lesson_id,
                title=meta["title"],
                level=lv["number"],
                summary=meta.get("summary", "").strip(),
                body=body,
                minutes=int(meta.get("minutes", 10)),
                prerequisites=list(meta.get("prerequisites", []) or []),
                simulators=list(meta.get("simulators", []) or []),
                objectives=list(meta.get("objectives", []) or []),
                quiz=_load_quiz(stem),
            )
    return Curriculum(levels=levels, lessons=lessons)


@functools.cache
def load_glossary() -> dict[str, GlossaryTerm]:
    data = yaml.safe_load((CONTENT_DIR / "glossary.yaml").read_text(encoding="utf-8"))
    terms = {}
    for key, entry in data.items():
        terms[key] = GlossaryTerm(
            key=key,
            term=entry["term"],
            definition=entry["definition"].strip(),
            see_also=list(entry.get("see_also", []) or []),
            lessons=list(entry.get("lessons", []) or []),
        )
    return dict(sorted(terms.items(), key=lambda kv: kv[1].term.lower()))
