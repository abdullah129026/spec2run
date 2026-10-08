from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/sandbox", tags=["sandbox"])


@router.post("/up")
def sandbox_up(payload: dict):
    """Boot the generated service in an isolated subprocess; return its URL."""
    raise HTTPException(status_code=501, detail="sandbox not implemented yet")


@router.delete("/{sandbox_id}")
def sandbox_down(sandbox_id: str):
    raise HTTPException(status_code=501, detail="sandbox not implemented yet")
