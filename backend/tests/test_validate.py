from app.services.validate import validate_openapi


def valid_spec() -> dict:
    return {
        "openapi": "3.0.0",
        "info": {"title": "Todo API", "version": "1.0.0"},
        "paths": {
            "/todos": {
                "get": {"responses": {"200": {"description": "ok"}}},
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Todo"}
                            }
                        }
                    },
                    "responses": {"201": {"description": "created"}},
                },
            }
        },
        "components": {
            "schemas": {"Todo": {"type": "object", "properties": {"title": {"type": "string"}}}}
        },
    }


def test_valid_spec_has_no_errors():
    assert validate_openapi(valid_spec()) == []


def test_wrong_openapi_version():
    spec = valid_spec()
    spec["openapi"] = "2.0"
    assert any("openapi" in e for e in validate_openapi(spec))


def test_missing_info_title():
    spec = valid_spec()
    del spec["info"]["title"]
    assert any("info.title" in e for e in validate_openapi(spec))


def test_empty_paths_rejected():
    spec = valid_spec()
    spec["paths"] = {}
    assert any("paths" in e for e in validate_openapi(spec))


def test_path_must_start_with_slash():
    spec = valid_spec()
    spec["paths"] = {"todos": {"get": {"responses": {"200": {"description": "ok"}}}}}
    assert any("start with" in e for e in validate_openapi(spec))


def test_unknown_method_rejected():
    spec = valid_spec()
    spec["paths"]["/todos"]["fetch"] = {"responses": {"200": {"description": "ok"}}}
    assert any("unknown method" in e for e in validate_openapi(spec))


def test_operation_needs_responses():
    spec = valid_spec()
    del spec["paths"]["/todos"]["get"]["responses"]
    assert any("responses" in e for e in validate_openapi(spec))


def test_unresolved_ref_rejected():
    spec = valid_spec()
    spec["paths"]["/todos"]["get"]["responses"]["200"]["content"] = {
        "application/json": {"schema": {"$ref": "#/components/schemas/Missing"}}
    }
    assert any("unresolved ref" in e for e in validate_openapi(spec))


def test_external_ref_rejected():
    spec = valid_spec()
    spec["components"]["schemas"]["Todo"]["properties"]["link"] = {
        "$ref": "https://example.com/schemas/X.json"
    }
    assert any("only local" in e for e in validate_openapi(spec))


def test_info_missing_version():
    spec = valid_spec()
    del spec["info"]["version"]
    assert any("info.version" in e for e in validate_openapi(spec))


def test_path_item_fields_are_not_methods():
    """Real OpenAPI path items carry summary/description/parameters next to
    the operations; those fields are not methods and must not be rejected."""
    spec = valid_spec()
    spec["paths"]["/todos"]["summary"] = "Todo operations"
    spec["paths"]["/todos"]["parameters"] = [
        {"name": "X-Tenant", "in": "header", "schema": {"type": "string"}}
    ]
    assert validate_openapi(spec) == []


def test_path_with_no_operation_rejected():
    spec = valid_spec()
    spec["paths"]["/todos"] = {}
    assert any("at least one operation" in e for e in validate_openapi(spec))


def test_path_with_only_path_item_fields_rejected():
    spec = valid_spec()
    spec["paths"]["/todos"] = {"summary": "Todo operations"}
    assert any("at least one operation" in e for e in validate_openapi(spec))


def test_path_operations_must_be_object():
    spec = valid_spec()
    spec["paths"]["/todos"] = "not an object"
    assert any("must map to an object of operations" in e for e in validate_openapi(spec))


def test_components_schemas_must_be_object():
    spec = valid_spec()
    spec["components"]["schemas"] = ["Todo"]
    assert any("components.schemas" in e for e in validate_openapi(spec))


def test_components_must_be_object():
    for bad in ("not an object", ["schemas"], 42):
        spec = valid_spec()
        spec["components"] = bad
        assert any("components" in e for e in validate_openapi(spec))


def test_ref_collection_survives_hostile_nesting():
    """A submitted spec nested deeper than the interpreter's recursion limit
    must not crash validation (RecursionError -> 500); the walk skips
    nothing it needs to see, it just never recurses."""
    import sys

    deep = []
    node = deep
    for _ in range(sys.getrecursionlimit() + 100):
        inner = []
        node.append(inner)
        node = inner
    doc = {
        "openapi": "3.0.0",
        "info": {"title": "t", "version": "1"},
        "paths": {"/x": {"get": {"responses": {}}}},
        "components": {"schemas": {"Deep": deep}},
    }
    assert isinstance(validate_openapi(doc), list)
