"""Entity/field/relation slot filling from an OpenAPI document.

The LLM drafts the spec; everything below is deterministic. Template
authors get plain dicts and never touch OpenAPI.
"""

import re

# OpenAPI type -> SQLAlchemy column type. Format "date-time" is special-cased.
COLUMN_TYPES = {
    "string": "String",
    "integer": "Integer",
    "number": "Float",
    "boolean": "Boolean",
    "array": "JSON",
    "object": "JSON",
}
PY_TYPES = {
    "String": "str",
    "Integer": "int",
    "Float": "float",
    "Boolean": "bool",
    "JSON": "Any",
    "DateTime": "datetime",
}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


def _plural(name: str) -> str:
    lower = name.lower()
    if lower.endswith(("s", "x", "z", "ch", "sh")):
        return lower + "es"
    if lower.endswith("y") and len(lower) > 1 and lower[-2] not in "aeiou":
        return lower[:-1] + "ies"
    return lower + "s"
    # ponytail: naive inflection, right for the nouns specs use; revisit if a corpus shows misses


def _check_ident(value: str, what: str) -> str:
    if not IDENT.match(value):
        raise ValueError(f"spec uses unsupported {what} name: {value!r}")
    return value


def _class_name(schema_name: str) -> str:
    _check_ident(schema_name, "schema")
    return schema_name[0].upper() + schema_name[1:]


def _auth_requested(spec: dict, options: dict | None) -> bool:
    """True when the user asked for auth or the spec declares a bearer scheme."""
    if (options or {}).get("auth"):
        return True
    schemes = (spec.get("components") or {}).get("securitySchemes") or {}
    for scheme in schemes.values():
        if not isinstance(scheme, dict):
            continue
        if scheme.get("type") == "http" and scheme.get("scheme") == "bearer":
            return True
        if scheme.get("type") == "apiKey":  # pragma: no cover - specgen never emits this
            return True
    return bool(spec.get("security"))


def _field(name: str, prop: dict, required: set[str], plurals: dict[str, str]) -> dict:
    _check_ident(name, "field")
    prop = prop if isinstance(prop, dict) else {}
    otype = prop.get("type", "string")
    col = "DateTime" if prop.get("format") == "date-time" else COLUMN_TYPES.get(otype, "String")
    fk = None
    if name.endswith("_id") and otype == "integer":
        target = _class_name(name[:-3])
        if target in plurals:
            fk = plurals[target]
    py = PY_TYPES[col]
    req = name in required or name == "id"
    return {
        "name": name,
        "py": py,
        "annotation": py if req else f"Optional[{py}] = None",
        "col": col,
        "required": req,
        "fk": fk,
    }


def slots_from_spec(spec: dict, options: dict | None = None) -> dict:
    """Fill template slots from a validated OpenAPI document.

    Returns {"info", "entities", "auth"}. Entities carry name/plural/singular
    plus typed fields; relations come from `<entity>_id` integer fields.
    Raises ValueError on names that are not valid Python identifiers.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be an object")
    info = spec.get("info") or {}
    schemas = (spec.get("components") or {}).get("schemas") or {}
    auth = _auth_requested(spec, options)

    plurals = {_class_name(n): _plural(_class_name(n)) for n in schemas if isinstance(n, str)}
    entities = []
    for schema_name, schema in schemas.items():
        cls = _class_name(schema_name)
        if auth and cls == "User":
            # the auth template owns the users table (username + password
            # hash); a spec-defined User would collide with it.
            continue
        schema = schema if isinstance(schema, dict) else {}
        props = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        fields = [_field(n, p, required, plurals) for n, p in props.items()]
        create_fields = [f for f in fields if f["name"] != "id"]
        entities.append({
            "name": cls,
            "plural": plurals[cls],
            "singular": cls.lower(),
            "fields": fields,
            "create_fields": create_fields,
        })
    return {"info": info, "entities": entities, "auth": auth}
