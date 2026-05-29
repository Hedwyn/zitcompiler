"""
Test for annotations and type conversions from Python to Zig.

@date: 29.05.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

from typing import Annotated

import pytest

from zitcompiler import (
    Annotation,
    UnsupportedType,
    ZigType,
    get_annotation,
    get_annotations,
    get_zig_type,
    iter_annotations,
)


@pytest.mark.parametrize(
    ("type_hint", "expected_count"),
    [
        pytest.param(Annotated[int, ZigType("i32")], 1, id="single_annotation"),
        pytest.param(
            Annotated[int, ZigType("i32"), ZigType("i64")],
            2,
            id="multiple_annotations",
        ),
        pytest.param(
            Annotated[int, "some string", ZigType("i32"), 42],
            1,
            id="mixed_metadata",
        ),
        pytest.param(int, 0, id="unannotated_type"),
        pytest.param(Annotated[int, "just a string", 42], 0, id="no_annotations"),
    ],
)
def test_iter_annotations(type_hint: object, expected_count: int) -> None:
    """iter_annotations yields Annotation objects based on type and metadata."""
    annotations = list(iter_annotations(type_hint))
    assert len(annotations) == expected_count


@pytest.mark.parametrize(
    ("type_hint", "filter_type", "expected_count"),
    [
        pytest.param(
            Annotated[int, ZigType("i32"), "other"],
            ZigType,
            1,
            id="with_filter_matches",
        ),
        pytest.param(
            Annotated[int, ZigType("i32")],
            None,
            1,
            id="no_filter",
        ),
        pytest.param(
            int,
            ZigType,
            0,
            id="unannotated_type",
        ),
        pytest.param(
            Annotated[int, ZigType("i32"), ZigType("i64")],
            ZigType,
            2,
            id="multiple_matching",
        ),
    ],
)
def test_get_annotations(
    type_hint: object,
    filter_type: type[Annotation] | None,
    expected_count: int,
) -> None:
    """get_annotations filters and returns Annotation objects based on type."""
    annotations = get_annotations(type_hint, filter_type)
    assert len(annotations) == expected_count


def test_get_annotations_with_filter_no_match() -> None:
    """get_annotations returns empty list when no annotations match filter."""

    class CustomAnnotation(Annotation):
        pass

    zig_type = ZigType("i32")
    type_hint = Annotated[int, zig_type]

    annotations = get_annotations(type_hint, CustomAnnotation)

    assert len(annotations) == 0


def test_get_annotation_single_match() -> None:
    """get_annotation returns the single matching annotation."""
    zig_type = ZigType("i32")
    type_hint = Annotated[int, zig_type]

    annotation = get_annotation(type_hint, ZigType)

    assert annotation is zig_type


def test_get_annotation_no_match() -> None:
    """get_annotation returns None when no annotations match."""

    class CustomAnnotation(Annotation):
        pass

    zig_type = ZigType("i32")
    type_hint = Annotated[int, zig_type]

    annotation = get_annotation(type_hint, CustomAnnotation)

    assert annotation is None


def test_get_annotation_unannotated_type() -> None:
    """get_annotation returns None for unannotated type."""
    annotation: Annotation | None = get_annotation(int, ZigType)

    assert annotation is None


def test_get_annotation_multiple_matches_raises() -> None:
    """get_annotation raises TypeError when multiple annotations match."""
    zig_type1 = ZigType("i32")
    zig_type2 = ZigType("i64")
    type_hint = Annotated[int, zig_type1, zig_type2]

    with pytest.raises(TypeError, match="more than one annotation"):
        get_annotation(type_hint, ZigType)


def test_get_zig_type_with_annotation() -> None:
    """get_zig_type returns user-defined type from annotation."""
    expected_type = "custom_zig_type"
    zig_type = ZigType(expected_type)
    type_hint = Annotated[int, zig_type]

    result = get_zig_type(type_hint)

    assert result == expected_type


@pytest.mark.parametrize(
    ("builtin_type", "expected_zig_type"),
    [
        pytest.param(int, "i64", id="int"),
        pytest.param(float, "f64", id="float"),
        pytest.param(str, "const [] u8", id="str"),
        pytest.param(bytes, "const [] u8", id="bytes"),
    ],
)
def test_get_zig_type_builtin(builtin_type: type, expected_zig_type: str) -> None:
    """get_zig_type returns correct Zig type for builtin types."""
    result = get_zig_type(builtin_type)
    assert result == expected_zig_type


def test_get_zig_type_annotation_overrides_builtin() -> None:
    """get_zig_type prefers annotation over builtin mapping."""
    zig_type = ZigType("custom_int")
    type_hint = Annotated[int, zig_type]

    result = get_zig_type(type_hint)

    assert result == "custom_int"


def test_get_zig_type_unsupported_non_builtin_no_annotation() -> None:
    """get_zig_type raises UnsupportedType for custom type without annotation."""

    class CustomClass:
        pass

    with pytest.raises(UnsupportedType):
        get_zig_type(CustomClass)


def test_get_zig_type_unsupported_unknown_builtin() -> None:
    """get_zig_type raises UnsupportedType for unknown builtin type."""
    with pytest.raises(UnsupportedType):
        get_zig_type(dict)


def test_get_zig_type_with_generic_type_annotation() -> None:
    """get_zig_type works with generic type with annotation."""
    zig_type = ZigType("list_i32")
    type_hint = Annotated[list, zig_type]

    result = get_zig_type(type_hint)

    assert result == "list_i32"


def test_zig_type_dataclass_behavior() -> None:
    """ZigType is a dataclass and can be compared."""
    zig_type1 = ZigType("i32")
    zig_type2 = ZigType("i32")
    zig_type3 = ZigType("i64")

    assert zig_type1 == zig_type2
    assert zig_type1 != zig_type3


def test_integration_full_workflow_annotated_type() -> None:
    """Integration test: get zig type for annotated type."""
    zig_type = ZigType("custom_i32")
    type_hint = Annotated[int, zig_type]
    zig_type_str = get_zig_type(type_hint)

    assert zig_type_str == "custom_i32"


def test_integration_full_workflow_with_multiple_metadata() -> None:
    """Integration test: get zig type from Annotated with mixed metadata."""
    zig_type = ZigType("special_type")
    type_hint = Annotated[str, "documentation", zig_type, 123]

    result = get_zig_type(type_hint)

    assert result == "special_type"


def test_integration_annotation_lifecycle() -> None:
    """Integration test: create, store, and retrieve annotation."""
    zig_type = ZigType("lifecycle_test")
    type_hint = Annotated[float, zig_type]

    retrieved = get_annotation(type_hint, ZigType)

    assert retrieved is zig_type
    assert retrieved.value == "lifecycle_test"
