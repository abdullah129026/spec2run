"""Eval harness pure logic. The boot-and-smoke path is exercised by the
runner itself (docs/EVAL.md), not faked here."""

from types import SimpleNamespace

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


def test_load_fixtures_missing_dir_is_empty(tmp_path):
    assert eval_svc.load_fixtures(str(tmp_path / "nope")) == {}


def test_load_fixtures_reads_json_only(tmp_path):
    (tmp_path / "a.json").write_text('{"openapi": "3.0.0"}')
    (tmp_path / "b.json").write_text('{"openapi": "3.0.0"}')
    (tmp_path / "notes.txt").write_text("not a fixture")
    assert list(eval_svc.load_fixtures(str(tmp_path))) == ["a", "b"]


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


def test_spec_match_needs_clarification_short_circuits():
    """A prompt that asked for clarification has nothing to match against:
    missing entities and auth are not problems."""
    rendered = {"entities": [], "auth": False}
    assert eval_svc.spec_match_problems(
        {}, rendered,
        {"entities": ["orders"], "auth": True,
         "needs_clarification": True}) == []


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


def test_run_eval_skips_without_fixtures_or_llm(tmp_path):
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        '{"id": "a", "prompt": "p"}\n{"id": "b", "prompt": "p"}\n')
    result = eval_svc.run_eval(str(corpus))
    assert result["mode"] == "fixtures"
    assert result["total"] == 2
    assert result["passed"] == 0
    assert result["failed"] == 0
    assert result["skipped"] == 2
    assert all(i["result"] == "skipped" for i in result["items"])


def test_run_eval_honours_only_filter(tmp_path):
    corpus = tmp_path / "c.jsonl"
    corpus.write_text(
        '{"id": "a", "prompt": "p"}\n{"id": "b", "prompt": "p"}\n')
    result = eval_svc.run_eval(str(corpus), only=["b"])
    assert result["total"] == 1
    assert result["items"][0]["id"] == "b"


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


def test_smoke_test_records_failure_not_crash_on_auth_spec_with_no_entities(monkeypatch):
    """An auth spec with no schemas has no entities to protect: the 401
    probe must record a failure, not crash on entities[0] and kill the
    whole eval run."""
    from app.services.codegen import render_service

    spec = {
        "openapi": "3.0.0",
        "info": {"title": "Health only", "version": "1.0.0"},
        "paths": {
            "/health": {"get": {"responses": {"200": {"description": "ok"}}}},
        },
        "components": {
            "securitySchemes": {"bearer": {"type": "http", "scheme": "bearer"}},
        },
    }
    monkeypatch.setattr(
        eval_svc.sandbox_svc, "proxy", _fake_proxy([{"id": 1}]))
    failures = eval_svc.smoke_test(None, spec, render_service(spec, {"auth": True}))
    assert failures
    assert any("no entities" in f for f in failures)


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


def test_write_report_fixtures_mode_lists_skipped(tmp_path):
    """Fixtures mode must say the LLM stage was not measured and name
    the skipped prompts, or the report reads as a full run."""
    out = tmp_path / "EVAL.md"
    eval_svc.write_report({
        "ran_at": "2026-10-12", "mode": "fixtures", "total": 2,
        "passed": 0, "failed": 0, "skipped": 2, "spec_match_issues": 0,
        "items": [
            {"id": "a", "result": "skipped", "stages": {},
             "spec_match": [], "failures": ["no fixture; needs key"], "ms": 0},
            {"id": "b", "result": "skipped", "stages": {},
             "spec_match": [], "failures": ["no fixture; needs key"], "ms": 0},
        ],
    }, str(out))
    text = out.read_text()
    assert "LLM generation stage was not measured" in text
    assert "## Not measured" in text
    assert "`a`" in text and "`b`" in text
    assert "None. Every measured prompt" in text


def _entry(pid="x"):
    return {"id": pid, "prompt": "build a bookstore", "expect": {}}


def _valid_spec():
    return {"openapi": "3.0.0",
            "info": {"title": "T", "version": "1"},
            "paths": {"/health": {"get": {"responses": {"200": {"description": "ok"}}}}}}


def _fake_rendered(monkeypatch):
    """Skip validate/render so the test exercises the stage after them."""
    monkeypatch.setattr(eval_svc, "validate_openapi", lambda spec: [])
    monkeypatch.setattr(
        eval_svc, "render_service",
        lambda spec, opts: {"files": {"app.py": "x"}, "entities": [],
                            "auth": False})


def test_run_one_validate_failure():
    # A fixture that fails structural validation is a measured failure, not
    # a crash: the stage is named and the run can continue to the next item.
    item = eval_svc._run_one(_entry(), {"openapi": "3.0.0"}, None, "auto")
    assert item["result"] == "failed"
    assert item["stages"]["validate"] == "failed"
    assert any(f.startswith("validate:") for f in item["failures"])


def test_run_one_render_failure(monkeypatch):
    monkeypatch.setattr(eval_svc, "validate_openapi", lambda spec: [])

    def _boom(spec, opts):
        raise ValueError("bad template")

    monkeypatch.setattr(eval_svc, "render_service", _boom)
    item = eval_svc._run_one(_entry(), _valid_spec(), None, "auto")
    assert item["result"] == "failed"
    assert item["stages"]["render"] == "failed"
    assert any(f.startswith("render:") for f in item["failures"])


def test_run_one_boot_failure(monkeypatch):
    _fake_rendered(monkeypatch)

    def _boom(files, database="auto"):
        raise eval_svc.sandbox_svc.SandboxError("no docker")

    monkeypatch.setattr(eval_svc.sandbox_svc, "boot", _boom)
    item = eval_svc._run_one(_entry(), _valid_spec(), None, "auto")
    assert item["result"] == "failed"
    assert item["stages"]["boot"] == "failed"
    assert any(f.startswith("boot:") for f in item["failures"])


def test_run_one_smoke_failure(monkeypatch):
    _fake_rendered(monkeypatch)
    monkeypatch.setattr(
        eval_svc.sandbox_svc, "boot",
        lambda files, database="auto": SimpleNamespace(id="0" * 32))
    monkeypatch.setattr(eval_svc.sandbox_svc, "kill", lambda sid: True)
    monkeypatch.setattr(
        eval_svc, "smoke_test",
        lambda sb, spec, rendered: ["GET /books: 500"])
    item = eval_svc._run_one(_entry(), _valid_spec(), None, "auto")
    assert item["result"] == "failed"
    assert item["stages"]["smoke"] == "failed"
    assert item["failures"] == ["smoke: GET /books: 500"]


def test_run_one_passes_when_every_stage_ok(monkeypatch):
    _fake_rendered(monkeypatch)
    monkeypatch.setattr(
        eval_svc.sandbox_svc, "boot",
        lambda files, database="auto": SimpleNamespace(id="0" * 32))
    killed = []
    monkeypatch.setattr(eval_svc.sandbox_svc, "kill",
                        lambda sid: killed.append(sid))
    monkeypatch.setattr(eval_svc, "smoke_test",
                        lambda sb, spec, rendered: [])
    item = eval_svc._run_one(_entry(), _valid_spec(), None, "auto")
    assert item["result"] == "passed"
    assert item["stages"] == {"spec": "ok", "validate": "ok", "render": "ok",
                              "boot": "ok", "smoke": "ok"}
    assert item["spec_match"] == []
    assert killed == ["0" * 32]  # the sandbox is always torn down


def test_main_returns_one_when_prompts_failed(monkeypatch):
    calls = {}

    def _fake_run(corpus, fixtures, only=None, database="auto"):
        calls["only"] = only
        return {"passed": 0, "failed": 1, "skipped": 0}

    monkeypatch.setattr(eval_svc, "run_eval", _fake_run)
    monkeypatch.setattr(eval_svc, "write_report",
                        lambda result, path: calls.setdefault("report", path))
    assert eval_svc.main(["--corpus", "c.jsonl", "--fixtures", "fx",
                          "--out", "out.md", "--only", "a, b"]) == 1
    assert calls["only"] == ["a", "b"]
    assert calls["report"] == "out.md"


def test_main_returns_zero_when_nothing_failed(monkeypatch):
    monkeypatch.setattr(
        eval_svc, "run_eval",
        lambda corpus, fixtures, only=None, database="auto": {
            "passed": 2, "failed": 0, "skipped": 0})
    monkeypatch.setattr(eval_svc, "write_report", lambda result, path: None)
    assert eval_svc.main(["--corpus", "c.jsonl"]) == 0
