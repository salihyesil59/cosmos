"""GUI-independent physics engine used by lessons and simulators."""

from cosmos.physics.cosmology import Cosmology, Fate
from cosmos.physics.presets import PRESETS, get_preset

__all__ = ["Cosmology", "Fate", "PRESETS", "get_preset"]
