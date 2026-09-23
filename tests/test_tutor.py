"""The optional tutor (E9): settings, request building and error handling — never the network."""

import json
import urllib.error

import pytest

from cosmos import tutor
from cosmos.content.loader import load_curriculum, load_glossary
from cosmos.gui.context import AppContext, AppSignals
from cosmos.gui.routes import page_context
from cosmos.progress import ProgressStore

REPLY = {"content": [{"type": "text", "text": "Because space itself expands."}]}


@pytest.fixture
def ctx(tmp_path):
    return AppContext(load_curriculum(), load_glossary(), ProgressStore(tmp_path / "p.json"), AppSignals())


def conversation(question="Why does redshift grow with distance?"):
    c = tutor.Conversation()
    c.add("user", question)
    return c


def test_config_keeps_the_key_out_of_the_file_unless_asked(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    path = tmp_path / "tutor.json"
    config = tutor.TutorConfig(api_key="sk-ant-secret", model="claude-opus-5")
    config.save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["api_key"] == ""
    assert tutor.TutorConfig.load(path).model == "claude-opus-5"
    assert tutor.TutorConfig.load(path).api_key == ""

    config.remember_key = True
    config.save(path)
    assert tutor.TutorConfig.load(path).api_key == "sk-ant-secret"


def test_environment_key_is_used_when_nothing_is_stored(tmp_path, monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-from-env")
    config = tutor.TutorConfig.load(tmp_path / "missing.json")
    assert config.api_key == "sk-ant-from-env" and config.configured


def test_payload_carries_the_page_only_when_allowed():
    config = tutor.TutorConfig(api_key="k")
    payload = tutor.build_payload(conversation(), config, "Lesson L2.2 — Cosmological redshift")
    assert payload["model"] == tutor.DEFAULT_MODEL
    assert "Cosmological redshift" in payload["system"]
    assert payload["messages"][0]["role"] == "user"

    payload = tutor.build_payload(conversation(), config, "")
    assert "Cosmological redshift" not in payload["system"]
    assert tutor.SYSTEM_PROMPT in payload["system"]


def test_long_pages_are_trimmed():
    trimmed = tutor.trim_context("word " * 5000, limit=100)
    assert len(trimmed) <= 106 and trimmed.endswith("[…]")


def test_ask_uses_the_injected_transport():
    sent = {}

    def transport(url, headers, payload):
        sent.update(url=url, headers=headers, payload=payload)
        return REPLY

    config = tutor.TutorConfig(api_key="sk-ant-test")
    text = tutor.ask(conversation(), config, "page text", transport)
    assert text == "Because space itself expands."
    assert sent["url"] == tutor.API_URL
    assert sent["headers"]["x-api-key"] == "sk-ant-test"
    assert sent["headers"]["anthropic-version"] == tutor.API_VERSION
    assert "page text" in sent["payload"]["system"]


def test_ask_refuses_without_a_key_or_a_question():
    with pytest.raises(tutor.TutorError, match="No API key"):
        tutor.ask(conversation(), tutor.TutorConfig())
    with pytest.raises(tutor.TutorError, match="Ask a question"):
        tutor.ask(tutor.Conversation(), tutor.TutorConfig(api_key="k"))


def test_empty_or_broken_answers_become_readable_errors():
    with pytest.raises(tutor.TutorError):
        tutor.answer_text({"content": []})
    with pytest.raises(tutor.TutorError):
        tutor.ask(conversation(), tutor.TutorConfig(api_key="k"), transport=lambda *a: {"content": []})


@pytest.mark.parametrize("code,expected", [(401, "key was refused"), (429, "rate limiting"), (500, "error")])
def test_http_errors_are_translated(monkeypatch, code, expected):
    import io

    def raise_http(request, timeout=0):
        raise urllib.error.HTTPError(tutor.API_URL, code, "boom", {},
                                     io.BytesIO(b'{"error": {"message": "boom"}}'))

    monkeypatch.setattr(tutor.urllib.request, "urlopen", raise_http)
    with pytest.raises(tutor.TutorError, match=expected):
        tutor.ask(conversation(), tutor.TutorConfig(api_key="k"))


def test_offline_is_explained(monkeypatch):
    def raise_url(request, timeout=0):
        raise urllib.error.URLError("no route to host")

    monkeypatch.setattr(tutor.urllib.request, "urlopen", raise_url)
    with pytest.raises(tutor.TutorError, match="Are you online"):
        tutor.ask(conversation(), tutor.TutorConfig(api_key="k"))


def test_page_context_describes_what_is_on_screen(ctx):
    lesson = page_context(ctx, "lesson:L2.2")
    assert lesson.startswith("Lesson L2.2")
    assert "[[" not in lesson and "{{figure" not in lesson    # app mark-up is stripped
    assert "$$" in lesson                                     # formulas are kept: the tutor can read them
    assert "Simulator S1" in page_context(ctx, "sim:S1")
    assert "Glossary term" in page_context(ctx, "glossary:redshift")
    assert "Progress" in page_context(ctx, "progress")
