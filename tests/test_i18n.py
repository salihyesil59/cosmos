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
