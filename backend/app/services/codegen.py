"""Template + LLM hybrid code generation.

The LLM never writes the service freehand. It fills typed slots (entities,
fields, relations, auth) and Jinja2 templates render runnable code.
"""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

TEMPLATES = Path(__file__).parent.parent / "templates"


def render_service(spec: dict, slots: dict, stack: str = "fastapi") -> dict[str, str]:
    """Render every template for the stack; returns {relative_path: content}."""
    raise NotImplementedError  # week 2
