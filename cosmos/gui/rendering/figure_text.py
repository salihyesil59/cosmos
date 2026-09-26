"""What a plot says, in words (`A2`).

A canvas is where the answer usually is, and to a screen reader it is a blank
rectangle. Naming it "Hubble diagram" is better than nothing and still does not
tell anybody what the curve *does*.

So the description is read off the finished figure rather than written by hand:
the axes and their ranges, then each labelled series with how many points it has
and which way it goes. That has three advantages over a note somebody types. It
covers all sixty-odd plots at once, it moves when a slider moves, and it cannot
drift out of date, because there is nothing to keep in step — it is a reading of
the picture that was actually drawn.

Nothing here imports Qt: it takes a matplotlib figure and returns a string.
"""

from __future__ import annotations

import math

#: Series with fewer points than this are landmarks — a marker, a fitted point —
#: rather than curves, and calling them "rising" would be reading tea leaves.
MIN_POINTS_FOR_SHAPE = 4

#: Ignore wiggles smaller than this fraction of the whole vertical range.
FLATNESS = 0.02


def _points(count: int) -> str:
    return "1 point" if count == 1 else f"{count} points"


def _round(value: float) -> str:
    if value is None or not math.isfinite(value):
        return "?"
    if value == 0:
        return "0"
    magnitude = abs(value)
    if magnitude >= 1000 or magnitude < 0.01:
        return f"{value:.3g}"
    return f"{value:.4g}"


def _shape(xs, ys) -> str:
    """Which way a curve goes, in the words a person would use."""
    import numpy as np

    ys = np.asarray(ys, dtype=float)
    xs = np.asarray(xs, dtype=float)
    good = np.isfinite(ys) & np.isfinite(xs)
    ys, xs = ys[good], xs[good]
    if ys.size < MIN_POINTS_FOR_SHAPE:
        return ""
    span = float(np.nanmax(ys) - np.nanmin(ys))
    if span <= abs(float(np.nanmean(ys))) * FLATNESS or span == 0:
        return f"flat at about {_round(float(np.nanmean(ys)))}"

    first, last = float(ys[0]), float(ys[-1])
    peak, trough = int(np.argmax(ys)), int(np.argmin(ys))
    interior = range(1, ys.size - 1)
    if peak in interior and ys[peak] - max(first, last) > span * 0.05:
        return (f"rises to about {_round(float(ys[peak]))} near {_round(float(xs[peak]))}, "
                f"then falls to {_round(last)}")
    if trough in interior and min(first, last) - ys[trough] > span * 0.05:
        return (f"falls to about {_round(float(ys[trough]))} near {_round(float(xs[trough]))}, "
                f"then rises to {_round(last)}")
    direction = "rises" if last > first else "falls"
    return f"{direction} from {_round(first)} to {_round(last)}"


def _series(ax) -> list[str]:
    """Every labelled thing drawn on one pair of axes."""
    described = []
    for line in getattr(ax, "lines", []):
        label = line.get_label()
        if not label or label.startswith("_"):
            continue
        xs, ys = line.get_xdata(), line.get_ydata()
        count = len(ys) if ys is not None else 0
        shape = _shape(xs, ys) if count else ""
        marker_only = line.get_linestyle() in ("", "None", " ") and line.get_marker() not in ("", "None")
        if marker_only:
            described.append(f"{label}, {_points(count)}")
        elif shape:
            described.append(f"{label}, {shape}")
        else:
            described.append(str(label))
    for collection in getattr(ax, "collections", []):
        label = collection.get_label()
        if not label or label.startswith("_"):
            continue
        try:
            count = len(collection.get_offsets())
        except (AttributeError, TypeError):
            count = 0
        described.append(f"{label}, {_points(count)}" if count else str(label))
    return described


def _extras(ax) -> list[str]:
    """Things drawn on the axes that are not a series of points."""
    found = []
    for image in getattr(ax, "images", []):
        try:
            rows, columns = image.get_array().shape[:2]
            found.append(f"an image {columns} by {rows}")
        except (AttributeError, ValueError):
            found.append("an image")
    # Error bars leave Line2D objects behind, so a bar chart with them still has
    # lines; count the bars regardless and let the series list say the rest.
    bars = [patch for patch in getattr(ax, "patches", []) if hasattr(patch, "get_height")]
    if bars:
        found.append("1 bar" if len(bars) == 1 else f"{len(bars)} bars")
    return found


def _axis(ax, which: str) -> str:
    label = (ax.get_xlabel() if which == "x" else ax.get_ylabel()).strip()
    axis = ax.xaxis if which == "x" else ax.yaxis
    low, high = ax.get_xlim() if which == "x" else ax.get_ylim()
    scale = axis.get_scale()
    log = ", logarithmic" if scale == "log" else ""
    # An unlabelled axis has no name to give, and "axis vertical" is worse than
    # saying nothing: just read the range.
    span = f"{_round(low)} to {_round(high)}{log}"
    return f"{label}, {span}" if label else span


def describe(fig) -> str:
    """One paragraph a screen reader can read out in place of the picture."""
    axes = [ax for ax in fig.get_axes() if ax.get_visible() and not _is_colorbar(ax)]
    if not axes:
        return ""

    parts = []
    heading = ""
    if fig._suptitle is not None and fig._suptitle.get_text():
        heading = fig._suptitle.get_text().strip()
    elif axes[0].get_title():
        heading = axes[0].get_title().strip()
    if heading:
        parts.append(heading.rstrip(".") + ".")

    for number, ax in enumerate(axes, 1):
        piece = []
        if len(axes) > 1:
            title = ax.get_title().strip()
            if title == heading:
                title = ""                     # already said, at the top
            piece.append(f"Panel {number} of {len(axes)}" + (f", {title}" if title else "") + ".")
        piece.append(f"Horizontal axis {_axis(ax, 'x')}.")
        piece.append(f"Vertical axis {_axis(ax, 'y')}.")
        series = _series(ax)
        if series:
            piece.append(f"{len(series)} series: " + "; ".join(series) + ".")
        for extra in _extras(ax):
            piece.append(f"Shows {extra}.")
        parts.append(" ".join(piece))
    return " ".join(parts)


def _is_colorbar(ax) -> bool:
    """A colour bar is part of the picture beside it, not a panel of its own."""
    return getattr(ax, "_colorbar", None) is not None or bool(getattr(ax, "_colorbar_info", None))
