import pytest

from app.services import slots

BOOKSTORE = {
    "openapi": "3.0.0",
    "info": {"title": "Bookstore", "version": "1.0.0"},
    "paths": {
        "/books": {"get": {"responses": {"200": {"description": "ok"}}}},
        "/authors": {"get": {"responses": {"200": {"description": "ok"}}}},
    },
    "components": {
        "schemas": {
            "Book": {
                "type": "object",
                "required": ["title"],
                "properties": {
                    "id": {"type": "integer"},
                    "title": {"type": "string"},
                    "pages": {"type": "integer"},
                    "price": {"type": "number"},
                    "in_print": {"type": "boolean"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "published_at": {"type": "string", "format": "date-time"},
                    "author_id": {"type": "integer"},
                    "shelf_id": {"type": "integer"},
                },
            },
            "Author": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "id": {"type": "integer"},
                    "name": {"type": "string"},
                },
            },
        },
    },
}


def test_entities_extracted():
    out = slots.slots_from_spec(BOOKSTORE)
    by_name = {e["name"]: e for e in out["entities"]}
    assert set(by_name) == {"Book", "Author"}
    assert by_name["Book"]["plural"] == "books"
    assert by_name["Book"]["singular"] == "book"
    assert out["auth"] is False


def test_field_types_mapped():
    book = {e["name"]: e for e in slots.slots_from_spec(BOOKSTORE)["entities"]}["Book"]
    cols = {f["name"]: f for f in book["fields"]}
    assert cols["title"] == {"name": "title", "py": "str", "col": "String",
                             "required": True, "fk": None}
    assert cols["pages"]["col"] == "Integer" and cols["pages"]["py"] == "int"
    assert cols["price"]["col"] == "Float"
    assert cols["in_print"]["col"] == "Boolean"
    assert cols["tags"]["col"] == "JSON" and cols["tags"]["py"] == "Any"
    assert cols["published_at"]["col"] == "DateTime"
    assert cols["pages"]["required"] is False
    # id is never part of the create payload
    assert [f["name"] for f in book["create_fields"]] == [
        "title", "pages", "price", "in_print", "tags",
        "published_at", "author_id", "shelf_id",
    ]


def test_relation_from_id_suffix():
    book = {e["name"]: e for e in slots.slots_from_spec(BOOKSTORE)["entities"]}["Book"]
    cols = {f["name"]: f for f in book["fields"]}
    assert cols["author_id"]["fk"] == "authors"  # Author exists
    assert cols["shelf_id"]["fk"] is None  # no Shelf schema, no guessing


def test_plural_forms():
    assert slots._plural("Category") == "categories"
    assert slots._plural("Box") == "boxes"
    assert slots._plural("Order") == "orders"


def test_auth_from_option():
    out = slots.slots_from_spec(BOOKSTORE, {"auth": True})
    assert out["auth"] is True


def test_auth_from_bearer_scheme():
    spec = dict(BOOKSTORE)
    spec["components"] = {
        **BOOKSTORE["components"],
        "securitySchemes": {
            "bearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
        },
    }
    spec["security"] = [{"bearerAuth": []}]
    assert slots.slots_from_spec(spec)["auth"] is True


def test_user_schema_skipped_when_auth():
    spec = dict(BOOKSTORE)
    spec["components"] = {
        **BOOKSTORE["components"],
        "schemas": {**BOOKSTORE["components"]["schemas"],
                    "User": {"type": "object", "properties": {"email": {"type": "string"}}}},
    }
    names = [e["name"] for e in slots.slots_from_spec(spec, {"auth": True})["entities"]]
    assert "User" not in names
    names = [e["name"] for e in slots.slots_from_spec(spec)["entities"]]
    assert "User" in names  # kept when auth is off; template renders it plain


def test_bad_schema_name_rejected():
    spec = dict(BOOKSTORE, components={"schemas": {"123nope": {"type": "object"}}})
    with pytest.raises(ValueError, match="schema"):
        slots.slots_from_spec(spec)


def test_bad_field_name_rejected():
    spec = dict(BOOKSTORE, components={"schemas": {
        "Book": {"type": "object", "properties": {"not a name": {"type": "string"}}}}})
    with pytest.raises(ValueError, match="field"):
        slots.slots_from_spec(spec)


def test_non_dict_spec_rejected():
    with pytest.raises(ValueError):
        slots.slots_from_spec(["nope"])
