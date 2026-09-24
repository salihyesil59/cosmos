"""Start-up cost (E12), the update check (E13) and simulator plugins (E14)."""

import json
import os
import subprocess
import sys
import textwrap
from datetime import date, timedelta
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from cosmos import plugins, updates  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# --------------------------------------------------------------- E12: start-up
STARTUP_PROBE = """
import json, os, sys, tempfile
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["COSMOS_DATA_DIR"] = tempfile.mkdtemp()
from PySide6.QtWidgets import QApplication
app = QApplication([])
from cosmos.app import create_window
window = create_window(app)
window.show()
app.processEvents()
print(json.dumps({name: name in sys.modules
                  for name in ("numpy", "scipy", "matplotlib",
                               "cosmos.physics.cosmology", "cosmos.physics.structure")}))
"""


def test_the_heavy_libraries_are_not_imported_to_show_the_window():
    """E12: numpy, scipy and matplotlib cost about a second, and the home page needs none."""
    result = subprocess.run([sys.executable, "-c", STARTUP_PROBE], capture_output=True, text=True,
                            cwd=ROOT, timeout=180)
    assert result.returncode == 0, result.stderr[-2000:]
    loaded = json.loads(result.stdout.strip().splitlines()[-1])
    assert loaded == dict.fromkeys(loaded, False), f"still imported at start-up: {loaded}"


def test_the_figure_modules_load_only_when_a_figure_is_drawn(app):
    from cosmos.gui.rendering import figures

    # available() and render_png() both have to pull them in, or a lesson would show a gap.
    names = figures.available()
    assert len(names) > 40
    assert "cmb_polarisation" in names and "mock_chain" in names
    loaded = [m for m in sys.modules if m.startswith("cosmos.gui.rendering.figures_")]
    assert len(loaded) == len(figures._EXTRA_MODULES) == 9


def test_the_content_is_parsed_with_libyaml_when_it_is_there():
    import yaml

    from cosmos.content import loader

    expected = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    assert loader._LOADER is expected
    assert loader._read_yaml("a: 1\nb: [2, 3]\n") == {"a": 1, "b": [2, 3]}


def test_the_physics_package_defers_its_re_exports():
    """``from cosmos.physics import constants`` must not drag in numpy (E12)."""
    probe = ("import sys, cosmos.physics.constants as c;"
             "print(c.C > 0, 'numpy' in sys.modules)")
    result = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                            cwd=ROOT, timeout=120)
    assert result.returncode == 0, result.stderr[-2000:]
    assert result.stdout.strip() == "True False"

    # But the convenience names still work.
    from cosmos.physics import PRESETS, Cosmology
    assert Cosmology.__name__ == "Cosmology" and len(PRESETS) > 5


# ------------------------------------------------------------- E13: updates
def test_version_comparison():
    assert updates.parse_version("v1.4.2") == (1, 4, 2)
    assert updates.parse_version("1.4") == (1, 4, 0)
    assert updates.parse_version("v2.0.0-beta1") == (2, 0, 0)
    assert updates.parse_version("") == (0, 0, 0)
    assert updates.parse_version("not a version") == (0, 0, 0)
    assert updates.is_newer("1.1", "1.0") and updates.is_newer("v1.0.1", "1.0")
    assert not updates.is_newer("1.0", "1.0")
    assert not updates.is_newer("0.9", "1.0")
    assert not updates.is_newer("rubbish", "0.1")


def test_the_check_is_off_until_it_is_turned_on():
    today = date(2026, 7, 1)
    assert updates.should_check(False, "", today) is False
    assert updates.should_check(False, "2020-01-01", today) is False
    assert updates.should_check(True, "", today) is True          # never looked
    assert updates.should_check(True, "nonsense", today) is True
    assert updates.should_check(True, today.isoformat(), today) is False
    yesterday = (today - timedelta(days=1)).isoformat()
    assert updates.should_check(True, yesterday, today) is True


def test_a_failed_check_is_silent(monkeypatch):
    monkeypatch.setattr(updates, "fetch_latest", lambda *a, **k: None)
    assert updates.check("1.0") is None


def test_only_a_newer_release_is_reported(monkeypatch):
    monkeypatch.setattr(updates, "fetch_latest",
                        lambda *a, **k: updates.Release("v1.0", "u", "same version"))
    assert updates.check("1.0") is None
    monkeypatch.setattr(updates, "fetch_latest",
                        lambda *a, **k: updates.Release("v2.0", "u", "notes\n\nmore"))
    release = updates.check("1.0")
    assert release is not None and release.version == "v2.0"
    assert release.short_notes == "notes"


def test_long_release_notes_are_trimmed():
    release = updates.Release("v2", "u", "x" * 900)
    assert len(release.short_notes) <= 400 and release.short_notes.endswith("…")
    assert updates.Release("v2", "u", "").short_notes == ""


def test_fetch_never_raises(monkeypatch):
    """Whatever the network does, start-up must not be affected."""
    def explode(*args, **kwargs):
        raise OSError("no network")

    monkeypatch.setattr(updates, "urlopen", explode)
    assert updates.fetch_latest() is None


# -------------------------------------------------------------- E14: plugins
GOOD_PLUGIN = textwrap.dedent('''
    from cosmos.gui.simulators.base import SimulatorBase
    from cosmos.plugins import SimulatorPlugin


    class Tiny(SimulatorBase):
        def __init__(self, info, parent=None):
            super().__init__(info, parent)
            self.finish_controls()

        def recompute(self):
            pass


    PLUGIN = SimulatorPlugin(id="{id}", title="{title}", tagline="A tiny plugin.",
                             description="For the tests.", simulator=Tiny)
''')


@pytest.fixture
def plugin_dir(tmp_path):
    data_file = tmp_path / "progress.json"
    return data_file, plugins.ensure_folder(data_file)


def test_the_folder_is_created_with_a_readme(plugin_dir):
    data_file, folder = plugin_dir
    assert folder.is_dir() and folder.name == "plugins"
    assert folder == plugins.folder(data_file)
    readme = (folder / "README.md").read_text(encoding="utf-8")
    assert "SimulatorPlugin" in readme and "must start with P" in readme
    assert "Only add files you wrote or trust." in readme


def test_no_folder_means_no_plugins(tmp_path):
    assert plugins.discover(tmp_path / "nowhere" / "progress.json").plugins == []


def test_a_plugin_is_found_and_described(app, plugin_dir):
    data_file, folder = plugin_dir
    (folder / "tiny.py").write_text(GOOD_PLUGIN.format(id="P1", title="Tiny"), encoding="utf-8")
    loaded = plugins.discover(data_file)
    assert loaded.ok and len(loaded.plugins) == 1
    plugin = loaded.plugins[0]
    assert plugin.id == "P1" and plugin.title == "Tiny"

    info = plugins.to_info(plugin)
    assert info.is_plugin and info.id == "P1" and info.icon == "🔌"
    simulator = info.create()
    assert type(simulator).__name__ == "Tiny"


def test_files_starting_with_an_underscore_are_ignored(plugin_dir):
    data_file, folder = plugin_dir
    (folder / "_helper.py").write_text("raise RuntimeError('should never run')", encoding="utf-8")
    loaded = plugins.discover(data_file)
    assert loaded.ok and loaded.plugins == []


@pytest.mark.parametrize("name,source,expected", [
    ("boom.py", "raise RuntimeError('deliberate')", "RuntimeError"),
    ("empty.py", "X = 1", "AttributeError"),
    ("wrong.py", "PLUGIN = 'not a plugin'", "TypeError"),
    ("badid.py", GOOD_PLUGIN.format(id="S1", title="Collide"), "must start with"),
    ("letters.py", GOOD_PLUGIN.format(id="Pxx", title="Letters"), "followed by a number"),
])
def test_a_broken_plugin_is_reported_and_skipped(app, plugin_dir, name, source, expected):
    data_file, folder = plugin_dir
    (folder / name).write_text(source, encoding="utf-8")
    (folder / "fine.py").write_text(GOOD_PLUGIN.format(id="P9", title="Fine"), encoding="utf-8")
    loaded = plugins.discover(data_file)
    assert [p.id for p in loaded.plugins] == ["P9"], "one bad file must not lose the good ones"
    assert not loaded.ok
    assert len(loaded.errors) == 1
    failed, message = loaded.errors[0]
    assert failed == name and expected in message


def test_two_plugins_cannot_share_an_id(app, plugin_dir):
    data_file, folder = plugin_dir
    (folder / "a.py").write_text(GOOD_PLUGIN.format(id="P1", title="First"), encoding="utf-8")
    (folder / "b.py").write_text(GOOD_PLUGIN.format(id="P1", title="Second"), encoding="utf-8")
    loaded = plugins.discover(data_file)
    assert [p.title for p in loaded.plugins] == ["First"]
    assert "already taken" in loaded.errors[0][1]


def test_a_plugin_cannot_take_a_built_in_id(app, plugin_dir):
    from cosmos.gui.simulators.registry import SIMULATORS

    data_file, folder = plugin_dir
    (folder / "p.py").write_text(GOOD_PLUGIN.format(id="P2", title="Fine"), encoding="utf-8")
    loaded = plugins.discover(data_file, taken=set(SIMULATORS) | {"P2"})
    assert loaded.plugins == [] and "already taken" in loaded.errors[0][1]


def test_registering_plugins_keeps_the_built_ins_first(app, plugin_dir):
    from cosmos.gui.simulators.registry import BUILTIN_IDS, SIMULATORS, forget_plugins, register_plugins

    data_file, folder = plugin_dir
    (folder / "p3.py").write_text(GOOD_PLUGIN.format(id="P3", title="Third"), encoding="utf-8")
    (folder / "p1.py").write_text(GOOD_PLUGIN.format(id="P1", title="First"), encoding="utf-8")
    loaded = plugins.discover(data_file, taken=set(SIMULATORS))
    try:
        added = register_plugins(loaded.plugins)
        assert sorted(added) == ["P1", "P3"]
        keys = list(SIMULATORS)
        assert keys[-2:] == ["P1", "P3"], "plugins sort after every built-in, and among themselves"
        assert all(k.startswith("S") for k in keys[:-2])
        assert BUILTIN_IDS <= set(SIMULATORS)
        assert register_plugins(loaded.plugins) == [], "registering twice adds nothing"
    finally:
        forget_plugins()
    assert set(SIMULATORS) == set(BUILTIN_IDS)
