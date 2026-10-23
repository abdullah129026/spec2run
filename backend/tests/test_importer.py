import httpx
import ipaddress
import json
import socket
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.routers import specs
from app.services import importer

client = TestClient(app)

GOOD = {
    "openapi": "3.0.0",
    "info": {"title": "Books", "version": "1.0.0"},
    "paths": {"/books": {"get": {"responses": {"200": {"description": "ok"}}}}},
    "components": {"schemas": {}},
}


def test_import_json_content():
    doc = importer.import_openapi(content=json.dumps(GOOD))
    assert doc["info"]["title"] == "Books"


def test_import_yaml_content():
    doc = importer.import_openapi(content="openapi: 3.0.0\ninfo:\n  title: Books\n  version: 1.0.0\npaths:\n  /books:\n    get:\n      responses:\n        '200':\n          description: ok\n")
    assert doc["openapi"] == "3.0.0"


def test_import_rejects_both_and_neither():
    with pytest.raises(ValueError, match="exactly one"):
        importer.import_openapi()
    with pytest.raises(ValueError, match="exactly one"):
        importer.import_openapi(url="http://example.com/x", content="{}")


def test_import_rejects_invalid_document():
    bad = dict(GOOD, info={"title": "", "version": "1"})
    with pytest.raises(ValueError, match="not usable OpenAPI"):
        importer.import_openapi(content=json.dumps(bad))


def test_import_rejects_garbage():
    with pytest.raises(ValueError, match="could not parse"):
        importer.import_openapi(content="{unclosed: [bracket")


def test_import_ssrf_guard_blocks_internal():
    for url in ("file:///etc/passwd", "http://169.254.169.254/latest",
                "http://localhost:8080/admin", "http://127.0.0.1/x"):
        with pytest.raises(ValueError, match="rejected"):
            importer.import_openapi(url=url)


def _fake_dns(monkeypatch):
    """This sandbox resolves example.com to a non-global IP; fake public DNS."""
    monkeypatch.setattr(
        socket,
        "getaddrinfo",
        lambda *a, **k: [(2, 1, 6, "", ("93.184.216.34", 0))],
    )


def test_import_url_fetch(monkeypatch):
    _fake_dns(monkeypatch)
    class FakeResp:
        status_code = 200
        headers = {}
        content = json.dumps(GOOD).encode()
        text = json.dumps(GOOD)

        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    doc = importer.import_openapi(url="https://example.com/swagger.json")
    assert doc["info"]["title"] == "Books"


def test_import_url_oversize(monkeypatch):
    _fake_dns(monkeypatch)
    class FakeResp:
        status_code = 200
        headers = {}
        content = b"x" * (importer.MAX_IMPORT_BYTES + 1)

        def raise_for_status(self):
            pass

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResp())
    with pytest.raises(ValueError, match="too large"):
        importer.import_openapi(url="https://example.com/big.json")


def _redirect_resp(location):
    class FakeResp:
        status_code = 302
        headers = {"location": location}
        content = b""
        text = ""

        def raise_for_status(self):
            pass

    return FakeResp()


def _fake_dns_loopback_aware(monkeypatch):
    """Fake public DNS, but IP literals still resolve to themselves."""
    def fake(host, *a, **k):
        try:
            addr = str(ipaddress.ip_address(host))
        except ValueError:
            addr = "93.184.216.34"
        return [(2, 1, 6, "", (addr, 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake)


def test_import_redirect_to_internal_blocked(monkeypatch):
    _fake_dns_loopback_aware(monkeypatch)
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        assert kwargs.get("follow_redirects") is False
        return _redirect_resp("http://127.0.0.1/admin")

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(ValueError, match="rejected"):
        importer.import_openapi(url="https://example.com/swagger.json")
    assert calls == ["https://example.com/swagger.json"]


def test_import_redirect_to_public_followed(monkeypatch):
    _fake_dns(monkeypatch)
    seen = []

    class Final:
        status_code = 200
        headers = {}
        content = json.dumps(GOOD).encode()
        text = json.dumps(GOOD)

        def raise_for_status(self):
            pass

    def fake_get(url, **kwargs):
        seen.append(url)
        if url == "https://example.com/swagger.json":
            return _redirect_resp("https://cdn.example.com/swagger.json")
        return Final()

    monkeypatch.setattr(httpx, "get", fake_get)
    doc = importer.import_openapi(url="https://example.com/swagger.json")
    assert doc["info"]["title"] == "Books"
    assert seen == ["https://example.com/swagger.json",
                    "https://cdn.example.com/swagger.json"]


def test_import_too_many_redirects(monkeypatch):
    _fake_dns(monkeypatch)

    def fake_get(url, **kwargs):
        return _redirect_resp("https://example.com/loop")

    monkeypatch.setattr(httpx, "get", fake_get)
    with pytest.raises(ValueError, match="too many redirects"):
        importer.import_openapi(url="https://example.com/swagger.json")


def test_router_import_success(monkeypatch):
    monkeypatch.setattr(specs, "import_openapi", lambda url=None, content=None: GOOD)
    r = client.post("/specs/import", json={"content": "{}"})
    assert r.status_code == 200
    assert r.json() == GOOD


def test_router_import_invalid_is_422(monkeypatch):
    def boom(url=None, content=None):
        raise ValueError("not usable")

    monkeypatch.setattr(specs, "import_openapi", boom)
    r = client.post("/specs/import", json={"content": "{}"})
    assert r.status_code == 422


def test_router_import_network_error_is_502(monkeypatch):
    def boom(url=None, content=None):
        raise httpx.ConnectError("no route")

    monkeypatch.setattr(specs, "import_openapi", boom)
    r = client.post("/specs/import", json={"url": "https://example.com/x"})
    assert r.status_code == 502
