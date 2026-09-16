"""Global search across lessons, glossary, simulators and formulas (G10)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from cosmos.content.loader import load_formulas
from cosmos.gui.context import AppContext
from cosmos.i18n import tr, tr_noop

KIND_LABELS = {"lesson": tr_noop("Lesson"), "glossary": tr_noop("Term"),
               "simulator": tr_noop("Simulator"), "formula": tr_noop("Formula")}
# Singular and plural for the "3 lessons, 1 term" summary line.
KIND_COUNTS = {
    "lesson": (tr_noop("{n} lesson"), tr_noop("{n} lessons")),
    "glossary": (tr_noop("{n} term"), tr_noop("{n} terms")),
    "simulator": (tr_noop("{n} simulator"), tr_noop("{n} simulators")),
    "formula": (tr_noop("{n} formula"), tr_noop("{n} formulas")),
}
KIND_ICONS = {"lesson": "📖", "glossary": "🔤", "simulator": "🧪", "formula": "∑"}
SNIPPET_CHARS = 150


@dataclass(frozen=True)
class SearchHit:
    kind: str            # lesson | glossary | simulator | formula
    route: str           # where clicking the hit takes the learner
    title: str
    subtitle: str
    snippet: str
    score: float

    @property
    def icon(self) -> str:
        return KIND_ICONS[self.kind]

    @property
    def label(self) -> str:
        return tr(KIND_LABELS[self.kind])


def _clean(text: str) -> str:
    """Strip the lesson mark-up so snippets read as plain prose."""
    text = re.sub(r"\{\{figure:[^}]*\}\}", " ", text)
    text = re.sub(r":::\w+ ?", " ", text)
    text = re.sub(r"\[\[([^\]|]*)\|?([^\]]*)\]\]", lambda m: m.group(2) or m.group(1), text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#*`>|]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _snippet(text: str, needle: str) -> str:
    plain = _clean(text)
    index = plain.lower().find(needle)
    if index < 0:
        return plain[:SNIPPET_CHARS] + ("…" if len(plain) > SNIPPET_CHARS else "")
    start = max(0, index - SNIPPET_CHARS // 3)
    end = min(len(plain), index + len(needle) + 2 * SNIPPET_CHARS // 3)
    return ("…" if start else "") + plain[start:end].strip() + ("…" if end < len(plain) else "")


def _score(needle: str, fields: list[tuple[str, float]]) -> float:
    """Weighted score: exact-word matches count more than matches inside a word."""
    total = 0.0
    for text, weight in fields:
        low = text.lower()
        count = low.count(needle)
        if not count:
            continue
        total += weight * (1 + 0.15 * min(count - 1, 6))
        if re.search(rf"\b{re.escape(needle)}\b", low):
            total += weight * 0.5
    return total


def search(ctx: AppContext, query: str, limit: int = 60) -> list[SearchHit]:
    """Rank lessons, glossary terms, simulators and formulas against a query."""
    from cosmos.gui.simulators.registry import SIMULATORS

    needle = query.strip().lower()
    if len(needle) < 2:
        return []
    hits: list[SearchHit] = []

    for lesson in ctx.curriculum.lessons.values():
        objectives = " ".join(lesson.objectives)
        score = _score(needle, [(lesson.title, 100), (lesson.id, 90), (lesson.summary, 45),
                                (objectives, 30), (_clean(lesson.body), 12)])
        if score:
            hits.append(SearchHit("lesson", f"lesson:{lesson.id}", f"{lesson.id}  {lesson.title}",
                                  f"Level {lesson.level} · {lesson.minutes} min",
                                  _snippet(lesson.summary + " " + lesson.body, needle), score))

    for term in ctx.glossary.values():
        score = _score(needle, [(term.term, 100), (term.key, 70), (term.definition, 35)])
        if score:
            hits.append(SearchHit("glossary", f"glossary:{term.key}", term.term,
                                  "Glossary term", _snippet(term.definition, needle), score))

    for info in SIMULATORS.values():
        extra = " ".join(tr(t) for t in info.things_to_try + info.how_to_use)
        title, description = tr(info.title), tr(info.description)
        score = _score(needle, [(title, 100), (info.id, 80), (tr(info.tagline), 45),
                                (description, 30), (extra, 12)])
        if score:
            hits.append(SearchHit("simulator", f"sim:{info.id}", f"{info.icon}  {title}",
                                  f"Simulator {info.id}", _snippet(description, needle), score))

    for formula in load_formulas():
        score = _score(needle, [(formula.title, 100), (formula.group, 40), (formula.symbols, 35),
                                (formula.description, 30), (formula.formula, 25),
                                (formula.lesson or "", 60)])
        if score:
            hits.append(SearchHit("formula", f"reference:{formula.id}", formula.title, formula.group,
                                  _clean(formula.symbols or formula.description), score))

    hits.sort(key=lambda h: (-h.score, h.title))
    return hits[:limit]
