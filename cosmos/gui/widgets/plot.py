"""Themed matplotlib canvas with image and CSV export."""

from __future__ import annotations

import csv
import textwrap
import warnings
from collections.abc import Callable, Sequence

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.theme import repolish, style_axes, style_legend, theme
from cosmos.i18n import tr

# Qt sometimes paints a canvas before the docks have settled on their sizes. The figure is
# redrawn correctly once the widget has its real size, so the layout complaint is noise.
warnings.filterwarnings("ignore", message="constrained_layout not applied.*", category=UserWarning)

CsvProvider = Callable[[], tuple[Sequence[str], Sequence[Sequence[object]]]]


class PlotWidget(QWidget):
    """A matplotlib figure that follows the app theme.

    ``draw`` is called with the figure whenever the plot must be redrawn
    (explicit :meth:`refresh` calls and theme changes).
    """

    def __init__(
        self,
        draw: Callable[[Figure], None],
        *,
        csv_provider: CsvProvider | None = None,
        export_name: str = "cosmos_plot",
        toolbar: bool = True,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._draw = draw
        self._csv = csv_provider
        self._name = export_name
        self.figure = Figure(figsize=(6, 4), layout="constrained")
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        # A2: a canvas Qt will not give focus to is a canvas a screen reader cannot
        # reach, and the description below would never be read out.
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        # Low enough that a simulator still fits a 768-pixel screen, high enough
        # that the axes stay readable.
        self.canvas.setMinimumHeight(180)

        # A3: the focus ring G17 gave every other control cannot be drawn on the
        # canvas, which paints its own pixels and would cover a stylesheet border.
        # A frame around it can take the ring instead, and it reserves the two
        # pixels whether or not they are showing so nothing shifts on focus.
        self.canvas_frame = QFrame()
        self.canvas_frame.setObjectName("plotFrame")
        self.canvas_frame.setProperty("focused", "no")
        frame_layout = QVBoxLayout(self.canvas_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.addWidget(self.canvas)
        self.canvas.installEventFilter(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.canvas_frame, 1)
        if toolbar:
            bar = QHBoxLayout()
            bar.addStretch(1)
            save = QPushButton(tr("Save image…"))
            save.setToolTip(tr("Save this plot as a PNG or SVG image."))
            save.clicked.connect(self.export_image)
            bar.addWidget(save)
            if csv_provider:
                data = QPushButton(tr("Export data (CSV)…"))
                data.setToolTip(tr("Save the numbers behind this plot as a CSV file (opens in Excel)."))
                data.clicked.connect(self.export_csv)
                bar.addWidget(data)
            layout.addLayout(bar)
        self._dirty = False
        theme().changed.connect(self._theme_changed)

    def eventFilter(self, watched, event):  # noqa: N802 (Qt override)
        """Show the focus ring on the frame when the canvas takes focus (A3)."""
        if watched is self.canvas and event.type() in (QEvent.FocusIn, QEvent.FocusOut):
            self.canvas_frame.setProperty("focused", "yes" if event.type() == QEvent.FocusIn else "no")
            repolish(self.canvas_frame)
        return super().eventFilter(watched, event)

    def _theme_changed(self, _palette) -> None:
        # Hidden plots are redrawn only when they become visible again.
        if self.isVisible():
            self.refresh()
        else:
            self._dirty = True

    def showEvent(self, event):  # noqa: N802 (Qt override)
        if self._dirty:
            self.refresh()
        super().showEvent(event)

    MIN_DRAW_PX = 40

    def refresh(self) -> None:
        # A canvas that has not been laid out yet would make matplotlib complain about
        # collapsed axes; draw it when it becomes visible instead.
        if self.canvas.width() < self.MIN_DRAW_PX or self.canvas.height() < self.MIN_DRAW_PX:
            self._dirty = True
            return
        self._dirty = False
        p = theme().palette
        self.figure.clear()
        self.figure.patch.set_facecolor(p.surface)
        self._draw(self.figure)
        for ax in self.figure.axes:
            style_axes(ax, p)
            if ax.get_legend():
                style_legend(ax.get_legend(), p)
        self._describe()
        self.canvas.draw_idle()

    def _describe(self) -> None:
        """A2: read the finished figure back out as words, for a screen reader.

        Done after every redraw, so the description follows the sliders rather
        than describing the plot as it was when the page opened.
        """
        from cosmos.gui.rendering import figure_text

        self.canvas.setAccessibleName(self._name.replace("_", " "))
        try:
            self.canvas.setAccessibleDescription(figure_text.describe(self.figure))
        except Exception:                       # noqa: BLE001 - a description is never worth a crash
            self.canvas.setAccessibleDescription("")

    def description(self) -> str:
        """What this plot would be read out as. Used by the tests and the export."""
        return self.canvas.accessibleDescription()

    # -------------------------------------------------------- provenance (V2)
    def owning_simulator(self):
        """The simulator this plot lives in, if any, found by walking up the widgets.

        Asking the parent chain rather than being told keeps all sixty-odd plots in
        the app working without each one having to pass itself in.
        """
        from cosmos.gui.simulators.base import SimulatorBase

        widget = self.parentWidget()
        while widget is not None:
            if isinstance(widget, SimulatorBase):
                return widget
            widget = widget.parentWidget()
        return None

    def provenance(self) -> list[str]:
        """What an exported copy of this plot has to say about where it came from."""
        from cosmos import provenance

        owner = self.owning_simulator()
        return provenance.export_note(
            self._name.replace("_", " "),
            simulator_id=owner.info.id if owner else "",
            simulator_title=tr(owner.info.title) if owner else "",
            detail=owner.provenance(self._name) if owner else (),
        )

    # ------------------------------------------------------------ export
    def export_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save plot"), f"{self._name}.png",
            tr("PNG image (*.png);;SVG vector image (*.svg)")
        )
        if not path:
            return
        note = self.provenance()
        # Placed below the figure and pulled back in by ``bbox_inches="tight"``, so the
        # caption reaches the file without ever disturbing the plot on screen.
        caption = self.figure.text(
            0.0, -0.035, "\n".join(textwrap.fill(line, 110) for line in note),
            fontsize=6.5, va="top", ha="left", color=theme().palette.muted, linespacing=1.4,
        )
        try:
            self.figure.savefig(path, dpi=200, facecolor=self.figure.get_facecolor(),
                                bbox_inches="tight", bbox_extra_artists=[caption],
                                metadata=_image_metadata(path, note))
        except OSError as exc:
            QMessageBox.warning(self, tr("Could not save"), str(exc))
        finally:
            caption.remove()
            self.canvas.draw_idle()

    def export_csv(self) -> None:
        if not self._csv:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export data"), f"{self._name}.csv",
                                                  tr("CSV file (*.csv)"))
        if not path:
            return
        headers, rows = self._csv()
        try:
            write_csv(path, headers, rows, note=self.provenance())
        except OSError as exc:
            QMessageBox.warning(self, tr("Could not save"), str(exc))


def _image_metadata(path: str, note: Sequence[str]) -> dict[str, str]:
    """The same note again, where a program can read it.

    PNG and SVG spell their metadata differently, and matplotlib rejects a key the
    format does not know, so each gets only what it understands.
    """
    text = " ".join(note)
    if path.lower().endswith(".svg"):
        return {"Description": text}
    return {"Description": text, "Software": note[0]}


def write_csv(path: str, headers: Sequence[str], rows: Sequence[Sequence[object]],
              note: Sequence[str] = ()) -> None:
    """Write a table, with the provenance note as comment lines above it.

    Spreadsheets skip the leading ``#`` lines or show them in the first column; either
    way the file no longer arrives somewhere else with no idea what it is.
    """
    with open(path, "w", newline="", encoding="utf-8") as fh:
        for line in note:
            fh.write(f"# {line}\n")
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
