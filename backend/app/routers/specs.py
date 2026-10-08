from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.specgen import prompt_to_spec

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


@router.post("/import")
def import_spec(payload: dict):
    """Import an existing OpenAPI document from a URL or pasted JSON/YAML."""
    raise HTTPException(status_code=501, detail="spec import not implemented yet")


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
