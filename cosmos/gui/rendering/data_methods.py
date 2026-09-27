"""The Data & methods text, written once for both places that show it (`R3`).

`V1` put this in the desktop app's Reference page. The static site that ships
with every release had none of it, so a reader of the web edition got a quietly
less honest version of the same course — no note of where a measurement came
from, no validation table. Copying the prose across would have started the two
drifting apart the same day, so both render this.

The only difference between them is how a link to a simulator is written, which
is what ``link`` is for.
"""

from __future__ import annotations

from collections.abc import Callable

from cosmos.i18n import tr

#: How the desktop app writes a link to a simulator; the site overrides it.
def app_link(simulator_id: str, title: str) -> str:
    return f"[{simulator_id} {title}](sim:{simulator_id})"


def validation_lines() -> list[str]:
        """V4: the engine's report card, with the numbers rather than the claim."""
        from cosmos import validation

        # The numbers are read, not recomputed. Running the checks here cost 2.8
        # seconds every time this page was opened for the first time, and bought
        # nothing: the astropy half cannot run in a packaged build at all, and a
        # test compares the record with a fresh run on every change.
        record = validation.read_record()
        if record is None:
            return ["## How the physics is checked", "",
                    "The checks have not been recorded in this copy. Run "
                    "`python tools/record_validation.py` to fill them in.", ""]
        rows_by_kind: dict[str, list[str]] = {}
        for check in validation.CHECKS:
            worst = record["worst"].get(check.id)
            shown = check.format(worst) if worst is not None else "not recorded"
            rows_by_kind.setdefault(check.against, []).append(
                f"| {check.quantity} | {check.reference} | {shown} | "
                f"{check.format(check.tolerance)} |")

        lines = [
            "## How the physics is checked", "",
            "The engine is not trusted because it looks right. Every quantity below is "
            "computed twice — once here, once by something that had nothing to do with "
            "this app — and the third column is the largest disagreement found anywhere "
            "in the range tested. The fourth is the most that would be accepted before "
            "the test suite fails, on Linux and on Windows, on every change.", "",
        ]
        headings = {
            validation.AGAINST_ASTROPY:
                ("Against another implementation",
                 "[astropy](https://www.astropy.org/) is the standard astronomy library "
                 "for Python, written by other people from the same equations. Agreement "
                 "at this level means the two codes are doing the same arithmetic."),
            validation.AGAINST_CLOSED_FORM:
                ("Against mathematics",
                 "Some universes can be solved with a pen. Those solutions are exact, so "
                 "any disagreement is the numerical method's own error and nothing else."),
            validation.AGAINST_PUBLISHED:
                ("Against published measurements",
                 "Here the tolerance is the published uncertainty rather than the "
                 "engine's: the app is being asked to land on a number the field agrees "
                 "on, not to reproduce it exactly."),
        }
        for kind, (title, blurb) in headings.items():
            lines += [f"### {title}", "", blurb, "",
                      "| Quantity | Compared with | Worst disagreement | Allowed |",
                      "|---|---|---|---|", *rows_by_kind.get(kind, []), ""]

        lines += [
            f"Measured on {record['measured']} and shipped with the app. The comparisons "
            "against astropy cannot be repeated inside a packaged build — astropy is a "
            "development dependency and is not included — so they are run where it is "
            "installed and the results travel with the app. A test repeats every one of "
            "them against a fresh run on every change, so what you see here cannot "
            "quietly go stale. `python tools/record_validation.py` repeats them for "
            "yourself.", "",
        ]
        lines += [
            "Alongside these, the suite opens every page, every lesson and every "
            "simulator, checks that this data list still matches the files in "
            "`cosmos/data`, and checks that no figure drawing invented data forgets to "
            "say so. A packaged build runs its own `--selftest` before it is published.", "",
        ]
        return lines


def data_markdown(link: Callable[[str, str], str] = app_link) -> str:
        """V1: every source the app plots, real and invented, in one place."""
        from cosmos import provenance
        from cosmos.gui.simulators.registry import SIMULATORS

        def links(ids: tuple[str, ...]) -> str:
            named = [link(i, tr(SIMULATORS[i].title)) for i in ids if i in SIMULATORS]
            return ", ".join(named)

        real, made = provenance.MEASUREMENTS, provenance.GENERATED
        lines = [
            "# Data and methods", "",
            f"The app plots two different kinds of thing. **{len(real)} files of real "
            f"measurements** are bundled with it, so that the course works without a "
            f"network; everything else it works out or invents as you go. Each plot says "
            f"which it is showing. This page says where each one came from.", "",
            "## Real measurements", "",
            "These are other people's work, redistributed so the course runs offline. If "
            "you use them for anything beyond learning, cite the papers, not this app.", "",
        ]
        for m in real:
            # A list rather than a table: a two-column table needs a header row, and an
            # empty one draws a blank band across the page.
            lines += [f"### {m.title}", "", f"`cosmos/data/{m.file}`", "", m.holds, "",
                      f"- **Source** — [{m.archive}]({m.url})",
                      f"- **Retrieved** — {m.retrieved}",
                      f"- **Cite** — {m.cite}",
                      f"- **Terms** — {m.terms}", ""]
            if m.prepared:
                lines += [f"**Prepared for the app.** {m.prepared}", ""]
            if m.caveat:
                lines += [f"**What it does not claim.** {m.caveat}", ""]
            where = links(m.used_by)
            if m.figures:
                where = f"{where} · {m.figures}" if where else m.figures
            if where:
                lines += [f"Used by {where}", ""]

        lines += [
            "## Data the app generates", "",
            "None of the following was measured by anyone. It is drawn, simulated or "
            "modelled inside the app to show how a measurement behaves, and it says so "
            "where it is shown — in the title of the figure, in the note beside the "
            "control that produced it, and in anything you export.", "",
        ]
        for g in made:
            lines += [f"### {g.title}", "", g.holds, "", g.how, ""]
            where = links(g.shown_in)
            if g.figures:
                where = f"{where} · {g.figures}" if where else g.figures
            if where:
                lines += [f"Shown in {where}", ""]
            lines += [f"Generated by `{g.module}`.", ""]

        lines += [
            *validation_lines(),
            "## What leaves with a file", "",
            "Save a plot and the picture carries a caption under it: the app and its "
            "version, which simulator drew it, whether what you are looking at was "
            "measured or generated, the sample or the model behind it, and the date. The "
            "same text goes into the image's metadata, where a program can read it. "
            "Export a table and it sits above the numbers as comment lines, which a "
            "spreadsheet ignores and a reader does not. A figure that ends up in someone "
            "else's slide deck should not need this page to be understood.", "",
            "## Where this list lives", "",
            "`cosmos/provenance.py` in the source, beside the code that loads the files, "
            "so the two cannot drift apart. The licence terms are in `NOTICE`, and "
            "`cosmos/data/external/README.md` carries the same record with the data "
            "itself, for anyone who takes the files without the app.", "",
        ]
        return "\n".join(lines)

