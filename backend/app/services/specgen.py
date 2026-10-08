"""Prompt -> OpenAPI 3.0. The LLM drafts; the validator decides."""

SYSTEM_PROMPT = """\
You are Spec2Run's spec engine. Convert the user's description into an
OpenAPI 3.0 document. Output ONLY a JSON object with keys: openapi, info,
paths, components. If the request is too vague to build from, output
{"needs_clarification": true, "questions": [...]} instead. Never invent auth
schemes the user didn't ask for.\
"""


def prompt_to_spec(prompt: str, options: dict) -> dict:
    """Full pipeline: LLM draft -> structural validation -> normalized spec."""
    raise NotImplementedError  # week 1
