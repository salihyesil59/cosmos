"""The standalone build (E7): the self-test, the icon and the PyInstaller spec."""

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "tools" / "cosmos.spec"
ICON = ROOT / "cosmos" / "gui" / "resources" / "cosmos.ico"


def test_selftest_passes(tmp_path, monkeypatch):
    """``Cosmos.exe --selftest`` is what verifies a packaged build, so it must pass here."""
    monkeypatch.setenv("COSMOS_DATA_DIR", str(tmp_path))
    from cosmos.app import selftest

    report = tmp_path / "report.txt"
    assert selftest(str(report)) == 0
    text = report.read_text(encoding="utf-8")
    assert "RESULT: ok" in text
    assert "lessons: 43" in text and "simulators: 18" in text


def test_version_and_selftest_flags(tmp_path, monkeypatch):
    monkeypatch.setenv("COSMOS_DATA_DIR", str(tmp_path))
    from cosmos import APP_NAME, __version__
    from cosmos.app import run

    assert run(["cosmos", "--version"]) == 0
    assert APP_NAME and re.match(r"\d+\.\d+", __version__)
    assert run(["cosmos", "--selftest", str(tmp_path / "r.txt")]) == 0


def test_icon_is_a_multi_size_ico():
    assert ICON.exists(), "run python tools/make_icon.py"
    header = ICON.read_bytes()[:6]
    assert header[:4] == b"\x00\x00\x01\x00"          # ICONDIR for an .ico file
    images = int.from_bytes(header[4:6], "little")
    assert images >= 5, "the icon should carry several sizes for Windows"

    from cosmos.gui.icons import app_icon

    icon = app_icon()
    assert not icon.isNull() and icon.availableSizes()


def test_spec_bundles_all_content():
    assert SPEC.exists()
    spec = SPEC.read_text(encoding="utf-8")
    for folder in ("cosmos/content", "cosmos/data", "cosmos/gui/resources"):
        quoted = folder.replace("/", '" / "')
        assert quoted in spec or folder in spec, f"{folder} is not bundled by the spec"
    assert 'collect_submodules("cosmos")' in spec       # simulators are imported by name
    assert '"astropy"' in spec and '"pytest"' in spec   # test-only dependencies stay out


@pytest.mark.parametrize("name", ["build_exe.py", "make_icon.py", "cosmos.spec"])
def test_packaging_files_exist(name):
    assert (ROOT / "tools" / name).exists()
