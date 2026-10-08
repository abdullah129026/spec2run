import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import specs

client = TestClient(app)


def test_generate_returns_spec(monkeypatch):
    spec = {"openapi": "3.0.0", "info": {"title": "x", "version": "1"}}
    monkeypatch.setattr(specs, "prompt_to_spec", lambda p, o: spec)
    r = client.post("/specs/generate", json={"prompt": "A todo API"})
    assert r.status_code == 200
    assert r.json() == spec


def test_generate_passes_options(monkeypatch):
    seen = {}
    monkeypatch.setattr(specs, "prompt_to_spec", lambda p, o: seen.update({"p": p, "o": o}) or {})
    client.post("/specs/generate", json={"prompt": "x", "auth": True})
    assert seen == {"p": "x", "o": {"auth": True, "database": "postgres", "language": "python"}}


def test_generate_returns_clarification_payload(monkeypatch):
    payload = {"needs_clarification": True, "questions": ["What should it manage?"]}
    monkeypatch.setattr(specs, "prompt_to_spec", lambda p, o: payload)
    r = client.post("/specs/generate", json={"prompt": "Make me an API"})
    assert r.status_code == 200
    assert r.json() == payload


def test_generate_rejects_oversize_prompt():
    r = client.post("/specs/generate", json={"prompt": "x" * 4001})
    assert r.status_code == 422


def test_generate_missing_key_is_503(monkeypatch):
    def boom(prompt, options):
        raise RuntimeError("SPEC2RUN_GROQ_API_KEY is not set")

    monkeypatch.setattr(specs, "prompt_to_spec", boom)
    r = client.post("/specs/generate", json={"prompt": "x"})
    assert r.status_code == 503


def test_generate_invalid_draft_is_422(monkeypatch):
    def boom(prompt, options):
        raise ValueError("model produced invalid OpenAPI: bad")

    monkeypatch.setattr(specs, "prompt_to_spec", boom)
    r = client.post("/specs/generate", json={"prompt": "x"})
    assert r.status_code == 422


def test_refine_appends_answers(monkeypatch):
    seen = {}
    monkeypatch.setattr(specs, "prompt_to_spec", lambda p, o: seen.update({"p": p}) or {})
    client.post(
        "/specs/refine",
        json={
            "prompt": "Make me an API for my shop",
            "questions": ["What should it manage?"],
            "answers": ["book inventory"],
        },
    )
    assert "book inventory" in seen["p"]
