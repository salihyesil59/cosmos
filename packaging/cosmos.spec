# PyInstaller specification for the standalone Cosmos executable (E7).
#
# Build with:  python packaging/build_exe.py        (or: pyinstaller packaging/cosmos.spec)
#
# The course content is plain Markdown and YAML, so it is copied into the bundle
# keeping the same relative paths the loaders expect (cosmos/content, cosmos/data).

import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(os.path.abspath(SPECPATH)).parent
ONEFILE = os.environ.get("COSMOS_ONEDIR") != "1"

datas = [
    (str(ROOT / "cosmos" / "content"), "cosmos/content"),
    (str(ROOT / "cosmos" / "data"), "cosmos/data"),
    (str(ROOT / "cosmos" / "gui" / "resources"), "cosmos/gui/resources"),
]

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
    icon=str(ROOT / "cosmos" / "gui" / "resources" / "cosmos.ico"),
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
