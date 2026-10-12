from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response
from pydantic import BaseModel, Field

from app.routers.generate import _check_spec, _render
from app.services import sandbox as sandbox_svc
from app.services.sandbox import SandboxError

router = APIRouter(prefix="/sandbox", tags=["sandbox"])

MAX_BODY_BYTES = 10 * 1024 * 1024
_RESPONSE_HOP_HEADERS = {
    "content-encoding", "content-length", "transfer-encoding", "connection"
}


class SandboxUpRequest(BaseModel):
    spec: dict = Field(min_length=1)
    auth: bool = False
    database: Literal["auto", "neon", "sqlite"] = "auto"


def _get_or_404(sandbox_id: str):
    sb = sandbox_svc.get(sandbox_id)
    if sb is None:
        raise HTTPException(status_code=404, detail="unknown sandbox")
    return sb


@router.post("/up", status_code=201)
def sandbox_up(req: SandboxUpRequest):
    """Render the service from a validated spec and boot it in a sandbox.

    Returns {"sandbox_id", "proxy_url", "database", ...}. The service is
    reachable only through /sandbox/{id}/proxy/... and dies after the TTL.
    """
    _check_spec(req.spec)
    try:
        files = _render(req.spec, req.auth)["files"]
        sb = sandbox_svc.boot(files, database=req.database)
    except SandboxError as e:
        raise HTTPException(status_code=502, detail=str(e))
    info = sandbox_svc.status(sb)
    info["proxy_url"] = f"/sandbox/{sb.id}/proxy"
    return info


@router.get("/{sandbox_id}")
def sandbox_status(sandbox_id: str):
    return sandbox_svc.status(_get_or_404(sandbox_id))


@router.get("/{sandbox_id}/logs")
def sandbox_logs(
    sandbox_id: str, tail: int = Query(default=200, ge=1, le=1000)
):
    """Last lines of the sandboxed service's stdout/stderr."""
    return {"lines": sandbox_svc.log_tail(_get_or_404(sandbox_id), tail)}


@router.delete("/{sandbox_id}", status_code=204)
def sandbox_down(sandbox_id: str):
    if not sandbox_svc.kill(sandbox_id):
        raise HTTPException(status_code=404, detail="unknown sandbox")


@router.api_route(
    "/{sandbox_id}/proxy/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"],
)
async def sandbox_proxy(sandbox_id: str, path: str, request: Request):
    """Forward one HTTP call to the sandboxed service on loopback."""
    sb = _get_or_404(sandbox_id)
    body = await request.body()
    if len(body) > MAX_BODY_BYTES:
        raise HTTPException(status_code=413, detail="request body exceeds 10 MB")
    try:
        r = await run_in_threadpool(
            sandbox_svc.proxy,
            sb,
            request.method,
            path,
            str(request.query_params),
            dict(request.headers),
            body,
        )
    except SandboxError as e:
        raise HTTPException(status_code=502, detail=str(e))
    headers = {
        k: v for k, v in r.headers.items()
        if k.lower() not in _RESPONSE_HOP_HEADERS
    }
    return Response(
        content=r.content,
        status_code=r.status_code,
        headers=headers,
        media_type=r.headers.get("content-type"),
    )
