import pytest

from app.services import specgen
from app.services.validate import validate_openapi
from tests.test_validate import valid_spec


@pytest.fixture()
def fake_llm(monkeypatch):
    calls = {}

    def fake(system: str, user: str) -> dict:
        calls["system"] = system
        calls["user"] = user
        return calls["draft"]

    monkeypatch.setattr(specgen.llm, "complete_json", fake)
    return calls


def test_happy_path_returns_normalized_spec(fake_llm):
    draft = valid_spec()
    draft["extra_key"] = "dropped"
    fake_llm["draft"] = draft
    out = specgen.prompt_to_spec("A todo API with lists and items", {"auth": True})
    assert "extra_key" not in out
    assert validate_openapi(out) == []
    assert "auth=True" in fake_llm["user"]


def test_clarification_shape_passes_through(fake_llm):
    fake_llm["draft"] = {
        "needs_clarification": True,
        "questions": ["What should the API manage?", "Who uses it?"],
    }
    out = specgen.prompt_to_spec("Make me an API for my shop")
    assert out == {
        "needs_clarification": True,
        "questions": ["What should the API manage?", "Who uses it?"],
    }


def test_too_many_questions_trimmed(fake_llm):
    fake_llm["draft"] = {
        "needs_clarification": True,
        "questions": ["q1", "q2", "q3", "q4", "q5", "q6"],
    }
    out = specgen.prompt_to_spec("vague")
    assert len(out["questions"]) == 4


def test_invalid_draft_raises_not_guesses(fake_llm):
    fake_llm["draft"] = {"openapi": "3.0.0", "info": {"title": "x", "version": "1"}}
    with pytest.raises(ValueError, match="invalid OpenAPI"):
        specgen.prompt_to_spec("A todo API")


def test_unknown_options_are_ignored(fake_llm):
    fake_llm["draft"] = valid_spec()
    specgen.prompt_to_spec("A todo API", {"auth": False, "hacker": "rm -rf /"})
    assert "hacker" not in fake_llm["user"]
