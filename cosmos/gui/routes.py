"""Human-readable names for routes, used by bookmarks, notes and search."""

from __future__ import annotations

from cosmos.gui.context import AppContext

STATIC_TITLES = {
    "home": ("⌂", "Home"),
    "sims": ("🧪", "All simulators"),
    "glossary": ("📖", "Glossary"),
    "progress": ("📈", "Progress"),
    "reference": ("∑", "Reference"),
    "notes": ("📝", "Notes & bookmarks"),
    "search": ("🔎", "Search"),
    "problems": ("✏", "Problem sets"),
    "review": ("🔁", "Review"),
    "classroom": ("🎓", "Classroom"),
}


def route_parts(ctx: AppContext, route: str) -> tuple[str, str]:
    """Return an icon and a title for a route, even for routes that no longer exist."""
    from cosmos.gui.simulators.registry import SIMULATORS

    kind, _, target = route.partition(":")
    if kind == "lesson" and target in ctx.curriculum.lessons:
        return "📖", f"{target}  {ctx.curriculum.lessons[target].title}"
    if kind == "sim" and target in SIMULATORS:
        return SIMULATORS[target].icon, SIMULATORS[target].title
    if kind == "glossary" and target in ctx.glossary:
        return "🔤", f"{ctx.glossary[target].term} (glossary)"
    if kind == "problems" and target:
        from cosmos.content.loader import load_problems

        problem = next((p for s in load_problems() for p in s.problems if p.id == target), None)
        if problem:
            return "✏", f"{problem.title} (problem, level {problem.level})"
    if kind == "search" and target:
        return "🔎", f"Search: {target}"
    if kind in STATIC_TITLES:
        return STATIC_TITLES[kind]
    return "•", route


def route_title(ctx: AppContext, route: str) -> str:
    icon, title = route_parts(ctx, route)
    return f"{icon}  {title}"


def page_context(ctx: AppContext, route: str) -> str:
    """A plain-text description of the page, for the optional tutor (E9).

    Only what is already on the learner's screen: the lesson they are reading,
    or the simulator and the values it currently shows.
    """
    from cosmos.gui.search import _clean
    from cosmos.gui.simulators.registry import SIMULATORS

    kind, _, target = route.partition(":")
    if kind == "lesson" and target in ctx.curriculum.lessons:
        lesson = ctx.curriculum.lessons[target]
        objectives = "; ".join(lesson.objectives)
        return (f"Lesson {lesson.id} — {lesson.title}\nSummary: {lesson.summary}\n"
                f"Objectives: {objectives}\n\n{_clean(lesson.body)}")
    if kind == "sim" and target in SIMULATORS:
        info = SIMULATORS[target]
        return f"Simulator {info.id} — {info.title}\n{info.description}"
    if kind == "glossary" and target in ctx.glossary:
        term = ctx.glossary[target]
        return f"Glossary term: {term.term}\n{term.definition}"
    if kind == "problems" and target:
        from cosmos.content.loader import load_problems

        problem = next((p for s in load_problems() for p in s.problems if p.id == target), None)
        if problem:
            # The statement only: the tutor should help the learner reach the answer, not hand it over.
            return (f"Worked problem (level {problem.level}, lesson {problem.lesson}): {problem.title}\n"
                    f"{problem.statement}\nAnswer unit: {problem.unit or 'none'}")
    icon, title = route_parts(ctx, route)
    return f"The learner is on the page: {title}"


def is_noteworthy(route: str) -> bool:
    """Pages a learner can bookmark or attach a note to."""
    kind, _, _target = route.partition(":")
    return kind in ("lesson", "sim", "glossary", "sims", "home", "progress", "reference", "problems")
