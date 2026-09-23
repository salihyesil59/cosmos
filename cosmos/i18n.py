"""Translation infrastructure (E8).

The course itself — lessons, quizzes, the glossary — is written in English and
stays that way. What can be translated is the *interface*: menus, buttons, page
headings and the short texts around the content.

Strings are marked with :func:`tr`, which is Qt's translation call with a fixed
context, so the standard Qt tools work:

    python tools/update_translations.py --language de      # create/refresh a .ts
    (translate cosmos/i18n/cosmos_de.ts in Qt Linguist)
    python tools/update_translations.py --release          # compile the .qm files

A compiled ``cosmos_<code>.qm`` in ``cosmos/i18n`` makes that language appear in
**View → Language**. Nothing is bundled by default: without a .qm the app is
English, exactly as before.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QLocale, QTranslator

CONTEXT = "cosmos"
TRANSLATIONS_DIR = Path(__file__).resolve().parent / "i18n"
SOURCE_LANGUAGE = "en"

# Languages the interface knows how to name. Any other .qm still works; it is listed by its code.
LANGUAGE_NAMES = {
    "en": "English",
    "tr": "Türkçe",
    "de": "Deutsch",
    "es": "Español",
    "fr": "Français",
    "it": "Italiano",
    "pt": "Português",
    "ru": "Русский",
    "zh": "中文",
    "ja": "日本語",
    "ar": "العربية",
}

_installed: list[QTranslator] = []


def tr_noop(text: str) -> str:
    """Mark a string for the translation tools without translating it yet.

    Use it where the text is defined (a table of badges, say) and call :func:`tr`
    on it where it is shown, so the language can change without a restart.
    """
    return text


def tr(text: str, disambiguation: str | None = None) -> str:
    """Mark a user-visible string for translation and return it in the active language."""
    return QCoreApplication.translate(CONTEXT, text, disambiguation)


@dataclass(frozen=True)
class Language:
    code: str
    name: str
    path: Path | None = None       # None for the built-in English source language

    @property
    def label(self) -> str:
        return f"{self.name} ({self.code})"


def language_name(code: str) -> str:
    return LANGUAGE_NAMES.get(code, QLocale(code).nativeLanguageName() or code)


def available_languages() -> list[Language]:
    """English plus every compiled translation found next to the app."""
    languages = [Language(SOURCE_LANGUAGE, language_name(SOURCE_LANGUAGE))]
    for path in sorted(TRANSLATIONS_DIR.glob("cosmos_*.qm")):
        code = path.stem.split("_", 1)[1]
        if code != SOURCE_LANGUAGE:
            languages.append(Language(code, language_name(code), path))
    return languages


def find(code: str) -> Language | None:
    return next((lang for lang in available_languages() if lang.code == code), None)


def install(app: QCoreApplication, code: str) -> bool:
    """Switch the interface to ``code``; returns True if a translation was loaded.

    English (or an unknown code) simply removes any translation that was active.
    """
    global _installed
    for translator in _installed:
        app.removeTranslator(translator)
    _installed = []

    language = find(code)
    if language is None or language.path is None:
        return False

    loaded = []
    translator = QTranslator(app)
    if translator.load(str(language.path)):
        app.installTranslator(translator)
        loaded.append(translator)
    # Qt's own strings (dialog buttons, file chooser) when they are available.
    qt_translator = QTranslator(app)
    qt_path = QLibraryInfo.path(QLibraryInfo.TranslationsPath)
    if qt_translator.load(QLocale(code), "qtbase", "_", qt_path):
        app.installTranslator(qt_translator)
        loaded.append(qt_translator)
    _installed = loaded
    return bool(loaded)


def system_language() -> str:
    """The code of the system language if the app has a translation for it, else English."""
    code = QLocale.system().name().split("_")[0]
    return code if find(code) else SOURCE_LANGUAGE
