"""Dark and light themes for Qt widgets, lesson pages and matplotlib plots."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


@dataclass(frozen=True)
class Palette:
    name: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted: str
    accent: str
    accent_text: str
    accent2: str
    success: str
    warning: str
    danger: str
    link: str
    series: tuple[str, ...]

    def mix(self, color: str, amount: float, base: str | None = None) -> str:
        """Blend ``color`` into ``base`` (surface by default) by ``amount`` (0..1)."""
        c1, c2 = QColor(base or self.surface), QColor(color)
        r = c1.red() + (c2.red() - c1.red()) * amount
        g = c1.green() + (c2.green() - c1.green()) * amount
        b = c1.blue() + (c2.blue() - c1.blue()) * amount
        return QColor(int(r), int(g), int(b)).name()


DARK = Palette(
    name="dark",
    bg="#0e1320",
    surface="#161d2d",
    surface_alt="#1e2740",
    border="#2c3752",
    text="#e6e9f2",
    muted="#9aa4bd",
    accent="#6ea8fe",
    accent_text="#0b1020",
    accent2="#f5b35c",
    success="#4fd18b",
    warning="#f2c14e",
    danger="#ef6b73",
    link="#8ab4ff",
    series=("#6ea8fe", "#f5b35c", "#4fd18b", "#ef6b73", "#b58cff", "#4dd0e1", "#e6e9f2"),
)

LIGHT = Palette(
    name="light",
    bg="#f3f5fa",
    surface="#ffffff",
    surface_alt="#eaeef7",
    border="#d3d9e6",
    text="#1b2233",
    muted="#5b667d",
    accent="#2f6fdb",
    accent_text="#ffffff",
    accent2="#c7771a",
    success="#1f9d57",
    warning="#a87800",
    danger="#c9384a",
    link="#2059c4",
    series=("#2f6fdb", "#d9822b", "#1f9d57", "#c9384a", "#7c4dcc", "#0f8fa3", "#1b2233"),
)

# A deliberately harsh palette for anyone who needs the contrast (G17): pure white on
# near-black, every accent pushed to the brightest version that still reads as itself.
# Every pair here clears the WCAG AAA ratio of 7:1 against its background.
HIGH_CONTRAST = Palette(
    name="contrast",
    bg="#000000",
    surface="#0a0a0a",
    surface_alt="#1c1c1c",
    border="#8c8c8c",
    text="#ffffff",
    muted="#d6d6d6",
    accent="#7fd4ff",
    accent_text="#000000",
    accent2="#ffd24d",
    success="#69f0a5",
    warning="#ffd24d",
    danger="#ff8e8e",
    link="#9fdcff",
    series=("#7fd4ff", "#ffd24d", "#69f0a5", "#ff8e8e", "#d7a8ff", "#6fe5f5", "#ffffff"),
)

THEMES = {"dark": DARK, "light": LIGHT, "contrast": HIGH_CONTRAST}
THEME_ORDER = ("dark", "light", "contrast")

# Interface text can be scaled for readability; every point size below is multiplied by it.
MIN_SCALE, MAX_SCALE, SCALE_STEP = 0.8, 1.6, 0.1
BASE_POINT_SIZE = 10.0


def _pt(size: float, scale: float) -> str:
    """A point size in the stylesheet, scaled for readability (G17)."""
    return f"{max(size * scale, 6.0):.1f}pt"


def _stylesheet(p: Palette, scale: float = 1.0) -> str:
    focus = p.accent if p.name != "contrast" else p.accent2
    return f"""
    QWidget {{ color: {p.text}; font-size: {_pt(10, scale)}; }}
    QMainWindow, QDialog {{ background: {p.bg}; }}
    QToolTip {{
        background: {p.surface_alt}; color: {p.text}; border: 1px solid {p.border};
        padding: 6px; border-radius: 4px;
    }}
    QToolBar {{ background: {p.surface}; border: none; border-bottom: 1px solid {p.border};
                spacing: 4px; padding: 4px; }}
    QToolBar QToolButton {{ padding: 5px 10px; border-radius: 6px; }}
    QToolBar QToolButton:hover {{ background: {p.surface_alt}; }}
    QToolBar QToolButton:checked {{ background: {p.mix(p.accent, 0.25)}; }}
    QStatusBar {{ background: {p.surface}; color: {p.muted}; border-top: 1px solid {p.border}; }}
    QMenuBar {{ background: {p.surface}; }}
    QMenuBar::item:selected, QMenu::item:selected {{ background: {p.mix(p.accent, 0.3)}; }}
    QMenu {{ background: {p.surface}; border: 1px solid {p.border}; }}

    QTreeWidget#sidebar {{
        background: {p.surface}; border: none; border-right: 1px solid {p.border};
        padding-top: 6px; outline: 0;
    }}
    QTreeWidget#sidebar::item {{ padding: 5px 4px; border-radius: 5px; }}
    QTreeWidget#sidebar::item:hover {{ background: {p.surface_alt}; }}
    QTreeWidget#sidebar::item:selected {{ background: {p.mix(p.accent, 0.3)}; color: {p.text}; }}

    QDockWidget {{ titlebar-close-icon: none; }}
    QDockWidget::title {{ background: {p.surface}; padding: 6px; border-bottom: 1px solid {p.border}; }}

    QFrame[card="true"] {{
        background: {p.surface}; border: 1px solid {p.border}; border-radius: 10px;
    }}
    QFrame[banner="info"] {{
        background: {p.mix(p.accent, 0.15)}; border: 1px solid {p.mix(p.accent, 0.5)}; border-radius: 8px;
    }}
    QFrame[banner="warning"] {{
        background: {p.mix(p.warning, 0.15)}; border: 1px solid {p.mix(p.warning, 0.5)}; border-radius: 8px;
    }}
    QFrame[banner="success"] {{
        background: {p.mix(p.success, 0.15)}; border: 1px solid {p.mix(p.success, 0.5)}; border-radius: 8px;
    }}
    QFrame[banner="danger"] {{
        background: {p.mix(p.danger, 0.15)}; border: 1px solid {p.mix(p.danger, 0.5)}; border-radius: 8px;
    }}
    QLabel[role="title"] {{ font-size: {_pt(20, scale)}; font-weight: 600; }}
    QLabel[role="subtitle"] {{ font-size: {_pt(13, scale)}; font-weight: 600; }}
    QLabel[role="muted"] {{ color: {p.muted}; }}
    QLabel[role="badge"] {{
        background: {p.mix(p.accent, 0.25)}; color: {p.text}; border-radius: 9px; padding: 2px 9px;
        font-size: {_pt(9, scale)}; font-weight: 600;
    }}
    QLabel[role="value"] {{ font-size: {_pt(15, scale)}; font-weight: 600; color: {p.accent}; }}

    QPushButton {{
        background: {p.surface_alt}; border: 1px solid {p.border}; border-radius: 6px; padding: 6px 14px;
    }}
    QPushButton:hover {{ border-color: {p.accent}; }}
    QPushButton:pressed {{ background: {p.mix(p.accent, 0.2)}; }}
    QPushButton:disabled {{ color: {p.muted}; border-color: {p.border}; }}
    QPushButton[role="primary"] {{
        background: {p.accent}; color: {p.accent_text}; border: 1px solid {p.accent}; font-weight: 600;
    }}
    QPushButton[role="primary"]:hover {{ background: {p.mix("#ffffff", 0.15, p.accent)}; }}
    QFrame[card="true"][earned="no"] {{ background: {p.bg}; border-style: dashed; }}
    QFrame#challengeBar {{ border-color: {p.accent2}; }}
    QPushButton[segment="left"] {{ border-top-right-radius: 0; border-bottom-right-radius: 0; padding: 4px 10px; }}
    QPushButton[segment="right"] {{
        border-top-left-radius: 0; border-bottom-left-radius: 0; border-left: none; padding: 4px 10px;
    }}
    QPushButton[segment]:checked {{
        background: {p.accent}; color: {p.accent_text}; border-color: {p.accent}; font-weight: 600;
    }}
    QPushButton[role="link"] {{ background: transparent; border: none; color: {p.link}; padding: 2px;
                                text-align: left; }}
    QPushButton[role="link"]:hover {{ text-decoration: underline; }}
    QToolButton[role="info"] {{
        background: {p.surface_alt}; border: 1px solid {p.border}; border-radius: 9px;
        color: {p.accent}; font-weight: 700; min-width: 18px; max-width: 18px; min-height: 18px; max-height: 18px;
        padding: 0px;
    }}
    QToolButton[role="info"]:hover {{ background: {p.mix(p.accent, 0.3)}; }}

    QGroupBox {{
        background: {p.surface}; border: 1px solid {p.border}; border-radius: 8px;
        margin-top: 14px; padding: 12px 8px 8px 8px; font-weight: 600;
    }}
    QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {p.accent}; }}

    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox {{
        background: {p.bg}; border: 1px solid {p.border}; border-radius: 5px; padding: 4px 6px;
    }}
    QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus, QComboBox:focus {{ border-color: {p.accent}; }}
    QComboBox QAbstractItemView {{ background: {p.surface}; selection-background-color: {p.mix(p.accent, 0.35)}; }}

    QTabWidget::pane {{ border: 1px solid {p.border}; border-radius: 6px; background: {p.surface}; top: -1px; }}
    QTabBar::tab {{
        background: {p.surface_alt}; border: 1px solid {p.border}; padding: 6px 16px;
        border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; color: {p.muted};
    }}
    QTabBar::tab:selected {{ background: {p.surface}; color: {p.text}; border-bottom-color: {p.surface}; }}

    QTextBrowser, QListWidget, QTableWidget {{
        background: {p.surface}; border: 1px solid {p.border}; border-radius: 6px;
    }}
    QListWidget::item {{ padding: 5px; }}
    QListWidget::item:selected, QTableWidget::item:selected {{ background: {p.mix(p.accent, 0.3)}; color: {p.text}; }}
    QHeaderView::section {{ background: {p.surface_alt}; border: none; border-bottom: 1px solid {p.border};
                            padding: 5px; }}
    QTableWidget {{ gridline-color: {p.border}; }}

    QProgressBar {{ background: {p.surface_alt}; border: none; border-radius: 5px; height: 10px; text-align: center; }}
    QProgressBar::chunk {{ background: {p.success}; border-radius: 5px; }}

    QSlider::groove:horizontal {{ height: 4px; background: {p.border}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {p.accent}; border-radius: 2px; }}
    QSlider::handle:horizontal {{
        background: {p.accent}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
    }}
    QRadioButton, QCheckBox {{ spacing: 6px; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: transparent; width: 10px; }}
    QScrollBar::handle:vertical {{ background: {p.border}; border-radius: 5px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar:horizontal {{ background: transparent; height: 10px; }}
    QScrollBar::handle:horizontal {{ background: {p.border}; border-radius: 5px; min-width: 30px; }}
    QSplitter::handle {{ background: {p.border}; }}

    /* G17 — keyboard navigation. Every control that can take focus says so clearly,
       which is what makes the app usable without ever touching the mouse. */
    QPushButton:focus, QToolButton:focus, QComboBox:focus, QLineEdit:focus,
    QSpinBox:focus, QDoubleSpinBox:focus, QCheckBox:focus, QRadioButton:focus,
    QSlider:focus, QTabBar::tab:focus {{
        border: 2px solid {focus};
        outline: none;
    }}
    QTreeWidget#sidebar::item:focus, QListWidget::item:focus {{
        border: 2px solid {focus}; border-radius: 5px;
    }}
    QTextBrowser:focus, QTableWidget:focus, QListWidget:focus, QTreeWidget:focus,
    QScrollArea:focus {{
        border: 2px solid {focus};
    }}
    """


class ThemeManager(QObject):
    """Holds the active palette and notifies widgets when it changes."""

    changed = Signal(object)

    def __init__(self, name: str = "dark", scale: float = 1.0):
        super().__init__()
        self._palette = THEMES.get(name, DARK)
        self._scale = clamp_scale(scale)

    @property
    def palette(self) -> Palette:
        return self._palette

    @property
    def name(self) -> str:
        return self._palette.name

    @property
    def scale(self) -> float:
        return self._scale

    def apply(self, app: QApplication | None = None) -> None:
        app = app or QApplication.instance()
        p = self._palette
        app.setStyle("Fusion")
        qp = QPalette()
        roles = {
            QPalette.Window: p.bg,
            QPalette.WindowText: p.text,
            QPalette.Base: p.surface,
            QPalette.AlternateBase: p.surface_alt,
            QPalette.Text: p.text,
            QPalette.Button: p.surface_alt,
            QPalette.ButtonText: p.text,
            QPalette.Highlight: p.accent,
            QPalette.HighlightedText: p.accent_text,
            QPalette.ToolTipBase: p.surface_alt,
            QPalette.ToolTipText: p.text,
            QPalette.Link: p.link,
            QPalette.PlaceholderText: p.muted,
        }
        for role, color in roles.items():
            qp.setColor(role, QColor(color))
        qp.setColor(QPalette.Disabled, QPalette.Text, QColor(p.muted))
        qp.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(p.muted))
        app.setPalette(qp)
        font = app.font()
        font.setPointSizeF(BASE_POINT_SIZE * self._scale)
        app.setFont(font)
        app.setStyleSheet(_stylesheet(p, self._scale))

    def set_theme(self, name: str) -> None:
        if name == self._palette.name or name not in THEMES:
            return
        self._palette = THEMES[name]
        self.apply()
        self.changed.emit(self._palette)

    def toggle(self) -> None:
        """Cycle dark → light → high contrast → dark."""
        following = THEME_ORDER[(THEME_ORDER.index(self.name) + 1) % len(THEME_ORDER)]
        self.set_theme(following)

    def set_scale(self, scale: float) -> bool:
        """Resize every piece of interface text. Returns True if anything changed."""
        scale = clamp_scale(scale)
        if abs(scale - self._scale) < 1e-6:
            return False
        self._scale = scale
        self.apply()
        self.changed.emit(self._palette)
        return True

    def step_scale(self, steps: int) -> bool:
        return self.set_scale(self._scale + steps * SCALE_STEP)


def clamp_scale(scale: float) -> float:
    """Keep the text size inside the range the layouts were designed for."""
    return round(min(max(float(scale), MIN_SCALE), MAX_SCALE), 2)


_manager: ThemeManager | None = None


def theme() -> ThemeManager:
    """The application-wide theme manager."""
    global _manager
    if _manager is None:
        _manager = ThemeManager()
    return _manager


def repolish(widget) -> None:
    """Re-apply the stylesheet after changing a dynamic property."""
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def style_axes(ax, palette: Palette | None = None) -> None:
    """Apply palette colours to a matplotlib Axes."""
    p = palette or theme().palette
    ax.set_facecolor(p.surface)
    for spine in ax.spines.values():
        spine.set_color(p.border)
    ax.tick_params(colors=p.muted, which="both")
    ax.xaxis.label.set_color(p.text)
    ax.yaxis.label.set_color(p.text)
    ax.title.set_color(p.text)
    if not ax.images:  # grid lines on top of pictures only distract
        ax.grid(True, color=p.border, alpha=0.6, linewidth=0.6)
    legend = ax.get_legend()
    if legend is not None:
        style_legend(legend, p)


def style_legend(legend, palette: Palette | None = None) -> None:
    p = palette or theme().palette
    legend.get_frame().set_facecolor(p.surface_alt)
    legend.get_frame().set_edgecolor(p.border)
    for text in legend.get_texts():
        text.set_color(p.text)
