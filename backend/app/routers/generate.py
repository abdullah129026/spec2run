from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/code")
def generate_code(payload: dict):
    """Render template-based service code from an OpenAPI document."""
    raise HTTPException(status_code=501, detail="code generation not implemented yet")


@router.post("/zip")
def download_zip(payload: dict):
    """Bundle the generated service as a .zip download."""
    raise HTTPException(status_code=501, detail="zip download not implemented yet")
