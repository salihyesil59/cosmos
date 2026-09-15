"""Formula rendering with matplotlib's mathtext engine."""

from __future__ import annotations

import functools
import io

import matplotlib

matplotlib.use("QtAgg")

from matplotlib import mathtext, rc_context  # noqa: E402
from matplotlib.font_manager import FontProperties  # noqa: E402

SCREEN_DPI = 96


class MathError(ValueError):
    """Raised when mathtext cannot parse a formula."""


@functools.lru_cache(maxsize=2048)
def render_png(tex: str, color: str, size_pt: float, device_ratio: float = 1.0) -> bytes:
    """Render ``tex`` (without surrounding dollars) to PNG bytes.

    The image is rendered at ``device_ratio`` times the screen resolution so it
    stays crisp on high-DPI displays.
    """
    buf = io.BytesIO()
    try:
        with rc_context({"mathtext.fontset": "cm"}):
            mathtext.math_to_image(
                f"${tex}$",
                buf,
                prop=FontProperties(size=size_pt),
                dpi=SCREEN_DPI * device_ratio,
                format="png",
                color=color,
            )
    except Exception as exc:  # mathtext raises ValueError subclasses
        raise MathError(f"cannot render formula {tex!r}: {exc}") from exc
    return buf.getvalue()


def validate(tex: str) -> None:
    """Raise :class:`MathError` if the formula cannot be rendered."""
    render_png(tex, "#000000", 11.0, 1.0)
