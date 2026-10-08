"""Structural checks for LLM-drafted OpenAPI 3.0 documents.

The model drafts; this module decides. JSON-mode output is no guarantee of a
usable spec, so every draft goes through here before anything renders from it.
Returns plain strings, not exceptions — the caller decides what to do with them.
"""

METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}


def _collect_refs(node, refs: set):
    """Walk the document and collect every $ref value."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                refs.add(value)
            else:
                _collect_refs(value, refs)
    elif isinstance(node, list):
        for item in node:
            _collect_refs(item, refs)


def validate_openapi(doc: dict) -> list[str]:
    """Return a list of problems; empty means the spec is usable."""
    errors = []

    version = doc.get("openapi")
    if not isinstance(version, str) or not version.startswith("3.0."):
        errors.append(f"'openapi' must be a 3.0.x version string, got {version!r}")

    info = doc.get("info")
    if not isinstance(info, dict):
        errors.append("'info' must be an object")
    else:
        if not info.get("title"):
            errors.append("'info.title' is required")
        if not info.get("version"):
            errors.append("'info.version' is required")

    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        errors.append("'paths' must be a non-empty object")
    else:
        for path, operations in paths.items():
            if not isinstance(path, str) or not path.startswith("/"):
                errors.append(f"path {path!r} must start with '/'")
                continue
            if not isinstance(operations, dict):
                errors.append(f"path {path!r} must map to an object of operations")
                continue
            for method, operation in operations.items():
                if method not in METHODS:
                    errors.append(f"{path}: unknown method {method!r}")
                    continue
                if not isinstance(operation, dict) or not operation.get("responses"):
                    errors.append(f"{path} {method}: 'responses' is required")

    schemas = (doc.get("components") or {}).get("schemas") or {}
    if not isinstance(schemas, dict):
        errors.append("'components.schemas' must be an object")
        schemas = {}

    refs: set[str] = set()
    _collect_refs(doc, refs)
    for ref in sorted(refs):
        if not ref.startswith("#/components/schemas/"):
            errors.append(f"only local schema refs allowed, got {ref!r}")
        elif ref.split("/")[-1] not in schemas:
            errors.append(f"unresolved ref {ref!r}")

    return errors
