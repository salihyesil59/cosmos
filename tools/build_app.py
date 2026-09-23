"""Build a standalone Cosmos for this platform and verify it (E7, E11).

    python tools/build_app.py                  # Windows: dist/Cosmos.exe
                                               # macOS:   dist/Cosmos.app
                                               # Linux:   dist/Cosmos/Cosmos
    python tools/build_app.py --onedir         # Windows: a folder instead (starts faster)
    python tools/build_app.py --package        # also make a zip, dmg-ready folder or AppImage
    python tools/build_app.py --skip-verify    # build only

The build takes a few minutes and needs PyInstaller (``pip install -r
requirements-dev.txt``). After the build the script runs the packaged program with
``--selftest``, which opens every kind of page off-screen and reports whether the
whole course was bundled.

On Linux ``--package`` makes an AppImage if ``appimagetool`` is on the PATH, and a
``.tar.gz`` otherwise; both are self-contained and need nothing installed.
"""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SPEC = ROOT / "tools" / "cosmos.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"

WINDOWS = sys.platform == "win32"
MACOS = sys.platform == "darwin"
LINUX = not WINDOWS and not MACOS

DESKTOP_ENTRY = """\
[Desktop Entry]
Type=Application
Name=Cosmos
GenericName=Cosmology course
Comment=Learn cosmology from the basics to the frontier
Exec=Cosmos
Icon=cosmos
Categories=Education;Science;Astronomy;
Terminal=false
"""


def human(size: int) -> str:
    return f"{size / 1024 / 1024:.0f} MB"


def tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def platform_tag() -> str:
    system = {"win32": "windows", "darwin": "macos"}.get(sys.platform, "linux")
    return f"{system}-{platform.machine().lower()}"


def make_icns() -> Path | None:
    """Build a macOS .icns from the PNG, using the iconutil that ships with macOS."""
    if not MACOS:
        return None
    resources = ROOT / "cosmos" / "gui" / "resources"
    target = resources / "cosmos.icns"
    source = next((resources / name for name in ("cosmos.png", "cosmos-512.png")
                   if (resources / name).exists()), None)
    if target.exists() or source is None or shutil.which("iconutil") is None:
        return target if target.exists() else None
    iconset = BUILD / "cosmos.iconset"
    shutil.rmtree(iconset, ignore_errors=True)
    iconset.mkdir(parents=True)
    for size in (16, 32, 128, 256, 512):
        for scale, suffix in ((1, ""), (2, "@2x")):
            out = iconset / f"icon_{size}x{size}{suffix}.png"
            subprocess.run(["sips", "-z", str(size * scale), str(size * scale), str(source),
                            "--out", str(out)], check=True, capture_output=True)
    subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(target)], check=True)
    print(f"Icon: {target}")
    return target


def build(onedir: bool, clean: bool) -> Path:
    """Run PyInstaller and return the thing you can launch."""
    make_icns()
    env = dict(os.environ, COSMOS_ONEDIR="1" if onedir else "0")
    command = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm",
               "--distpath", str(DIST), "--workpath", str(BUILD)]
    if clean:
        command.append("--clean")
    print("$ " + " ".join(command))
    started = time.time()
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    target = launchable(onedir)
    print(f"\nBuilt {target} in {time.time() - started:.0f} s")
    return target


def launchable(onedir: bool) -> Path:
    """Where the executable ends up on this platform."""
    if MACOS:
        return DIST / "Cosmos.app" / "Contents" / "MacOS" / "Cosmos"
    if WINDOWS:
        return DIST / "Cosmos" / "Cosmos.exe" if onedir else DIST / "Cosmos.exe"
    return DIST / "Cosmos" / "Cosmos"


def payload(onedir: bool) -> Path:
    """The whole thing to hand to somebody: a file, a folder or a bundle."""
    if MACOS:
        return DIST / "Cosmos.app"
    if WINDOWS and not onedir:
        return DIST / "Cosmos.exe"
    return DIST / "Cosmos"


def package(onedir: bool) -> Path:
    """Make one file somebody can download."""
    from cosmos import __version__

    name = f"Cosmos-{__version__}-{platform_tag()}"
    source = payload(onedir)
    if LINUX:
        return _appimage_or_tarball(source, name)
    if MACOS or source.is_dir():
        return Path(shutil.make_archive(str(DIST / name), "zip",
                                        root_dir=source.parent, base_dir=source.name))
    staging = BUILD / name
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copy2(source, staging / source.name)
    return Path(shutil.make_archive(str(DIST / name), "zip",
                                    root_dir=staging.parent, base_dir=staging.name))


def _appimage_or_tarball(source: Path, name: str) -> Path:
    """An AppImage when appimagetool is available, otherwise a plain tarball."""
    tool = shutil.which("appimagetool") or shutil.which("appimagetool-x86_64.AppImage")
    if tool is None:
        archive = DIST / f"{name}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(source, arcname="Cosmos")
        print("appimagetool was not found, so this is a tarball. Unpack it and run ./Cosmos/Cosmos.")
        return archive

    appdir = BUILD / "Cosmos.AppDir"
    shutil.rmtree(appdir, ignore_errors=True)
    shutil.copytree(source, appdir / "usr" / "bin")
    (appdir / "cosmos.desktop").write_text(DESKTOP_ENTRY, encoding="utf-8")
    icon = ROOT / "cosmos" / "gui" / "resources" / "cosmos.png"
    if icon.exists():
        shutil.copy2(icon, appdir / "cosmos.png")
    run_script = appdir / "AppRun"
    run_script.write_text('#!/bin/sh\nexec "$(dirname "$0")/usr/bin/Cosmos" "$@"\n', encoding="utf-8")
    run_script.chmod(0o755)
    target = DIST / f"{name}.AppImage"
    subprocess.run([tool, str(appdir), str(target)], check=True,
                   env=dict(os.environ, ARCH=platform.machine()))
    return target


def verify(executable: Path, timeout: float = 420.0) -> int:
    report = BUILD / "selftest.txt"
    report.unlink(missing_ok=True)
    print(f"\nVerifying {executable.name} …")
    started = time.time()
    try:
        # A crash inside a packaged windowed app opens a message box, which would wait for ever.
        result = subprocess.run([str(executable), "--selftest", str(report)], cwd=ROOT, timeout=timeout)
    except subprocess.TimeoutExpired:
        print(f"The packaged program did not finish within {timeout:.0f} s. "
              "Start it by hand to see the error it is showing.")
        return 3
    elapsed = time.time() - started
    if report.exists():
        print(report.read_text(encoding="utf-8").strip())
    print(f"exit code {result.returncode} after {elapsed:.1f} s")
    return result.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--onedir", action="store_true",
                        help="Windows: build a folder instead of a single file (starts faster)")
    parser.add_argument("--clean", action="store_true", help="discard PyInstaller's caches first")
    parser.add_argument("--skip-verify", action="store_true", help="do not run the packaged self-test")
    parser.add_argument("--package", "--zip", dest="package", action="store_true",
                        help="also produce the file to hand out (zip, or AppImage on Linux)")
    args = parser.parse_args(argv)

    if shutil.which("pyinstaller") is None:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print("PyInstaller is not installed. Run: pip install -r requirements-dev.txt")
            return 2

    onedir = args.onedir or not WINDOWS
    executable = build(onedir, args.clean)
    print(f"Size: {human(tree_size(payload(onedir)))}")
    if args.package:
        archive = package(onedir)
        print(f"Package: {archive} ({human(archive.stat().st_size)})")
    if args.skip_verify:
        return 0
    return verify(executable)


if __name__ == "__main__":
    raise SystemExit(main())
