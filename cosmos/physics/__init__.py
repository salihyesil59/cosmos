"""GUI-independent physics engine used by lessons and simulators.

``Cosmology``, ``Fate``, ``PRESETS`` and ``get_preset`` are re-exported here for
convenience, but importing them drags in numpy and scipy — about a second. Several
parts of the interface only want ``cosmos.physics.constants``, which is pure Python,
so the re-exports are resolved on first use instead of on import (E12).
"""

from __future__ import annotations

__all__ = ["Cosmology", "Fate", "PRESETS", "get_preset"]

_SOURCES = {
    "Cosmology": "cosmos.physics.cosmology",
    "Fate": "cosmos.physics.cosmology",
    "PRESETS": "cosmos.physics.presets",
    "get_preset": "cosmos.physics.presets",
}


def __getattr__(name: str):
    """Import the heavy modules the first time one of their names is asked for."""
    module = _SOURCES.get(name)
    if module is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    import importlib

    value = getattr(importlib.import_module(module), name)
    globals()[name] = value          # cached: the next lookup skips this function
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
