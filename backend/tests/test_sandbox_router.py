"""Sandbox HTTP API, with the process layer faked (see test_sandbox.py
for the real boot machinery)."""
import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import sandbox as sandbox_svc
from app.services.sandbox import Sandbox
from tests.test_slots import BOOKSTORE

client = TestClient(app)


def _box(**kw):
    class Proc:
        def poll(self):
            return None  # still running

    kw.setdefault("id", "a" * 32)
    kw.setdefault("dir", "/tmp/x")
    kw.setdefault("port", 1)
    kw.setdefault("process", Proc())
    kw.setdefault("database", "sqlite")
    kw.setdefault("branch_id", None)
    kw.setdefault("expires_at", 0.0)
    return Sandbox(**kw)


def test_up_boots_rendered_files(monkeypatch):
    seen = {}

    def fake_boot(files, database="auto"):
        seen["files"] = files
        seen["database"] = database
        return _box()

    monkeypatch.setattr(sandbox_svc, "boot", fake_boot)
    r = client.post(
        "/sandbox/up", json={"spec": BOOKSTORE, "auth": True, "database": "sqlite"}
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["proxy_url"] == f"/sandbox/{'a' * 32}/proxy"
    assert body["database"] == "sqlite"
    assert "app.py" in seen["files"]  # rendered server-side, never trusted
    assert "bcrypt" in seen["files"]["app.py"]  # auth=true reached the template
    assert seen["database"] == "sqlite"


def test_up_rejects_bad_spec():
    r = client.post("/sandbox/up", json={"spec": {"openapi": "3.0.0"}})
    assert r.status_code == 422


def test_up_boot_failure_is_502(monkeypatch):
    def boom(files, database="auto"):
        raise sandbox_svc.SandboxError("service failed to boot: nope")

    monkeypatch.setattr(sandbox_svc, "boot", boom)
    r = client.post("/sandbox/up", json={"spec": BOOKSTORE})
    assert r.status_code == 502 and "nope" in r.json()["detail"]


def test_status_and_down(monkeypatch):
    box = _box()
    monkeypatch.setattr(sandbox_svc, "get", lambda sid: box if sid == box.id else None)
    assert client.get(f"/sandbox/{box.id}").status_code == 200
    assert client.get("/sandbox/" + "b" * 32).status_code == 404
    assert client.get("/sandbox/not-an-id").status_code == 404

    monkeypatch.setattr(sandbox_svc, "kill", lambda sid: sid == box.id)
    assert client.delete(f"/sandbox/{box.id}").status_code == 204
    assert client.delete("/sandbox/" + "b" * 32).status_code == 404


def test_logs(monkeypatch):
    box = _box()
    monkeypatch.setattr(sandbox_svc, "get", lambda sid: box)
    monkeypatch.setattr(
        sandbox_svc, "log_tail", lambda sb, n: ["l1", "l2"][:n]
    )
    r = client.get(f"/sandbox/{box.id}/logs", params={"tail": 1})
    assert r.json() == {"lines": ["l1"]}
    assert client.get(f"/sandbox/{box.id}/logs", params={"tail": 0}).status_code == 422


def test_proxy_forwards(monkeypatch):
    box = _box()
    monkeypatch.setattr(sandbox_svc, "get", lambda sid: box)
    seen = {}

    def fake_proxy(sb, method, path, query, headers, body):
        seen.update(method=method, path=path, query=query, body=body)
        return httpx.Response(201, json={"id": 1})

    monkeypatch.setattr(sandbox_svc, "proxy", fake_proxy)
    r = client.post(
        f"/sandbox/{box.id}/proxy/books?x=1", json={"title": "Dune"}
    )
    assert r.status_code == 201 and r.json() == {"id": 1}
    assert seen["method"] == "POST" and seen["path"] == "books"
    assert seen["query"] == "x=1" and b"Dune" in seen["body"]


def test_proxy_unknown_sandbox():
    assert client.get("/sandbox/" + "c" * 32 + "/proxy/health").status_code == 404
