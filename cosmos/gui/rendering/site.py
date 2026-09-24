"""Export the course as a static website (E19).

The same Markdown the desktop app shows becomes a folder of plain HTML pages that
open in any browser, from a web server or straight from disk, with no internet
connection: every formula and figure is rendered to a PNG file next to the pages,
and the quizzes and worked problems keep working through a few lines of
JavaScript. The simulators need Qt and stay in the desktop app; the site lists
them with their guidance and points to the download.

    from cosmos.gui.rendering.site import build_site
    report = build_site(Path("dist/site"))

A ``QGuiApplication`` must exist (formula sizes are measured with ``QImage``);
``tools/build_site.py`` creates one off-screen.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from cosmos import APP_NAME, __version__
from cosmos.content.models import Lesson, split_remember
from cosmos.gui.rendering import math as mathrender
from cosmos.gui.rendering.lesson_html import RenderContext, render_markdown
from cosmos.gui.theme import LIGHT

RELEASES_URL = "https://github.com/salihyesil59/cosmos/releases"
IMAGE_RATIO = 2.0                   # render images at twice the size, for sharp text on any screen


@dataclass
class SiteReport:
    out: Path
    pages: list[str] = field(default_factory=list)
    images: int = 0

    @property
    def bytes(self) -> int:
        return sum(p.stat().st_size for p in self.out.rglob("*") if p.is_file())


def lesson_file(lesson_id: str) -> str:
    return f"lessons/{lesson_id.replace('.', '_')}.html"


def esc(text: str) -> str:
    return html.escape(text or "", quote=True)


class SiteBuilder:
    def __init__(self, out: Path):
        from cosmos.content.loader import (load_curriculum, load_formulas, load_glossary,
                                           load_problems)
        from cosmos.gui.simulators.registry import BUILTIN_IDS, SIMULATORS

        self.out = Path(out)
        self.curriculum = load_curriculum()
        self.glossary = load_glossary()
        self.formulas = load_formulas()
        self.problem_sets = load_problems()
        self.simulators = {key: SIMULATORS[key] for key in SIMULATORS if key in BUILTIN_IDS}
        self.ctx = RenderContext(
            palette=LIGHT, font_pt=12.75, device_ratio=IMAGE_RATIO,     # 12.75 pt = the 17 px body text
            simulator_titles={key: info.title for key, info in self.simulators.items()},
            glossary_terms={key: term.definition for key, term in self.glossary.items()},
        )
        self.report = SiteReport(out=self.out)
        self._images: set[str] = set()

    # ------------------------------------------------------------ plumbing
    def _write(self, relative: str, text: str) -> None:
        path = self.out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        if relative.endswith(".html"):
            self.report.pages.append(relative)

    def _image(self, png: bytes) -> str:
        """Store a PNG once, named by its content; returns its path from the site root."""
        name = hashlib.sha1(png).hexdigest()[:16] + ".png"
        if name not in self._images:
            target = self.out / "assets" / "img" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(png)
            self._images.add(name)
        return f"assets/img/{name}"

    def markdown(self, text: str, depth: int) -> str:
        """Course Markdown as site HTML, with images saved and app links turned into web links."""
        doc = render_markdown(text, self.ctx)
        body = doc.html.removeprefix("<html><body>").removesuffix("</body></html>")
        prefix = "../" * depth
        for url, png in doc.images.items():
            body = body.replace(f'src="{url}"', f'src="{prefix}{self._image(png)}"')
        body = re.sub(r'href="lesson:([\w.]+)"', lambda m: f'href="{prefix}{lesson_file(m.group(1))}"', body)
        body = re.sub(r'href="glossary:([\w-]+)"', lambda m: f'href="{prefix}glossary.html#{m.group(1)}"', body)
        body = re.sub(r'href="sim:(S\d+)"', lambda m: f'href="{prefix}simulators.html#{m.group(1)}"', body)
        return body

    def math(self, tex: str, depth: int) -> str:
        png = mathrender.render_png(" ".join(tex.split()), LIGHT.text, 12.0, IMAGE_RATIO)
        from PySide6.QtGui import QImage

        image = QImage.fromData(png, "PNG")
        w, h = round(image.width() / IMAGE_RATIO), round(image.height() / IMAGE_RATIO)
        return (f'<img class="formula" src="{"../" * depth}{self._image(png)}" width="{w}" height="{h}" '
                f'alt="{esc(tex)}"/>')

    def page(self, relative: str, title: str, body: str, *, depth: int = 0, section: str = "") -> None:
        prefix = "../" * depth
        nav = [("index.html", "Course", "course"), ("glossary.html", "Glossary", "glossary"),
               ("formulas.html", "Formulas", "formulas"), ("problems.html", "Problems", "problems"),
               ("simulators.html", "Simulators", "simulators")]
        current = ' aria-current="page"'
        links = "".join(f'<a href="{prefix}{href}"{current if key == section else ""}>{label}</a>'
                        for href, label, key in nav)
        self._write(relative, f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · {APP_NAME}</title>
<link rel="stylesheet" href="{prefix}assets/site.css">
<link rel="icon" href="{prefix}assets/cosmos.png">
</head>
<body>
<header class="site"><a class="brand" href="{prefix}index.html">✦ {APP_NAME}</a><nav>{links}</nav></header>
<main>
{body}
</main>
<footer class="site">
<p>{APP_NAME} {__version__} — an interactive course in cosmology. The simulators run in the
<a href="{RELEASES_URL}">desktop app</a> for Windows, macOS and Linux. Course text under the MIT licence;
the observational data belong to the teams who measured it.</p>
</footer>
<script src="{prefix}assets/site.js"></script>
</body>
</html>
""")

    # -------------------------------------------------------------- pages
    def build(self) -> SiteReport:
        if self.out.exists():
            # Only ever replace an empty folder or a site built here before: never a folder of
            # someone's files that happened to be given as the target.
            if any(self.out.iterdir()) and not (self.out / "assets" / "site.css").exists():
                raise FileExistsError(f"{self.out} is not empty and is not a Cosmos website; "
                                      "choose an empty folder")
            shutil.rmtree(self.out)
        (self.out / "assets").mkdir(parents=True)
        self._write("assets/site.css", SITE_CSS)
        self._write("assets/site.js", SITE_JS)
        icon = Path(__file__).resolve().parents[1] / "resources" / "cosmos.png"
        if icon.exists():
            shutil.copyfile(icon, self.out / "assets" / "cosmos.png")
        self.index_page()
        for lesson_id in self.curriculum.ordered_ids:
            self.lesson_page(self.curriculum.lessons[lesson_id])
        self.glossary_page()
        self.formulas_page()
        self.problems_page()
        self.simulators_page()
        self.report.images = len(self._images)
        return self.report

    def index_page(self) -> None:
        cur = self.curriculum
        parts = [
            f"<h1>{APP_NAME}</h1>",
            '<p class="lead">An interactive course in cosmology — the science of the universe as a whole. '
            "Start with how big the universe is and how we measure it, and work your way up to the expanding "
            "universe, dark matter, dark energy, the first minutes after the Big Bang and the questions still "
            "open today.</p>",
            f'<p class="meta">{len(cur.lessons)} lessons in {len(cur.levels)} levels · '
            f'{sum(len(lesson.quiz) for lesson in cur.lessons.values())} quiz questions · '
            f'{len(self.glossary)} glossary terms · {len(self.formulas)} formulas · '
            f'{sum(len(s.problems) for s in self.problem_sets)} worked problems</p>',
            f'<p class="note">This is the reading edition. The {len(self.simulators)} simulators, progress '
            f'tracking, spaced repetition and flashcards live in the <a href="{RELEASES_URL}">desktop app</a>.</p>',
        ]
        for level in cur.levels:
            items = "".join(
                f'<li><a href="{lesson_file(i)}"><span class="id">{i}</span> {esc(cur.lessons[i].title)}</a>'
                f'<span class="minutes">{cur.lessons[i].minutes} min</span></li>'
                for i in level.lesson_ids)
            parts.append(f'<section class="level" id="level-{level.number}"><h2>Level {level.number} · '
                         f"{esc(level.title)}</h2><p>{esc(level.description)}</p><ol>{items}</ol></section>")
        self.page("index.html", "An interactive course in cosmology", "\n".join(parts), section="course")

    def lesson_page(self, lesson: Lesson) -> None:
        cur = self.curriculum
        level = cur.level_of(lesson.id)
        head, section = split_remember(lesson.body)
        md = []
        if lesson.objectives:
            md.append(":::key In this lesson you will learn\n" + "\n".join(f"- {o}" for o in lesson.objectives)
                      + "\n:::\n")
        md.append(head)
        if section:
            md.append("\n:::key Remember this\n" + section + "\n:::\n")
        body = self.markdown("\n".join(md), depth=1)
        prereqs = ", ".join(f'<a href="../{lesson_file(p)}">{p}</a>' for p in lesson.prerequisites
                            if p in cur.lessons)
        sims = ", ".join(f'<a href="../simulators.html#{s}">{esc(self.simulators[s].title)}</a>'
                         for s in lesson.simulators if s in self.simulators)
        meta = [f"≈ {lesson.minutes} min read"]
        if prereqs:
            meta.append(f"Before this: {prereqs}")
        if sims:
            meta.append(f"Simulators: {sims}")
        prev, nxt = cur.previous_lesson(lesson.id), cur.next_lesson(lesson.id)
        pager = '<nav class="pager">'
        pager += (f'<a href="../{lesson_file(prev.id)}">◀ {prev.id} {esc(prev.title)}</a>' if prev else "<span></span>")
        pager += (f'<a href="../{lesson_file(nxt.id)}">{nxt.id} {esc(nxt.title)} ▶</a>' if nxt else "<span></span>")
        pager += "</nav>"
        quiz = self.quiz_html(lesson)
        content = (f'<p class="badge">Level {level.number} · {esc(level.title)}</p>'
                   f"<h1>{lesson.id} {esc(lesson.title)}</h1>"
                   f'<p class="lead">{esc(lesson.summary)}</p><p class="meta">{" · ".join(meta)}</p>'
                   f'<article class="lesson">{body}</article>{quiz}{pager}')
        self.page(lesson_file(lesson.id), f"{lesson.id} {lesson.title}", content, depth=1, section="course")

    def quiz_html(self, lesson: Lesson) -> str:
        if not lesson.quiz:
            return ""
        items = []
        for number, q in enumerate(lesson.quiz, start=1):
            choices = "".join(f'<li><button type="button" data-index="{i}">{esc(choice)}</button></li>'
                              for i, choice in enumerate(q.choices))
            items.append(f'<div class="question" data-answer="{q.answer}"><p><b>{number}.</b> {esc(q.prompt)}</p>'
                         f'<ol type="a">{choices}</ol><p class="explanation" hidden>{esc(q.explanation)}</p></div>')
        return (f'<section class="quiz" data-total="{len(lesson.quiz)}"><h2>Quiz</h2>'
                f"<p>Choose an answer to see whether it is right, and why. Score 70% or more and you know this "
                f'lesson.</p>{"".join(items)}<p class="score" aria-live="polite"></p></section>')

    def glossary_page(self) -> None:
        cur = self.curriculum
        rows = []
        for key, term in sorted(self.glossary.items(), key=lambda kv: kv[1].term.lower()):
            see = ", ".join(f'<a href="#{k}">{esc(self.glossary[k].term)}</a>' for k in term.see_also
                            if k in self.glossary)
            lessons = ", ".join(f'<a href="{lesson_file(i)}">{i} {esc(cur.lessons[i].title)}</a>'
                                for i in term.lessons if i in cur.lessons)
            extra = ""
            if see:
                extra += f'<p class="meta">See also: {see}</p>'
            if lessons:
                extra += f'<p class="meta">Explained in: {lessons}</p>'
            rows.append(f'<dt id="{key}">{esc(term.term)}</dt><dd><p>{esc(term.definition)}</p>{extra}</dd>')
        letters = sorted({t.term[0].upper() for t in self.glossary.values()})
        body = (f"<h1>Glossary</h1><p class=\"lead\">{len(self.glossary)} terms used in the course.</p>"
                f'<p class="letters">{" ".join(letters)}</p><dl class="glossary">{"".join(rows)}</dl>')
        self.page("glossary.html", "Glossary", body, section="glossary")

    def formulas_page(self) -> None:
        groups: dict[str, list] = {}
        for f in self.formulas:
            groups.setdefault(f.group, []).append(f)
        parts = ["<h1>Formula sheet</h1>",
                 f'<p class="lead">{len(self.formulas)} formulas, each with its symbols and the lesson that '
                 "explains it.</p>"]
        for group, items in groups.items():
            parts.append(f"<h2>{esc(group)}</h2>")
            for f in items:
                lesson = self.curriculum.lessons.get(f.lesson or "")
                link = (f' · <a href="{lesson_file(lesson.id)}">{lesson.id} {esc(lesson.title)}</a>'
                        if lesson else "")
                symbols = self.markdown(f.symbols, depth=0)
                parts.append(f'<div class="formula-card" id="{f.id}"><h3>{esc(f.title)}</h3>'
                             f'<p class="display">{self.math(f.formula, 0)}</p>{symbols}'
                             f'<p class="meta">{esc(f.description)}{link}</p></div>')
        self.page("formulas.html", "Formula sheet", "\n".join(parts), section="formulas")

    def problems_page(self) -> None:
        parts = ["<h1>Worked problems</h1>",
                 '<p class="lead">Type a number and press <b>Check</b>. Hints and a worked solution are there '
                 "when you want them.</p>"]
        for problem_set in self.problem_sets:
            parts.append(f'<h2 id="level-{problem_set.level}">Level {problem_set.level} · '
                         f"{esc(problem_set.title)}</h2><p>{esc(problem_set.intro)}</p>")
            for p in problem_set.problems:
                statement = self.markdown(p.statement, depth=0)
                hints = "".join(f"<details><summary>Hint {i}</summary>{self.markdown(h, depth=0)}</details>"
                                for i, h in enumerate(p.hints, start=1))
                solution = self.markdown(p.solution, depth=0)
                unit = f' <span class="unit">{esc(p.unit)}</span>' if p.unit else ""
                lesson = self.curriculum.lessons.get(p.lesson)
                meta = f'<a href="{lesson_file(lesson.id)}">{lesson.id} {esc(lesson.title)}</a>' if lesson else ""
                parts.append(
                    f'<div class="problem" id="{p.id}" data-answer="{p.answer!r}" data-tolerance="{p.tolerance}">'
                    f'<h3>{esc(p.title)} <span class="stars">{"★" * p.difficulty}</span></h3>'
                    f'<p class="meta">{meta}</p>{statement}'
                    f'<p class="answer"><input type="text" inputmode="decimal" aria-label="Your answer">{unit} '
                    f'<button type="button">Check</button> <span class="verdict" aria-live="polite"></span></p>'
                    f"{hints}<details><summary>Solution</summary>{solution}</details></div>")
        self.page("problems.html", "Worked problems", "\n".join(parts), section="problems")

    def simulators_page(self) -> None:
        cur = self.curriculum
        parts = ["<h1>Simulators</h1>",
                 f'<p class="lead">{len(self.simulators)} hands-on tools that go with the lessons. They need the '
                 f'<a href="{RELEASES_URL}">desktop app</a>; here is what each one does and how to use it.</p>']
        for key, info in self.simulators.items():
            how = "".join(f"<li>{text}</li>" for text in info.how_to_use)      # already HTML (<b>…</b>)
            tries = "".join(f"<li>{text}</li>" for text in info.things_to_try)
            lessons = ", ".join(f'<a href="{lesson_file(i)}">{i} {esc(cur.lessons[i].title)}</a>'
                                for i in info.lessons if i in cur.lessons)
            parts.append(f'<section class="sim" id="{key}"><h2>{esc(info.icon)} {esc(info.title)}</h2>'
                         f'<p class="lead">{esc(info.tagline)}</p><p>{esc(info.description)}</p>'
                         f"<h3>How to use it</h3><ul>{how}</ul><h3>Things to try</h3><ul>{tries}</ul>"
                         f'<p class="meta">Used in: {lessons}</p></section>')
        self.page("simulators.html", "Simulators", "\n".join(parts), section="simulators")


def build_site(out: Path) -> SiteReport:
    return SiteBuilder(out).build()


def manifest(report: SiteReport) -> str:
    return json.dumps({"pages": len(report.pages), "images": report.images, "bytes": report.bytes})


SITE_CSS = """
:root { --bg: #f7f8fb; --surface: #ffffff; --text: #1b2233; --muted: #5b6477; --accent: #2f6fdb;
        --border: #d9deea; --good: #1f9d57; --bad: #c9384a; }
* { box-sizing: border-box; }
html { color-scheme: light; }
body { margin: 0; background: var(--bg); color: var(--text); font: 17px/1.6 system-ui, -apple-system,
       "Segoe UI", Roboto, sans-serif; }
a { color: var(--accent); }
header.site { display: flex; flex-wrap: wrap; gap: 8px 20px; align-items: center; padding: 12px 16px;
              background: var(--surface); border-bottom: 1px solid var(--border); position: sticky; top: 0; }
header.site .brand { font-weight: 700; text-decoration: none; color: var(--text); font-size: 1.1em; }
header.site nav { display: flex; flex-wrap: wrap; gap: 4px 16px; }
header.site nav a { text-decoration: none; }
header.site nav a[aria-current] { font-weight: 700; color: var(--text); }
main { max-width: 860px; margin: 0 auto; padding: 16px; }
footer.site { max-width: 860px; margin: 32px auto; padding: 16px; color: var(--muted); font-size: 0.85em;
              border-top: 1px solid var(--border); }
h1 { font-size: 1.9em; line-height: 1.2; margin: 0.6em 0 0.3em; }
h2 { color: var(--accent); margin-top: 1.6em; }
.lead { font-size: 1.1em; }
.meta, .badge { color: var(--muted); font-size: 0.9em; }
.badge { text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0; }
.note { background: var(--surface); border-left: 4px solid var(--accent); padding: 10px 14px; }
img { max-width: 100%; height: auto; }
article.lesson table { border-collapse: collapse; }
article.lesson table.data td, article.lesson table.data th { padding: 6px 8px; }
article.lesson table.data { display: block; max-width: 100%; overflow-x: auto; }
.level ol { padding-left: 0; list-style: none; }
.level li { display: flex; justify-content: space-between; gap: 12px; padding: 4px 0;
            border-bottom: 1px dashed var(--border); }
.level .id { color: var(--muted); font-variant-numeric: tabular-nums; margin-right: 6px; }
.level .minutes { color: var(--muted); white-space: nowrap; font-size: 0.9em; }
.pager { display: flex; justify-content: space-between; gap: 16px; margin: 32px 0; flex-wrap: wrap; }
.quiz, .problem, .formula-card, .sim { background: var(--surface); border: 1px solid var(--border);
       border-radius: 8px; padding: 12px 16px; margin: 16px 0; }
.question { margin: 16px 0; }
.question ol { padding-left: 1.4em; }
.question button { font: inherit; text-align: left; width: 100%; padding: 6px 10px; margin: 3px 0;
                   border: 1px solid var(--border); border-radius: 6px; background: var(--bg); cursor: pointer; }
.question button.right { border-color: var(--good); background: #e5f5ec; }
.question button.wrong { border-color: var(--bad); background: #fbe7ea; }
.explanation { color: var(--muted); }
.score { font-weight: 700; }
.problem input { font: inherit; width: 10em; padding: 4px 8px; }
.problem button { font: inherit; padding: 4px 12px; }
.verdict.right { color: var(--good); font-weight: 700; }
.verdict.wrong { color: var(--bad); font-weight: 700; }
.stars { color: #d9822b; font-size: 0.8em; }
details { margin: 6px 0; }
summary { cursor: pointer; color: var(--accent); }
.formula-card .display { text-align: center; }
dl.glossary dt { font-weight: 700; margin-top: 16px; scroll-margin-top: 70px; }
dl.glossary dd { margin: 0 0 0 1em; }
.letters { letter-spacing: 0.3em; color: var(--muted); }
:target { background: #fff7d6; }
"""

SITE_JS = """
// Quizzes: pick an answer, see whether it is right and why.
document.querySelectorAll('.quiz').forEach(function (quiz) {
  var total = +quiz.dataset.total, answered = 0, correct = 0;
  quiz.querySelectorAll('.question').forEach(function (q) {
    var answer = +q.dataset.answer, buttons = q.querySelectorAll('button');
    buttons.forEach(function (b) {
      b.addEventListener('click', function () {
        if (q.dataset.done) return;
        q.dataset.done = '1';
        var pick = +b.dataset.index;
        buttons[answer].classList.add('right');
        if (pick !== answer) b.classList.add('wrong'); else correct++;
        q.querySelector('.explanation').hidden = false;
        answered++;
        if (answered === total) {
          var score = Math.round(100 * correct / total);
          quiz.querySelector('.score').textContent = 'Score: ' + correct + ' of ' + total + ' (' + score + '%)' +
            (score >= 70 ? ' — you know this lesson.' : ' — read it again and have another go.');
        }
      });
    });
  });
});

// Worked problems: accept 4.25, 4,25, 5.6e11, 5.6×10^11 and 5.6 x 10¹¹.
function parseNumber(text) {
  var sup = {'⁰':'0','¹':'1','²':'2','³':'3','⁴':'4','⁵':'5','⁶':'6','⁷':'7','⁸':'8','⁹':'9','⁻':'-'};
  var t = text.trim().replace(/[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]/g, function (c) { return sup[c]; })
              .replace(/−/g, '-').replace(/\\s+/g, '');
  t = t.replace(/(?:×|x|\\*)10\\^?(-?\\d+)/i, 'e$1');
  if (/^-?\\d{1,3}(,\\d{3})+(\\.\\d+)?$/.test(t)) t = t.replace(/,/g, '');
  else t = t.replace(',', '.');
  return /^-?(\\d+\\.?\\d*|\\.\\d+)(e-?\\d+)?$/i.test(t) ? parseFloat(t) : NaN;
}
document.querySelectorAll('.problem').forEach(function (p) {
  var answer = parseFloat(p.dataset.answer), tol = parseFloat(p.dataset.tolerance);
  var input = p.querySelector('input'), verdict = p.querySelector('.verdict');
  function check() {
    var value = parseNumber(input.value);
    verdict.className = 'verdict';
    if (isNaN(value)) { verdict.textContent = 'Type a number, like 4.25 or 5.6e11.'; return; }
    var ok = Math.abs(value - answer) <= tol * Math.abs(answer);
    verdict.classList.add(ok ? 'right' : 'wrong');
    if (ok) verdict.textContent = 'Correct.';
    else if (value !== 0 && Math.abs(Math.log10(Math.abs(value / answer)) % 1) < 0.02 &&
             Math.abs(Math.log10(Math.abs(value / answer))) > 0.5)
      verdict.textContent = 'Right digits, wrong power of ten.';
    else if (Math.abs(value + answer) <= tol * Math.abs(answer)) verdict.textContent = 'Check the sign.';
    else verdict.textContent = 'Not yet — try a hint.';
  }
  p.querySelector('button').addEventListener('click', check);
  input.addEventListener('keydown', function (e) { if (e.key === 'Enter') check(); });
});
"""
