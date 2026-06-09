"""
Processes raw JSON schemas and converts them
to a Python structured representation.

@date: 09.08.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum, auto
from typing import NewType, TypeGuard

type _JsonValueType = int | str | float | None
type JsonLike = list[JsonLike | _JsonValueType] | Mapping[str, JsonLike | _JsonValueType]
SchemaKeyword = NewType("SchemaKeyword", str)
SanitizedSchemaKeyword = NewType("SanitizedSchemaKeyword", str)


class JsonSchemasVersion(StrEnum):
    DRAFT_2020_12 = "https://json-schema.org/draft/2020-12/schema"
    DRAFT_07 = "http://json-schema.org/draft-07/schema#"

    @classmethod
    def last(cls) -> JsonSchemasVersion:
        return cls.DRAFT_2020_12


class JsonSchemaBaseTypes(StrEnum):
    # invariant: should be convertable by value,
    # given a standard JSON schema type,
    # e.g., JsonSchemaBaseTypes('object')
    OBJECT = auto()
    STRING = auto()
    INTEGER = auto()
    NUMBER = auto()
    BOOLEAN = auto()
    NULL = auto()


JSON_ATOMIC_TYPES = (int, str, float, None)
KEYWORD_HINT = "$"

_PYTHON_TYPE_STUB: dict[JsonSchemaBaseTypes, str] = {
    JsonSchemaBaseTypes.STRING: "str",
    JsonSchemaBaseTypes.INTEGER: "int",
    JsonSchemaBaseTypes.NUMBER: "float",
    JsonSchemaBaseTypes.BOOLEAN: "bool",
    JsonSchemaBaseTypes.NULL: "None",
}


def is_schema_keyword(key: str) -> TypeGuard[SchemaKeyword]:
    return key.startswith(KEYWORD_HINT)


def sanitize_keyword(keyword: SchemaKeyword) -> str:
    return keyword.replace(KEYWORD_HINT, "kw_")


def preprocess_data(payload: JsonLike) -> JsonLike:
    if isinstance(payload, (int, str, float, list)) or payload is None:
        return payload
    return {
        sanitize_keyword(key) if is_schema_keyword(key) else key: val
        for key, val in payload.items()
    }


@dataclass
class SchemaProperty:
    name: str
    type: JsonSchemaBaseTypes


@dataclass
class SchemaDef:
    properties: dict[str, SchemaProperty]
    kw_type: JsonSchemaBaseTypes = JsonSchemaBaseTypes.OBJECT
    required: frozenset[str] = field(default_factory=frozenset)
    title: str | None = None


def parse_schema(payload: JsonLike) -> SchemaDef:
    processed = preprocess_data(payload)
    assert isinstance(processed, Mapping), "schema must be a JSON object"

    type_raw = processed.get("type", "object")
    assert isinstance(type_raw, str), "'type' must be a string"
    kw_type = JsonSchemaBaseTypes(type_raw)
    assert kw_type == JsonSchemaBaseTypes.OBJECT, f"root type must be 'object', got {kw_type!r}"

    properties_raw = processed.get("properties", {})
    assert isinstance(properties_raw, Mapping), "'properties' must be a JSON object"

    properties: dict[str, SchemaProperty] = {}
    for prop_name, prop_def in properties_raw.items():
        assert isinstance(prop_def, Mapping), (
            f"property {prop_name!r} definition must be a JSON object"
        )
        prop_type_raw = prop_def.get("type")
        assert isinstance(prop_type_raw, str), f"property {prop_name!r} must have a string 'type'"
        properties[prop_name] = SchemaProperty(
            name=prop_name,
            type=JsonSchemaBaseTypes(prop_type_raw),
        )

    required_raw = processed.get("required", [])
    assert isinstance(required_raw, list), "'required' must be a JSON array"
    required: frozenset[str] = frozenset(item for item in required_raw if isinstance(item, str))

    title_raw = processed.get("title")
    title: str | None = str(title_raw) if title_raw is not None else None

    return SchemaDef(properties=properties, kw_type=kw_type, required=required, title=title)


def generate_stub(
    schema: SchemaDef,
    class_name: str = "Schema",
    *,
    with_defaults: bool = False,
) -> str:
    name = schema.title or class_name
    lines: list[str] = [f"class {name}:"]

    if not schema.properties:
        lines.append("    ...")
        return "\n".join(lines)

    for prop_name, prop in schema.properties.items():
        python_type = _PYTHON_TYPE_STUB.get(prop.type, "object")
        if prop_name not in schema.required:
            suffix = " = None" if with_defaults else ""
            lines.append(f"    {prop_name}: {python_type} | None{suffix}")
        else:
            lines.append(f"    {prop_name}: {python_type}")

    return "\n".join(lines)
