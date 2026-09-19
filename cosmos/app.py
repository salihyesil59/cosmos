"""Application start-up."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from cosmos import APP_NAME, __version__, i18n
from cosmos.gui.icons import app_icon


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
    i18n.install(app, store.data.language or i18n.system_language())
    theme().set_theme(store.data.theme)
    theme().set_scale(store.data.font_scale)
    theme().apply(app)
    ctx = AppContext(
        curriculum=load_curriculum(),
        glossary=load_glossary(),
        store=store,
        signals=AppSignals(),
    )
    return MainWindow(ctx)


def selftest(report_path: str | None = None) -> int:
    """Open every kind of page once and check the content is complete.

    Used to verify a packaged build: ``Cosmos.exe --selftest report.txt``.
    """
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from cosmos.content.loader import load_challenges, load_formulas, load_history, load_problems
    from cosmos.gui.simulators.registry import SIMULATORS

    app = QApplication.instance() or QApplication([])
    lines = [f"{APP_NAME} {__version__}", f"progress file: {data_path()}"]
    failures = []
    window = create_window(app)
    window.show()
    app.processEvents()
    curriculum = window.ctx.curriculum
    checks = [
        ("lessons", len(curriculum.lessons)),
        ("simulators", len(SIMULATORS)),
        ("glossary terms", len(window.ctx.glossary)),
        ("formulas", len(load_formulas())),
        ("challenges", sum(len(v) for v in load_challenges().values())),
        ("history events", len(load_history()[0])),
        ("problems", sum(len(s.problems) for s in load_problems())),
    ]
    for name, count in checks:
        lines.append(f"{name}: {count}")
        if count == 0:
            failures.append(f"no {name} were bundled")

    routes = ["home", "sims", "glossary", "reference", "history", "notes", "progress", "problems",
              f"lesson:{curriculum.ordered_ids[0]}", "sim:S1", "search:redshift"]
    for route in routes:
        try:
            window.navigate(route)
            app.processEvents()
        except Exception as exc:                       # noqa: BLE001 - reported, not raised
            failures.append(f"{route}: {exc!r}")
    lines.append(f"pages opened: {len(routes)}")
    lines.append("RESULT: " + ("ok" if not failures else "failed"))
    lines += [f"  - {problem}" for problem in failures]
    window.close()

    text = "\n".join(lines)
    if report_path:
        Path(report_path).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if not failures else 1


def run(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv)
    if "--version" in args:
        print(f"{APP_NAME} {__version__}")
        return 0
    if "--selftest" in args:
        index = args.index("--selftest")
        report = args[index + 1] if len(args) > index + 1 else None
        return selftest(report)

    app = QApplication(argv if argv is not None else sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName(APP_NAME)
    app.setApplicationVersion(__version__)
    app.setWindowIcon(app_icon())
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
