"""Live sandbox: boot a generated service as a supervised subprocess.

Each sandbox gets its own database and a loopback-only port; HTTP reaches
it exclusively through this API's proxy routes, so nothing outside can
dial the child directly. Sandboxes die after SANDBOX_TTL_SECONDS
(default 3600); a sweeper thread reaps the expired ones, and the oldest
goes when the pool is full (SANDBOX_MAX, default 8).

This is process-level isolation, not a container: the child binds
127.0.0.1 and gets a scrubbed environment (no *KEY*/*TOKEN*/*SECRET* in
its env), but it runs as the same user. Right for demos and evals of our
own generated code; not a boundary for untrusted code.
"""

import hashlib
import os
import re
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass, field

import httpx

from app.services import neon


class SandboxError(RuntimeError):
    """Boot or proxy failure; the message is safe to show the caller."""


@dataclass
class Sandbox:
    id: str
    dir: str
    port: int
    process: subprocess.Popen
    database: str  # "neon" or "sqlite"
    branch_id: str | None  # Neon branch id; deleted on kill
    expires_at: float
    created_at: float = field(default_factory=time.time)


REGISTRY: dict[str, Sandbox] = {}
_lock = threading.Lock()
_sweeper_started = False

TTL_SECONDS = int(os.environ.get("SANDBOX_TTL_SECONDS", "3600"))
MAX_SANDBOXES = int(os.environ.get("SANDBOX_MAX", "8"))
BOOT_TIMEOUT = 30
MAX_PROXY_BYTES = 10 * 1024 * 1024
LOG_READ_BYTES = 1024 * 1024  # read at most the last 1 MB of child output

# env vars carrying these hints never cross into the child
_SECRET_HINTS = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
_HOP_HEADERS = {
    "host", "connection", "keep-alive", "proxy-connection",
    "transfer-encoding", "upgrade", "content-length", "content-encoding",
}

# Loopback traffic to the child must never go through an egress proxy
# (httpx honors proxy env vars by default; the child isn't reachable via one).
_loopback = httpx.Client(trust_env=False, timeout=30)


def _sandbox_root() -> str:
    root = os.environ.get(
        "SANDBOX_DIR", os.path.join(tempfile.gettempdir(), "spec2run-sandboxes")
    )
    os.makedirs(root, exist_ok=True)
    return root


def _venv_python(requirements: str) -> str:
    """Shared runtime venv for sandboxed services, rebuilt only when the
    rendered requirements change, so boots after the first skip pip."""
    venv_dir = os.environ.get(
        "SANDBOX_VENV",
        os.path.join(tempfile.gettempdir(), "spec2run-sandbox-venv"),
    )
    python = os.path.join(venv_dir, "bin", "python")
    want = hashlib.sha256(requirements.encode()).hexdigest()
    sha_file = os.path.join(venv_dir, ".spec2run-req-sha")
    if os.path.exists(python) and os.path.exists(sha_file):
        with open(sha_file) as f:
            if f.read().strip() == want:
                return python
    shutil.rmtree(venv_dir, ignore_errors=True)
    subprocess.run([sys.executable, "-m", "venv", venv_dir], check=True)
    req_path = os.path.join(tempfile.gettempdir(), f"spec2run-req-{want[:12]}.txt")
    with open(req_path, "w") as f:
        f.write(requirements)
    try:
        proc = subprocess.run(
            [python, "-m", "pip", "install", "-r", req_path],
            capture_output=True, text=True, timeout=600,
        )
    finally:
        os.path.exists(req_path) and os.unlink(req_path)
    if proc.returncode != 0:
        shutil.rmtree(venv_dir, ignore_errors=True)
        raise SandboxError(
            "could not install the service's dependencies: "
            + "\n".join(proc.stderr.splitlines()[-5:])
        )
    with open(sha_file, "w") as f:
        f.write(want)
    return python


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _child_env(database_url: str) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items()
        if not any(hint in k.upper() for hint in _SECRET_HINTS)
    }
    env.update(
        {
            "DATABASE_URL": database_url,
            "JWT_SECRET": secrets.token_hex(32),
            "PYTHONUNBUFFERED": "1",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
    )
    return env


def _log_path(box_dir: str) -> str:
    return os.path.join(box_dir, "sandbox.log")


def _read_tail(path: str, n: int) -> list[str]:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            f.seek(max(0, f.tell() - LOG_READ_BYTES))
            data = f.read()
    except OSError:
        return []
    return data.decode("utf-8", "replace").splitlines()[-n:]


def _wait_healthy(port: int, proc: subprocess.Popen) -> None:
    deadline = time.time() + BOOT_TIMEOUT
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        if proc.poll() is not None:
            raise SandboxError(
                f"service exited during boot (code {proc.returncode})"
            )
        try:
            if _loopback.get(url, timeout=1.5).status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(0.3)
    raise SandboxError("service did not answer /health within 30s")


def _start_sweeper() -> None:
    global _sweeper_started
    if _sweeper_started:
        return

    def sweep() -> None:
        while True:
            time.sleep(60)
            now = time.time()
            with _lock:
                expired = [
                    s.id for s in REGISTRY.values() if s.expires_at <= now
                ]
                for sid in expired:
                    _kill_locked(sid)

    threading.Thread(target=sweep, daemon=True, name="sandbox-sweeper").start()
    _sweeper_started = True


def _kill_locked(sandbox_id: str) -> bool:
    sb = REGISTRY.pop(sandbox_id, None)
    if sb is None:
        return False
    try:
        sb.process.terminate()
        sb.process.wait(timeout=5)
    except Exception:
        sb.process.kill()
    if sb.branch_id:
        try:
            neon.delete_branch(sb.branch_id)
        except neon.NeonError:
            pass  # orphaned branches are cheap; the sweeper retries on next kill
    shutil.rmtree(sb.dir, ignore_errors=True)
    return True


def boot(files: dict[str, str], database: str = "auto") -> Sandbox:
    """Write the rendered files to a temp dir and boot them under uvicorn.

    Returns the registered Sandbox. Raises SandboxError with the cause
    (and the child's last log lines) when the service won't start.
    """
    if "app.py" not in files:
        raise SandboxError("nothing to boot: rendered files have no app.py")
    for path in files:
        if path.startswith("/") or ".." in path.split("/"):
            raise SandboxError(f"unsafe path in rendered files: {path!r}")
    if database not in ("auto", "neon", "sqlite"):
        raise SandboxError(f"unknown database: {database!r}")
    if database == "neon" and not neon.configured():
        raise SandboxError("Neon requested but NEON_API_KEY/NEON_PROJECT_ID are unset")

    sid = uuid.uuid4().hex
    box_dir = os.path.join(_sandbox_root(), sid)
    os.makedirs(box_dir)
    for path, content in files.items():
        full = os.path.join(box_dir, path)
        parent = os.path.dirname(full)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(full, "w") as f:
            f.write(content)

    branch_id = None
    if database == "neon" or (database == "auto" and neon.configured()):
        try:
            branch = neon.create_branch(f"spec2run-{sid[:8]}")
        except neon.NeonError as e:
            shutil.rmtree(box_dir, ignore_errors=True)
            raise SandboxError(f"Neon branch failed: {e}")
        branch_id = branch["branch_id"]
        database_url = branch["database_url"]
        db_kind = "neon"
    else:
        database_url = f"sqlite:///{os.path.join(box_dir, 'sandbox.db')}"
        db_kind = "sqlite"

    try:
        python = _venv_python(files.get("requirements.txt", ""))
    except SandboxError:
        shutil.rmtree(box_dir, ignore_errors=True)
        if branch_id:
            try:
                neon.delete_branch(branch_id)
            except neon.NeonError:
                pass
        raise

    log = _log_path(box_dir)
    proc = None
    port = 0
    try:
        for _ in range(3):  # retry if something else grabbed our port first
            port = _free_port()
            with open(log, "a") as lf:
                proc = subprocess.Popen(
                    [python, "-m", "uvicorn", "app:app",
                     "--host", "127.0.0.1", "--port", str(port)],
                    cwd=box_dir,
                    env=_child_env(database_url),
                    stdout=lf,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.DEVNULL,
                )
            try:
                _wait_healthy(port, proc)
                break
            except SandboxError:
                proc.kill()
                proc.wait()
                proc = None
                tail = "\n".join(_read_tail(log, 20)).lower()
                if "address already in use" not in tail:
                    raise SandboxError(
                        "service failed to boot: " + " | ".join(_read_tail(log, 8))
                    )
        else:
            raise SandboxError("could not bind a free loopback port after 3 tries")
    except SandboxError:
        shutil.rmtree(box_dir, ignore_errors=True)
        if branch_id:
            try:
                neon.delete_branch(branch_id)
            except neon.NeonError:
                pass
        raise

    sb = Sandbox(
        id=sid,
        dir=box_dir,
        port=port,
        process=proc,
        database=db_kind,
        branch_id=branch_id,
        expires_at=time.time() + TTL_SECONDS,
    )
    with _lock:
        _start_sweeper()
        while len(REGISTRY) >= MAX_SANDBOXES:  # pool full: oldest goes
            oldest = min(REGISTRY.values(), key=lambda s: s.created_at)
            _kill_locked(oldest.id)
        REGISTRY[sid] = sb
    return sb


def get(sandbox_id: str) -> Sandbox | None:
    if not re.fullmatch(r"[0-9a-f]{32}", sandbox_id or ""):
        return None
    with _lock:
        return REGISTRY.get(sandbox_id)


def kill(sandbox_id: str) -> bool:
    """Stop the sandbox, delete its dir and its Neon branch. False if unknown."""
    with _lock:
        return _kill_locked(sandbox_id)


def status(sb: Sandbox) -> dict:
    return {
        "sandbox_id": sb.id,
        "state": "running" if sb.process.poll() is None else "exited",
        "database": sb.database,
        "expires_at": sb.expires_at,
        "uptime_s": round(time.time() - sb.created_at, 1),
    }


def log_tail(sb: Sandbox, n: int = 200) -> list[str]:
    return _read_tail(_log_path(sb.dir), max(1, min(n, 1000)))


def proxy(
    sb: Sandbox,
    method: str,
    path: str,
    query: str,
    headers: dict,
    body: bytes,
) -> httpx.Response:
    """Forward one HTTP call to the sandboxed service on loopback."""
    if sb.process.poll() is not None:
        raise SandboxError("sandboxed service has exited")
    url = f"http://127.0.0.1:{sb.port}/{path.lstrip('/')}"
    if query:
        url += "?" + query
    fwd = {
        k: v for k, v in headers.items() if k.lower() not in _HOP_HEADERS
    }
    try:
        r = _loopback.request(method, url, content=body or None, headers=fwd)
    except httpx.HTTPError as e:
        raise SandboxError(f"sandbox unreachable: {e}")
    if len(r.content) > MAX_PROXY_BYTES:
        raise SandboxError("sandbox response exceeded 10 MB")
    return r
