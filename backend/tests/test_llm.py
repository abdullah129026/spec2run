import importlib

import pytest

from app.services import llm


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
