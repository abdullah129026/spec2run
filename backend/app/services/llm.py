"""Groq LLM client — JSON-mode completions for spec generation."""
import json
import os

from groq import Groq

MODEL = os.environ.get("SPEC2RUN_MODEL", "openai/gpt-oss-120b")


def _client() -> Groq:
    key = os.environ.get("SPEC2RUN_GROQ_API_KEY")
    if not key:
        raise RuntimeError("SPEC2RUN_GROQ_API_KEY is not set")
    return Groq(api_key=key)


def complete_json(system: str, user: str) -> dict:
    """Ask the model for a single JSON object; raises on invalid JSON."""
    client = _client()
    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    return json.loads(resp.choices[0].message.content or "{}")
