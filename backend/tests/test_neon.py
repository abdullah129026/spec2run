"""Neon branch lifecycle, with the HTTP layer faked."""
import pytest

from app.services import neon


class FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


def _fake_request(calls, response):
    def fake(method, url, **kwargs):
        calls.append((method, url, kwargs))
        return response

    return fake


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("NEON_API_KEY", "test-key")
    monkeypatch.setenv("NEON_PROJECT_ID", "proj-123")
    assert neon.configured()


def _branch_payload(uri="postgres://u:p@ep-1.aws.neon.tech/db?sslmode=require"):
    return {
        "branch": {"id": "br-test-1"},
        "connection_uris": [{"connection_uri": uri, "is_pooled": False}],
    }


def test_create_branch_posts_and_rewrites_uri(monkeypatch, env):
    calls = []
    monkeypatch.setattr(
        neon.httpx, "request",
        _fake_request(calls, FakeResponse(201, _branch_payload())),
    )
    out = neon.create_branch("spec2run-abc")
    method, url, kwargs = calls[0]
    assert method == "POST" and url.endswith("/projects/proj-123/branches")
    assert kwargs["headers"]["Authorization"] == "Bearer test-key"
    assert "test-key" not in url
    assert kwargs["json"]["branch"]["name"] == "spec2run-abc"
    assert kwargs["json"]["endpoints"] == [{"type": "read_write"}]
    assert out["branch_id"] == "br-test-1"
    assert out["database_url"].startswith("postgresql+psycopg://u:p@")


def test_create_branch_prefers_direct_over_pooled(monkeypatch, env):
    payload = {
        "branch": {"id": "br-2"},
        "connection_uris": [
            {"connection_uri": "postgres://pooled/x", "is_pooled": True},
            {"connection_uri": "postgres://direct/x", "is_pooled": False},
        ],
    }
    monkeypatch.setattr(
        neon.httpx, "request", _fake_request([], FakeResponse(201, payload))
    )
    out = neon.create_branch("b")
    assert "direct" in out["database_url"]


def test_create_branch_http_error(monkeypatch, env):
    monkeypatch.setattr(
        neon.httpx, "request", _fake_request([], FakeResponse(401))
    )
    with pytest.raises(neon.NeonError, match="HTTP 401"):
        neon.create_branch("b")


def test_create_branch_no_uri_cleans_up(monkeypatch, env):
    calls = []
    payload = {"branch": {"id": "br-3"}, "connection_uris": []}
    monkeypatch.setattr(
        neon.httpx, "request", _fake_request(calls, FakeResponse(201, payload))
    )
    with pytest.raises(neon.NeonError, match="no connection URI"):
        neon.create_branch("b")
    assert calls[1][0] == "DELETE" and calls[1][1].endswith("/branches/br-3")


def test_delete_branch_ok_and_404(monkeypatch, env):
    calls = []
    monkeypatch.setattr(
        neon.httpx, "request", _fake_request(calls, FakeResponse(200))
    )
    neon.delete_branch("br-1")
    assert calls[0][1].endswith("/branches/br-1")
    monkeypatch.setattr(
        neon.httpx, "request", _fake_request([], FakeResponse(404))
    )
    neon.delete_branch("br-gone")  # already gone is not an error


def test_delete_branch_500_raises(monkeypatch, env):
    monkeypatch.setattr(
        neon.httpx, "request", _fake_request([], FakeResponse(500))
    )
    with pytest.raises(neon.NeonError):
        neon.delete_branch("br-1")


def test_unconfigured_without_keys(monkeypatch):
    monkeypatch.delenv("NEON_API_KEY", raising=False)
    monkeypatch.delenv("NEON_PROJECT_ID", raising=False)
    assert not neon.configured()
