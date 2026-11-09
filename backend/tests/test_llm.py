import importlib
from types import SimpleNamespace

import pytest

from app.services import llm


def _fake_client(content, choices=None):
    """A Groq-shaped stub: create() returns one choice with `content`."""
    message = SimpleNamespace(content=content)
    if choices is None:
        choices = [SimpleNamespace(message=message)]
    resp = SimpleNamespace(choices=choices)
    completions = SimpleNamespace(create=lambda **kw: resp)
    return SimpleNamespace(chat=SimpleNamespace(completions=completions))


def test_missing_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("SPEC2RUN_GROQ_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SPEC2RUN_GROQ_API_KEY"):
        llm._client()


def test_model_default_is_gpt_oss(monkeypatch):
    monkeypatch.delenv("SPEC2RUN_MODEL", raising=False)
    reloaded = importlib.reload(llm)
    try:
        assert reloaded.MODEL == "openai/gpt-oss-120b"
    finally:
        importlib.reload(llm)  # restore for the rest of the suite


def test_model_env_override(monkeypatch):
    monkeypatch.setenv("SPEC2RUN_MODEL", "custom/model")
    reloaded = importlib.reload(llm)
    try:
        assert reloaded.MODEL == "custom/model"
    finally:
        importlib.reload(llm)


def test_complete_json_returns_parsed_object(monkeypatch):
    monkeypatch.setattr(llm, "_client", lambda: _fake_client('{"a": 1}'))
    assert llm.complete_json("sys", "user") == {"a": 1}


def test_complete_json_invalid_json_is_a_clear_value_error(monkeypatch):
    # A raw JSONDecodeError would reach the user as a parser message
    # ("Expecting value: line 1..."); the router maps ValueError to 422,
    # so say plainly that the model output was unusable.
    monkeypatch.setattr(llm, "_client", lambda: _fake_client("not json"))
    with pytest.raises(ValueError, match="model returned invalid JSON"):
        llm.complete_json("sys", "user")


def test_complete_json_empty_choices_is_a_clear_value_error(monkeypatch):
    # No choices at all used to raise IndexError, which no router handler
    # catches: a 500 for a model hiccup. Treat it like any broken draft.
    monkeypatch.setattr(llm, "_client", lambda: _fake_client(None, choices=[]))
    with pytest.raises(ValueError, match="model returned no completion"):
        llm.complete_json("sys", "user")
