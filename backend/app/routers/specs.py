import json
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.routers.generate import MAX_SPEC_BYTES
from app.services.importer import import_openapi
from app.services.specgen import patch_spec, prompt_to_spec
from app.services.validate import validate_openapi

router = APIRouter(prefix="/specs", tags=["specs"])


class GenerateRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    auth: bool = False
    database: Literal["postgres"] = "postgres"
    language: Literal["python"] = "python"


class RefineRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=4000)
    questions: list[str] = Field(default_factory=list, max_length=10)
    answers: list[str] = Field(default_factory=list, max_length=10)
    auth: bool = False


def _run(prompt: str, options: dict) -> dict:
    """One error policy for every spec endpoint: missing key -> 503,
    broken draft -> 422. Clarification payloads pass through with 200."""
    try:
        return prompt_to_spec(prompt, options)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/generate")
def generate_spec(req: GenerateRequest):
    """Turn a natural-language prompt into an OpenAPI 3.0 document.

    Returns the spec, or {"needs_clarification": true, "questions": [...]}
    when the prompt is too vague to build from."""
    return _run(req.prompt, {"auth": req.auth, "database": req.database,
                             "language": req.language})


class ImportRequest(BaseModel):
    url: Optional[str] = Field(default=None, max_length=2048)
    content: Optional[str] = Field(default=None, max_length=2 * 1024 * 1024)


@router.post("/import")
def import_spec(req: ImportRequest):
    """Import an existing OpenAPI document from a URL or pasted JSON/YAML.

    No LLM involved. Public http(s) URLs only; documents must validate
    as usable OpenAPI 3.0."""
    try:
        return import_openapi(url=req.url, content=req.content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"fetch failed: {e}")


@router.post("/refine")
def refine_spec(req: RefineRequest):
    """Answer the guardrail's clarifying questions and regenerate the spec."""
    clarifications = "\n".join(
        f"- {q.strip()}: {a.strip()}"
        for q, a in zip(req.questions, req.answers)
        if q.strip() and a.strip()
    )[:2000]
    enriched = req.prompt
    if clarifications:
        enriched += "\n\nThe user answered these clarifying questions:\n" + clarifications
    return _run(enriched, {"auth": req.auth})


class PatchRequest(BaseModel):
    spec: dict = Field(min_length=1)
    prompt: str = Field(min_length=1, max_length=4000)
    auth: bool = False


@router.post("/patch")
def patch_existing_spec(req: PatchRequest):
    """Apply a natural-language change to an existing spec ("add reviews to books").

    Returns the updated, re-validated spec — or the clarification payload when
    the change is too vague to apply. The old spec must itself be valid."""
    # Same 2 MB ceiling as the other spec-taking endpoints; without it a
    # huge spec would reach the LLM call unchecked.
    if len(json.dumps(req.spec)) > MAX_SPEC_BYTES:
        raise HTTPException(status_code=413, detail="spec exceeds 2 MB")
    problems = validate_openapi(req.spec)
    if problems:
        raise HTTPException(
            status_code=422,
            detail="existing spec invalid: " + "; ".join(problems),
        )
    try:
        return patch_spec(req.spec, req.prompt, {"auth": req.auth})
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
