"""Contrast, as a number rather than an opinion (`A4`).

Whether text can be read against its background is not a matter of taste, and
"looks fine to me" is exactly the judgement somebody with low vision cannot
share. WCAG 2.1 defines it arithmetically: a relative luminance for each colour,
and a ratio between the two. This is that arithmetic, and nothing else — no Qt,
so a test or a script can use it without a window.

The thresholds the guidelines set:

* **4.5** — normal body text (AA)
* **3.0** — large text, and the outline of a control you have to be able to find
  (AA); also the floor for anything that carries meaning, like a plot line
* **7.0** — body text at the stricter AAA level, which is what a theme calling
  itself *high contrast* ought to reach
"""

from __future__ import annotations

AA_TEXT = 4.5
AA_LARGE = 3.0
AAA_TEXT = 7.0


def _channel(value: float) -> float:
    """One sRGB channel, linearised the way the standard defines it."""
    value /= 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def _rgb(colour: str) -> tuple[int, int, int]:
    text = colour.strip().lstrip("#")
    if len(text) == 3:
        text = "".join(character * 2 for character in text)
    if len(text) != 6:
        raise ValueError(f"not a hex colour: {colour!r}")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def luminance(colour: str) -> float:
    """Relative luminance, 0 for black and 1 for white."""
    red, green, blue = (_channel(part) for part in _rgb(colour))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def ratio(foreground: str, background: str) -> float:
    """The WCAG contrast ratio between two colours, from 1 to 21."""
    first, second = luminance(foreground), luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return (lighter + 0.05) / (darker + 0.05)


def passes(foreground: str, background: str, minimum: float = AA_TEXT) -> bool:
    return ratio(foreground, background) >= minimum
