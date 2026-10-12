"""Neon Postgres branches: one throwaway database per sandbox.

Needs NEON_API_KEY and NEON_PROJECT_ID in the environment. When they're
absent, configured() is False and the sandbox falls back to SQLite —
the key lives in Render env, never in chat or the repo. The key travels
in an Authorization header and never in logs or error messages.
"""

import os

import httpx

API = "https://console.neon.tech/api/v2"


class NeonError(RuntimeError):
    pass


def configured() -> bool:
    return bool(os.environ.get("NEON_API_KEY") and os.environ.get("NEON_PROJECT_ID"))


def _call(method: str, path: str, payload: dict | None = None) -> dict:
    key = os.environ["NEON_API_KEY"]
    project = os.environ["NEON_PROJECT_ID"]
    url = f"{API}/projects/{project}{path}"
    try:
        r = httpx.request(
            method,
            url,
            headers={"Authorization": f"Bearer {key}", "Accept": "application/json"},
            json=payload,
            timeout=30,
        )
    except httpx.HTTPError as e:
        raise NeonError(f"Neon API unreachable: {e}")
    if r.status_code >= 400:
        raise NeonError(f"Neon API returned HTTP {r.status_code}")
    return r.json()


def create_branch(name: str) -> dict:
    """Create a branch with a read-write endpoint.

    Returns {"branch_id", "database_url"} with the URL rewritten for the
    psycopg dialect SQLAlchemy expects. Raises NeonError on any failure.
    """
    data = _call(
        "POST",
        "/branches",
        {"branch": {"name": name}, "endpoints": [{"type": "read_write"}]},
    )
    branch_id = data["branch"]["id"]
    uris = data.get("connection_uris") or []
    uri = next(
        (u["connection_uri"] for u in uris if not u.get("is_pooled")), None
    ) or next((u["connection_uri"] for u in uris), None)
    if not uri:
        delete_branch(branch_id)
        raise NeonError("Neon returned no connection URI")
    for prefix in ("postgres://", "postgresql://"):
        if uri.startswith(prefix):
            uri = "postgresql+psycopg://" + uri[len(prefix):]
            break
    return {"branch_id": branch_id, "database_url": uri}


def delete_branch(branch_id: str) -> None:
    """Delete a branch; a 404 (already gone) is not an error."""
    try:
        _call("DELETE", f"/branches/{branch_id}")
    except NeonError as e:
        if "HTTP 404" not in str(e):
            raise
