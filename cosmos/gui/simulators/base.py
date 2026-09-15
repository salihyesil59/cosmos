"""Common frame for simulators: a control column and a display area."""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QHBoxLayout, QScrollArea, QSplitter, QVBoxLayout, QWidget

from cosmos.gui.simulators.registry import SimulatorInfo


class SimulatorBase(QWidget):
    """Base class. Subclasses fill ``self.controls`` and ``self.display``."""

    CONTROL_WIDTH = 330

    def __init__(self, info: SimulatorInfo, parent: QWidget | None = None):
        super().__init__(parent)
        self.info = info
        self.setObjectName(f"simulator_{info.id}")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumWidth(self.CONTROL_WIDTH)
        scroll.setMaximumWidth(self.CONTROL_WIDTH + 80)
        controls_host = QWidget()
        self.controls = QVBoxLayout(controls_host)
        self.controls.setContentsMargins(4, 4, 12, 4)
        self.controls.setSpacing(8)
        scroll.setWidget(controls_host)
        splitter.addWidget(scroll)

        display_host = QWidget()
        self.display = QVBoxLayout(display_host)
        self.display.setContentsMargins(8, 4, 4, 4)
        splitter.addWidget(display_host)
        splitter.setStretchFactor(1, 1)

        # Coalesce rapid slider movements into a single recomputation.
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(40)
        self._update_timer.timeout.connect(self.recompute)

    def schedule_update(self, *_args) -> None:
        self._update_timer.start()

    def recompute(self) -> None:
        """Recalculate and redraw. Override in subclasses."""

    def finish_controls(self) -> None:
        self.controls.addStretch(1)

    def on_shown(self) -> None:
        """Called when the simulator becomes visible."""

    def on_hidden(self) -> None:
        """Called when the user navigates away (stop animations here)."""
