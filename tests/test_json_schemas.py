"""
Test suite for JSON schema parsing and stub generation.
"""

from __future__ import annotations

import pytest

from zitcompiler.jsonschemas import (
    JsonSchemaBaseTypes,
    SchemaDef,
    SchemaProperty,
    generate_stub,
    parse_schema,
)

# ---------------------------------------------------------------------------
# parse_schema
# ---------------------------------------------------------------------------


def test_parse_flat_all_required() -> None:
    schema = parse_schema(
        {
            "type": "object",
            "title": "Person",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "height": {"type": "number"},
            },
            "required": ["name", "age", "height"],
        },
    )
    assert schema.title == "Person"
    assert schema.kw_type == JsonSchemaBaseTypes.OBJECT
    assert set(schema.properties) == {"name", "age", "height"}
    assert schema.properties["name"].type == JsonSchemaBaseTypes.STRING
    assert schema.properties["age"].type == JsonSchemaBaseTypes.INTEGER
    assert schema.properties["height"].type == JsonSchemaBaseTypes.NUMBER
    assert schema.required == frozenset({"name", "age", "height"})


def test_parse_flat_partial_required() -> None:
    schema = parse_schema(
        {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "nickname": {"type": "string"},
            },
            "required": ["name"],
        },
    )
    assert "name" in schema.required
    assert "nickname" not in schema.required


def test_parse_no_required_field() -> None:
    schema = parse_schema(
        {
            "type": "object",
            "properties": {"x": {"type": "integer"}},
        },
    )
    assert schema.required == frozenset()


def test_parse_no_title() -> None:
    schema = parse_schema({"type": "object", "properties": {}})
    assert schema.title is None


def test_parse_boolean_and_null_types() -> None:
    schema = parse_schema(
        {
            "type": "object",
            "properties": {
                "active": {"type": "boolean"},
                "deleted_at": {"type": "null"},
            },
        },
    )
    assert schema.properties["active"].type == JsonSchemaBaseTypes.BOOLEAN
    assert schema.properties["deleted_at"].type == JsonSchemaBaseTypes.NULL


def test_parse_non_object_root_raises() -> None:
    with pytest.raises(AssertionError):
        parse_schema({"type": "string"})


def test_parse_missing_property_type_raises() -> None:
    with pytest.raises((AssertionError, KeyError)):
        parse_schema({"type": "object", "properties": {"x": {}}})


def test_parse_unknown_type_raises() -> None:
    with pytest.raises(ValueError):
        parse_schema({"type": "object", "properties": {"x": {"type": "array"}}})


# ---------------------------------------------------------------------------
# generate_stub
# ---------------------------------------------------------------------------


def test_stub_all_required() -> None:
    schema = SchemaDef(
        properties={
            "name": SchemaProperty(name="name", type=JsonSchemaBaseTypes.STRING),
            "age": SchemaProperty(name="age", type=JsonSchemaBaseTypes.INTEGER),
        },
        required=frozenset({"name", "age"}),
        title="Person",
    )
    stub = generate_stub(schema)
    assert stub.startswith("class Person:")
    assert "name: str" in stub
    assert "age: int" in stub
    assert "None" not in stub


def test_stub_optional_fields() -> None:
    schema = SchemaDef(
        properties={
            "name": SchemaProperty(name="name", type=JsonSchemaBaseTypes.STRING),
            "nickname": SchemaProperty(name="nickname", type=JsonSchemaBaseTypes.STRING),
        },
        required=frozenset({"name"}),
    )
    stub = generate_stub(schema)
    assert "name: str\n" in stub or stub.endswith("name: str")
    assert "nickname: str | None" in stub


def test_stub_uses_title_as_class_name() -> None:
    schema = SchemaDef(properties={}, title="MyModel")
    stub = generate_stub(schema)
    assert "class MyModel:" in stub


def test_stub_uses_fallback_class_name() -> None:
    schema = SchemaDef(properties={}, title=None)
    stub = generate_stub(schema, class_name="Fallback")
    assert "class Fallback:" in stub


def test_stub_empty_properties() -> None:
    schema = SchemaDef(properties={})
    stub = generate_stub(schema)
    assert "..." in stub


def test_stub_number_and_bool_types() -> None:
    schema = SchemaDef(
        properties={
            "score": SchemaProperty(name="score", type=JsonSchemaBaseTypes.NUMBER),
            "active": SchemaProperty(name="active", type=JsonSchemaBaseTypes.BOOLEAN),
        },
        required=frozenset({"score", "active"}),
    )
    stub = generate_stub(schema)
    assert "score: float" in stub
    assert "active: bool" in stub


# ---------------------------------------------------------------------------
# round-trip
# ---------------------------------------------------------------------------


def test_roundtrip_parse_then_stub() -> None:
    raw = {
        "type": "object",
        "title": "Product",
        "properties": {
            "id": {"type": "integer"},
            "name": {"type": "string"},
            "price": {"type": "number"},
        },
        "required": ["id", "name"],
    }
    stub = generate_stub(parse_schema(raw))
    assert "class Product:" in stub
    assert "id: int" in stub
    assert "name: str" in stub
    assert "price: float | None" in stub
