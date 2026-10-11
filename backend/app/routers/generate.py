import io
import json
import re
import zipfile
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.services.codegen import render_service
from app.services.diffing import diff_files, diff_specs
from app.services.validate import validate_openapi

router = APIRouter(prefix="/generate", tags=["generate"])

# A spec is small JSON; anything past 2 MB is abuse, not an API.
MAX_SPEC_BYTES = 2 * 1024 * 1024


class CodeRequest(BaseModel):
    spec: dict = Field(min_length=1)
    auth: bool = False
    stack: Literal["fastapi"] = "fastapi"


class ZipRequest(BaseModel):
    spec: dict = Field(min_length=1)
    auth: bool = False


class DiffRequest(BaseModel):
    old_spec: dict = Field(min_length=1)
    new_spec: dict = Field(min_length=1)
    # Override the new rendered files (e.g. Monaco edits); old files are
    # always rendered fresh from old_spec.
    new_files: Optional[dict[str, str]] = None


class GithubPushRequest(BaseModel):
    spec: dict = Field(min_length=1)
    token: str = Field(min_length=1, max_length=512)
    repo: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._-]+$")
    description: str = Field(default="", max_length=300)
    private: bool = False
    auth: bool = False


def _check_spec(spec: dict, what: str = "spec") -> None:
    if len(json.dumps(spec)) > MAX_SPEC_BYTES:
        raise HTTPException(status_code=413, detail=f"{what} exceeds 2 MB")
    problems = validate_openapi(spec)
    if problems:
        raise HTTPException(
            status_code=422, detail=f"invalid {what}: " + "; ".join(problems)
        )


def _render(spec: dict, auth: bool) -> dict:
    try:
        return render_service(spec, {"auth": auth})
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:  # template bug; never user input
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/code")
def generate_code(req: CodeRequest):
    """Render a runnable service from a validated OpenAPI document.

    Returns {"files": {path: content}, "entities", "auth"}. Every rendered
    .py file passed a syntax check before it got here."""
    _check_spec(req.spec)
    return _render(req.spec, req.auth)


@router.post("/zip")
def download_zip(req: ZipRequest):
    """Render the service and stream it back as a .zip download."""
    _check_spec(req.spec)
    files = _render(req.spec, req.auth)["files"]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in files.items():
            zf.writestr(path, content)
    buf.seek(0)
    title = req.spec.get("info", {}).get("title", "spec2run-service")
    slug = re.sub(r"[^a-z0-9]+", "-", str(title).lower()).strip("-")
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{slug or "spec2run-service"}.zip"'
        },
    )


@router.post("/diff")
def diff_versions(req: DiffRequest):
    """Git-style diff between two specs: structured spec changes plus
    unified diffs of the rendered files.

    Returns {"spec_changes": [{path, old_value, new_value}],
    "file_diffs": {path: unified_diff}}."""
    _check_spec(req.old_spec, "old_spec")
    _check_spec(req.new_spec, "new_spec")
    old_files = _render(req.old_spec, False)["files"]
    new_files = (
        req.new_files if req.new_files is not None
        else _render(req.new_spec, False)["files"]
    )
    return {
        "spec_changes": diff_specs(req.old_spec, req.new_spec),
        "file_diffs": diff_files(old_files, new_files),
    }


def _gh(token: str, method: str, path: str, payload: Optional[dict] = None) -> dict:
    """One GitHub REST call. The token travels in a header, never in logs."""
    url = "https://api.github.com" + path
    try:
        r = httpx.request(
            method, url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json=payload,
            timeout=30,
        )
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"GitHub unreachable: {e}")
    if r.status_code >= 400:
        detail = "GitHub rejected the request"
        try:
            errors = r.json().get("message")
            if errors:
                detail = f"GitHub: {errors}"
        except ValueError:
            pass
        if r.status_code in (401, 403):
            detail += " (check the token and its repo scope)"
        raise HTTPException(status_code=502, detail=detail)
    return r.json() if r.content else {}


@router.post("/github")
def push_to_github(req: GithubPushRequest):
    """Create a repo under the user's account and push the rendered service.

    The token is used for this request only; it is never stored or logged.
    If the repo already exists, the files are committed on top of its
    default branch instead."""
    _check_spec(req.spec)
    files = _render(req.spec, req.auth)["files"]

    me = _gh(req.token, "GET", "/user")
    login = me.get("login")
    if not login:
        raise HTTPException(status_code=502, detail="GitHub: could not read user")

    try:
        _gh(
            req.token, "POST", "/user/repos",
            {"name": req.repo, "description": req.description or None,
             "private": req.private, "auto_init": False},
        )
        base_sha = None
        branch = "main"
    except HTTPException as e:
        # 502 from a name conflict means the repo exists; push onto it.
        if "already exists" not in e.detail:
            raise
        repo = _gh(req.token, "GET", f"/repos/{login}/{req.repo}")
        branch = repo.get("default_branch", "main")
        ref = _gh(req.token, "GET", f"/repos/{login}/{req.repo}/git/ref/heads/{branch}")
        base_sha = ref["object"]["sha"]

    tree_payload: dict = {
        "tree": [
            {"path": path, "mode": "100644", "type": "blob", "content": content}
            for path, content in files.items()
        ]
    }
    if base_sha:
        tree_payload["base_tree"] = base_sha
    tree = _gh(req.token, "POST", f"/repos/{login}/{req.repo}/git/trees", tree_payload)

    commit_payload: dict = {
        "message": "Spec2Run: generated service",
        "tree": tree["sha"],
    }
    if base_sha:
        commit_payload["parents"] = [base_sha]
    commit = _gh(req.token, "POST", f"/repos/{login}/{req.repo}/git/commits", commit_payload)

    if base_sha:
        _gh(req.token, "PATCH",
            f"/repos/{login}/{req.repo}/git/refs/heads/{branch}",
            {"sha": commit["sha"]})
    else:
        _gh(req.token, "POST", f"/repos/{login}/{req.repo}/git/refs",
            {"ref": "refs/heads/main", "sha": commit["sha"]})

    return {"repo": f"{login}/{req.repo}", "url": f"https://github.com/{login}/{req.repo}"}
