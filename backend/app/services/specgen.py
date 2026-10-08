"""Prompt -> OpenAPI 3.0. The LLM drafts; the validator decides."""

from app.services import llm
from app.services.validate import validate_openapi

SYSTEM_PROMPT = """\
You are Spec2Run's spec engine. Convert the user's description into an
OpenAPI 3.0 document. Output ONLY a JSON object with keys: openapi, info,
paths, components.

Rules:
- "openapi" must be "3.0.0".
- "info" must have "title" (short, derived from the request) and "version"
  ("1.0.0" unless the user says otherwise).
- "paths" must be non-empty. Every operation needs a "responses" object.
- $refs may only point at local schemas: "#/components/schemas/<Name>".
  Every referenced schema must be defined under "components.schemas".
- Never invent auth schemes the user didn't ask for. If they asked for auth,
  use a bearer JWT scheme and document register/login endpoints.
- Keep it concrete: real endpoints for the entities described, sensible field
  types, no placeholders.

If the request is too vague to build from (no discernible entities or
operations), do NOT guess. Output exactly this shape instead:
{"needs_clarification": true, "questions": ["...", "..."]}
Two to four specific questions, never more than four.\
"""

# What the frontend may send; everything else is ignored, not trusted.
KNOWN_OPTIONS = {"auth", "database", "language"}


def _user_message(prompt: str, options: dict) -> str:
    lines = [f"User request: {prompt.strip()}"]
    prefs = [f"{k}={options[k]}" for k in KNOWN_OPTIONS if k in options]
    if prefs:
        lines.append("Options: " + ", ".join(prefs))
    return "\n".join(lines)


def _normalize(doc: dict) -> dict:
    """Keep only the top-level keys a spec may carry."""
    return {k: doc[k] for k in ("openapi", "info", "paths", "components") if k in doc}


def prompt_to_spec(prompt: str, options: dict | None = None) -> dict:
    """Full pipeline: LLM draft -> clarification handling -> validation.

    Returns the normalized spec, or {"needs_clarification": True,
    "questions": [...]} when the prompt is too vague. Raises ValueError when
    the model produces something unusable (never guess from a broken draft).
    """
    options = {k: v for k, v in (options or {}).items() if k in KNOWN_OPTIONS}
    doc = llm.complete_json(SYSTEM_PROMPT, _user_message(prompt, options))

    if doc.get("needs_clarification"):
        questions = [q for q in doc.get("questions", []) if isinstance(q, str)]
        return {"needs_clarification": True, "questions": questions[:4]}

    doc = _normalize(doc)
    problems = validate_openapi(doc)
    if problems:
        raise ValueError("model produced invalid OpenAPI: " + "; ".join(problems))
    return doc
