"""Prompt -> OpenAPI 3.0. The LLM drafts; the validator decides."""

import json

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


def _clarification_questions(doc: dict) -> list[str]:
    """Questions from a clarification draft, or raise on malformed output.

    complete_json returns whatever JSON the model produced, so a non-list
    'questions' (e.g. a bare string) used to iterate into single-character
    questions, and a non-dict document crashed the caller with AttributeError
    (a 500) instead of a clean 422. A broken draft is never guessed from.
    """
    if not isinstance(doc, dict):
        raise ValueError("model produced invalid OpenAPI: expected a JSON object")
    questions = doc.get("questions")
    if not isinstance(questions, list):
        raise ValueError("model produced unusable clarification: 'questions' must be a list")
    questions = [q for q in questions if isinstance(q, str)]
    if not questions:
        raise ValueError("model produced unusable clarification: no questions")
    return questions[:4]


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

    if not isinstance(doc, dict):
        raise ValueError("model produced invalid OpenAPI: expected a JSON object")
    if doc.get("needs_clarification"):
        return {"needs_clarification": True,
                "questions": _clarification_questions(doc)}

    doc = _normalize(doc)
    problems = validate_openapi(doc)
    if problems:
        raise ValueError("model produced invalid OpenAPI: " + "; ".join(problems))
    return doc


PATCH_SYSTEM_PROMPT = """\
You are Spec2Run's spec editor. The user has an existing OpenAPI 3.0 document
and wants it changed. Output ONLY the complete updated JSON document with the
same top-level keys: openapi, info, paths, components.

Rules:
- Make the smallest edit that satisfies the request. Keep everything else
  identical — same schemas, same endpoints, same field types.
- "openapi" stays "3.0.0". $refs may only point at local schemas:
  "#/components/schemas/<Name>". Every referenced schema must be defined
  under "components.schemas".
- Every operation needs a "responses" object.
- Never invent auth schemes the user didn't ask for.

If the request is too vague to apply (no discernible change), do NOT guess.
Output exactly this shape instead:
{"needs_clarification": true, "questions": ["...", "..."]}
Two to four specific questions, never more than four.\
"""


def patch_spec(existing: dict, change: str, options: dict | None = None) -> dict:
    """Apply a natural-language change to an existing spec ("add reviews to books").

    Returns the updated spec, or {"needs_clarification": True, "questions":
    [...]} when the request is too vague. Raises ValueError when the model
    produces something unusable (never guess from a broken edit).
    """
    options = {k: v for k, v in (options or {}).items() if k in KNOWN_OPTIONS}
    prefs = [f"{k}={options[k]}" for k in KNOWN_OPTIONS if k in options]
    user_message = (
        "Current spec:\n" + json.dumps(existing)
        + "\n\nRequested change: " + change.strip()
    )
    if prefs:
        user_message += "\nOptions: " + ", ".join(prefs)
    doc = llm.complete_json(PATCH_SYSTEM_PROMPT, user_message)

    if not isinstance(doc, dict):
        raise ValueError("model produced invalid OpenAPI: expected a JSON object")
    if doc.get("needs_clarification"):
        return {"needs_clarification": True,
                "questions": _clarification_questions(doc)}

    doc = _normalize(doc)
    problems = validate_openapi(doc)
    if problems:
        raise ValueError("model produced invalid OpenAPI: " + "; ".join(problems))
    return doc
