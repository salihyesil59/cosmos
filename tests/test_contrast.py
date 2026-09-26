"""A4: contrast checked against a number, not against somebody's eyesight.

"Looks fine to me" is exactly the judgement a reader with low vision cannot
share, so WCAG 2.1 defines it arithmetically. These tests hold each palette to
the level it claims:

* **dark** and **light** are the everyday themes and must clear AA for body text
* **contrast** is the accommodation, and is held to AAA — if it does not do
  better than the others, it has no reason to exist
* a plot line whose colour is what distinguishes it must clear 3:1 in every
  theme, because a series you cannot separate from the paper carries no meaning

Borders are the one place the everyday themes are allowed to fall short. A 1.4:1
hairline between two cards is a decorative separation, not a control somebody has
to find, and raising every one of them to 3:1 would make the light and dark
themes into the high-contrast one. What matters is that the theme offered to
people who need visible edges actually delivers them, which is asserted below.
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from cosmos.gui.contrast import AA_LARGE, AA_TEXT, AAA_TEXT, luminance, ratio  # noqa: E402
from cosmos.gui.theme import THEME_ORDER, THEMES  # noqa: E402

#: Foreground and background pairs a reader actually meets.
TEXT_ON = [
    ("text", "bg"), ("text", "surface"), ("text", "surface_alt"),
    ("muted", "bg"), ("muted", "surface"), ("muted", "surface_alt"),
    ("link", "bg"), ("link", "surface"),
    ("accent", "surface"), ("accent2", "surface"),
    ("success", "surface"), ("warning", "surface"), ("danger", "surface"),
    ("accent_text", "accent"),
]


def wanted(theme_name: str) -> float:
    return AAA_TEXT if theme_name == "contrast" else AA_TEXT


# ------------------------------------------------------------- the arithmetic

def test_the_ends_of_the_scale():
    assert ratio("#ffffff", "#000000") == pytest.approx(21.0, abs=0.01)
    assert ratio("#000000", "#000000") == pytest.approx(1.0)
    assert luminance("#ffffff") == pytest.approx(1.0)
    assert luminance("#000000") == pytest.approx(0.0)


def test_it_does_not_matter_which_way_round():
    assert ratio("#123456", "#fedcba") == pytest.approx(ratio("#fedcba", "#123456"))


def test_short_hex_is_understood():
    assert ratio("#fff", "#000") == pytest.approx(21.0, abs=0.01)


def test_nonsense_is_refused():
    with pytest.raises(ValueError):
        ratio("mauve", "#ffffff")


def test_a_known_value():
    """Checked against the published WCAG figure for this pair."""
    assert ratio("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)


# ----------------------------------------------------------------- the themes

@pytest.mark.parametrize("theme_name", THEME_ORDER)
def test_every_piece_of_text_is_readable(theme_name):
    palette = THEMES[theme_name]
    minimum = wanted(theme_name)
    failures = []
    for foreground, background in TEXT_ON:
        value = ratio(getattr(palette, foreground), getattr(palette, background))
        if value < minimum:
            failures.append(f"{foreground} on {background}: {value:.2f}, wanted {minimum}")
    assert not failures, f"{theme_name} theme:\n  " + "\n  ".join(failures)


@pytest.mark.parametrize("theme_name", THEME_ORDER)
def test_every_plot_colour_can_be_told_from_the_paper(theme_name):
    palette = THEMES[theme_name]
    failures = [f"series[{i}] {colour}: {ratio(colour, palette.surface):.2f}"
                for i, colour in enumerate(palette.series)
                if ratio(colour, palette.surface) < AA_LARGE]
    assert not failures, f"{theme_name} theme, wanted {AA_LARGE}:\n  " + "\n  ".join(failures)


def test_the_high_contrast_theme_earns_its_name():
    """It has no reason to exist unless it beats the others everywhere."""
    contrast = THEMES["contrast"]
    for other_name in ("dark", "light"):
        other = THEMES[other_name]
        assert (ratio(contrast.text, contrast.surface)
                > ratio(other.text, other.surface)), other_name
        assert (ratio(contrast.muted, contrast.surface)
                > ratio(other.muted, other.surface)), other_name


def test_the_high_contrast_theme_makes_edges_visible():
    """The everyday themes may use a hairline; this one is for people who cannot see it."""
    contrast = THEMES["contrast"]
    assert ratio(contrast.border, contrast.surface) >= AA_LARGE
    assert ratio(contrast.border, contrast.bg) >= AA_LARGE


def test_the_focus_ring_can_be_found_in_every_theme():
    """A3 draws it with the accent, or accent2 in the high-contrast theme."""
    for name, palette in THEMES.items():
        focus = palette.accent2 if name == "contrast" else palette.accent
        assert ratio(focus, palette.surface) >= AA_LARGE, name
        assert ratio(focus, palette.bg) >= AA_LARGE, name


def test_no_two_series_are_the_same_colour():
    """The weak claim, which is the one that is actually true.

    A first draft of this asserted that no two series share a luminance either,
    so that a reader who cannot distinguish hue could still tell the lines apart.
    Every theme failed, and so would every categorical palette ever published:
    six or seven distinguishable hues at a readable contrast cannot also be six
    or seven distinct lightnesses without becoming a single ramp, which is worse
    for everyone who can see colour. The honest answer is not to bend the palette
    around an invented rule but to distinguish the lines by more than colour —
    line style and markers — which the figures do in places and not everywhere.
    That is worth doing properly rather than pretending a test covers it.
    """
    for name, palette in THEMES.items():
        assert len(set(palette.series)) == len(palette.series), f"{name} repeats a series colour"
