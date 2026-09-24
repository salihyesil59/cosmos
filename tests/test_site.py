"""E19: the course as a static website — complete, self-contained and linked up."""

import os
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("MPLBACKEND", "Agg")

from PySide6.QtGui import QGuiApplication  # noqa: E402

from cosmos.content.loader import load_curriculum, load_glossary, load_problems  # noqa: E402


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.ids, self.images = [], set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "a" and "href" in a:
            self.links.append(a["href"])
        if tag in ("img", "script", "link") and ("src" in a or "href" in a):
            self.images.append(a.get("src") or a.get("href"))


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    QGuiApplication.instance() or QGuiApplication([])
    from cosmos.gui.rendering.site import build_site

    out = tmp_path_factory.mktemp("site") / "cosmos-website"
    report = build_site(out)
    pages = {}
    for path in out.rglob("*.html"):
        parser = Page()
        parser.feed(path.read_text(encoding="utf-8"))
        pages[path.resolve()] = parser
    return out, report, pages


def test_every_page_is_there(site):
    out, report, _pages = site
    curriculum = load_curriculum()
    for name in ("index.html", "glossary.html", "formulas.html", "problems.html", "simulators.html",
                 "assets/site.css", "assets/site.js"):
        assert (out / name).exists(), name
    lessons = sorted(p.name for p in (out / "lessons").glob("*.html"))
    assert len(lessons) == len(curriculum.lessons)
    assert len(report.pages) == len(curriculum.lessons) + 5
    assert report.images > 100


def test_every_link_and_image_resolves(site):
    _out, _report, pages = site
    for path, page in pages.items():
        for target in page.links + page.images:
            if target.startswith("http"):
                continue
            assert not re.match(r"^\w+:", target), f"{path.name}: app link {target} left in the site"
            file_part, _, fragment = target.partition("#")
            resolved = (path.parent / file_part).resolve() if file_part else path
            assert resolved.exists(), f"{path.name}: broken link {target}"
            if fragment and resolved.suffix == ".html":
                assert fragment in pages[resolved].ids, f"{path.name}: no anchor {target}"


def test_nothing_is_fetched_from_the_internet(site):
    out, _report, _pages = site
    for path in out.rglob("*.html"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r'(src|href)="(https?:)?//(?!github\.com/salihyesil59)', text), path.name
        assert "CSMTOKEN" not in text and "$$" not in text and ":::" not in text, path.name


def test_quizzes_problems_and_glossary_are_complete(site):
    out, _report, pages = site
    curriculum = load_curriculum()
    lesson = curriculum.lessons["L6.10"]
    text = (out / "lessons" / "L6_10.html").read_text(encoding="utf-8")
    assert text.count('class="question"') == len(lesson.quiz)
    assert "Remember this" in text and "Open The Far Future" in text
    problems = (out / "problems.html").read_text(encoding="utf-8")
    assert problems.count('class="problem"') == sum(len(s.problems) for s in load_problems())
    glossary_ids = pages[(out / "glossary.html").resolve()].ids
    assert set(load_glossary()) <= glossary_ids


def test_a_folder_of_someone_elses_files_is_never_replaced(tmp_path):
    QGuiApplication.instance() or QGuiApplication([])
    from cosmos.gui.rendering.site import build_site

    precious = tmp_path / "homework"
    precious.mkdir()
    (precious / "essay.txt").write_text("mine", encoding="utf-8")
    with pytest.raises(FileExistsError):
        build_site(precious)
    assert (precious / "essay.txt").read_text(encoding="utf-8") == "mine"


def test_the_command_line_tool(tmp_path, monkeypatch):
    import tools.build_site as tool

    calls = []
    monkeypatch.setattr("cosmos.gui.rendering.site.build_site",
                        lambda out: calls.append(out) or type("R", (), {"pages": [], "images": 0, "bytes": 0})())
    assert tool.main(["--out", str(tmp_path / "x")]) == 0
    assert calls == [Path(tmp_path / "x")]
