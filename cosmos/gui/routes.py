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
    if kind == "search" and target:
        return "🔎", f"Search: {target}"
    if kind in STATIC_TITLES:
        return STATIC_TITLES[kind]
    return "•", route


def route_title(ctx: AppContext, route: str) -> str:
    icon, title = route_parts(ctx, route)
    return f"{icon}  {title}"


def is_noteworthy(route: str) -> bool:
    """Pages a learner can bookmark or attach a note to."""
    kind, _, _target = route.partition(":")
    return kind in ("lesson", "sim", "glossary", "sims", "home", "progress", "reference")
