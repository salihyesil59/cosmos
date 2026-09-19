"""The main application window: navigation, pages, Guide panel and tour."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt
from PySide6.QtGui import QAction, QActionGroup, QColor, QIcon, QKeySequence, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QDockWidget,
    QMainWindow,
    QMenu,
    QMessageBox,
    QSizePolicy,
    QStackedWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
)

from cosmos import APP_NAME, __version__, i18n
from cosmos.i18n import tr
from cosmos.gui.labels import physics
from cosmos.gui.context import AppContext
from cosmos.gui.pages.glossary import GlossaryPage
from cosmos.gui.pages.history_page import HistoryPage
from cosmos.gui.pages.home import HomePage
from cosmos.gui.pages.lesson import LessonPage
from cosmos.gui.pages.notes_page import NotesPage
from cosmos.gui.pages.problems_page import ProblemsPage
from cosmos.gui.pages.classroom_page import ClassroomPage
from cosmos.gui.pages.review_page import ReviewPage
from cosmos.gui.pages.progress_page import ProgressPage
from cosmos.gui.pages.reference import ReferencePage
from cosmos.gui.pages.search_page import SearchBox, SearchPage
from cosmos.gui.pages.simulators import SimulatorHostPage, SimulatorHubPage
from cosmos.gui.simulators.registry import SIMULATORS
from cosmos.gui.routes import page_context
from cosmos.gui import theme as theme_module
from cosmos.gui.theme import theme
from cosmos.gui.widgets.guide_panel import GuidePanel
from cosmos.gui.widgets.notes_panel import NotesPanel
from cosmos.gui.widgets.tutor_panel import TutorPanel
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


def _command_name(text: str) -> str:
    """A menu label reduced to the plain command, for the keyboard-shortcut sheet."""
    return text.strip("◀▶◐⌂📖∑🕰📝☆🔎📈💡✎🤖🧭🔁 ").replace("&", "")


def _focus_area(widget: QWidget) -> None:
    """Give the keyboard to a region, or to the first thing inside it that can take it."""
    if widget.focusPolicy() != Qt.NoFocus:
        widget.setFocus(Qt.TabFocusReason)
        return
    child = widget.nextInFocusChain()
    seen = 0
    while child is not None and seen < 400:
        if widget.isAncestorOf(child) and child.focusPolicy() != Qt.NoFocus and child.isVisible():
            child.setFocus(Qt.TabFocusReason)
            return
        child = child.nextInFocusChain()
        seen += 1
    # Nothing inside would take it, so let the region itself hold the focus.
    widget.setFocusPolicy(Qt.StrongFocus)
    widget.setFocus(Qt.TabFocusReason)


class MainWindow(QMainWindow):
    def __init__(self, ctx: AppContext):
        super().__init__()
        self.ctx = ctx
        self.setWindowTitle(f"{APP_NAME} — " + tr("Learn Cosmology"))
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
        self.history_page = HistoryPage(ctx)
        self.search_page = SearchPage(ctx)
        self.notes_page = NotesPage(ctx)
        self.problems_page = ProblemsPage(ctx)
        self.review_page = ReviewPage(ctx)
        self.classroom_page = ClassroomPage(ctx)
        for page in (self.home, self.lesson_page, self.sim_hub, self.glossary_page, self.progress_page,
                     self.reference_page, self.history_page, self.search_page, self.notes_page,
                     self.problems_page, self.review_page, self.classroom_page):
            self.stack.addWidget(page)
        self.setCentralWidget(self.stack)

        self._build_sidebar()
        self._build_guide()
        self._build_notes()
        self._build_tutor()
        self._build_actions()
        self.statusBar().showMessage(tr("Tip: hover over any control for a short explanation."))

        ctx.signals.navigate.connect(self.navigate)
        ctx.signals.progressChanged.connect(self._refresh_sidebar)
        ctx.signals.progressChanged.connect(self._update_review_action)
        ctx.signals.notesChanged.connect(self._refresh_notes)
        ctx.signals.statusMessage.connect(lambda text: self.statusBar().showMessage(text, 8000))
        ctx.signals.updateFound.connect(self._update_result)
        ctx.signals.progressChanged.connect(self.check_achievements)
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

        top("⌂  " + tr("Home"), "home", tr("Welcome page and where to continue"))
        self.curriculum_item = top("📚  " + tr("Course"), None, tr("All lessons, grouped by level"))
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
        self.sims_item = top("🧪  " + tr("Simulators"), "sims", tr("Interactive tools"))
        self.sim_items: dict[str, QTreeWidgetItem] = {}
        for info in SIMULATORS.values():
            item = QTreeWidgetItem([f"{info.icon}  {tr(info.title)}"])
            item.setData(0, ROUTE_ROLE, f"sim:{info.id}")
            item.setToolTip(0, tr(info.tagline))
            self.sims_item.addChild(item)
            self.sim_items[info.id] = item
        self.problems_item = top("✏  " + tr("Problem sets"), "problems",
                                 tr("Worked numeric problems with checked answers, one set per level"))
        self.glossary_item = top("📖  " + tr("Glossary"), "glossary", tr("Definitions of all important terms"))
        self.reference_item = top("∑  " + tr("Reference"), "reference",
                                  tr("Formula sheet, constants, units and models"))
        self.history_item = top("🕰  " + tr("History"), "history",
                                tr("The discoveries and the people behind them"))
        self.search_item = top("🔎  " + tr("Search"), "search",
                               tr("Search lessons, glossary, simulators and formulas"))
        self.notes_item = top("📝  " + tr("Notes & bookmarks"), "notes", tr("Everything you saved"))
        self.review_item = top("🔁  " + tr("Review"), "review",
                               tr("Quiz questions you got wrong, brought back on a schedule"))
        self.progress_item = top("📈  " + tr("Progress"), "progress", tr("Your progress and the lesson map"))
        self.classroom_item = top("🎓  " + tr("Classroom"), "classroom",
                                  tr("A progress report to hand on, and teacher notes per lesson"))
        self.curriculum_item.setExpanded(True)
        for i in range(self.curriculum_item.childCount()):
            self.curriculum_item.child(i).setExpanded(True)
        self.sims_item.setExpanded(True)
        tree.itemClicked.connect(self._on_tree_click)
        tree.itemActivated.connect(self._on_tree_click)

        dock = QDockWidget(tr("Navigation"), self)
        dock.setObjectName("navigationDock")
        dock.setWidget(tree)
        dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        dock.setTitleBarWidget(QWidget())
        self.addDockWidget(Qt.LeftDockWidgetArea, dock)
        self._refresh_sidebar()

    def _build_guide(self) -> None:
        self.guide = GuidePanel(self.ctx)
        dock = QDockWidget(tr("Guide"), self)
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
        dock = QDockWidget(tr("Notes"), self)
        dock.setObjectName("notesDock")
        dock.setWidget(self.notes)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(300)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        # The Guide and the Notes share the right-hand side as tabs; the Guide starts on top.
        self.tabifyDockWidget(self.guide_dock, dock)
        self.guide_dock.raise_()
        self.notes_dock = dock

    def _build_tutor(self) -> None:
        from cosmos.app import data_path

        self.tutor = TutorPanel(self.ctx, data_path().with_name("tutor.json"))
        dock = QDockWidget(tr("Tutor"), self)
        dock.setObjectName("tutorDock")
        dock.setWidget(self.tutor)
        dock.setFeatures(QDockWidget.DockWidgetClosable | QDockWidget.DockWidgetMovable)
        dock.setMinimumWidth(300)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
        self.tabifyDockWidget(self.notes_dock, dock)
        self.guide_dock.raise_()
        self.tutor_dock = dock

    def _build_actions(self) -> None:
        tb = self.addToolBar("Main")
        tb.setObjectName("mainToolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.toolbar = tb

        def action(text, tip, slot, shortcut=None, checkable=False):
            a = QAction(text, self)
            a.setProperty("command", _command_name(text))
            a.setToolTip(tip)
            a.setStatusTip(tip)
            a.triggered.connect(slot)
            if shortcut:
                a.setShortcut(QKeySequence(shortcut))
            a.setCheckable(checkable)
            return a

        self.back_action = action("◀ " + tr("Back"), tr("Go back to the previous page (Alt+Left)"),
                                  self.go_back, "Alt+Left")
        self.forward_action = action(tr("Forward") + " ▶", tr("Go forward (Alt+Right)"),
                                     self.go_forward, "Alt+Right")
        home = action("⌂ " + tr("Home"), tr("Home page (Ctrl+H)"), lambda: self.navigate("home"), "Ctrl+H")
        cont = action("▶ " + tr("Continue"), tr("Open the next recommended lesson (Ctrl+L)"),
                      self.continue_learning, "Ctrl+L")
        glossary = action("📖 " + tr("Glossary"), tr("Open the glossary (Ctrl+G)"),
                          lambda: self.navigate("glossary"), "Ctrl+G")
        reference = action("∑ " + tr("Reference"), tr("Formula sheet, constants and units (Ctrl+R)"),
                           lambda: self.navigate("reference"), "Ctrl+R")
        history = action("🕰 " + tr("History"), tr("The history of cosmology and its scientists"),
                         lambda: self.navigate("history"))
        notes = action("📝 " + tr("Notes"), tr("All your notes and bookmarks (Ctrl+Shift+N)"),
                       lambda: self.navigate("notes"), "Ctrl+Shift+N")
        self.bookmark_action = action("☆ " + tr("Bookmark"), tr("Bookmark the current page (Ctrl+D)"),
                                      self.toggle_bookmark, "Ctrl+D")
        self.search_box = SearchBox(self.ctx)
        find = action("🔎 " + tr("Find"), tr("Search the whole course (Ctrl+F)"), self.focus_search, "Ctrl+F")
        progress = action("📈 " + tr("Progress"), tr("Your progress and lesson map (Ctrl+P)"),
                          lambda: self.navigate("progress"), "Ctrl+P")
        self.review_action = action("🔁 " + tr("Review"),
                                    tr("Quiz questions you got wrong, brought back on a schedule "
                                       "(Ctrl+Shift+R)"),
                                    lambda: self.navigate("review"), "Ctrl+Shift+R")
        self.theme_action = action("◐ " + tr("Theme"),
                                   tr("Cycle dark, light and high-contrast themes (Ctrl+T)"),
                                   self.toggle_theme, "Ctrl+T")
        self.bigger_action = action(tr("Larger text"), tr("Make every label and control bigger (Ctrl++)"),
                                    lambda: self.change_text_size(+1), "Ctrl++")
        self.smaller_action = action(tr("Smaller text"), tr("Fit more on the screen (Ctrl+-)"),
                                     lambda: self.change_text_size(-1), "Ctrl+-")
        self.reset_text_action = action(tr("Reset text size"), tr("Back to the standard size (Ctrl+0)"),
                                        lambda: self.set_text_size(1.0), "Ctrl+0")
        self.focus_action = action(tr("Move focus to the next area"),
                                   tr("Cycle the keyboard focus between the lesson list, the page and the "
                                      "side panels (F6)"),
                                   self.cycle_focus, "F6")
        self.addAction(self.bigger_action)
        self.addAction(self.smaller_action)
        self.addAction(self.reset_text_action)
        self.addAction(self.focus_action)
        # Ctrl+= is what an unshifted keyboard actually produces for "larger".
        self.bigger_action.setShortcuts([QKeySequence("Ctrl++"), QKeySequence("Ctrl+=")])
        self.guide_action = self.guide_dock.toggleViewAction()
        self.guide_action.setText("💡 " + tr("Guide"))
        self.guide_action.setToolTip(tr("Show or hide the Guide panel (F1)"))
        self.guide_action.setShortcut(QKeySequence("F1"))
        self.notes_action = self.notes_dock.toggleViewAction()
        self.notes_action.setText("✎ " + tr("Notes panel"))
        self.notes_action.setToolTip(tr("Show or hide the Notes panel (F2)"))
        self.notes_action.setShortcut(QKeySequence("F2"))
        self.tutor_action = self.tutor_dock.toggleViewAction()
        self.tutor_action.setText("🤖 " + tr("Tutor"))
        self.tutor_action.setToolTip(tr("Ask the Tutor about this page (F3) — needs your own API key"))
        self.tutor_action.setShortcut(QKeySequence("F3"))
        tour = action("🧭 " + tr("Tour"), tr("Replay the guided tour of the app"), self.start_tour)
        for a in (self.back_action, self.forward_action, home, cont):
            tb.addAction(a)
        tb.addSeparator()
        for a in (glossary, reference, progress, self.review_action):
            tb.addAction(a)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        tb.addWidget(spacer)
        tb.addWidget(self.search_box)
        tb.addAction(self.bookmark_action)
        for a in (self.guide_action, self.notes_action, self.tutor_action, self.theme_action, tour):
            tb.addAction(a)
        self._update_nav_actions()
        self._update_review_action()

        menu = self.menuBar()
        file_menu = menu.addMenu(tr("&File"))
        file_menu.addAction(action(tr("Export notes…"), tr("Save all notes and bookmarks as a Markdown file"),
                                   self.notes_page.export))
        file_menu.addSeparator()
        self.print_lesson_action = action(
            tr("Print this lesson as PDF…"),
            tr("Save the lesson you are reading, with its figures and quiz, as a PDF (Ctrl+P is Progress; "
               "this is Ctrl+Shift+P)"),
            self.export_lesson_pdf, "Ctrl+Shift+P")
        file_menu.addAction(self.print_lesson_action)
        file_menu.addAction(action(tr("Print this level as PDF…"),
                                   tr("Every lesson of one level, each starting on a new page"),
                                   self.export_level_pdf))
        file_menu.addAction(action(tr("Print the whole course as PDF…"),
                                   tr("All lessons in one file. It is long; give it a moment."),
                                   self.export_course_pdf))
        file_menu.addSeparator()
        file_menu.addAction(action(tr("Quit"), tr("Close Cosmos"), self.close, "Ctrl+Q"))
        learn = menu.addMenu(tr("&Learn"))
        for a in (home, cont, glossary, reference, history, progress, self.review_action):
            learn.addAction(a)
        learn.addSeparator()
        learn.addAction(action(tr("Simulators"), tr("All simulators"), lambda: self.navigate("sims")))
        learn.addAction(action("🎓 " + tr("Classroom"),
                               tr("A progress report to hand on, and teacher notes per lesson"),
                               lambda: self.navigate("classroom")))
        learn.addAction(find)
        learn.addSeparator()
        learn.addAction(self.bookmark_action)
        learn.addAction(notes)
        view = menu.addMenu(tr("&View"))
        view.addMenu(self._theme_menu())
        text_size = view.addMenu(tr("Text size"))
        for a in (self.bigger_action, self.smaller_action, self.reset_text_action):
            text_size.addAction(a)
        view.addAction(self.guide_action)
        view.addAction(self.notes_action)
        view.addAction(self.tutor_action)
        view.addAction(self.back_action)
        view.addAction(self.forward_action)
        view.addSeparator()
        view.addAction(self.focus_action)
        view.addMenu(self._language_menu())
        help_menu = menu.addMenu(tr("&Help"))
        help_menu.addAction(tour)
        help_menu.addAction(action(tr("How to use Cosmos"), tr("Show help in the Guide panel"), self.show_help))
        help_menu.addAction(action(tr("Keyboard shortcuts"), tr("Every command you can reach without the mouse"),
                                   self.show_shortcuts))
        help_menu.addAction(action(tr("Simulator plugins…"),
                                   tr("Add your own simulator by dropping a Python file in a folder"),
                                   self.show_plugins))
        help_menu.addSeparator()
        self.update_action = action(tr("Check for updates now"),
                                    tr("Ask GitHub whether a newer Cosmos has been released. Nothing about "
                                       "you or this computer is sent."),
                                    lambda: self.check_for_updates(manual=True))
        help_menu.addAction(self.update_action)
        self.auto_update_action = action(
            tr("Check for updates on start-up"),
            tr("Look once a day, in the background. Off by default; nothing is ever uploaded."),
            self.set_auto_update, checkable=True)
        self.auto_update_action.setChecked(self.ctx.store.data.update_check == "on")
        help_menu.addAction(self.auto_update_action)
        help_menu.addSeparator()
        help_menu.addAction(action(tr("About Cosmos"), tr("Version and credits"), self.show_about))

    def _theme_menu(self) -> QMenu:
        """View → Theme: dark, light, and a high-contrast option (G17)."""
        from cosmos.gui.theme import THEME_ORDER

        names = {"dark": tr("Dark"), "light": tr("Light"), "contrast": tr("High contrast")}
        tips = {
            "dark": tr("Easy on the eyes in a dark room."),
            "light": tr("Better in bright daylight, and for printing screenshots."),
            "contrast": tr("Pure white on black with the strongest accents, for low vision or glare."),
        }
        menu = QMenu("◐ " + tr("Theme"), self)
        menu.setToolTipsVisible(True)
        self.theme_group = QActionGroup(self)
        self.theme_group.setExclusive(True)
        self.theme_actions = {}
        for name in THEME_ORDER:
            entry = QAction(names[name], self, checkable=True)
            entry.setChecked(name == theme().name)
            entry.setToolTip(tips[name])
            entry.triggered.connect(lambda _=False, key=name: self.set_theme(key))
            self.theme_group.addAction(entry)
            menu.addAction(entry)
            self.theme_actions[name] = entry
        menu.addSeparator()
        menu.addAction(self.theme_action)
        self.theme_menu = menu
        return menu

    def _language_menu(self) -> QMenu:
        """View → Language: every compiled translation found next to the app."""
        menu = QMenu(tr("Language"), self)
        menu.setToolTipsVisible(True)
        current = self.ctx.store.data.language or i18n.system_language()
        group = QActionGroup(self)
        group.setExclusive(True)
        for language in i18n.available_languages():
            entry = QAction(language.label, self, checkable=True)
            entry.setChecked(language.code == current)
            entry.setToolTip(tr("Applies the next time Cosmos starts."))
            entry.triggered.connect(lambda _=False, code=language.code: self.set_language(code))
            group.addAction(entry)
            menu.addAction(entry)
        menu.addSeparator()
        hint = QAction(tr("Add a language…"), self)
        hint.setToolTip(tr("See README: tools/update_translations.py creates the file to translate."))
        hint.triggered.connect(self.show_language_help)
        menu.addAction(hint)
        self.language_menu = menu
        return menu

    def set_language(self, code: str) -> None:
        self.ctx.store.data.language = code
        self.ctx.store.save()
        QMessageBox.information(
            self, tr("Language"),
            tr("The interface language changes the next time you start Cosmos.\n\n"
               "The course content — lessons, quizzes and the glossary — is written in English."))

    def show_language_help(self) -> None:
        QMessageBox.information(
            self, tr("Add a language"),
            tr("Interface translations live in cosmos/i18n as Qt .ts files.\n\n"
               "1. python tools/update_translations.py --language <code>\n"
               "2. Translate the file with Qt Linguist (pyside6-linguist)\n"
               "3. python tools/update_translations.py --release\n\n"
               "The new language then appears in this menu."))

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
        self.tutor.set_page(route, page_context(self.ctx, route))
        self._update_bookmark_action()
        self._select_sidebar(route)
        self._update_nav_actions()
        if route in ("home", "progress", "glossary", "sims", "reference", "notes", "history", "problems",
                     "review", "classroom") \
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
        if kind == "review":
            self.review_page.refresh()
            return self.review_page
        if kind == "classroom":
            self.classroom_page.refresh()
            return self.classroom_page
        if kind == "sims":
            return self.sim_hub
        if kind == "sim" and target in SIMULATORS:
            if target not in self._sim_pages:
                page = SimulatorHostPage(self.ctx, SIMULATORS[target])
                self._sim_pages[target] = page
                self.stack.addWidget(page)
            self.ctx.store.mark_opened("simulator", target)
            self.check_achievements()
            return self._sim_pages[target]
        if kind == "glossary":
            if target:
                self.glossary_page.select(target)
            return self.glossary_page
        if kind == "progress":
            self.progress_page.refresh()
            return self.progress_page
        if kind == "history":
            self.ctx.store.mark_page_seen("history")
            self.check_achievements()
            return self.history_page
        if kind == "reference":
            self.reference_page.refresh()
            if target:
                self.reference_page.show_formula(target)
            return self.reference_page
        if kind == "search":
            self.search_page.set_query(target)
            return self.search_page
        if kind == "notes":
            self.notes_page.refresh()
            return self.notes_page
        if kind == "problems":
            if target:
                self.problems_page.select(target)
            return self.problems_page
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

    def _update_review_action(self) -> None:
        """G16: the toolbar says how many questions are waiting."""
        count = len(self.ctx.store.due_reviews())
        self.review_action.setText("🔁 " + (tr("Review ({count})").format(count=count) if count
                                            else tr("Review")))

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
        elif kind == "history":
            item = self.history_item
        elif kind == "search":
            item = self.search_item
        elif kind == "notes":
            item = self.notes_item
        elif kind == "problems":
            item = self.problems_item
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
            item.setToolTip(0, lesson.summary + "\n\n"
                            + tr("Status: {status}").format(status=physics(status.value)))
        due = len(store.due_reviews())
        self.review_item.setText(0, "🔁  " + (tr("Review ({count})").format(count=due) if due
                                              else tr("Review")))

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
        self.bookmark_action.setText("★ " + tr("Bookmarked") if marked else "☆ " + tr("Bookmark"))
        self.bookmark_action.setEnabled(bool(self.notes.route))

    def check_achievements(self) -> list[str]:
        """Record anything the learner has just earned and celebrate it."""
        from cosmos.achievements import BY_ID

        new = self.ctx.store.refresh_achievements(self.ctx.curriculum)
        if new:
            names = ", ".join(f"{BY_ID[i].icon} {tr(BY_ID[i].title)}" for i in new)
            self.statusBar().showMessage(tr("Badge earned: {names}").format(names=names), 12000)
            self.progress_page.refresh()
            self.ctx.signals.achievementsUnlocked.emit(new)
        return new

    def _refresh_notes(self) -> None:
        self.notes_page.refresh()
        self._update_bookmark_action()

    def toggle_theme(self) -> None:
        theme().toggle()
        self._theme_applied()

    def set_theme(self, name: str) -> None:
        theme().set_theme(name)
        self._theme_applied()

    def _theme_applied(self) -> None:
        name = theme().name
        self.ctx.store.data.theme = name
        self.ctx.store.save()
        for key, entry in getattr(self, "theme_actions", {}).items():
            entry.setChecked(key == name)
        label = self.theme_actions[name].text() if name in getattr(self, "theme_actions", {}) else name
        self.statusBar().showMessage(tr("Theme: {name}").format(name=label), 3000)
        # Guide content contains themed images; re-render it.
        page = self.stack.currentWidget()
        if hasattr(page, "guide_markdown"):
            self.guide.set_context(page.guide_markdown())

    # ----------------------------------------------------- accessibility
    def change_text_size(self, steps: int) -> None:
        self.set_text_size(theme().scale + steps * theme_module.SCALE_STEP)

    def set_text_size(self, scale: float) -> None:
        """G17: scale every label and control, and remember the choice."""
        theme().set_scale(scale)
        self.ctx.store.data.font_scale = theme().scale
        self.ctx.store.save()
        self.statusBar().showMessage(
            tr("Text size: {percent}").format(percent=f"{theme().scale:.0%}"), 3000)

    def focus_areas(self) -> list:
        """The regions F6 cycles through, in reading order."""
        areas = [self.sidebar, self.stack.currentWidget()]
        areas += [dock.widget() for dock in (self.guide_dock, self.notes_dock, self.tutor_dock)
                  if dock.isVisible()]
        return [a for a in areas if a is not None]

    def cycle_focus(self) -> None:
        """Move the keyboard focus to the next major area of the window (F6)."""
        areas = self.focus_areas()
        if not areas:
            return
        current = self.focusWidget()      # this window's focus, not some other top level's
        index = -1
        for i, area in enumerate(areas):
            if current is area or (current is not None and area.isAncestorOf(current)):
                index = i
        target = areas[(index + 1) % len(areas)]
        _focus_area(target)

    def shortcut_rows(self) -> list[tuple[str, str]]:
        """Every command with a shortcut, for the Help sheet and for the tests."""
        rows = []
        for entry in self.findChildren(QAction):
            keys = entry.shortcut().toString()
            text = entry.property("command") or _command_name(entry.text())
            if keys and text:
                rows.append((text, keys))
        return sorted(dict(rows).items())

    def show_shortcuts(self) -> None:
        lines = [tr("Every command in Cosmos can be reached from the keyboard."), ""]
        lines += [f"- **{keys}** — {text}" for text, keys in self.shortcut_rows()]
        lines += ["", tr("Tab and Shift+Tab move between controls; F6 jumps between the lesson list, the "
                         "page and the side panels.")]
        self.guide_dock.show()
        self.guide.set_context("## " + tr("Keyboard shortcuts") + "\n\n" + "\n".join(lines))

    # ------------------------------------------------------------- printing
    def _pdf_options(self, title: str, subtitle: str):
        from cosmos.content.loader import load_teacher_notes
        from cosmos.gui.pages.classroom_page import note_labels
        from cosmos.gui.rendering.pdf import PdfOptions

        notes = {}
        if self.ctx.store.data.classroom:
            labels = note_labels()
            notes = {key: note.markdown(labels) for key, note in load_teacher_notes().items()}
        return PdfOptions(title=title, subtitle=subtitle, math_view=self.ctx.store.data.math_view,
                          teacher_notes=notes)

    def _save_pdf(self, suggested: str, lessons, subtitle: str) -> None:
        """Ask where to put the file, render it, and say what happened."""
        from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

        from cosmos.gui.rendering import pdf

        if not lessons:
            return
        path, _filter = QFileDialog.getSaveFileName(self, tr("Save as PDF"), suggested, "PDF (*.pdf)")
        if not path:
            return
        options = self._pdf_options(APP_NAME, subtitle)
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            pages = pdf.export(path, pdf.course_markdown(list(lessons), options), options)
        except OSError as error:
            QApplication.restoreOverrideCursor()
            QMessageBox.warning(self, tr("Could not save the PDF"), str(error))
            return
        finally:
            if QApplication.overrideCursor() is not None:
                QApplication.restoreOverrideCursor()
        self.statusBar().showMessage(
            tr("Saved {pages} page(s) to {path}").format(pages=pages, path=path), 8000)

    def export_lesson_pdf(self) -> None:
        lesson = self.lesson_page.lesson if self.stack.currentWidget() is self.lesson_page else None
        if lesson is None:
            self.statusBar().showMessage(tr("Open a lesson first, then print it."), 5000)
            return
        self._save_pdf(f"{lesson.id.replace('.', '_')}.pdf", [lesson], lesson.title)

    def export_level_pdf(self) -> None:
        cur = self.ctx.curriculum
        lesson = self.lesson_page.lesson if self.stack.currentWidget() is self.lesson_page else None
        number = lesson.level if lesson is not None else 0
        level = next((lv for lv in cur.levels if lv.number == number), cur.levels[0])
        lessons = [cur.lessons[i] for i in level.lesson_ids]
        self._save_pdf(f"cosmos_level_{level.number}.pdf", lessons,
                       tr("Level {number} · {title}").format(number=level.number, title=level.title))

    def export_course_pdf(self) -> None:
        cur = self.ctx.curriculum
        self._save_pdf("cosmos_course.pdf", [cur.lessons[i] for i in cur.ordered_ids],
                       tr("The whole course"))

    # ------------------------------------------------------- plugins (E14)
    def plugins_folder(self):
        from cosmos import plugins

        return plugins.folder(self.ctx.store.path)

    def report_plugins(self) -> None:
        """Say what the plugins folder produced, if anything went wrong or right."""
        loaded = getattr(self.ctx, "plugins", None)
        if loaded is None:
            return
        if loaded.errors:
            names = ", ".join(name for name, _message in loaded.errors)
            self.statusBar().showMessage(
                tr("{count} plugin(s) could not be loaded ({names}). See Help → Simulator plugins.")
                .format(count=len(loaded.errors), names=names), 15000)
        elif loaded.plugins:
            self.statusBar().showMessage(
                tr("Loaded {count} simulator plugin(s).").format(count=len(loaded.plugins)), 8000)

    def show_plugins(self) -> None:
        """Explain plugins in the Guide panel, with whatever happened this time."""
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from cosmos import plugins

        target = plugins.ensure_folder(self.ctx.store.path)
        loaded = getattr(self.ctx, "plugins", None)
        lines = [
            "## " + tr("Simulator plugins"),
            "",
            tr("You can add your own simulator without changing Cosmos. Put one Python file in this "
               "folder and restart:"),
            "",
            f"`{target}`",
            "",
            tr("The folder contains a README with a complete example. A plugin is ordinary Python and "
               "runs with the same permissions as Cosmos itself, so only add files you wrote or trust."),
            "",
        ]
        if loaded is not None and loaded.plugins:
            lines += ["### " + tr("Loaded"), ""]
            lines += [f"- **{plugin.id}** {plugin.title} — {plugin.tagline}" for plugin in loaded.plugins]
            lines.append("")
        if loaded is not None and loaded.errors:
            lines += ["### " + tr("Not loaded"), ""]
            lines += [f"- **{name}** — `{message}`" for name, message in loaded.errors]
            lines.append("")
        if loaded is None or (not loaded.plugins and not loaded.errors):
            lines += [tr("No plugins are installed."), ""]
        self.guide_dock.show()
        self.guide.set_context("\n".join(lines))
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))

    # ------------------------------------------------------- updates (E13)
    def set_auto_update(self, on: bool) -> None:
        self.ctx.store.data.update_check = "on" if on else "off"
        self.ctx.store.save()
        self.statusBar().showMessage(
            tr("Cosmos will look for updates once a day.") if on
            else tr("Cosmos will not look for updates."), 6000)
        if on:
            self.check_for_updates()

    def offer_update_check(self) -> None:
        """Ask once, on a later start-up, whether the app may look for updates."""
        from PySide6.QtWidgets import QMessageBox

        if self.ctx.store.data.update_check != "ask":
            return
        box = QMessageBox(self)
        box.setWindowTitle(tr("Check for updates?"))
        box.setText(tr("Shall Cosmos look for a newer version once a day?"))
        box.setInformativeText(
            tr("It asks GitHub for the latest release number and nothing else. No information about you, "
               "this computer or your progress is sent, and there is no identifier of any kind. You can "
               "change this at any time under Help."))
        yes = box.addButton(tr("Yes, check daily"), QMessageBox.AcceptRole)
        box.addButton(tr("No, thanks"), QMessageBox.RejectRole)
        box.exec()
        self.ctx.store.data.update_check = "on" if box.clickedButton() is yes else "off"
        self.ctx.store.save()
        self.auto_update_action.setChecked(self.ctx.store.data.update_check == "on")
        if self.ctx.store.data.update_check == "on":
            self.check_for_updates()

    def check_for_updates(self, manual: bool = False) -> bool:
        """Start a check on a worker thread. Returns True if one was started."""
        from datetime import date

        from PySide6.QtCore import QThreadPool, QRunnable, Slot

        from cosmos import updates

        data = self.ctx.store.data
        if not manual and not updates.should_check(data.update_check == "on", data.update_last_checked):
            return False
        data.update_last_checked = date.today().isoformat()
        self.ctx.store.save()
        if manual:
            self.statusBar().showMessage(tr("Looking for a newer version…"), 4000)

        signals = self.ctx.signals          # not the window: it may close while we wait

        class _Check(QRunnable):
            @Slot()
            def run(self):                       # noqa: D102 (Qt override)
                release = updates.check(__version__)
                try:
                    # Back onto the GUI thread; a failed check says nothing unless asked.
                    signals.updateFound.emit(release.version if release else "",
                                             release.url if release else "",
                                             release.short_notes if release else "",
                                             manual)
                except RuntimeError:
                    pass                         # the window went away first; nothing to report

        QThreadPool.globalInstance().start(_Check())
        return True

    def _update_result(self, version: str, url: str, notes: str, manual: bool) -> None:
        if not version:
            if manual:
                self.statusBar().showMessage(
                    tr("No newer version found — or the check could not reach GitHub."), 8000)
            return
        self.statusBar().showMessage(
            tr("Cosmos {version} is available.").format(version=version), 0)
        from PySide6.QtWidgets import QMessageBox

        box = QMessageBox(self)
        box.setWindowTitle(tr("A newer Cosmos is available"))
        box.setText(tr("Version {version} has been released.").format(version=version))
        if notes:
            box.setInformativeText(notes)
        open_page = box.addButton(tr("Open the release page"), QMessageBox.AcceptRole)
        box.addButton(tr("Later"), QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is open_page:
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl

            QDesktopServices.openUrl(QUrl(url))

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
                tr("Welcome to Cosmos!"),
                tr("This short tour shows you around. It takes less than a minute. You can leave with "
                   "<b>Skip tour</b> or the Esc key and replay it later from the <b>Tour</b> button."),
                before=lambda: self.navigate("home"),
            ),
            TourStep(
                tr("Navigation"),
                tr("The sidebar lists the whole course. Lessons are grouped into levels. The icon next to each "
                   "lesson shows its status: <b>filled with ✓</b> = completed, <b>ring</b> = ready, "
                   "<b>small grey circle</b> = prerequisites missing."),
                target=lambda: self.sidebar,
            ),
            TourStep(
                tr("Start here"),
                tr("This button always takes you to the next lesson you are ready for. If you are new to "
                   "cosmology, simply follow it."),
                target=lambda: self.home.continue_btn,
            ),
            TourStep(
                tr("The Guide panel"),
                tr("The Guide explains the page you are on: how to use it, what to try and where to go next. "
                   "When you click a coloured term in a lesson, its definition appears here too."),
                target=lambda: self.guide_dock,
            ),
            TourStep(
                tr("Lessons and quizzes"),
                tr("Each lesson has a <b>Lesson</b> tab with explanations, formulas and figures, and a "
                   "<b>Quiz</b> tab. Score at least 70% to complete the lesson."),
                target=lambda: self.lesson_page.tabs,
                before=lambda: self.navigate(f"lesson:{self.ctx.curriculum.ordered_ids[0]}"),
            ),
            TourStep(
                tr("Two ways to read a lesson"),
                tr("Every lesson has a <b>View</b> switch at the top right. <b>Intuitive</b> tells the story in "
                   "words, hiding the formulas and derivations; <b>With the maths</b> shows the complete lesson. "
                   "Switch whenever you like — your choice is remembered."),
                target=lambda: self.lesson_page.view_buttons.buttons()[0],
            ),
            TourStep(
                tr("Simulators"),
                tr("Simulators let you experiment. Lessons link to them with <b>Try it</b> boxes, and you "
                   "can open them any time from the sidebar."),
                target=lambda: self.sidebar,
                before=lambda: self.sidebar.scrollToItem(self.sims_item),
            ),
            TourStep(
                tr("Challenges"),
                tr("Many simulators open with a <b>challenge</b>: a concrete task such as finding a universe "
                   "that ends in a Big Crunch. Set the controls and press <b>Check my answer</b>; hints are "
                   "there if you need them, and solved challenges earn badges."),
                target=lambda: self.stack.currentWidget().challenge_bar,
                before=lambda: self.navigate("sim:S2"),
            ),
            TourStep(
                tr("Search and the formula sheet"),
                tr("The <b>search box</b> (Ctrl+F) looks through lessons, the glossary, the simulators and the "
                   "formula sheet at once. <b>Reference</b> (Ctrl+R) collects every formula, constant and unit "
                   "conversion in one place."),
                target=lambda: self.search_box,
            ),
            TourStep(
                tr("Your own notes"),
                tr("The <b>Notes</b> panel, next to the Guide, is a private notebook: one note per page, saved "
                   "automatically. Press <b>☆ Bookmark</b> (Ctrl+D) to keep a link to a page, and open "
                   "<b>Notes &amp; bookmarks</b> to see or export everything you saved."),
                target=lambda: self.notes_dock,
                before=lambda: (self.notes_dock.show(), self.notes_dock.raise_()),
            ),
            TourStep(
                tr("Toolbar"),
                tr("Go <b>Back</b> and <b>Forward</b> between pages, open the <b>Glossary</b> and your "
                   "<b>Progress</b> map, toggle the Guide panel, switch the <b>Theme</b>, or replay this tour."),
                target=lambda: self.toolbar,
            ),
            TourStep(
                tr("History and badges"),
                tr("<b>History</b> follows cosmology from Copernicus to the latest surveys, with cards for the "
                   "scientists. <b>Progress</b> shows your lesson map and the <b>badges</b> you have earned."),
                before=lambda: self.navigate("history"),
            ),
            TourStep(
                tr("You're ready"),
                tr("Every control has a tooltip, and <b>?</b> buttons give detailed explanations. "
                   "Enjoy exploring the universe!"),
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
        from PySide6.QtCore import QThreadPool

        QThreadPool.globalInstance().waitForDone(3000)   # an update check may still be waiting
        self.notes.save()
        worker = getattr(self.tutor, "_worker", None)
        if worker is not None:
            worker.wait(2000)
        for page in self._sim_pages.values():
            page.simulator.on_hidden()
        self.ctx.store.save()
        super().closeEvent(event)
