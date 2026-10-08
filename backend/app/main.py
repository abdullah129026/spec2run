"""Spec2Run backend — voice/text prompt to live microservice."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import generate, sandbox, specs

app = FastAPI(title="Spec2Run API", version="0.1.0")

origins = [
    o.strip()
    for o in os.environ.get("SPEC2RUN_CORS_ORIGINS", "").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(specs.router)
app.include_router(generate.router)
app.include_router(sandbox.router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "spec2run-api"}
