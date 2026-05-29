"""
Types conversions and annotations; allows converting Python types into Zig.

@author: Baptiste Pestourie
@date: 29.05.2026
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import TYPE_CHECKING, TypeAlias, overload

if TYPE_CHECKING:
    from collections.abc import Iterator

    from _typeshed import DataclassInstance

type TypeHint = TypeAlias | type


class Annotation: ...


class UnsupportedType(Exception): ...


ZIG_TYPE_MAP: dict[type, str] = {
    int: "i64",
    float: "f64",
    str: "const [] u8",
    bytes: "const [] u8",
}


@dataclass
class ZigType(Annotation):
    """
    Indicates which Zig type should be used to translate
    the Python type in Zig code.
    """

    value: str


def iter_annotations(type_hint: TypeHint) -> Iterator[Annotation]:
    """
    Iterates over all the `Annotation` objects present in
    an `Annotated` type hint.
    """
    metadata = getattr(type_hint, "__metadata__", None)
    if metadata is None:
        return
    for annotation in metadata:
        if isinstance(annotation, Annotation):
            yield annotation


@overload
def get_annotations(type_hint: TypeHint, annotation_type: None) -> list[Annotation]: ...
@overload
def get_annotations[T: Annotation](type_hint: TypeHint, annotation_type: type[T]) -> list[T]: ...


def get_annotations[T: Annotation](
    type_hint: TypeHint,
    annotation_type: type[T] | None,
) -> list[T] | list[Annotation]:
    """
    Returns all the `Annotation` objects present in
    an `Annotated` type hint.
    """
    return [
        annotation
        for annotation in iter_annotations(type_hint)
        if annotation_type is None or isinstance(annotation, annotation_type)
    ]


def get_annotation[T: Annotation](type_hint: TypeHint, annotation_type: type[T]) -> T | None:
    annotations = get_annotations(type_hint, annotation_type)
    if not annotations:
        return None
    if len(annotations) > 1:
        error = f"Received more than one annotation of type {annotation_type} in {type_hint}"
        raise TypeError(error)
    return annotations[0]


def get_zig_type(type_hint: TypeHint) -> str:
    """
    Returns the zig type that should be used for the given Python `type_hint`.
    """

    if (user_defined_type := get_annotation(type_hint, ZigType)) is not None:
        return user_defined_type.value
    if not isinstance(type_hint, type):
        raise UnsupportedType("Non-builtin type annotation with no annotated zig type")
    if (builtin_type := ZIG_TYPE_MAP.get(type_hint)) is None:
        raise UnsupportedType(str(type_hint))
    return builtin_type


def generate_zig_code(constants: DataclassInstance) -> list[str]:
    return [
        f"pub const {f.name}: {f.type} = {getattr(constants, f.name)};" for f in fields(constants)
    ]
