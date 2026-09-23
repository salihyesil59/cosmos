"""Pull one version's section out of CHANGELOG.md, for the release notes.

The changelog is the single place a release is described; this script is what the
workflow uses so that the notes on GitHub and the file in the repository can never
drift apart.

    python tools/release_notes.py 0.1.0 > notes.md
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def section(text: str, version: str) -> str:
    """The body of the `## <version>` heading, without the heading itself."""
    headings = list(re.finditer(r"^## +(\S+).*$", text, re.M))
    for index, heading in enumerate(headings):
        if heading.group(1) != version:
            continue
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        return text[heading.end():end].strip("\n") + "\n"
    raise SystemExit(f"CHANGELOG.md has no section for {version}")


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit(__doc__)
    sys.stdout.write(section(CHANGELOG.read_text(encoding="utf-8"), argv[1]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
