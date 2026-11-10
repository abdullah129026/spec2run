"""Sandbox lifecycle. The boot machinery runs for real (a real uvicorn
subprocess on loopback); only the pip-install step is faked, because the
test service is a stdlib-only ASGI app and the venv already has uvicorn.
"""
import hashlib
import os
import subprocess
import sys

import pytest

from app.services import sandbox

TINY_APP = '''
async def app(scope, receive, send):
    assert scope["type"] == "http"
    body = b'{"status": "ok"}'
    await send({"type": "http.response.start", "status": 200,
                "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": body})
'''


@pytest.fixture
def fast_boot(monkeypatch, tmp_path):
    monkeypatch.setattr(sandbox, "_venv_python", lambda req: sys.executable)
    monkeypatch.setenv("SANDBOX_DIR", str(tmp_path / "boxes"))
    yield
    for sb in list(sandbox.REGISTRY.values()):
        sandbox.kill(sb.id)


def test_get_rejects_malformed_ids():
    assert sandbox.get("") is None
    assert sandbox.get("nope") is None
    assert sandbox.get("../../etc/passwd") is None
    assert sandbox.get("a" * 31) is None


def test_kill_unknown_returns_false():
    assert sandbox.kill("0" * 32) is False


def test_child_env_scrubs_secrets(monkeypatch):
    monkeypatch.setenv("SPEC2RUN_GROQ_API_KEY", "shh")
    monkeypatch.setenv("MY_TOKEN", "shh")
    monkeypatch.setenv("DB_PASSWORD", "shh")
    monkeypatch.setenv("SAFE_THING", "keep")
    env = sandbox._child_env("sqlite:///x")
    assert "SPEC2RUN_GROQ_API_KEY" not in env
    assert "MY_TOKEN" not in env
    assert "DB_PASSWORD" not in env
    assert env["SAFE_THING"] == "keep"
    assert env["DATABASE_URL"] == "sqlite:///x"
    assert len(env["JWT_SECRET"]) == 64


def test_boot_rejects_bad_input(fast_boot):
    with pytest.raises(sandbox.SandboxError, match="no app.py"):
        sandbox.boot({"requirements.txt": ""})
    with pytest.raises(sandbox.SandboxError, match="unsafe path"):
        sandbox.boot({"app.py": "x", "../evil.py": "x"})
    with pytest.raises(sandbox.SandboxError, match="unknown database"):
        sandbox.boot({"app.py": "x"}, database="oracle")
    with pytest.raises(sandbox.SandboxError, match="NEON_API_KEY"):
        sandbox.boot({"app.py": "x"}, database="neon")


def test_boot_proxy_logs_kill_cycle(fast_boot):
    sb = sandbox.boot({"app.py": TINY_APP, "requirements.txt": ""})
    try:
        assert sandbox.get(sb.id) is sb
        info = sandbox.status(sb)
        assert info["state"] == "running"
        assert info["database"] == "sqlite"  # no Neon keys in test env
        r = sandbox.proxy(sb, "GET", "health", "", {}, b"")
        assert r.status_code == 200 and r.json() == {"status": "ok"}
        assert any("started" in line.lower() or "uvicorn" in line.lower()
                   for line in sandbox.log_tail(sb, 50))
    finally:
        assert sandbox.kill(sb.id) is True
    assert sandbox.get(sb.id) is None


def test_pool_evicts_oldest(fast_boot, monkeypatch):
    monkeypatch.setattr(sandbox, "MAX_SANDBOXES", 1)
    first = sandbox.boot({"app.py": TINY_APP, "requirements.txt": ""})
    second = sandbox.boot({"app.py": TINY_APP, "requirements.txt": ""})
    assert sandbox.get(first.id) is None  # evicted
    assert sandbox.get(second.id) is second


def _fake_subprocess_run(monkeypatch, pip_returncode=0, pip_stderr=""):
    """Fake subprocess.run: venv creation materializes a bin/python, pip
    install answers with the given return code."""
    calls = []

    def _run(cmd, **kwargs):
        calls.append(cmd)
        if "-m" in cmd and "venv" in cmd:
            bin_dir = os.path.join(cmd[-1], "bin")
            os.makedirs(bin_dir, exist_ok=True)
            open(os.path.join(bin_dir, "python"), "w").close()
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        return subprocess.CompletedProcess(cmd, pip_returncode,
                                           stdout="", stderr=pip_stderr)

    monkeypatch.setattr(sandbox.subprocess, "run", _run)
    return calls


def test_venv_python_reuses_matching_venv(monkeypatch, tmp_path):
    # Same requirements as the recorded hash: no venv rebuild, no pip run.
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("")
    want = hashlib.sha256(b"uvicorn==1.0").hexdigest()
    (venv / ".spec2run-req-sha").write_text(want)
    monkeypatch.setenv("SANDBOX_VENV", str(venv))
    calls = _fake_subprocess_run(monkeypatch)
    assert sandbox._venv_python("uvicorn==1.0") == str(venv / "bin" / "python")
    assert calls == []


def test_venv_python_rebuilds_on_stale_sha(monkeypatch, tmp_path):
    venv = tmp_path / "venv"
    (venv / "bin").mkdir(parents=True)
    (venv / "bin" / "python").write_text("")
    (venv / ".spec2run-req-sha").write_text("stale")
    monkeypatch.setenv("SANDBOX_VENV", str(venv))
    calls = _fake_subprocess_run(monkeypatch)
    assert sandbox._venv_python("uvicorn==2.0") == str(venv / "bin" / "python")
    assert (venv / ".spec2run-req-sha").read_text() == hashlib.sha256(
        b"uvicorn==2.0").hexdigest()
    assert any(cmd[:3] == [sys.executable, "-m", "venv"] for cmd in calls)
    assert any("pip" in cmd for cmd in calls)


def test_venv_python_pip_failure_raises_and_cleans_up(monkeypatch, tmp_path):
    # A venv whose dependencies cannot install must not linger half-built:
    # the next boot starts from a clean slate instead of a broken venv.
    venv = tmp_path / "venv"
    monkeypatch.setenv("SANDBOX_VENV", str(venv))
    _fake_subprocess_run(monkeypatch, pip_returncode=1,
                         pip_stderr="ERROR: could not find a version\n"
                         "  for badpkg==9.9.9\n")
    with pytest.raises(sandbox.SandboxError, match="could not install"):
        sandbox._venv_python("badpkg==9.9.9")
    assert not venv.exists()
