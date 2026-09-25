"""Loading simulators a teacher wrote, without touching the app (E14).

A plugin is one Python file in the ``plugins`` folder next to the progress file. It
declares a :class:`~cosmos.gui.simulators.registry.SimulatorInfo` and the class it
names, exactly as a built-in simulator does, and the app picks it up at start-up:

    # my_simulator.py
    from cosmos.gui.simulators.base import SimulatorBase
    from cosmos.plugins import SimulatorPlugin

    class Doubler(SimulatorBase):
        ...

    PLUGIN = SimulatorPlugin(
        id="P1", title="My simulator", tagline="What it does in one line.",
        description="A paragraph for the Guide panel.",
        simulator=Doubler,
    )

Two rules keep this honest:

* **Plugin ids start with P.** They cannot collide with the built-in S-numbers, and
  the learner can always tell which simulators came from where.
* **A broken plugin never stops the app.** Anything that raises while loading is
  reported in :attr:`Loaded.errors` and skipped; the rest still work.

A plugin is ordinary Python and runs with the app's own permissions, which is the
same trust you extend to any script you are handed. The app says so before loading
anything, and the folder is empty until somebody puts a file in it.
"""

from __future__ import annotations

import importlib.util
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

PLUGIN_PREFIX = "P"
FOLDER_NAME = "plugins"
README = """\
# Cosmos plugins

Drop a single Python file in this folder and Cosmos will offer it as an extra
simulator the next time it starts. The file must define a `PLUGIN` object:

```python
from cosmos.gui.simulators.base import SimulatorBase
from cosmos.plugins import SimulatorPlugin


class MySimulator(SimulatorBase):
    def __init__(self, info, parent=None):
        super().__init__(info, parent)
        # build controls into self.controls and plots into self.display
        self.finish_controls()

    def recompute(self):
        ...


PLUGIN = SimulatorPlugin(
    id="P1",                       # must start with P; P1, P2, ... are yours
    title="My simulator",
    tagline="One line, shown in the list.",
    description="A paragraph, shown in the Guide panel.",
    simulator=MySimulator,
    lessons=["L1.2"],              # optional: lessons that link to it
)
```

A plugin is ordinary Python and runs with the same permissions as Cosmos itself.
Only add files you wrote or trust.
"""


@dataclass
class SimulatorPlugin:
    """What a plugin file declares."""

    id: str
    title: str
    tagline: str
    description: str
    simulator: type
    how_to_use: list[str] = field(default_factory=list)
    things_to_try: list[str] = field(default_factory=list)
    lessons: list[str] = field(default_factory=list)
    icon: str = "🔌"

    def validate(self) -> None:
        """Raise ValueError if the plugin could not be shown safely."""
        if not self.id.startswith(PLUGIN_PREFIX) or len(self.id) < 2:
            raise ValueError(f"plugin id {self.id!r} must start with {PLUGIN_PREFIX!r}, as in P1")
        if not self.id[1:].isdigit():
            raise ValueError(f"plugin id {self.id!r} must be {PLUGIN_PREFIX} followed by a number")
        if not self.title or not self.tagline:
            raise ValueError(f"plugin {self.id} needs a title and a tagline")
        if not isinstance(self.simulator, type):
            raise ValueError(f"plugin {self.id}: 'simulator' must be a class, not {self.simulator!r}")


@dataclass
class Loaded:
    """The result of a scan: what worked, and what did not."""

    plugins: list[SimulatorPlugin] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)      # file name, message

    @property
    def ok(self) -> bool:
        return not self.errors


def folder(data_file: Path) -> Path:
    """Where plugins live: a ``plugins`` folder beside the progress file."""
    return Path(data_file).parent / FOLDER_NAME


def ensure_folder(data_file: Path) -> Path:
    """Create the folder and its README the first time, and return it."""
    target = folder(data_file)
    try:
        target.mkdir(parents=True, exist_ok=True)
        readme = target / "README.md"
        if not readme.exists():
            readme.write_text(README, encoding="utf-8")
    except OSError:
        pass                       # a read-only install is fine; there just are no plugins
    return target


def _load_file(path: Path) -> SimulatorPlugin:
    name = f"cosmos_plugin_{path.stem}"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"{path.name} is not importable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(name, None)
        raise
    plugin = getattr(module, "PLUGIN", None)
    if plugin is None:
        raise AttributeError("no PLUGIN object; see README.md in the plugins folder")
    if not isinstance(plugin, SimulatorPlugin):
        raise TypeError("PLUGIN must be a SimulatorPlugin")
    plugin.validate()
    return plugin


def discover(data_file: Path, taken: set[str] | None = None) -> Loaded:
    """Load every plugin file. A broken one is reported and skipped, never fatal."""
    result = Loaded()
    target = folder(data_file)
    if not target.is_dir():
        return result
    used = set(taken or ())
    for path in sorted(target.glob("*.py")):
        if path.name.startswith("_"):
            continue
        try:
            plugin = _load_file(path)
            if plugin.id in used:
                raise ValueError(f"id {plugin.id} is already taken")
            used.add(plugin.id)
            result.plugins.append(plugin)
        except BaseException as error:              # a plugin must not be able to stop the app
            message = f"{type(error).__name__}: {error}".strip()
            result.errors.append((path.name, message))
            traceback.clear_frames(error.__traceback__) if error.__traceback__ else None
    return result


def to_info(plugin: SimulatorPlugin):
    """Turn a plugin into the SimulatorInfo the rest of the app already understands."""
    from cosmos.gui.simulators.registry import PLUGINS, SimulatorInfo

    return SimulatorInfo(
        id=plugin.id,
        title=plugin.title,
        tagline=plugin.tagline,
        description=plugin.description,
        how_to_use=list(plugin.how_to_use),
        things_to_try=list(plugin.things_to_try),
        lessons=list(plugin.lessons),
        module="",                      # nothing to import: the class is already here
        class_name=plugin.simulator.__name__,
        icon=plugin.icon,
        group=PLUGINS,                  # a family of its own, at the end of the list
        extra={"plugin": plugin},
    )
