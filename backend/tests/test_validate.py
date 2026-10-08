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
