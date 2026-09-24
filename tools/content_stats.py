"""Count what the course contains, and check that the README says the same (E17).

The README advertises how many lessons, simulators, questions and so on the app
has. Every content change used to mean hunting for those numbers by hand; this
script counts them from the content itself, and ``tests/test_readme_numbers.py``
fails when the README has fallen behind.

    python tools/content_stats.py            # print the counts
    python tools/content_stats.py --check    # exit 1 and list what is out of date
    python tools/content_stats.py --write    # update the README in place
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

NUMBER_WORDS = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight",
                9: "nine", 10: "ten", 11: "eleven", 12: "twelve"}


def counts() -> dict[str, int]:
    """Everything the README quotes a number for, counted from the content."""
    import xml.etree.ElementTree as ET

    import yaml

    from cosmos.achievements import ACHIEVEMENTS
    from cosmos.content.loader import (load_challenges, load_curriculum, load_formulas, load_history,
                                       load_problems)
    from cosmos.gui.simulators.registry import BUILTIN_IDS

    curriculum = load_curriculum()
    events, scientists = load_history()
    sets = load_problems()
    glossary = yaml.safe_load((ROOT / "cosmos" / "content" / "glossary.yaml").read_text(encoding="utf-8"))
    ts = ET.parse(ROOT / "cosmos" / "i18n" / "cosmos_tr.ts").getroot()
    return {
        "lessons": len(curriculum.lessons),
        "levels": len(curriculum.levels),
        "simulators": len(BUILTIN_IDS),
        "quiz questions": sum(len(lesson.quiz) for lesson in curriculum.lessons.values()),
        "challenges": sum(len(steps) for steps in load_challenges().values()),
        "problems": sum(len(s.problems) for s in sets),
        "problem sets": len(sets),
        "glossary terms": len(glossary),
        "formulas": len(load_formulas()),
        "history events": len(events),
        "scientists": len(scientists),
        "badges": len(ACHIEVEMENTS),
        "turkish strings": sum(1 for _ in ts.iter("message")),
    }


# Each claim: a pattern with one number in it, and the count it must equal. A claim
# of the form "More than N" is satisfied by any count above N, rounded down to 100s.
CLAIMS = [
    (r"\*\*(\d+) lessons in (?:\w+) levels\*\*", "lessons"),
    (r"\*\*\d+ lessons in (\w+) levels\*\*", "levels"),
    (r"- \*\*(\d+) simulators\*\*", "simulators"),
    (r"\*\*(\d+) quiz questions\*\*", "quiz questions"),
    (r"\*\*(\d+) guided challenges\*\*", "challenges"),
    (r"\*\*(\d+) worked problems\*\*", "problems"),
    (r"\*\*\d+ worked problems\*\* in (\w+) sets", "problem sets"),
    (r"\*\*(\d+)-term glossary\*\*", "glossary terms"),
    (r"a (\d+)-entry formula sheet", "formulas"),
    (r"(\d+) milestones from", "history events"),
    (r"and (\d+)\s+scientist cards", "scientists"),
    (r"\*\*(\d+) badges\*\*", "badges"),
]
TRANSLATED = r"More than (\d+) strings"


def _value(text: str) -> int:
    if text.isdigit():
        return int(text)
    words = {v: k for k, v in NUMBER_WORDS.items()}
    return words.get(text.lower(), -1)


def _format(original: str, value: int) -> str:
    return str(value) if original.isdigit() else NUMBER_WORDS.get(value, str(value))


def simulator_bullets(readme: str) -> int:
    """The number of simulators listed under the simulators bullet."""
    match = re.search(r"- \*\*\d+ simulators\*\*\n((?:  - .*\n)+)", readme)
    return len(match.group(1).splitlines()) if match else 0


def problems(readme: str, found: dict[str, int]) -> list[str]:
    """What in the README disagrees with the content, as human-readable lines."""
    out = []
    for pattern, key in CLAIMS:
        match = re.search(pattern, readme)
        if match is None:
            out.append(f"README no longer mentions the {key} (pattern {pattern!r})")
        elif _value(match.group(1)) != found[key]:
            out.append(f"README says {match.group(1)} {key}, the content has {found[key]}")
    match = re.search(TRANSLATED, readme)
    if match is None:
        out.append("README no longer says how many strings are translated")
    else:
        claimed = int(match.group(1))
        floor = found["turkish strings"] // 100 * 100
        if not claimed <= found["turkish strings"] or claimed != floor:
            out.append(f"README says more than {claimed} translated strings, the pack has "
                       f"{found['turkish strings']} (write {floor})")
    listed = simulator_bullets(readme)
    if listed != found["simulators"]:
        out.append(f"README lists {listed} simulators by name, the app has {found['simulators']}")
    return out


def rewrite(readme: str, found: dict[str, int]) -> str:
    """The README with every number brought up to date (the simulator list is left to a human)."""
    for pattern, key in CLAIMS:
        def fix(match, key=key):
            whole, number = match.group(0), match.group(1)
            start = match.start(1) - match.start(0)
            return whole[:start] + _format(number, found[key]) + whole[start + len(number):]
        readme = re.sub(pattern, fix, readme, count=1)
    floor = found["turkish strings"] // 100 * 100
    return re.sub(TRANSLATED, f"More than {floor} strings", readme, count=1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true", help="exit 1 if the README is out of date")
    group.add_argument("--write", action="store_true", help="update the numbers in the README")
    args = parser.parse_args(argv)

    found = counts()
    readme = README.read_text(encoding="utf-8")
    if args.write:
        README.write_text(rewrite(readme, found), encoding="utf-8")
        readme = README.read_text(encoding="utf-8")
    wrong = problems(readme, found)
    if args.check or args.write:
        for line in wrong:
            print(line)
        return 1 if wrong else 0
    width = max(map(len, found))
    for key, value in found.items():
        print(f"{key:<{width}}  {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
