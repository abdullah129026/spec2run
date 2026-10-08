"""Live sandbox: run a generated service as a supervised subprocess.

Each sandbox gets a real Postgres database: a Neon branch (copy-on-write,
created in ~1s via the Neon API), connection string injected as env, branch
deleted on expiry. Falls back to SQLite when NEON_API_KEY is unset.
HTTP is proxied at /sandbox/{id}. Processes are killed after
SANDBOX_TTL_SECONDS (default 3600). No network egress from the child.
"""

import subprocess

REGISTRY: dict[str, subprocess.Popen] = {}


def boot(files: dict[str, str]) -> str:
    """Write files to a temp dir, start uvicorn on a loopback port, return the sandbox id."""
    raise NotImplementedError  # week 3


def kill(sandbox_id: str) -> None:
    proc = REGISTRY.pop(sandbox_id, None)
    if proc:
        proc.terminate()
