"""Template + LLM hybrid code generation.

The LLM never writes the service freehand. It fills typed slots (entities,
fields, relations, auth) and Jinja2 templates render runnable code.
"""

import ast
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.services.slots import slots_from_spec

TEMPLATES = Path(__file__).parent.parent / "templates"

_env = Environment(
    loader=FileSystemLoader(TEMPLATES / "fastapi"),
    undefined=StrictUndefined,
    trim_blocks=True,
    lstrip_blocks=True,
)

# template name -> output path (templates live as <name>.j2)
STACK_FILES = ["app.py", "requirements.txt", "README.md", ".env.example"]


def check_syntax(files: dict[str, str]) -> list[str]:
    """Parse every rendered .py file; returns ["path:line: msg", ...]."""
    problems = []
    for path, content in files.items():
        if not path.endswith(".py"):
            continue
        try:
            ast.parse(content, filename=path)
        except SyntaxError as e:
            problems.append(f"{path}:{e.lineno}: {e.msg}")
    return problems


def render_service(spec: dict, options: dict | None = None) -> dict:
    """Render the full service from a validated OpenAPI document.

    Returns {"files": {path: content}, "info", "entities", "auth"}.
    Raises ValueError on a bad spec; RuntimeError if a template renders
    broken Python (a template bug, never user-facing output).
    """
    slots = slots_from_spec(spec, options)
    files = {}
    for name in STACK_FILES:
        files[name] = _env.get_template(name + ".j2").render(**slots)
    bad = check_syntax(files)
    if bad:
        raise RuntimeError("template rendered invalid Python: " + "; ".join(bad))
    return {"files": files, **slots}
