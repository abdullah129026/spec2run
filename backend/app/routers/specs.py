from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/specs", tags=["specs"])


@router.post("/generate")
def generate_spec(payload: dict):
    """Turn a natural-language prompt into an OpenAPI 3.0 document."""
    raise HTTPException(status_code=501, detail="spec generation not implemented yet")


@router.post("/import")
def import_spec(payload: dict):
    """Import an existing OpenAPI document from a URL or pasted JSON/YAML."""
    raise HTTPException(status_code=501, detail="spec import not implemented yet")


@router.post("/refine")
def refine_spec(payload: dict):
    """Answer a clarifying question, or patch an existing spec."""
    raise HTTPException(status_code=501, detail="spec refinement not implemented yet")
