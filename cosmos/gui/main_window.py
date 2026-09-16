"""The main application window: navigation, pages, Guide panel and tour."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QDockWidget,
    QMainWindow,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from cosmos import APP_NAME, __version__
from cosmos.gui.context import AppContext
from cosmos.gui.pages.glossary import GlossaryPage
from cosmos.gui.pages.home import HomePage
from cosmos.gui.pages.lesson import LessonPage
from cosmos.gui.pages.notes_page import NotesPage
from cosmos.gui.pages.progress_page import ProgressPage
from cosmos.gui.pages.reference import ReferencePage
from cosmos.gui.pages.search_page import SearchBox, SearchPage
from cosmos.gui.pages.simulators import SimulatorHostPage, SimulatorHubPage
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.theme import theme
from cosmos.gui.widgets.guide_panel import GuidePanel
from cosmos.gui.widgets.notes_panel import NotesPanel
from cosmos.gui.widgets.tour import TourOverlay, TourStep
from cosmos.progress import LessonStatus

ROUTE_ROLE = Qt.UserRole


def status_icon(status: LessonStatus) -> QIcon:
    p = theme().palette
    color = {LessonStatus.COMPLETED: p.success, LessonStatus.READY: p.accent, LessonStatus.NOT_READY: p.muted}[status]
    pix = QPixmap(32, 32)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    c = QColor(color)
    if status is LessonStatus.COMPLETED:
        painter.setBrush(c)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(3, 3, 26, 26)
        pen = QPen(QColor(p.surface), 4)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawLine(10, 16, 14, 21)
        painter.drawLine(14, 21, 22, 11)
    elif status is LessonStatus.READY:
        painter.setPen(QPen(c, 3))
        painter.setBrush(QColor(p.mix(color, 0.3)))
        painter.drawEllipse(5, 5, 22, 22)
    else:
        painter.setPen(QPen(c, 2))
        painter.drawEllipse(7, 7, 18, 18)
    painter.end()
    return QIcon(pix)


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME} — Learn Cosmology")
        self.resize(1440, 900)
        self.setMinimumSize(1100, 700)

        self._history: list[str] = []
        self._future: list[str] = []
        self._current_route = ""
        self._sim_pages: dict[str, SimulatorHostPage] = {}

        # Pages
        self.stack = QStackedWidget()
        self.home = HomePage(ctx)
        self.lesson_page = LessonPage(ctx)
        self.sim_hub = SimulatorHubPage(ctx)
        self.glossary_page = GlossaryPage(ctx)
        self.progress_page = ProgressPage(ctx)
        self.reference_page = ReferencePage(ctx)
        self.search_page = SearchPage(ctx)
        self.notes_page = NotesPage(ctx)
        for page in (self.home, self.lesson_page, self.sim_hub, self.glossary_page, self.progress_page,
                     self.reference_page, self.search_page, self.notes_page):
            self.stack.addWidget(page)
        self.setCentralWidget(self.stack)

        self._build_sidebar()
        self._build_guide()
        self._build_notes()
        self._build_actions()
        self.statusBar().showMessage("Tip: hover over any control for a short explanation.")

        ctx.signals.navigate.connect(self.navigate)
        ctx.signals.progressChanged.connect(self._refresh_sidebar)
        ctx.signals.notesChanged.connect(self._refresh_notes)
        theme().changed.connect(lambda _p: self._refresh_sidebar())

    # --------------------------------------------------------------- build
    def _build_sidebar(self) -> None:
        tree = QTreeWidget()
        tree.setObjectName("sidebar")
        tree.setHeaderHidden(True)
        tree.setIndentation(14)
        tree.setIconSize(QSize(14, 14))
        tree.setMinimumWidth(300)
        tree.setAnimated(True)
        self.sidebar = tree

        def top(text: str, route: str | None, tip: str) -> QTreeWidgetItem:
            item = QTreeWidgetItem([text])
            item.setData(0, ROUTE_ROLE, route)
            item.setToolTip(0, tip)
            font = item.font(0)
            font.setBold(True)
            item.setFont(0, font)
            tree.addTopLevelItem(item)
            return item

        top("⌂  Home", "home", "Welcome page and where to continue")
        self.curriculum_item = top("📚  Course", None, "All lessons, grouped by level")
        self.lesson_items: dict[str, QTreeWidgetItem] = {}
        for level in self.ctx.curriculum.levels:
            lv = QTreeWidgetItem([f"Level {level.number} · {level.title}"])
            lv.setToolTip(0, level.description)
            lv.setData(0, ROUTE_ROLE, None)
            self.curriculum_item.addChild(lv)
            for lesson_id in level.lesson_ids:
                lesson = self.ctx.curriculum.lessons[lesson_id]
                item = QTreeWidgetItem([f"{lesson.id}  {lesson.title}"])
                item.setData(0, ROUTE_ROLE, f"lesson:{lesson.id}")
                item.setToolTip(0, lesson.summary)
                lv.addChild(item)
                self.lesson_items[lesson_id] = item
        self.sims_item = top("🧪  Simulators", "sims", "Interactive tools")
        self.sim_items: dict[str, QTreeWidgetItem] = {}
        for info in SIMULATORS.values():
            item = QTreeWidgetItem([f"{info.icon}  {info.title}"])
            item.setData(0, ROUTE_ROLE, f"sim:{info.id}")
            item.setToolTip(0, info.tagline)
            self.sims_item.addChild(item)
            self.sim_items[info.id] = item
        self.glossary_item = top("📖  Glossary", "glossary", "Definitions of all important terms")
        self.reference_item = top("∑  Reference", "reference", "Formula sheet, constants, units and models")
        self.search_item = top("🔎  Search", "search", "Search lessons, glossary, simulators and formulas")
        self.notes_item = top("📝  Notes & bookmarks", "notes", "Everything you saved")
        self.progress_item = top("📈  Progress", "progress", "Your progress and the lesson map")
        self.curriculum_item.setExpanded(True)
        for i in range(self.curriculum_item.childCount()):
            self.curriculum_item.child(i).setExpanded(True)
        self.sims_item.setExpanded(True)
        tree.itemClicked.connect(self._on_tree_click)
        tree.itemActivated.connect(self._on_tree_click)

        dock = QDockWidget("Navigation", self)
        dock.setObjectName("navigationDock")
        dock.setWidget(tree)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._refresh_sidebar()

    def _build_guide(self) -> None:
        self.guide = GuidePanel(self.ctx)
        dock = QDockWidget("Guide", self)
        dock.setObjectName("guideDock")
        dock.setWidget(self.guide)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(300)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.resizeDocks([dock], [340], Qt.Horizontal)
        self.guide_dock = dock

    def _build_notes(self) -> None:
        self.notes = NotesPanel(self.ctx)
        self.notes.bookmarksChanged.connect(self._refresh_notes)
        dock = QDockWidget("Notes", self)
        dock.setObjectName("notesDock")
        dock.setWidget(self.notes)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(300)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        # The Guide and the Notes share the right-hand side as tabs; the Guide starts on top.
        self.tabifyDockWidget(self.guide_dock, dock)
        self.guide_dock.raise_()
        self.notes_dock = dock

    def _build_actions(self) -> None:
        tb = self.addToolBar("Main")
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.toolbar = tb

        def action(text, tip, slot, shortcut=None, checkable=False):
            a = QAction(text, self)
            a.setToolTip(tip)
            a.setStatusTip(tip)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setCheckable(checkable)
            return a

        self.back_action = action("◀ Back", "Go back to the previous page (Alt+Left)", self.go_back, "Alt+Left")
        self.forward_action = action("Forward ▶", "Go forward (Alt+Right)", self.go_forward, "Alt+Right")
        home = action("⌂ Home", "Home page (Ctrl+H)", lambda: self.navigate("home"), "Ctrl+H")
        cont = action("▶ Continue", "Open the next recommended lesson (Ctrl+L)", self.continue_learning, "Ctrl+L")
        glossary = action("📖 Glossary", "Open the glossary (Ctrl+G)", lambda: self.navigate("glossary"), "Ctrl+G")
        reference = action("∑ Reference", "Formula sheet, constants and units (Ctrl+R)",
                           lambda: self.navigate("reference"), "Ctrl+R")
        notes = action("📝 Notes", "All your notes and bookmarks (Ctrl+Shift+N)",
                       lambda: self.navigate("notes"), "Ctrl+Shift+N")
        self.bookmark_action = action("☆ Bookmark", "Bookmark the current page (Ctrl+D)",
                                      self.toggle_bookmark, "Ctrl+D")
        self.search_box = SearchBox(self.ctx)
        find = action("🔎 Find", "Search the whole course (Ctrl+F)", self.focus_search, "Ctrl+F")
        progress = action("📈 Progress", "Your progress and lesson map (Ctrl+P)", lambda: self.navigate("progress"), "Ctrl+P")
        self.theme_action = action("◐ Theme", "Switch between dark and light theme (Ctrl+T)", self.toggle_theme, "Ctrl+T")
        self.guide_action = self.guide_dock.toggleViewAction()
        self.guide_action.setText("💡 Guide")
        self.guide_action.setToolTip("Show or hide the Guide panel (F1)")
        self.guide_action.setShortcut(QKeySequence("F1"))
        self.notes_action = self.notes_dock.toggleViewAction()
        self.notes_action.setText("✎ Notes panel")
        self.notes_action.setToolTip("Show or hide the Notes panel (F2)")
        self.notes_action.setShortcut(QKeySequence("F2"))
        tour = action("🧭 Tour", "Replay the guided tour of the app", self.start_tour)
        for a in (self.back_action, self.forward_action, home, cont):
            tb.addAction(a)
        tb.addSeparator()
        for a in (glossary, reference, progress):
            tb.addAction(a)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        tb.addWidget(self.search_box)
        tb.addAction(self.bookmark_action)
        for a in (self.guide_action, self.notes_action, self.theme_action, tour):
            tb.addAction(a)
        self._update_nav_actions()

        menu = self.menuBar()
        file_menu = menu.addMenu("&File")
        file_menu.addAction(action("Export notes…", "Save all notes and bookmarks as a Markdown file",
                                   self.notes_page.export))
        file_menu.addSeparator()
        file_menu.addAction(action("Quit", "Close Cosmos", self.close, "Ctrl+Q"))
        learn = menu.addMenu("&Learn")
        for a in (home, cont, glossary, reference, progress):
            learn.addAction(a)
        learn.addSeparator()
        learn.addAction(action("Simulators", "All simulators", lambda: self.navigate("sims")))
        learn.addAction(find)
        learn.addSeparator()
        learn.addAction(self.bookmark_action)
        learn.addAction(notes)
        view = menu.addMenu("&View")
        view.addAction(self.theme_action)
        view.addAction(self.guide_action)
        view.addAction(self.notes_action)
        view.addAction(self.back_action)
        view.addAction(self.forward_action)
        help_menu = menu.addMenu("&Help")
        help_menu.addAction(tour)
        help_menu.addAction(action("How to use Cosmos", "Show help in the Guide panel", self.show_help))
        help_menu.addAction(action("About Cosmos", "Version and credits", self.show_about))

    # ---------------------------------------------------------- navigation
    def navigate(self, route: str, record: bool = True) -> None:
        if route.startswith("action:"):
            if route == "action:tour":
                self.start_tour()
            return
        if route == self._current_route:
            return
        page = self._page_for(route)
        if page is None:
            return
        previous = self.stack.currentWidget()
        if isinstance(previous, SimulatorHostPage) and previous is not page:
            previous.simulator.on_hidden()
        if record and self._current_route:
            self._history.append(self._current_route)
            self._future.clear()
        self._current_route = route
        self.stack.setCurrentWidget(page)
        if isinstance(page, SimulatorHostPage):
            page.simulator.on_shown()
        self.guide.set_context(page.guide_markdown())
        self.notes.set_route(route)
        self._update_bookmark_action()
        self._select_sidebar(route)
        self._update_nav_actions()
        if route in ("home", "progress", "glossary", "sims", "reference", "notes") \
                or route.startswith(("lesson:", "sim:")):
            self.ctx.store.data.last_route = route
            self.ctx.store.save()

    def _page_for(self, route: str) -> QWidget | None:
        kind, _, target = route.partition(":")
        if kind == "home":
            self.home.refresh()
            return self.home
        if kind == "lesson" and target in self.ctx.curriculum.lessons:
            self.lesson_page.load(target)
            return self.lesson_page
        if kind == "sims":
            return self.sim_hub
        if kind == "sim" and target in SIMULATORS:
            if target not in self._sim_pages:
                page = SimulatorHostPage(self.ctx, SIMULATORS[target])
                self._sim_pages[target] = page
                self.stack.addWidget(page)
            self.ctx.store.mark_opened("simulator", target)
            return self._sim_pages[target]
        if kind == "glossary":
            if target:
                self.glossary_page.select(target)
            return self.glossary_page
        if kind == "progress":
            self.progress_page.refresh()
            return self.progress_page
        if kind == "reference":
            if target:
                self.reference_page.show_formula(target)
            return self.reference_page
        if kind == "search":
            self.search_page.set_query(target)
            return self.search_page
        if kind == "notes":
            self.notes_page.refresh()
            return self.notes_page
        return None

    def go_back(self) -> None:
        if self._history:
            self._future.append(self._current_route)
            self.navigate_without_record(self._history.pop())

    def go_forward(self) -> None:
        if self._future:
            self._history.append(self._current_route)
            self.navigate_without_record(self._future.pop())

    def navigate_without_record(self, route: str) -> None:
        self._current_route = ""  # force reload
        self.navigate(route, record=False)

    def _update_nav_actions(self) -> None:
        self.back_action.setEnabled(bool(self._history))
        self.forward_action.setEnabled(bool(self._future))

    def continue_learning(self) -> None:
        nxt = self.ctx.store.next_recommended(self.ctx.curriculum)
        self.navigate(f"lesson:{nxt}" if nxt else "progress")

    def _on_tree_click(self, item: QTreeWidgetItem, _column: int = 0) -> None:
        route = item.data(0, ROUTE_ROLE)
        if route:
            self.navigate(route)
        else:
            item.setExpanded(not item.isExpanded())

    def _select_sidebar(self, route: str) -> None:
        kind, _, target = route.partition(":")
        item = None
        if kind == "home":
            item = self.sidebar.topLevelItem(0)
        elif kind == "lesson":
            item = self.lesson_items.get(target)
        elif kind == "sim":
            item = self.sim_items.get(target)
        elif kind == "sims":
            item = self.sims_item
        elif kind == "glossary":
            item = self.glossary_item
        elif kind == "reference":
            item = self.reference_item
        elif kind == "search":
            item = self.search_item
        elif kind == "notes":
            item = self.notes_item
        elif kind == "progress":
            item = self.progress_item
        if item:
            self.sidebar.blockSignals(True)
            self.sidebar.setCurrentItem(item)
            self.sidebar.scrollToItem(item)
            self.sidebar.blockSignals(False)

    def _refresh_sidebar(self) -> None:
        cur, store = self.ctx.curriculum, self.ctx.store
        for lesson_id, item in self.lesson_items.items():
            status = store.status(cur, lesson_id)
            item.setIcon(0, status_icon(status))
            lesson = cur.lessons[lesson_id]
            item.setToolTip(0, f"{lesson.summary}\n\nStatus: {status.value}")

    # ----------------------------------------------------------- commands
    def focus_search(self) -> None:
        self.search_box.setFocus()
        self.search_box.selectAll()

    def toggle_bookmark(self) -> None:
        self.notes_dock.show()
        self.notes_dock.raise_()
        self.notes.toggle_bookmark()
        self._update_bookmark_action()

    def _update_bookmark_action(self) -> None:
        marked = self.ctx.store.is_bookmarked(self._current_route)
        self.bookmark_action.setText("★ Bookmarked" if marked else "☆ Bookmark")
        self.bookmark_action.setEnabled(bool(self.notes.route))

    def _refresh_notes(self) -> None:
        self.notes_page.refresh()
        self._update_bookmark_action()

    def toggle_theme(self) -> None:
        theme().toggle()
        self.ctx.store.data.theme = theme().name
        self.ctx.store.save()
        # Guide content contains themed images; re-render it.
        page = self.stack.currentWidget()
        if hasattr(page, "guide_markdown"):
            self.guide.set_context(page.guide_markdown())

    def show_help(self) -> None:
        self.guide_dock.show()
        self.guide.set_context(self.home.guide_markdown())

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME} {__version__}</h3>"
            "<p>An interactive course in cosmology, from the basics to advanced topics.</p>"
            "<p>Physics engine verified against astropy. Cosmological parameters from the Planck 2018 "
            "and WMAP 9-year results. Historical data from Hubble (1929).</p>"
            "<p>Built with Python, PySide6, NumPy, SciPy and Matplotlib.</p>"
            "<p>Your progress, notes and bookmarks are stored only on this computer.</p>",
        )

    def start_tour(self) -> None:
        steps = [
            TourStep(
                "Welcome to Cosmos!",
                "This short tour shows you around. It takes less than a minute. You can leave with "
                "<b>Skip tour</b> or the Esc key and replay it later from the <b>Tour</b> button.",
                before=lambda: self.navigate("home"),
            ),
            TourStep(
                "Navigation",
                "The sidebar lists the whole course. Lessons are grouped into levels. The icon next to each "
                "lesson shows its status: <b>filled with ✓</b> = completed, <b>ring</b> = ready, "
                "<b>small grey circle</b> = prerequisites missing.",
                target=lambda: self.sidebar,
            ),
            TourStep(
                "Start here",
                "This button always takes you to the next lesson you are ready for. If you are new to "
                "cosmology, simply follow it.",
                target=lambda: self.home.continue_btn,
            ),
            TourStep(
                "The Guide panel",
                "The Guide explains the page you are on: how to use it, what to try and where to go next. "
                "When you click a coloured term in a lesson, its definition appears here too.",
                target=lambda: self.guide_dock,
            ),
            TourStep(
                "Lessons and quizzes",
                "Each lesson has a <b>Lesson</b> tab with explanations, formulas and figures, and a "
                "<b>Quiz</b> tab. Score at least 70% to complete the lesson.",
                target=lambda: self.lesson_page.tabs,
                before=lambda: self.navigate(f"lesson:{self.ctx.curriculum.ordered_ids[0]}"),
            ),
            TourStep(
                "Simulators",
                "Simulators let you experiment. Lessons link to them with <b>Try it</b> boxes, and you "
                "can open them any time from the sidebar.",
                target=lambda: self.sidebar,
                before=lambda: self.sidebar.scrollToItem(self.sims_item),
            ),
            TourStep(
                "Search and the formula sheet",
                "The <b>search box</b> (Ctrl+F) looks through lessons, the glossary, the simulators and the "
                "formula sheet at once. <b>Reference</b> (Ctrl+R) collects every formula, constant and unit "
                "conversion in one place.",
                target=lambda: self.search_box,
            ),
            TourStep(
                "Your own notes",
                "The <b>Notes</b> panel, next to the Guide, is a private notebook: one note per page, saved "
                "automatically. Press <b>☆ Bookmark</b> (Ctrl+D) to keep a link to a page, and open "
                "<b>Notes &amp; bookmarks</b> to see or export everything you saved.",
                target=lambda: self.notes_dock,
                before=lambda: (self.notes_dock.show(), self.notes_dock.raise_()),
            ),
            TourStep(
                "Toolbar",
                "Go <b>Back</b> and <b>Forward</b> between pages, open the <b>Glossary</b> and your "
                "<b>Progress</b> map, toggle the Guide panel, switch the <b>Theme</b>, or replay this tour.",
                target=lambda: self.toolbar,
            ),
            TourStep(
                "You're ready",
                "Every control has a tooltip, and <b>?</b> buttons give detailed explanations. "
                "Enjoy exploring the universe!",
                before=lambda: self.navigate("home"),
            ),
        ]
        overlay = TourOverlay(self, steps)
        overlay.finished.connect(self._tour_finished)
        overlay.start()

    def _tour_finished(self) -> None:
        self.ctx.store.data.tour_completed = True
        self.ctx.store.save()

    def closeEvent(self, event):  # noqa: N802
        self.notes.save()
        for page in self._sim_pages.values():
            page.simulator.on_hidden()
        self.ctx.store.save()
        super().closeEvent(event)
