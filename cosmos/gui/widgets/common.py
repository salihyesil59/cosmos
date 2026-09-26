"""Small building blocks shared across pages: info buttons, sliders, cards."""

from __future__ import annotations

import math
import re

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from cosmos.gui.theme import repolish
from cosmos.i18n import tr

_MARKUP = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")


def describe(widget, name: str, description: str = "") -> None:
    """Give a control a name a screen reader can announce (A1)."""
    widget.setAccessibleName(strip_markup(name))
    if description:
        widget.setAccessibleDescription(strip_markup(description))


def placeholder(edit, text: str) -> None:
    """Set a field's placeholder, and use it as the field's name (A1).

    A search box has no label beside it: the placeholder is what tells a sighted
    user what the box is for, so it is exactly the name to announce. It vanishes
    as soon as anything is typed, which is precisely when a name is still needed.
    """
    edit.setPlaceholderText(text)
    if not edit.accessibleName():
        edit.setAccessibleName(strip_markup(text.split("…")[0].split("(")[0].strip() or text))


def strip_markup(text: str) -> str:
    """A label as a screen reader should hear it (A1).

    Labels in this app carry rich text — <b>, <sub>, <br> — because they are drawn,
    not spoken. Read aloud, the tags are noise, and a line break in the middle of a
    name is worse than none.
    """
    return _SPACE.sub(" ", _MARKUP.sub(" ", text)).strip()


class InfoPopup(QFrame):
    """A small floating panel with a detailed explanation."""

    def __init__(self, title: str, text: str, parent: QWidget | None = None):
        super().__init__(parent, Qt.Popup)
        self.setProperty("card", True)
        self.setMaximumWidth(380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        heading = QLabel(title)
        heading.setProperty("role", "subtitle")
        body = QLabel(text)
        body.setWordWrap(True)
        body.setTextFormat(Qt.RichText)
        body.setOpenExternalLinks(False)
        layout.addWidget(heading)
        layout.addWidget(body)


class InfoButton(QToolButton):
    """A round "?" button. Hover shows a short tooltip; click shows full details."""

    def __init__(self, title: str, text: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.title, self.text_body = title, text
        self.setText("?")
        self.setProperty("role", "info")
        self.setCursor(Qt.PointingHandCursor)
        self.setToolTip(f"<b>{title}</b><br>{text}")
        self.setStatusTip(f"{title}: click for an explanation")
        # A1: every one of these announces itself as "?" otherwise.
        self.setAccessibleName(tr("About {title}").format(title=strip_markup(title)))
        self.setAccessibleDescription(strip_markup(text))
        self.clicked.connect(self._show_popup)

    def _show_popup(self):
        popup = InfoPopup(self.title, self.text_body, self)
        popup.adjustSize()
        pos = self.mapToGlobal(QPoint(self.width() + 4, 0))
        popup.move(pos)
        popup.show()


class FlowLayout(QLayout):
    """A row of widgets that wraps onto the next line when the window is narrow.

    Qt has no such layout of its own. A row of buttons in a QHBoxLayout cannot get
    narrower than the sum of its buttons, so on a small window the last ones are
    simply cut off; here they move down instead (D2).
    """

    def __init__(self, parent: QWidget | None = None, spacing: int = 8):
        super().__init__(parent)
        self._items: list = []
        self.setSpacing(spacing)

    def addItem(self, item):        # noqa: N802 (Qt override)
        self._items.append(item)

    def insertWidget(self, index: int, widget: QWidget) -> None:    # noqa: N802 (Qt-style name)
        """Put a widget at a chosen place in the row rather than at its end."""
        self.addWidget(widget)          # lets Qt reparent it and wrap it in an item
        self._items.insert(index, self._items.pop())

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):   # noqa: N802 (Qt override)
        return self._items[index] if 0 <= index < len(self._items) else None

    def takeAt(self, index: int):   # noqa: N802 (Qt override)
        return self._items.pop(index) if 0 <= index < len(self._items) else None

    def expandingDirections(self):  # noqa: N802 (Qt override)
        return Qt.Orientations(Qt.Orientation(0))

    def hasHeightForWidth(self) -> bool:    # noqa: N802 (Qt override)
        return True

    def heightForWidth(self, width: int) -> int:    # noqa: N802 (Qt override)
        return self._lay_out(QRect(0, 0, width, 0), apply=False)

    def setGeometry(self, rect):    # noqa: N802 (Qt override)
        super().setGeometry(rect)
        self._lay_out(rect, apply=True)

    def sizeHint(self) -> QSize:    # noqa: N802 (Qt override)
        return self.minimumSize()

    def minimumSize(self) -> QSize:     # noqa: N802 (Qt override)
        # The widest single item, not the sum: anything wider than that wraps.
        size = QSize(0, 0)
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        return size + QSize(margins.left() + margins.right(), margins.top() + margins.bottom())

    def _lay_out(self, rect: QRect, apply: bool) -> int:
        """Place the items inside ``rect``; returns the height they needed."""
        margins = self.contentsMargins()
        x = rect.x() + margins.left()
        y = rect.y() + margins.top()
        right = rect.right() - margins.right()
        spacing, line_height = self.spacing(), 0
        for item in self._items:
            hint = item.sizeHint()
            if line_height and x + hint.width() > right:
                x = rect.x() + margins.left()
                y += line_height + spacing
                line_height = 0
            if apply:
                item.setGeometry(QRect(QPoint(x, y), hint))
            x += hint.width() + spacing
            line_height = max(line_height, hint.height())
        return y + line_height - rect.y() + margins.bottom()


def scrolling_page(page: QWidget) -> QScrollArea:
    """Let a page scroll up and down rather than be cut off on a short screen (D2).

    Sideways it never scrolls: the page is always exactly as wide as the window.
    """
    area = QScrollArea()
    area.setWidgetResizable(True)
    area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    area.setFrameShape(QScrollArea.NoFrame)
    area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    area.setWidget(page)
    return area


def centred(widget: QWidget, max_width: int = 1120) -> QWidget:
    """Hold a page to a comfortable width and centre it in whatever room there is.

    Cards stretched across a full-screen window are hard to read and hard to scan;
    a fixed column keeps the page looking the same whether the side panels are
    open or not (D1).
    """
    widget.setMaximumWidth(max_width)
    holder = QWidget()
    layout = QHBoxLayout(holder)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.addStretch(1)
    # The column grows to its maximum first; only what is left over goes to the
    # margins, which is why its stretch is so much larger than theirs.
    layout.addWidget(widget, 100)
    layout.addStretch(1)
    return holder


def labelled_row(label: str, widget: QWidget, info: tuple[str, str] | None = None) -> QWidget:
    row = QWidget()
    layout = QHBoxLayout(row)
    layout.setContentsMargins(0, 0, 0, 0)
    lab = QLabel(label)
    layout.addWidget(lab)
    layout.addStretch(1)
    if isinstance(widget, QComboBox):
        # Long item texts must not force the control column wider than the window allows.
        widget.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        widget.setMinimumContentsLength(14)
    layout.addWidget(widget, 1)
    if not widget.accessibleName():
        widget.setAccessibleName(strip_markup(label))          # A1
    if info:
        button = InfoButton(*info)
        layout.addWidget(button)
        if not widget.accessibleDescription():
            widget.setAccessibleDescription(strip_markup(info[1]))
    return row


class ParameterSlider(QWidget):
    """Slider + spin box + info button, synchronised, for a float parameter."""

    valueChanged = Signal(float)

    def __init__(
        self,
        label: str,
        minimum: float,
        maximum: float,
        value: float,
        *,
        decimals: int = 2,
        step: float | None = None,
        log: bool = False,
        suffix: str = "",
        info: tuple[str, str] | None = None,
        tooltip: str = "",
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._min, self._max, self._log = minimum, maximum, log
        self._steps = 1000
        self._block = False

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 2, 0, 2)
        outer.setSpacing(2)
        top = QHBoxLayout()
        self.label = QLabel(label)
        self.label.setWordWrap(True)
        top.addWidget(self.label, 1)
        top.addStretch(1)
        self.spin = QDoubleSpinBox()
        self.spin.setDecimals(decimals)
        self.spin.setRange(minimum, maximum)
        self.spin.setSingleStep(step or (maximum - minimum) / 100)
        self.spin.setSuffix(suffix)
        self.spin.setKeyboardTracking(False)
        self.spin.setMinimumWidth(84)
        self.spin.setMaximumWidth(120)
        if log:
            self.spin.setStepType(QDoubleSpinBox.AdaptiveDecimalStepType)
        top.addWidget(self.spin)
        if info:
            top.addWidget(InfoButton(*info))
        outer.addLayout(top)
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, self._steps)
        outer.addWidget(self.slider)

        if tooltip:
            for w in (self.label, self.slider, self.spin):
                w.setToolTip(tooltip)
                w.setStatusTip(tooltip)

        # A1: sighted users read the label to the left; a screen reader announces
        # "slider" and "spin box" and leaves the learner to guess which parameter
        # they are changing. Qt will not make that connection on its own.
        name = strip_markup(label)
        self.slider.setAccessibleName(name)
        self.spin.setAccessibleName(name)
        if tooltip:
            self.slider.setAccessibleDescription(tooltip)
            self.spin.setAccessibleDescription(tooltip)

        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)
        self.setValue(value)

    def _to_pos(self, v: float) -> int:
        if self._log:
            lo, hi = math.log10(self._min), math.log10(self._max)
            frac = (math.log10(max(v, self._min)) - lo) / (hi - lo)
        else:
            frac = (v - self._min) / (self._max - self._min)
        return round(min(max(frac, 0.0), 1.0) * self._steps)

    def _from_pos(self, pos: int) -> float:
        frac = pos / self._steps
        if self._log:
            lo, hi = math.log10(self._min), math.log10(self._max)
            return 10 ** (lo + frac * (hi - lo))
        return self._min + frac * (self._max - self._min)

    def _from_slider(self, pos: int):
        if self._block:
            return
        self._block = True
        self.spin.setValue(self._from_pos(pos))
        self._block = False
        self.valueChanged.emit(self.spin.value())

    def _from_spin(self, v: float):
        if self._block:
            return
        self._block = True
        self.slider.setValue(self._to_pos(v))
        self._block = False
        self.valueChanged.emit(v)

    def value(self) -> float:
        return self.spin.value()

    def set_range(self, minimum: float, maximum: float) -> None:
        """Change the allowed range, keeping the value inside it."""
        self._min, self._max = minimum, maximum
        self._block = True
        self.spin.setRange(minimum, maximum)
        self._block = False
        self.setValue(min(max(self.spin.value(), minimum), maximum), emit=False)

    def setValue(self, v: float, emit: bool = True) -> None:
        self._block = True
        self.spin.setValue(v)
        self.slider.setValue(self._to_pos(v))
        self._block = False
        if emit:
            self.valueChanged.emit(self.spin.value())

    def setEnabled(self, enabled: bool) -> None:  # noqa: N802 (Qt naming)
        super().setEnabled(enabled)
        self.slider.setEnabled(enabled)
        self.spin.setEnabled(enabled)


class PresetSelector(QComboBox):
    """Drop-down of named cosmological models with explanatory tooltips."""

    presetChosen = Signal(str)

    def __init__(self, include_custom: bool = True, parent: QWidget | None = None):
        super().__init__(parent)
        if include_custom:
            self.addItem(tr("Custom (your own values)"), "custom")
            self.setItemData(0, tr("Values you set with the controls below."), Qt.ToolTipRole)
        from cosmos.physics.presets import PRESETS      # E12: numpy and scipy, on demand

        for key, preset in PRESETS.items():
            self.addItem(preset.label, key)
            self.setItemData(self.count() - 1, preset.description, Qt.ToolTipRole)
        self.setToolTip(tr("Load the parameters of a well-known cosmological model."))
        self.currentIndexChanged.connect(self._emit)

    def _emit(self, _index: int):
        key = self.currentData()
        if key and key != "custom":
            self.presetChosen.emit(key)

    def set_key(self, key: str, emit: bool = False) -> None:
        idx = self.findData(key)
        if idx < 0:
            return
        self.blockSignals(True)
        self.setCurrentIndex(idx)
        self.blockSignals(False)
        if emit:
            self._emit(idx)


class Banner(QFrame):
    """Coloured message strip (info / warning / success / danger)."""

    def __init__(self, kind: str = "info", text: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setProperty("banner", kind)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        self.label = QLabel(text)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        layout.addWidget(self.label, 1)

    def set_message(self, kind: str, text: str) -> None:
        self.setProperty("banner", kind)
        self.label.setText(text)
        repolish(self)


def card(parent: QWidget | None = None) -> QFrame:
    frame = QFrame(parent)
    frame.setProperty("card", True)
    return frame


def title_label(text: str, role: str = "title") -> QLabel:
    label = QLabel(text)
    label.setProperty("role", role)
    label.setWordWrap(True)
    return label


def muted_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setProperty("role", "muted")
    label.setWordWrap(True)
    return label
