"""Create, refresh and compile interface translations (E8).

    python tools/update_translations.py --language de     # start or refresh German
    python tools/update_translations.py                   # refresh every existing .ts
    python tools/update_translations.py --release         # compile .ts -> .qm

Translate the generated ``cosmos/i18n/cosmos_<code>.ts`` with Qt Linguist
(``pyside6-linguist``), then run ``--release``. A compiled .qm makes the language
appear in **View → Language**; the course content itself stays in English.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "cosmos").rglob("*.py")
                 if "__pycache__" not in p.parts)
TS_DIR = ROOT / "cosmos" / "i18n"
CONTEXT = "cosmos"          # must match cosmos.i18n.CONTEXT


def tool(name: str) -> str:
    """The PySide6 command line tool, from this interpreter's environment."""
    candidate = Path(sys.executable).parent / name
    for suffix in ("", ".exe"):
        if (path := candidate.with_name(name + suffix)).exists():
            return str(path)
    return name          # fall back to PATH


def update(language: str | None) -> int:
    TS_DIR.mkdir(parents=True, exist_ok=True)
    targets = [TS_DIR / f"cosmos_{language}.ts"] if language else sorted(TS_DIR.glob("cosmos_*.ts"))
    if not targets:
        print("No .ts files yet. Start one with --language <code>, for example --language de.")
        return 1
    for target in targets:
        # lupdate cannot see the context our tr() uses, so every old entry looks obsolete to it.
        # Remember what was already translated and put it back afterwards.
        previous = existing_translations(target)
        # tr_noop() marks strings far from where they are shown; teach lupdate to read it too.
        command = [tool("pyside6-lupdate"), "-tr-function-alias", "QT_TR_NOOP+=tr_noop,QT_TR_NOOP+=_",
                   *SOURCES, "-ts", str(target)]
        print(f"$ pyside6-lupdate … -ts {target.name}")
        subprocess.run(command, check=True, cwd=ROOT)
        name_context(target)
        restored, missing = carry_over(target, previous)
        print(f"  {target.relative_to(ROOT)} written ({target.stat().st_size / 1024:.0f} KB)")
        print(f"  {restored} translation(s) kept, {missing} still to translate")
    return 0


def existing_translations(path: Path) -> dict[str, str]:
    """Source string -> translation for everything already translated in ``path``."""
    import xml.etree.ElementTree as ET

    if not path.exists():
        return {}
    root = ET.parse(path).getroot()
    done = {}
    for message in root.iter("message"):
        translation = message.find("translation")
        source = message.find("source")
        if source is None or translation is None or not (translation.text or "").strip():
            continue
        # Text is what matters: lupdate marks carried-over entries "unfinished" too.
        done[source.text] = translation.text
    return done


def carry_over(path: Path, previous: dict[str, str]) -> tuple[int, int]:
    """Fill the refreshed file with the translations it had before; drop stale entries."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)
    root = tree.getroot()
    restored = missing = 0
    for context in root.findall("context"):
        for message in list(context.findall("message")):
            translation = message.find("translation")
            source = message.find("source")
            if translation is None or source is None:
                continue
            if translation.get("type") in ("obsolete", "vanished"):
                context.remove(message)          # the string is gone from the code
                continue
            known = previous.get(source.text)
            current = (translation.text or "").strip()
            if known and current in ("", known.strip()):
                # lupdate copies the old text across but still calls the entry unfinished.
                translation.text = known
                translation.attrib.pop("type", None)
                restored += 1
            elif translation.get("type") == "unfinished":
                missing += 1
    tree.write(path, encoding="utf-8", xml_declaration=True)
    text = path.read_text(encoding="utf-8")
    if "<!DOCTYPE TS>" not in text:
        path.write_text(text.replace("<TS ", "<!DOCTYPE TS><TS ", 1), encoding="utf-8")
    return restored, missing


def name_context(path: Path) -> None:
    """Give the messages the context the app looks them up with.

    Strings are marked with a plain ``tr()`` helper, which lupdate cannot attribute
    to a class, so it leaves the context empty; the app translates them in the
    ``cosmos`` context.
    """
    text = path.read_text(encoding="utf-8").replace("<name></name>", f"<name>{CONTEXT}</name>")
    path.write_text(text, encoding="utf-8")
    merge_contexts(path)


def merge_contexts(path: Path) -> None:
    """Fold the contexts lupdate created into one, keeping the first translation of each string."""
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)
    root = tree.getroot()
    contexts = [c for c in root.findall("context") if (c.find("name").text or "") == CONTEXT]
    if len(contexts) < 2:
        return
    keeper, *rest = contexts
    seen = {m.find("source").text for m in keeper.findall("message")}
    for extra in rest:
        for message in extra.findall("message"):
            source = message.find("source").text
            if source not in seen:
                keeper.append(message)
                seen.add(source)
        root.remove(extra)
    tree.write(path, encoding="utf-8", xml_declaration=True)
    text = path.read_text(encoding="utf-8")
    if "<!DOCTYPE TS>" not in text:
        path.write_text(text.replace("<TS ", "<!DOCTYPE TS><TS ", 1), encoding="utf-8")


def release() -> int:
    files = sorted(TS_DIR.glob("cosmos_*.ts"))
    if not files:
        print("Nothing to compile: no .ts files in cosmos/i18n.")
        return 1
    for source in files:
        target = source.with_suffix(".qm")
        subprocess.run([tool("pyside6-lrelease"), str(source), "-qm", str(target)], check=True, cwd=ROOT)
        print(f"{source.name} -> {target.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", help="language code to create or refresh, e.g. de, tr, es")
    parser.add_argument("--release", action="store_true", help="compile the .ts files into .qm")
    args = parser.parse_args(argv)
    if args.release:
        return release()
    return update(args.language)


if __name__ == "__main__":
    raise SystemExit(main())
