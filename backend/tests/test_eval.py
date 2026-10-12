"""Eval harness pure logic. The boot-and-smoke path is exercised by the
runner itself (docs/EVAL.md), not faked here."""

import pytest

from app.services import eval as eval_svc
from tests.test_slots import BOOKSTORE


def test_load_corpus(tmp_path):
    p = tmp_path / "c.jsonl"
    p.write_text('{"id": "a"}\n\nnot json\n')
    with pytest.raises(ValueError, match="bad JSON"):
        eval_svc.load_corpus(str(p))
    p.write_text('{"id": "a"}\n{"id": "b"}\n')
    assert [i["id"] for i in eval_svc.load_corpus(str(p))] == ["a", "b"]


def test_spec_match_ok():
    rendered = {"entities": [{"plural": "books"}], "auth": True}
    assert eval_svc.spec_match_problems(
        {}, rendered, {"entities": ["books"], "auth": True}) == []


def test_spec_match_flags_missing_entity_and_auth():
    rendered = {"entities": [{"plural": "books"}], "auth": False}
    problems = eval_svc.spec_match_problems(
        {}, rendered, {"entities": ["books", "orders"], "auth": True})
    assert any("orders" in p for p in problems)
    assert any("auth mismatch" in p for p in problems)


def test_order_by_fk_parents_first():
    child = {"plural": "items",
             "fields": [{"name": "list_id", "fk": "lists"}]}
    parent = {"plural": "lists", "fields": [{"name": "title", "fk": None}]}
    ordered = eval_svc._order_by_fk([child, parent])
    assert [e["plural"] for e in ordered] == ["lists", "items"]


def test_sample_values():
    assert eval_svc._sample_value({"type": "string"}) == "smoke"
    assert eval_svc._sample_value({"type": "integer"}) == 1
    assert eval_svc._sample_value(
        {"type": "string", "format": "date-time"}) == "2026-01-01T00:00:00Z"


def test_run_one_skipped_without_fixture_or_llm():
    item = eval_svc._run_one(
        {"id": "x", "prompt": "p", "expect": {}}, None, None, "auto")
    assert item["result"] == "skipped"
    assert "GROQ" in item["failures"][0]


def test_run_one_rejects_bad_spec():
    item = eval_svc._run_one(
        {"id": "x", "prompt": "p", "expect": {}},
        {"nope": True}, None, "auto")
    assert item["result"] == "failed"
    assert item["stages"]["spec"] == "failed"


def test_run_one_rejects_invalid_openapi():
    bad = dict(BOOKSTORE, paths={})
    item = eval_svc._run_one(
        {"id": "x", "prompt": "p", "expect": {}}, bad, None, "auto")
    assert item["result"] == "failed"
    assert item["stages"]["validate"] == "failed"


def test_write_report(tmp_path):
    out = tmp_path / "EVAL.md"
    eval_svc.write_report({
        "ran_at": "2026-10-12", "mode": "fixtures", "total": 2,
        "passed": 1, "failed": 1, "skipped": 0, "spec_match_issues": 0,
        "items": [
            {"id": "a", "result": "passed", "stages": {"smoke": "ok"},
             "spec_match": [], "failures": [], "ms": 5},
            {"id": "b", "result": "failed", "stages": {"boot": "failed"},
             "spec_match": [], "failures": ["boot: nope"], "ms": 5},
        ],
    }, str(out))
    text = out.read_text()
    assert "| a | passed" in text and "| b | failed" in text
    assert "### b" in text and "boot: nope" in text
