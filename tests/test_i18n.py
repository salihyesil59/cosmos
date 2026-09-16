"""Interface translations (E8): the marking, the pipeline and the fallback to English."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from cosmos import i18n  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

TS_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS><TS version="2.1" language="{code}">
<context>
    <name>cosmos</name>
    <message>
        <source>Home</source>
        <translation>{home}</translation>
    </message>
</context>
</TS>
"""


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def lrelease() -> str | None:
    candidate = Path(sys.executable).parent / "pyside6-lrelease.exe"
    if candidate.exists():
        return str(candidate)
    return shutil.which("pyside6-lrelease")


def test_english_is_always_available(app):
    languages = i18n.available_languages()
    assert languages[0].code == "en" and languages[0].path is None
    assert i18n.find("en") is not None
    assert i18n.find("does-not-exist") is None
    assert i18n.install(app, "en") is False          # English needs no translation file
    assert i18n.tr("Home") == "Home"
    assert i18n.system_language() in {lang.code for lang in languages}


def test_language_names():
    assert i18n.language_name("tr") == "Türkçe"
    assert i18n.language_name("en") == "English"
    assert i18n.language_name("zz")                  # unknown codes still get a label


def test_a_compiled_translation_is_picked_up(app, tmp_path, monkeypatch):
    """The whole pipeline: a .ts, compiled to .qm, installed, and used by tr()."""
    tool = lrelease()
    if tool is None:
        pytest.skip("pyside6-lrelease is not available")
    source = tmp_path / "cosmos_zz.ts"
    source.write_text(TS_TEMPLATE.format(code="zz", home="Evim"), encoding="utf-8")
    subprocess.run([tool, str(source), "-qm", str(tmp_path / "cosmos_zz.qm")], check=True,
                   capture_output=True)
    monkeypatch.setattr(i18n, "TRANSLATIONS_DIR", tmp_path)

    assert [lang.code for lang in i18n.available_languages()] == ["en", "zz"]
    try:
        assert i18n.install(app, "zz") is True
        assert i18n.tr("Home") == "Evim"
        assert i18n.tr("Glossary") == "Glossary"     # untranslated strings stay English
    finally:
        i18n.install(app, "en")
    assert i18n.tr("Home") == "Home"


def test_the_interface_is_marked_for_translation():
    """The chrome must keep going through tr(); otherwise a translation is useless."""
    source = (ROOT / "cosmos" / "gui" / "main_window.py").read_text(encoding="utf-8")
    assert "from cosmos.i18n import tr" in source
    assert source.count("tr(") > 30
    for label in ('tr("Home")', 'tr("Glossary")', 'tr("Language")'):
        assert label in source


def test_update_script_names_the_context(tmp_path):
    from tools.update_translations import CONTEXT, name_context

    path = tmp_path / "cosmos_de.ts"
    path.write_text("<TS><context>\n    <name></name>\n</context></TS>", encoding="utf-8")
    name_context(path)
    assert f"<name>{CONTEXT}</name>" in path.read_text(encoding="utf-8")
    assert CONTEXT == i18n.CONTEXT


def test_language_setting_survives_a_restart(tmp_path):
    from cosmos.progress import ProgressStore

    store = ProgressStore(tmp_path / "p.json")
    assert store.data.language == ""                 # follow the system by default
    store.data.language = "de"
    store.save()
    assert ProgressStore(tmp_path / "p.json").data.language == "de"


def test_turkish_pack_is_complete(app, monkeypatch):
    """The bundled Turkish interface: every marked string is translated and loads."""
    import re

    ts = (ROOT / "cosmos" / "i18n" / "cosmos_tr.ts").read_text(encoding="utf-8")
    assert 'type="unfinished"' not in ts, "some Turkish strings are still untranslated"
    assert ts.count("<message>") > 200
    assert len(re.findall(r"<name>cosmos</name>", ts)) == 1, "the .ts should hold a single context"

    assert (ROOT / "cosmos" / "i18n" / "cosmos_tr.qm").exists()
    assert i18n.find("tr") is not None and i18n.language_name("tr") == "Türkçe"
    try:
        assert i18n.install(app, "tr") is True
        assert i18n.tr("Home") == "Ana sayfa"
        assert i18n.tr("Glossary") == "Sözlük"
        assert i18n.tr("First steps") == "İlk adımlar"              # badge, marked with tr_noop
        assert i18n.tr("{done} of {total} lessons completed").format(done=2, total=43) == \
            "43 dersin 2 tanesi tamamlandı"
    finally:
        i18n.install(app, "en")
    assert i18n.tr("Home") == "Home"


def test_placeholders_survive_translation():
    """A translation that loses a {placeholder} would raise at runtime."""
    import re
    import xml.etree.ElementTree as ET

    root = ET.parse(ROOT / "cosmos" / "i18n" / "cosmos_tr.ts").getroot()
    for message in root.iter("message"):
        source = message.find("source").text or ""
        translation = message.find("translation").text or ""
        assert set(re.findall(r"\{(\w+)\}", source)) == set(re.findall(r"\{(\w+)\}", translation)), source


def test_the_guide_panels_and_the_tour_are_marked():
    """G14: the Guide texts, the tour steps and the simulator guidance all go through tr()."""
    pages = ["glossary.py", "history_page.py", "home.py", "notes_page.py", "progress_page.py",
             "reference.py", "search_page.py", "simulators.py"]
    for name in pages:
        source = (ROOT / "cosmos" / "gui" / "pages" / name).read_text(encoding="utf-8")
        assert "tr_noop(" in source, f"{name} defines its guide text without tr_noop()"
        assert "return tr(" in source, f"{name} shows its guide text without tr()"

    main_window = (ROOT / "cosmos" / "gui" / "main_window.py").read_text(encoding="utf-8")
    assert main_window.count("TourStep(") == main_window.count("TourStep(\n                tr(")

    registry = (ROOT / "cosmos" / "gui" / "simulators" / "registry.py").read_text(encoding="utf-8")
    assert registry.count("tr_noop(") > 150, "the simulator guidance is not marked"
    assert 'title="' not in registry and 'tagline="' not in registry


def test_every_simulator_marks_its_controls():
    directory = ROOT / "cosmos" / "gui" / "simulators"
    for path in directory.glob("*.py"):
        if path.name in {"__init__.py", "base.py", "registry.py"}:
            continue
        source = path.read_text(encoding="utf-8")
        assert "from cosmos.i18n import tr" in source, f"{path.name} does not import tr"
        assert source.count("tr(") >= 8, f"{path.name} marks very few strings"


def test_turkish_reaches_the_simulators(app):
    from cosmos.gui.simulators.registry import SIMULATORS

    info = SIMULATORS["S2"]
    try:
        assert i18n.install(app, "tr") is True
        assert i18n.tr(info.title) == "Genişleme Tarihi Gezgini"
        assert i18n.tr(info.tagline).startswith("Madde ve karanlık enerji")
        assert "Ωm" in i18n.tr(info.how_to_use[0])
        assert i18n.tr("How to use") == "Nasıl kullanılır"
        assert i18n.tr("Things to try") == "Denenecek şeyler"
        assert i18n.tr("Save image…") == "Görüntüyü kaydet…"      # the plot toolbar
        assert i18n.tr("Universe contents") == "Evrenin içeriği"  # a control group box
        assert i18n.tr("Welcome to Cosmos!") == "Cosmos'a hoş geldiniz!"   # the tour
    finally:
        i18n.install(app, "en")
    assert i18n.tr(info.title) == "Expansion History Explorer"


def test_refreshing_the_ts_keeps_the_translations(tmp_path):
    """A refresh must not throw away work: lupdate cannot see our context."""
    from tools.update_translations import carry_over, existing_translations

    path = tmp_path / "cosmos_zz.ts"
    path.write_text(TS_TEMPLATE.format(code="zz", home="Evim"), encoding="utf-8")
    previous = existing_translations(path)
    assert previous == {"Home": "Evim"}

    refreshed = TS_TEMPLATE.format(code="zz", home="").replace(
        "<translation>", '<translation type="unfinished">')
    path.write_text(refreshed, encoding="utf-8")
    restored, missing = carry_over(path, previous)
    assert (restored, missing) == (1, 0)
    assert "Evim" in path.read_text(encoding="utf-8")
    assert 'type="unfinished"' not in path.read_text(encoding="utf-8")


def test_the_labels_table_covers_the_physics_layer():
    """G20: every string the physics layer can hand to the interface must be marked."""
    from cosmos.gui import labels
    from cosmos.physics.cosmology import _FATE_EXPLANATIONS, Cosmology, Fate
    from cosmos.physics.timeline import format_time
    from cosmos.progress import LessonStatus

    assert {f.value for f in Fate} <= set(labels.FATES)
    assert set(_FATE_EXPLANATIONS.values()) <= set(labels.FATE_EXPLANATIONS)
    assert {s.value for s in LessonStatus} <= set(labels.LESSON_STATUS)
    geometries = {Cosmology(H0=70, Om0=om, Ode0=ol).geometry
                  for om, ol in ((0.3, 0.7), (0.3, 0.2), (0.6, 0.8))}
    assert geometries <= set(labels.GEOMETRIES)

    seen = set()
    format_time(1e-20, unit=lambda word: seen.add(word) or word)
    for seconds in (1.0, 300.0, 1e5, 1e7, 1e9, 1e14, 1e18):
        format_time(seconds, unit=lambda word: seen.add(word) or word)
    assert seen <= set(labels.TIME_UNITS), seen - set(labels.TIME_UNITS)


def test_the_simulators_report_back_in_turkish(app):
    """The numbers a simulator writes out are translated, not only its controls."""
    try:
        assert i18n.install(app, "tr") is True
        assert i18n.tr("Age: <b>{age}</b>{crunch}<br>"
                       "Geometry: <b>{geometry}</b> (Ωk = {curvature})<br>"
                       "Today: <b>{trend}</b> (q0 = {q0})<br>"
                       "Hubble time 1/H0: {hubble} billion years<br><br>"
                       "<span style='color:{colour}'><b>Fate: this universe {fate}.</b></span><br>"
                       "{explanation}").startswith("Yaş:")
        assert i18n.tr("accelerating") == "hızlanıyor"
        assert i18n.tr("flat") == "düz"                      # from the physics layer
        assert i18n.tr("billion years") == "milyar yıl"
        assert i18n.tr("Question {number} of {total}").format(number=1, total=5) == "Soru 1 / 5"
        assert i18n.tr("<b>Solved.</b>") == "<b>Çözüldü.</b>"
    finally:
        i18n.install(app, "en")
    assert i18n.tr("flat") == "flat"
