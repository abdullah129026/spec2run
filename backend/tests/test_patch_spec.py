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


def test_patch_returns_normalized_spec(fake_llm):
    existing = valid_spec()
    draft = valid_spec()
    draft["info"]["title"] = "Todo API v2"
    draft["extra_key"] = "dropped"
    fake_llm["draft"] = draft
    out = specgen.patch_spec(
        existing, "Rename the API to Todo API v2", {"auth": True}
    )
    assert "extra_key" not in out
    assert out["info"]["title"] == "Todo API v2"
    assert validate_openapi(out) == []
    assert "Current spec:" in fake_llm["user"]
    assert "auth=True" in fake_llm["user"]


def test_patch_clarification_passes_through(fake_llm):
    fake_llm["draft"] = {
        "needs_clarification": True,
        "questions": ["q1", "q2", "q3", "q4", "q5"],
    }
    out = specgen.patch_spec(valid_spec(), "make it nicer")
    assert out == {
        "needs_clarification": True,
        "questions": ["q1", "q2", "q3", "q4"],
    }


def test_patch_invalid_edit_raises_not_guesses(fake_llm):
    fake_llm["draft"] = {"openapi": "3.0.0", "info": {"title": "x", "version": "1"}}
    with pytest.raises(ValueError, match="invalid OpenAPI"):
        specgen.patch_spec(valid_spec(), "delete everything")


def test_patch_unknown_options_are_ignored(fake_llm):
    fake_llm["draft"] = valid_spec()
    specgen.patch_spec(valid_spec(), "nothing", {"auth": False, "hacker": "rm -rf /"})
    assert "hacker" not in fake_llm["user"]
