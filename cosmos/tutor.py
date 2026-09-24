"""The optional "Ask the Tutor" assistant (E9).

Cosmos never talks to a network service on its own. A learner who wants a tutor
supplies their own API key; only then, and only when they press **Ask**, is a
question sent — together with the piece of the course they are looking at, if
they leave that box ticked.

Everything here is GUI independent and takes its transport as an argument, so
the tests never touch the network.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from collections.abc import Callable

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
DEFAULT_MODEL = "claude-sonnet-5"
MODELS = [
    ("claude-sonnet-5", "Claude Sonnet 5 — balanced (recommended)"),
    ("claude-opus-5", "Claude Opus 5 — most capable"),
    ("claude-haiku-4-5-20251001", "Claude Haiku 4.5 — fastest"),
]
MAX_CONTEXT_CHARS = 6000
TIMEOUT_S = 60

SYSTEM_PROMPT = (
    "You are the tutor inside Cosmos, a desktop course that teaches cosmology from the scales of the "
    "universe up to inflation and dark energy. You are helping one learner who is working through that "
    "course.\n"
    "- Answer in the language the learner writes in.\n"
    "- Be concrete and short: a few sentences, or a short list. Expand only when asked.\n"
    "- Prefer the physics the course already uses (ΛCDM, Planck 2018 parameters, the notation of the "
    "lesson quoted below).\n"
    "- Formulas in plain text or simple LaTeX; no images.\n"
    "- If the learner is wrong about something, say so kindly and explain why.\n"
    "- If you are not sure, say that instead of inventing numbers or references."
)

Transport = Callable[[str, dict, dict], dict]      # url, headers, payload -> decoded JSON


class TutorError(RuntimeError):
    """Something went wrong that the learner should read in plain words."""


@dataclass
class TutorConfig:
    api_key: str = ""
    model: str = DEFAULT_MODEL
    include_context: bool = True
    remember_key: bool = False
    max_tokens: int = 700

    @property
    def configured(self) -> bool:
        return bool(self.api_key.strip())

    @classmethod
    def load(cls, path: Path) -> TutorConfig:
        """Read the saved settings; a key in the environment always wins."""
        config = cls()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            for key, value in data.items():
                if key in cls.__dataclass_fields__:
                    setattr(config, key, value)
        except (OSError, ValueError, TypeError):
            pass
        env_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if env_key and not config.api_key:
            config.api_key = env_key
        return config

    def save(self, path: Path) -> None:
        """Write the settings, keeping the key out of the file unless asked to remember it."""
        data = asdict(self)
        if not self.remember_key:
            data["api_key"] = ""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")


@dataclass
class Message:
    role: str            # "user" or "assistant"
    text: str


@dataclass
class Conversation:
    """The running exchange; the page context is attached to the first question only."""

    messages: list[Message] = field(default_factory=list)

    def add(self, role: str, text: str) -> None:
        self.messages.append(Message(role, text))

    def clear(self) -> None:
        self.messages.clear()

    def payload_messages(self) -> list[dict]:
        return [{"role": m.role, "content": m.text} for m in self.messages]


def trim_context(text: str, limit: int = MAX_CONTEXT_CHARS) -> str:
    """Keep a page excerpt small enough to send."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[:limit] + " […]"


def build_payload(conversation: Conversation, config: TutorConfig, context: str = "") -> dict:
    system = SYSTEM_PROMPT
    if context:
        system += ("\n\nThe learner is looking at this part of the course. Use it as the ground truth "
                   "about what they have already seen:\n\n" + trim_context(context))
    return {
        "model": config.model,
        "max_tokens": int(config.max_tokens),
        "system": system,
        "messages": conversation.payload_messages(),
    }


def _http_transport(url: str, headers: dict, payload: dict) -> dict:
    request = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:                       # the API answered with an error
        detail = exc.read().decode("utf-8", "replace")[:500]
        try:
            message = json.loads(detail)["error"]["message"]
        except (ValueError, KeyError, TypeError):
            message = detail or exc.reason
        if exc.code in (401, 403):
            raise TutorError(f"The API key was refused ({exc.code}). Check the key and try again.") from exc
        if exc.code == 429:
            raise TutorError("The service is rate limiting this key. Wait a moment and ask again.") from exc
        raise TutorError(f"The service returned an error ({exc.code}): {message}") from exc
    except urllib.error.URLError as exc:
        raise TutorError(f"Could not reach the service: {exc.reason}. Are you online?") from exc
    except TimeoutError as exc:
        raise TutorError("The service took too long to answer.") from exc


def answer_text(response: dict) -> str:
    """Pull the text out of an Anthropic Messages response."""
    blocks = response.get("content") or []
    parts = [b.get("text", "") for b in blocks if isinstance(b, dict) and b.get("type", "text") == "text"]
    text = "\n".join(p for p in parts if p).strip()
    if not text:
        raise TutorError("The service sent an empty answer.")
    return text


def ask(conversation: Conversation, config: TutorConfig, context: str = "",
        transport: Transport | None = None) -> str:
    """Send the conversation and return the tutor's reply.

    ``transport`` is only replaced in tests; by default this makes one HTTPS
    request to the Anthropic Messages API with the learner's own key.
    """
    if not config.configured:
        raise TutorError("No API key yet. Paste one in the Tutor panel to switch the tutor on.")
    if not conversation.messages:
        raise TutorError("Ask a question first.")
    headers = {
        "content-type": "application/json",
        "x-api-key": config.api_key.strip(),
        "anthropic-version": API_VERSION,
    }
    payload = build_payload(conversation, config, context if config.include_context else "")
    response = (transport or _http_transport)(API_URL, headers, payload)
    return answer_text(response)
