"""The "Ask the Tutor" panel (E9): an optional assistant that uses the learner's own API key."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtGui import QDesktopServices, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from cosmos import tutor
from cosmos.gui.context import AppContext
from cosmos.gui.routes import route_title
from cosmos.gui.widgets.common import labelled_row, muted_label
from cosmos.gui.widgets.rich_browser import RichBrowser
from cosmos.i18n import tr

CONSOLE_URL = "https://console.anthropic.com/settings/keys"

SUGGESTIONS = [
    ("Explain simply", "Explain this page in simpler words, as if I had never studied physics."),
    ("Why?", "Why is this true? Walk me through the reasoning step by step."),
    ("Example", "Give me a worked numerical example for this page."),
    ("Check me", "I think I understood this as follows — tell me what I have wrong: "),
]

INTRO = """
## Ask the Tutor

This panel is **off until you add your own API key**. Nothing is ever sent
without you pressing **Ask**.

1. Paste an Anthropic API key in **Connection** below.
2. Ask anything about the page you are reading.
3. Tick *Include the page I am reading* to let the tutor see that lesson or
   simulator; untick it to send only your question.

Answers come from a language model. They can be wrong — the lessons, not the
tutor, are the course.
"""


class _AskWorker(QThread):
    """Runs one request off the interface thread."""

    answered = Signal(str)
    failed = Signal(str)

    def __init__(self, conversation, config, context, transport, parent=None):
        super().__init__(parent)
        self._conversation = conversation
        self._config = config
        self._context = context
        self._transport = transport

    def run(self) -> None:                       # pragma: no cover - exercised through the panel
        try:
            self.answered.emit(tutor.ask(self._conversation, self._config, self._context, self._transport))
        except tutor.TutorError as exc:
            self.failed.emit(str(exc))
        except Exception as exc:                 # noqa: BLE001 - never let a thread crash the app
            self.failed.emit(f"Unexpected problem: {exc}")


class TutorPanel(QWidget):
    """Question box, conversation and the key settings."""

    def __init__(self, ctx: AppContext, config_path: Path, parent: QWidget | None = None):
        super().__init__(parent)
        self.ctx = ctx
        self.config_path = Path(config_path)
        self.config = tutor.TutorConfig.load(self.config_path)
        self.conversation = tutor.Conversation()
        self.transport = None                    # replaced in tests; None means a real request
        self.synchronous = False                 # tests ask without a worker thread
        self.route = ""
        self._context = ""
        self._worker: _AskWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        self.view = RichBrowser(font_pt=10.5)
        self.view.lessonRequested.connect(lambda i: ctx.navigate(f"lesson:{i}"))
        self.view.set_markdown_content(INTRO)
        layout.addWidget(self.view, 1)

        self.page_label = muted_label("")
        layout.addWidget(self.page_label)

        suggestions = QHBoxLayout()
        suggestions.setSpacing(4)
        for label, prompt in SUGGESTIONS:
            button = QPushButton(label)
            button.setToolTip(prompt)
            button.clicked.connect(lambda _=False, text=prompt: self._suggest(text))
            suggestions.addWidget(button)
        layout.addLayout(suggestions)

        self.question = QTextEdit()
        self.question.setPlaceholderText(tr("Ask about this page…  (Ctrl+Enter to send)"))
        self.question.setAcceptRichText(False)
        self.question.setMaximumHeight(90)
        layout.addWidget(self.question)

        row = QHBoxLayout()
        self.ask_button = QPushButton(tr("Ask"))
        self.ask_button.setProperty("role", "primary")
        self.ask_button.clicked.connect(self.ask)
        row.addWidget(self.ask_button)
        self.include_context = QCheckBox(tr("Include the page I am reading"))
        self.include_context.setChecked(self.config.include_context)
        self.include_context.setToolTip(tr("Sends the text of the lesson, or the settings of the simulator, "
                                        "so the answer fits what you are looking at."))
        self.include_context.toggled.connect(self._context_toggled)
        row.addWidget(self.include_context, 1)
        clear = QPushButton(tr("New conversation"))
        clear.clicked.connect(self.reset_conversation)
        row.addWidget(clear)
        layout.addLayout(row)

        self.status = muted_label("")
        layout.addWidget(self.status)

        connection = QGroupBox(tr("Connection"))
        cl = QVBoxLayout(connection)
        self.key_edit = QLineEdit(self.config.api_key)
        self.key_edit.setEchoMode(QLineEdit.Password)
        self.key_edit.setPlaceholderText("sk-ant-…")
        self.key_edit.textChanged.connect(self._key_changed)
        cl.addWidget(labelled_row(tr("API key"), self.key_edit, (
            "Your own API key",
            "Cosmos has no account and no server of its own. Use a key from your Anthropic account; the "
            "requests are billed to you. The key is kept on this computer only, and only if you tick "
            "Remember.")))
        self.model_box = QComboBox()
        for model_id, label in tutor.MODELS:
            self.model_box.addItem(label, model_id)
        index = self.model_box.findData(self.config.model)
        self.model_box.setCurrentIndex(index if index >= 0 else 0)
        self.model_box.currentIndexChanged.connect(self._model_changed)
        cl.addWidget(labelled_row(tr("Model"), self.model_box))
        self.remember = QCheckBox(tr("Remember the key on this computer (stored as plain text)"))
        self.remember.setChecked(self.config.remember_key)
        self.remember.toggled.connect(self._remember_toggled)
        cl.addWidget(self.remember)
        get_key = QPushButton(tr("Where do I get a key?"))
        get_key.setProperty("role", "link")
        get_key.clicked.connect(lambda: QDesktopServices.openUrl(CONSOLE_URL))
        cl.addWidget(get_key, 0, Qt.AlignLeft)
        cl.addWidget(muted_label(tr("Questions and the page you include are sent to Anthropic. "
                                 "Nothing leaves this computer until you press Ask.")))
        layout.addWidget(connection)

        send = QShortcut(QKeySequence("Ctrl+Return"), self.question)
        send.activated.connect(self.ask)
        self._refresh_state()

    # ------------------------------------------------------------------ api
    def set_page(self, route: str, context: str) -> None:
        """Tell the panel which page the learner is on, and what its text is."""
        self.route = route
        self._context = context
        title = route_title(self.ctx, route) if route else ""
        self.page_label.setText(f"About: {title}" if title else "")
        self._refresh_state()

    def reset_conversation(self) -> None:
        self.conversation.clear()
        self.view.set_markdown_content(INTRO)
        self.status.setText("")

    def ask(self) -> None:
        question = self.question.toPlainText().strip()
        if not question:
            return
        if not self.config.configured:
            self.status.setText(tr("Add an API key below to switch the tutor on."))
            return
        first = not self.conversation.messages
        self.conversation.add("user", question)
        self.question.clear()
        self._render()
        self.status.setText(tr("Thinking…"))
        self.ask_button.setEnabled(False)
        context = self._context if (first and self.include_context.isChecked()) else ""
        if self.synchronous:
            try:
                self._answered(tutor.ask(self.conversation, self.config, context, self.transport))
            except tutor.TutorError as exc:
                self._failed(str(exc))
            return
        self._worker = _AskWorker(self.conversation, self.config, context, self.transport, self)
        self._worker.answered.connect(self._answered)
        self._worker.failed.connect(self._failed)
        self._worker.finished.connect(lambda: setattr(self, "_worker", None))
        self._worker.start()

    # -------------------------------------------------------------- private
    def _suggest(self, prompt: str) -> None:
        self.question.setPlainText(prompt)
        self.question.setFocus()
        cursor = self.question.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self.question.setTextCursor(cursor)

    def _answered(self, text: str) -> None:
        self.conversation.add("assistant", text)
        self.status.setText("")
        self.ask_button.setEnabled(True)
        self._render()

    def _failed(self, message: str) -> None:
        if self.conversation.messages and self.conversation.messages[-1].role == "user":
            # Put the question back in the box so it can be sent again unchanged.
            failed_question = self.conversation.messages.pop().text
            if not self.question.toPlainText().strip():
                self.question.setPlainText(failed_question)
        self.status.setText(message)
        self.ask_button.setEnabled(True)
        self._render()

    def _render(self) -> None:
        if not self.conversation.messages:
            self.view.set_markdown_content(INTRO)
            return
        parts = []
        for message in self.conversation.messages:
            who = "You" if message.role == "user" else "Tutor"
            parts.append(f"**{who}**\n\n{message.text}\n")
        self.view.set_markdown_content("\n---\n\n".join(parts))
        self.view.scroll_to_end()

    def _refresh_state(self) -> None:
        ready = self.config.configured
        self.ask_button.setEnabled(ready)
        self.ask_button.setToolTip(tr("Send the question") if ready else "Add an API key first")
        if not ready:
            self.status.setText(tr("The tutor is off: no API key yet."))
        elif self.status.text().startswith("The tutor is off"):
            self.status.setText("")

    def _key_changed(self, text: str) -> None:
        self.config.api_key = text
        self._save()
        self._refresh_state()

    def _model_changed(self, _index: int) -> None:
        self.config.model = self.model_box.currentData()
        self._save()

    def _remember_toggled(self, on: bool) -> None:
        self.config.remember_key = on
        self._save()

    def _context_toggled(self, on: bool) -> None:
        self.config.include_context = on
        self._save()

    def _save(self) -> None:
        try:
            self.config.save(self.config_path)
        except OSError as exc:
            self.status.setText(f"Could not save the tutor settings: {exc}")
