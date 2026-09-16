"""Build the standalone Cosmos executable and verify it (E7).

    python tools/build_exe.py                 # one file: dist/Cosmos.exe
    python tools/build_exe.py --onedir        # a folder: dist/Cosmos/Cosmos.exe (starts faster)
    python tools/build_exe.py --skip-verify   # build only

The build takes a few minutes and needs PyInstaller (``pip install -r
requirements-dev.txt``). After the build the script runs the packaged program
with ``--selftest``, which opens every kind of page off-screen and reports
whether the whole course was bundled.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
SPEC = ROOT / "tools" / "cosmos.spec"
DIST = ROOT / "dist"
BUILD = ROOT / "build"


def human(size: int) -> str:
    return f"{size / 1024 / 1024:.0f} MB"


def tree_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def build(onedir: bool, clean: bool) -> Path:
    env = dict(os.environ, COSMOS_ONEDIR="1" if onedir else "0")
    command = [sys.executable, "-m", "PyInstaller", str(SPEC), "--noconfirm",
               "--distpath", str(DIST), "--workpath", str(BUILD)]
    if clean:
        command.append("--clean")
    print("$ " + " ".join(command))
    started = time.time()
    subprocess.run(command, check=True, cwd=ROOT, env=env)
    target = DIST / ("Cosmos" if onedir else "Cosmos.exe")
    if onedir:
        target = target / "Cosmos.exe"
    print(f"\nBuilt {target} in {time.time() - started:.0f} s")
    return target


def pack(payload: Path) -> Path:
    """Zip the build so it can be handed to someone else."""
    from cosmos import __version__

    name = f"Cosmos-{__version__}-windows"
    if payload.is_dir():
        return Path(shutil.make_archive(str(DIST / name), "zip", root_dir=payload.parent, base_dir=payload.name))
    staging = BUILD / name
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir(parents=True)
    shutil.copy2(payload, staging / payload.name)
    return Path(shutil.make_archive(str(DIST / name), "zip", root_dir=staging.parent, base_dir=staging.name))


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
                        help="build a folder instead of a single file (starts much faster)")
    parser.add_argument("--clean", action="store_true", help="discard PyInstaller's caches first")
    parser.add_argument("--skip-verify", action="store_true", help="do not run the packaged self-test")
    parser.add_argument("--zip", action="store_true", help="also pack the result into a zip archive")
    args = parser.parse_args(argv)

    if shutil.which("pyinstaller") is None:
        try:
            import PyInstaller  # noqa: F401
        except ImportError:
            print("PyInstaller is not installed. Run: pip install -r requirements-dev.txt")
            return 2

    executable = build(args.onedir, args.clean)
    payload = executable.parent if args.onedir else executable
    print(f"Size: {human(tree_size(payload))}")
    if args.zip:
        archive = pack(payload)
        print(f"Archive: {archive} ({human(archive.stat().st_size)})")
    if args.skip_verify:
        return 0
    return verify(executable)


if __name__ == "__main__":
    raise SystemExit(main())
