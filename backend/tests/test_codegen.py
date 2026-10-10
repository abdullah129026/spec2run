import subprocess
import sys
import textwrap

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import codegen
from tests.test_slots import BOOKSTORE

client = TestClient(app)

BOOT_CHECK = textwrap.dedent("""\
    import importlib.util
    spec = importlib.util.spec_from_file_location("genapp", "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from fastapi.testclient import TestClient
    c = TestClient(mod.app)

    assert c.get("/health").json() == {"status": "ok"}

    r = c.post("/books", json={"title": "Dune"})
    assert r.status_code == 201, r.text
    book = r.json()
    assert book["title"] == "Dune" and book["id"] == 1

    assert c.get("/books").json()[0]["title"] == "Dune"
    assert c.get(f"/books/{book['id']}").json()["title"] == "Dune"
    assert c.put(f"/books/{book['id']}", json={"title": "Dune 2"}).json()["title"] == "Dune 2"
    assert c.get("/books/999").status_code == 404
    assert c.delete(f"/books/{book['id']}").status_code == 204
    assert c.get("/books").json() == []
    print("boot ok")
""")

AUTH_CHECK = textwrap.dedent("""\
    import importlib.util
    spec = importlib.util.spec_from_file_location("genapp", "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    from fastapi.testclient import TestClient
    c = TestClient(mod.app)

    # register + login round-trip
    assert c.post("/auth/register", json={"username": "ada", "password": "s3cret"}).status_code == 201
    assert c.post("/auth/register", json={"username": "ada", "password": "s3cret"}).status_code == 400
    r = c.post("/auth/login", data={"username": "ada", "password": "s3cret"})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    bad = c.post("/auth/login", data={"username": "ada", "password": "wrong"})
    assert bad.status_code == 401
    headers = {"Authorization": f"Bearer {token}"}

    # protected routes reject anonymous callers, serve authed ones
    assert c.get("/books").status_code == 401
    assert c.get("/books", headers={"Authorization": "Bearer junk"}).status_code == 401
    r = c.post("/books", json={"title": "Dune"}, headers=headers)
    assert r.status_code == 201, r.text
    assert c.get("/books", headers=headers).json()[0]["title"] == "Dune"
    print("auth ok")
""")


def _boot(tmp_path, files: dict, check: str):
    for name, content in files.items():
        (tmp_path / name).write_text(content)
    (tmp_path / "check.py").write_text(check)
    proc = subprocess.run(
        [sys.executable, "check.py"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr[-3000:]
    assert "ok" in proc.stdout


def test_render_returns_all_files():
    out = codegen.render_service(BOOKSTORE)
    assert set(out["files"]) == {"app.py", "requirements.txt", "README.md", ".env.example"}
    assert out["auth"] is False
    assert [e["name"] for e in out["entities"]] == ["Book", "Author"]


def test_rendered_python_parses():
    out = codegen.render_service(BOOKSTORE)
    assert codegen.check_syntax(out["files"]) == []


def test_check_syntax_catches_broken():
    assert codegen.check_syntax({"app.py": "def broken(:\n"}) != []


def test_no_auth_has_no_auth_code():
    src = codegen.render_service(BOOKSTORE)["files"]["app.py"]
    assert "get_current_user" not in src
    assert "/auth/register" not in src
    assert "Depends(get_current_user)" not in src


def test_auth_render_has_working_auth_shape():
    out = codegen.render_service(BOOKSTORE, {"auth": True})
    src = out["files"]["app.py"]
    assert out["auth"] is True
    assert "/auth/register" in src and "/auth/login" in src
    assert "bcrypt.hashpw" in src and "hashed_password" in src
    assert "jwt.decode" in src and "Depends(get_current_user)" in src
    # no hardcoded secret: env or a random one per boot
    assert 'os.environ.get("JWT_SECRET") or secrets.token_hex(32)' in src
    assert codegen.check_syntax(out["files"]) == []


def test_generated_service_boots_and_serves_crud(tmp_path):
    out = codegen.render_service(BOOKSTORE)
    _boot(tmp_path, out["files"], BOOT_CHECK)


def test_generated_auth_flow_end_to_end(tmp_path):
    pytest.importorskip("jwt")
    pytest.importorskip("bcrypt")
    out = codegen.render_service(BOOKSTORE, {"auth": True})
    _boot(tmp_path, out["files"], AUTH_CHECK)


def test_endpoint_returns_files():
    r = client.post("/generate/code", json={"spec": BOOKSTORE})
    assert r.status_code == 200
    body = r.json()
    assert set(body["files"]) == {"app.py", "requirements.txt", "README.md", ".env.example"}
    assert body["auth"] is False


def test_endpoint_auth_option():
    r = client.post("/generate/code", json={"spec": BOOKSTORE, "auth": True})
    assert r.status_code == 200
    assert r.json()["auth"] is True
    assert "/auth/login" in r.json()["files"]["app.py"]


def test_endpoint_rejects_invalid_spec():
    r = client.post("/generate/code", json={"spec": {"openapi": "3.0.0"}})
    assert r.status_code == 422


def test_endpoint_rejects_bad_stack():
    r = client.post("/generate/code", json={"spec": BOOKSTORE, "stack": "express"})
    assert r.status_code == 422


def test_endpoint_rejects_bad_names():
    spec = dict(BOOKSTORE, components={"schemas": {"nope-bad": {"type": "object"}}})
    r = client.post("/generate/code", json={"spec": spec})
    assert r.status_code == 422
