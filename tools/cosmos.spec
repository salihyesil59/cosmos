# PyInstaller specification for the standalone Cosmos build (E7, E11).
#
# Build with:  python tools/build_app.py        (or: pyinstaller tools/cosmos.spec)
#
# One spec covers all three platforms:
#   Windows   dist/Cosmos.exe            one file, or dist/Cosmos/ with COSMOS_ONEDIR=1
#   macOS     dist/Cosmos.app            an application bundle
#   Linux     dist/Cosmos/Cosmos         a folder, packed into an AppImage or a tarball
#
# The course content is plain Markdown and YAML, so it is copied into the bundle
# keeping the same relative paths the loaders expect (cosmos/content, cosmos/data).

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.path.abspath(SPECPATH)).parent
WINDOWS, MACOS = sys.platform == "win32", sys.platform == "darwin"
# macOS always wants a bundle directory, and a one-file Linux build cannot become an
# AppImage, so one-file is a Windows convenience only.
ONEFILE = WINDOWS and os.environ.get("COSMOS_ONEDIR") != "1"

RESOURCES = ROOT / "cosmos" / "gui" / "resources"
datas = [
    (str(ROOT / "cosmos" / "content"), "cosmos/content"),
    (str(ROOT / "cosmos" / "data"), "cosmos/data"),
    (str(RESOURCES), "cosmos/gui/resources"),
]
translations = ROOT / "cosmos" / "i18n"
if any(translations.glob("*.qm")):          # interface translations, when some have been compiled
    datas.append((str(translations), "cosmos/i18n"))


def _icon():
    """The icon PyInstaller wants on this platform, or None if we have none for it."""
    if WINDOWS:
        return str(RESOURCES / "cosmos.ico")
    if MACOS:
        icns = RESOURCES / "cosmos.icns"
        return str(icns) if icns.exists() else None
    return None                              # Linux takes its icon from the .desktop file


# Everything the app never imports: test tools, notebook machinery and other GUI toolkits.
excludes = [
    "astropy", "pytest", "_pytest", "pyinstaller", "PyInstaller",
    "tkinter", "PyQt5", "PyQt6", "PySide2", "wx",
    "IPython", "jupyter", "notebook", "nbformat", "pandas", "sphinx",
    "matplotlib.backends._backend_tk", "matplotlib.backends.backend_webagg",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.Qt3DCore",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtMultimedia", "PySide6.QtCharts",
    "PySide6.QtDataVisualization", "PySide6.QtNetworkAuth", "PySide6.QtSql",
    "PySide6.QtTest", "PySide6.QtBluetooth", "PySide6.QtPositioning",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    # Simulators and lesson figures are imported by name at run time, so collect the whole package.
    hiddenimports=collect_submodules("cosmos"),
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe_kwargs = dict(
    name="Cosmos",
    icon=_icon(),
    console=False,              # a windowed app; --selftest still sets the exit code
    disable_windowed_traceback=False,
    upx=False,
    bootloader_ignore_signals=False,
    strip=False,
)

if ONEFILE:
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], runtime_tmpdir=None, **exe_kwargs)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **exe_kwargs)
    coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="Cosmos")
    if MACOS:
        from cosmos import __version__

        app = BUNDLE(
            coll,
            name="Cosmos.app",
            icon=_icon(),
            bundle_identifier="io.github.salihyesil59.cosmos",
            version=__version__,
            info_plist={
                "CFBundleDisplayName": "Cosmos",
                "CFBundleShortVersionString": __version__,
                "NSHighResolutionCapable": True,
                # Nothing in the app reads documents, takes photographs or knows where it is.
                "LSApplicationCategoryType": "public.app-category.education",
            },
        )
