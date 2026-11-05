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


class _FakeResp:
    def __init__(self, status, body=None, bad_json=False):
        self.status_code = status
        self._body = body
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("not json")
        return self._body


def _fake_proxy(list_body, bad_json=False):
    """Stand-in for sandbox_svc.proxy: a well-behaved generated service
    except for what GET /{plural} returns."""
    deleted = set()

    def proxy(sb, method, path, query, headers, body):
        if method == "GET" and path == "health":
            return _FakeResp(200, {})
        if method == "POST":
            return _FakeResp(201, {"id": 1})
        if method == "GET" and path in ("books", "authors"):
            return _FakeResp(200, list_body, bad_json=bad_json)
        if method == "GET" and path.endswith("/1"):
            return _FakeResp(404 if path in deleted else 200, {"id": 1})
        if method == "PUT":
            return _FakeResp(200, {"id": 1})
        if method == "DELETE":
            deleted.add(path)
            return _FakeResp(204, None)
        raise AssertionError(f"unexpected {method} {path}")

    return proxy


def _rendered_bookstore():
    from app.services.codegen import render_service

    return render_service(BOOKSTORE, {"auth": False})


def test_smoke_test_passes_on_list_body(monkeypatch):
    monkeypatch.setattr(
        eval_svc.sandbox_svc, "proxy", _fake_proxy([{"id": 1}]))
    assert eval_svc.smoke_test(None, BOOKSTORE, _rendered_bookstore()) == []


def test_smoke_test_records_failure_not_crash_on_dict_body(monkeypatch):
    """A generated service wrapping its list in an object ({"items": [...]})
    must fail the smoke test, not crash the whole eval run with
    AttributeError from row.get on a dict key."""
    monkeypatch.setattr(
        eval_svc.sandbox_svc, "proxy", _fake_proxy({"items": [{"id": 1}]}))
    failures = eval_svc.smoke_test(None, BOOKSTORE, _rendered_bookstore())
    assert failures
    assert any("missing the created row" in f for f in failures)


def test_smoke_test_records_failure_not_crash_on_non_json_body(monkeypatch):
    monkeypatch.setattr(
        eval_svc.sandbox_svc, "proxy", _fake_proxy(None, bad_json=True))
    failures = eval_svc.smoke_test(None, BOOKSTORE, _rendered_bookstore())
    assert failures
    assert any("missing the created row" in f for f in failures)


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
