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
        command = [tool("pyside6-lupdate"), *SOURCES, "-ts", str(target)]
        print(f"$ pyside6-lupdate … -ts {target.name}")
        subprocess.run(command, check=True, cwd=ROOT)
        name_context(target)
        print(f"  {target.relative_to(ROOT)} written ({target.stat().st_size / 1024:.0f} KB)")
    return 0


def name_context(path: Path) -> None:
    """Give the messages the context the app looks them up with.

    Strings are marked with a plain ``tr()`` helper, which lupdate cannot attribute
    to a class, so it leaves the context empty; the app translates them in the
    ``cosmos`` context.
    """
    text = path.read_text(encoding="utf-8")
    if "<name></name>" in text:
        path.write_text(text.replace("<name></name>", f"<name>{CONTEXT}</name>", 1), encoding="utf-8")


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
