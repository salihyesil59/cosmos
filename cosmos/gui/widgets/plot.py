"""Themed matplotlib canvas with image and CSV export."""

from __future__ import annotations

import csv
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
            save = QPushButton("Save image…")
            save.setToolTip("Save this plot as a PNG or SVG image.")
            save.clicked.connect(self.export_image)
            bar.addWidget(save)
            if csv_provider:
                data = QPushButton("Export data (CSV)…")
                data.setToolTip("Save the numbers behind this plot as a CSV file (opens in Excel).")
                data.clicked.connect(self.export_csv)
                bar.addWidget(data)
            layout.addLayout(bar)
        theme().changed.connect(lambda _p: self.refresh())

    def refresh(self) -> None:
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
            self, "Save plot", f"{self._name}.png", "PNG image (*.png);;SVG vector image (*.svg)"
        )
        if not path:
            return
        try:
            self.figure.savefig(path, dpi=200, facecolor=self.figure.get_facecolor())
        except OSError as exc:
            QMessageBox.warning(self, "Could not save", str(exc))

    def export_csv(self) -> None:
        if not self._csv:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export data", f"{self._name}.csv", "CSV file (*.csv)")
        if not path:
            return
        headers, rows = self._csv()
        try:
            write_csv(path, headers, rows)
        except OSError as exc:
            QMessageBox.warning(self, "Could not save", str(exc))


def write_csv(path: str, headers: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(headers)
        writer.writerows(rows)
