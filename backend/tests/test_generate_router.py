import io
import zipfile

from fastapi.testclient import TestClient

from app.main import app
from app.routers import generate, specs
from tests.test_slots import BOOKSTORE

client = TestClient(app)

REVIEW_STORE = {
    **BOOKSTORE,
    "paths": {
        **BOOKSTORE["paths"],
        "/reviews": {"get": {"responses": {"200": {"description": "ok"}}}},
    },
    "components": {
        "schemas": {
            **BOOKSTORE["components"]["schemas"],
            "Review": {
                "type": "object",
                "required": ["text"],
                "properties": {
                    "id": {"type": "integer"},
                    "text": {"type": "string"},
                    "book_id": {"type": "integer"},
                },
            },
        }
    },
}


def test_zip_streams_real_archive():
    r = client.post("/generate/zip", json={"spec": BOOKSTORE})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert "bookstore" in r.headers["content-disposition"]
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert set(names) == {"app.py", "requirements.txt", "README.md", ".env.example"}


def test_zip_rejects_invalid_spec():
    r = client.post("/generate/zip", json={"spec": {"openapi": "3.0.0"}})
    assert r.status_code == 422


def test_diff_specs_and_files():
    r = client.post(
        "/generate/diff", json={"old_spec": BOOKSTORE, "new_spec": REVIEW_STORE}
    )
    assert r.status_code == 200
    body = r.json()
    paths = [c["path"] for c in body["spec_changes"]]
    assert "components.schemas.Review" in paths
    assert "app.py" in body["file_diffs"]
    assert "+class Review" in body["file_diffs"]["app.py"] or "Review" in body["file_diffs"]["app.py"]


def test_diff_with_edited_files_override():
    rendered = client.post("/generate/code", json={"spec": BOOKSTORE}).json()["files"]
    edited = dict(rendered)
    edited["app.py"] = rendered["app.py"] + "\n# edited in monaco\n"
    r = client.post(
        "/generate/diff",
        json={"old_spec": BOOKSTORE, "new_spec": BOOKSTORE, "new_files": edited},
    )
    body = r.json()
    assert body["spec_changes"] == []
    assert list(body["file_diffs"]) == ["app.py"]
    assert "+# edited in monaco" in body["file_diffs"]["app.py"]


def test_diff_rejects_invalid_old_spec():
    r = client.post(
        "/generate/diff",
        json={"old_spec": {"openapi": "3.0.0"}, "new_spec": BOOKSTORE},
    )
    assert r.status_code == 422


def test_patch_returns_updated_spec(monkeypatch):
    monkeypatch.setattr(specs, "patch_spec", lambda s, p, o: REVIEW_STORE)
    r = client.post(
        "/specs/patch", json={"spec": BOOKSTORE, "prompt": "add reviews to books"}
    )
    assert r.status_code == 200
    assert "Review" in r.json()["components"]["schemas"]


def test_patch_clarification_passes_through(monkeypatch):
    payload = {"needs_clarification": True, "questions": ["Reviews of what?"]}
    monkeypatch.setattr(specs, "patch_spec", lambda s, p, o: payload)
    r = client.post(
        "/specs/patch", json={"spec": BOOKSTORE, "prompt": "add reviews"}
    )
    assert r.status_code == 200
    assert r.json() == payload


def test_patch_rejects_invalid_existing_spec():
    r = client.post(
        "/specs/patch", json={"spec": {"openapi": "3.0.0"}, "prompt": "x"}
    )
    assert r.status_code == 422
    assert "existing spec" in r.json()["detail"]


def test_patch_missing_key_is_503(monkeypatch):
    def boom(spec, prompt, options):
        raise RuntimeError("SPEC2RUN_GROQ_API_KEY is not set")

    monkeypatch.setattr(specs, "patch_spec", boom)
    r = client.post("/specs/patch", json={"spec": BOOKSTORE, "prompt": "x"})
    assert r.status_code == 503


def _fake_gh(calls):
    def fake(token, method, path, payload=None):
        calls.append((token, method, path))
        if path == "/user":
            return {"login": "ada"}
        if method == "POST" and path == "/user/repos":
            return {"full_name": "ada/demo"}
        if "git/trees" in path:
            return {"sha": "treesha"}
        if "git/commits" in path:
            return {"sha": "commitsha"}
        if "git/refs" in path:
            return {"ref": "refs/heads/main"}
        raise AssertionError(f"unexpected {method} {path}")

    return fake


def test_github_push_creates_repo(monkeypatch):
    calls = []
    monkeypatch.setattr(generate, "_gh", _fake_gh(calls))
    r = client.post(
        "/generate/github",
        json={"spec": BOOKSTORE, "token": "ghp_fake", "repo": "demo"},
    )
    assert r.status_code == 200
    assert r.json() == {"repo": "ada/demo", "url": "https://github.com/ada/demo"}
    # the token is used for auth, never echoed back
    assert "ghp_fake" not in r.text
    assert all(t == "ghp_fake" for t, _, _ in calls)


def test_github_push_onto_existing_repo(monkeypatch):
    def fake(token, method, path, payload=None):
        if method == "POST" and path == "/user/repos":
            from fastapi import HTTPException

            raise HTTPException(status_code=502, detail="GitHub: name already exists.")
        if path == "/user":
            return {"login": "ada"}
        if path == "/repos/ada/demo":
            return {"default_branch": "main"}
        if "git/ref/heads/main" in path:
            return {"object": {"sha": "basesha"}}
        if "git/trees" in path:
            assert payload["base_tree"] == "basesha"
            return {"sha": "treesha"}
        if "git/commits" in path:
            assert payload["parents"] == ["basesha"]
            return {"sha": "commitsha"}
        if "git/refs" in path:
            return {"ref": "refs/heads/main"}
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(generate, "_gh", fake)
    r = client.post(
        "/generate/github",
        json={"spec": BOOKSTORE, "token": "ghp_fake", "repo": "demo"},
    )
    assert r.status_code == 200
    assert r.json()["repo"] == "ada/demo"


def test_github_push_rejects_bad_repo_name():
    r = client.post(
        "/generate/github",
        json={"spec": BOOKSTORE, "token": "ghp_fake", "repo": "evil name!"},
    )
    assert r.status_code == 422


def test_patch_engine_error_is_422(monkeypatch):
    def boom(spec, prompt, options):
        raise ValueError("could not apply that change")

    monkeypatch.setattr(specs, "patch_spec", boom)
    r = client.post(
        "/specs/patch", json={"spec": BOOKSTORE, "prompt": "add reviews to books"}
    )
    assert r.status_code == 422
    assert "could not apply" in r.json()["detail"]
