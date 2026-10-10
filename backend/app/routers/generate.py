from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.codegen import render_service
from app.services.validate import validate_openapi

router = APIRouter(prefix="/generate", tags=["generate"])


class CodeRequest(BaseModel):
    spec: dict = Field(min_length=1)
    auth: bool = False
    stack: Literal["fastapi"] = "fastapi"


@router.post("/code")
def generate_code(req: CodeRequest):
    """Render a runnable service from a validated OpenAPI document.

    Returns {"files": {path: content}, "entities", "auth"}. Every rendered
    .py file passed a syntax check before it got here."""
    problems = validate_openapi(req.spec)
    if problems:
        raise HTTPException(
            status_code=422, detail="invalid OpenAPI: " + "; ".join(problems)
        )
    try:
        return render_service(req.spec, {"auth": req.auth})
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except RuntimeError as e:  # template bug; never user input
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zip")
def download_zip(payload: dict):
    """Bundle the generated service as a .zip download."""
    raise HTTPException(status_code=501, detail="zip download not implemented yet")
