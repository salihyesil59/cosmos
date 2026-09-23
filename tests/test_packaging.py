"""The standalone build (E7, E11): the self-test, the icons, the spec and the packaging."""

import os
import re
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "tools" / "cosmos.spec"
RESOURCES = ROOT / "cosmos" / "gui" / "resources"
ICON = RESOURCES / "cosmos.ico"
PNG = RESOURCES / "cosmos.png"


def test_selftest_passes(tmp_path, monkeypatch):
    """``Cosmos.exe --selftest`` is what verifies a packaged build, so it must pass here."""
    monkeypatch.setenv("COSMOS_DATA_DIR", str(tmp_path))
    from cosmos.app import selftest

    report = tmp_path / "report.txt"
    assert selftest(str(report)) == 0
    text = report.read_text(encoding="utf-8")
    assert "RESULT: ok" in text
    lessons = int(re.search(r"lessons: (\d+)", text).group(1))
    simulators = int(re.search(r"simulators: (\d+)", text).group(1))
    assert lessons >= 43 and simulators >= 18


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


def test_there_is_a_png_icon_for_macos_and_linux():
    """E11: the .desktop entry and the macOS .icns both start from this file."""
    assert PNG.exists(), "run python tools/make_icon.py"
    assert PNG.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def test_spec_bundles_all_content():
    assert SPEC.exists()
    spec = SPEC.read_text(encoding="utf-8")
    for folder in ("cosmos/content", "cosmos/data", "cosmos/gui/resources"):
        quoted = folder.replace("/", '" / "')
        assert quoted in spec or folder in spec, f"{folder} is not bundled by the spec"
    assert 'collect_submodules("cosmos")' in spec       # simulators are imported by name
    assert '"astropy"' in spec and '"pytest"' in spec   # test-only dependencies stay out


@pytest.mark.parametrize("name", ["build_app.py", "build_exe.py", "make_icon.py", "cosmos.spec"])
def test_packaging_files_exist(name):
    assert (ROOT / "tools" / name).exists()


# ------------------------------------------------------- E11: the other platforms
def test_the_spec_builds_a_bundle_on_macos():
    spec = SPEC.read_text(encoding="utf-8")
    assert "BUNDLE(" in spec and "Cosmos.app" in spec
    assert "bundle_identifier=" in spec
    # One-file is a Windows convenience; macOS needs a directory and Linux an AppDir.
    assert "ONEFILE = WINDOWS" in spec
    assert "cosmos.icns" in spec


def test_the_builder_knows_where_each_platform_puts_things():
    import importlib.util

    spec = importlib.util.spec_from_file_location("cosmos_build_app", ROOT / "tools" / "build_app.py")
    build_app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build_app)

    assert build_app.WINDOWS + build_app.MACOS + build_app.LINUX == 1, "exactly one platform"
    launchable = build_app.launchable(onedir=False)
    payload = build_app.payload(onedir=False)
    assert launchable.name.startswith("Cosmos")
    assert str(payload) in str(launchable) or payload == launchable
    assert build_app.platform_tag().split("-")[0] in ("windows", "macos", "linux")
    # The Linux desktop entry has to be valid enough for appimagetool.
    entry = build_app.DESKTOP_ENTRY
    for key in ("[Desktop Entry]", "Type=Application", "Name=Cosmos", "Exec=Cosmos", "Icon=cosmos"):
        assert key in entry


def test_the_ci_workflow_packages_all_three_platforms():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for runner in ("windows-latest", "macos-latest", "ubuntu-latest"):
        assert runner in workflow
    assert "tools/build_app.py --clean --package" in workflow
    # A missing appimagetool must not fail the Linux job; the tarball is the fallback.
    assert "continue-on-error: true" in workflow
    assert "if-no-files-found: error" in workflow


# ------------------------------------------------------------------- releasing
def test_the_changelog_describes_this_version():
    """A release's notes come from CHANGELOG.md, so the version must be in it."""
    import sys

    sys.path.insert(0, str(ROOT / "tools"))
    import release_notes

    from cosmos import __version__

    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## {__version__}" in text

    notes = release_notes.section(text, __version__)
    assert len(notes) > 200 and not notes.startswith("#")
    assert "##" not in notes.split("### ")[0], "the heading itself must not be repeated"
    with pytest.raises(SystemExit):
        release_notes.section(text, "99.0.0")


def test_a_tag_builds_a_draft_release():
    """Pushing v* must package all three platforms and attach them to a draft."""
    import yaml

    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8"))
    triggers = workflow[True] if True in workflow else workflow["on"]
    assert "v*" in triggers["push"]["tags"]

    package = workflow["jobs"]["package"]
    assert package["needs"] == "tests", "a broken build must never reach a release"
    assert package["permissions"]["contents"] == "write"

    step = package["steps"][-1]
    assert "refs/tags/v" in step["if"]
    assert "--draft" in step["run"], "a release is published by a person, not by CI"
    assert "release upload" in step["run"]

    platforms = {entry["name"] for entry in package["strategy"]["matrix"]["include"]}
    assert platforms == {"windows", "macos", "linux"}
