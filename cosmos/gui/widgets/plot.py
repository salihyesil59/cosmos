"""Themed matplotlib canvas with image and CSV export."""

from __future__ import annotations

import csv
import warnings
from collections.abc import Callable, Sequence

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.theme import style_axes, style_legend, theme
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
        self.canvas.setMinimumHeight(220)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.canvas, 1)
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
        self.canvas.draw_idle()

    # ------------------------------------------------------------ export
    def export_image(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, tr("Save plot"), f"{self._name}.png",
            tr("PNG image (*.png);;SVG vector image (*.svg)")
        )
        if not path:
            return
        try:
            self.figure.savefig(path, dpi=200, facecolor=self.figure.get_facecolor())
        except OSError as exc:
            QMessageBox.warning(self, tr("Could not save"), str(exc))

    def export_csv(self) -> None:
        if not self._csv:
            return
        path, _ = QFileDialog.getSaveFileName(self, tr("Export data"), f"{self._name}.csv",
                                                  tr("CSV file (*.csv)"))
        if not path:
            return
        headers, rows = self._csv()
        try:
            write_csv(path, headers, rows)
        except OSError as exc:
            QMessageBox.warning(self, tr("Could not save"), str(exc))


def write_csv(path: str, headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
