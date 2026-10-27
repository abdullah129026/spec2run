"""Structural checks for LLM-drafted OpenAPI 3.0 documents.

The model drafts; this module decides. JSON-mode output is no guarantee of a
usable spec, so every draft goes through here before anything renders from it.
Returns plain strings, not exceptions — the caller decides what to do with them.
"""

METHODS = {"get", "put", "post", "delete", "patch", "head", "options", "trace"}

# Fields a path item may carry next to its operations (OpenAPI 3.0). These
# are not methods: a real imported document with path-level parameters or a
# summary must not be rejected as an "unknown method".
PATH_ITEM_FIELDS = {"summary", "description", "servers", "parameters", "$ref"}


def _collect_refs(node, refs: set):
    """Walk the document and collect every $ref value. Iterative on purpose:
    submitted specs are user-controlled, and a deeply nested one must not
    blow the call stack (RecursionError would surface as a 500)."""
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            for key, value in current.items():
                if key == "$ref" and isinstance(value, str):
                    refs.add(value)
                else:
                    stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)


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
        # OpenAPI requires strings here, and a truthy non-string (title: 123,
        # version: 1.0) used to pass this check and flow into templates and
        # the zip filename unchecked.
        title = info.get("title")
        if not isinstance(title, str) or not title:
            errors.append("'info.title' must be a non-empty string")
        version = info.get("version")
        if not isinstance(version, str) or not version:
            errors.append("'info.version' must be a non-empty string")

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
                if method in PATH_ITEM_FIELDS:
                    continue
                if method not in METHODS:
                    errors.append(f"{path}: unknown method {method!r}")
                    continue
                if not isinstance(operation, dict) or not operation.get("responses"):
                    errors.append(f"{path} {method}: 'responses' is required")
            if not any(key in METHODS for key in operations):
                errors.append(f"path {path!r} must define at least one operation")

    components = doc.get("components")
    if components is None:
        schemas = {}
    elif not isinstance(components, dict):
        errors.append("'components' must be an object")
        schemas = {}
    else:
        schemas = components.get("schemas") or {}
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
