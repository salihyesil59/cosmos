"""Application start-up."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from cosmos import APP_NAME, __version__


def data_path() -> Path:
    override = os.environ.get("COSMOS_DATA_DIR")
    if override:
        return Path(override) / "progress.json"
    base = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
    return Path(base) / "progress.json"


def create_window(app: QApplication):
    """Build the main window (used by ``run`` and by tests)."""
    from cosmos.content.loader import load_curriculum, load_glossary
    from cosmos.gui.context import AppContext, AppSignals
    from cosmos.gui.main_window import MainWindow
    from cosmos.gui.theme import theme
    from cosmos.progress import ProgressStore

    store = ProgressStore(data_path())
    theme().set_theme(store.data.theme)
    theme().apply(app)
    ctx = AppContext(
        curriculum=load_curriculum(),
        glossary=load_glossary(),
        store=store,
        signals=AppSignals(),
    )
    return MainWindow(ctx)


def run(argv: list[str] | None = None) -> int:
    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    font = QFont("Segoe UI" if sys.platform == "win32" else app.font().family())
    font.setPointSizeF(10)
    app.setFont(font)

    window = create_window(app)
    window.show()
    store = window.ctx.store
    last = store.data.last_route or "home"
    window.navigate(last)
    if not store.data.tour_completed:
        QTimer.singleShot(400, window.start_tour)
    return app.exec()
