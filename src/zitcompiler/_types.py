"""
Types conversions and annotations; allows converting Python types into Zig.

@author: Baptiste Pestourie
@date: 29.05.2026
"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, fields
from typing import (
    TYPE_CHECKING,
    Annotated,
    Literal,
    TypeAlias,
    get_args,
    get_origin,
    get_type_hints,
    overload,
)

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator, Mapping

    from _typeshed import DataclassInstance

type TypeHint = TypeAlias | type
type GenerationTarget = Literal["module", "struct"]


class Annotation: ...


class UnsupportedType(Exception): ...


ZIG_TYPE_MAP: dict[type, str] = {
    int: "i64",
    float: "f64",
    str: "[]const u8",
    bytes: "[]const u8",
}


@dataclass
class ZigType(Annotation):
    """
    Indicates which Zig type should be used to translate
    the Python type in Zig code.
    """

    value: str


@dataclass
class ZigModuleDef:
    """
    Defines the structure of a Zig module with top-level constants and structs.
    """

    top_level: type[DataclassInstance]
    structs: list[type[DataclassInstance]]
    module_name: str = "params"

    def generate_code(self, custom_type_map: dict[type, str] | None = None) -> list[str]:
        """
        Generates Zig code for this module definition.

        Returns:
            Lines of Zig code.
        """
        code: list[str] = []

        code.extend(
            generate_zig_code(self.top_level, target_type="module", custom_type_map=custom_type_map)
        )

        if self.structs:
            if code:
                code.append("")
            for struct_def in self.structs:
                code.extend(
                    generate_zig_code(
                        struct_def, target_type="struct", custom_type_map=custom_type_map
                    )
                )
                code.append("")

        return code


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


_ZIG_DEFAULT_TYPE_MAP: dict[type, str] = {
    int: "i64",
    float: "f64",
    str: "[:0]const u8",
}


def _base_type(type_hint: TypeHint) -> type:
    if get_origin(type_hint) is Annotated:
        first = get_args(type_hint)[0]
        assert isinstance(first, type)
        return first
    assert isinstance(type_hint, type), f"expected a type, got {type_hint!r}"
    return type_hint


def _zig_default_decl(fname: str, type_hint: TypeHint, value: object) -> str:
    base = _base_type(type_hint)
    zig_type = _ZIG_DEFAULT_TYPE_MAP.get(base)
    if zig_type is None:
        raise UnsupportedType(f"no default formatter for {base!r}")
    if base is int:
        assert isinstance(value, int)
        zig_val = str(value)
    elif base is float:
        assert isinstance(value, (int, float))
        zig_val = repr(float(value))
    elif base is str:
        assert isinstance(value, str)
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        zig_val = f'"{escaped}"'
    else:
        raise UnsupportedType(f"no default formatter for {base!r}")
    return f"    pub const {fname}_default: {zig_type} = {zig_val};"


def get_zig_type(
    type_hint: TypeHint,
    custom_type_map: dict[type, str] | None = None,
) -> str:
    """
    Returns the zig type that should be used for the given Python `type_hint`.
    `custom_type_map` entries take precedence over `ZIG_TYPE_MAP`.
    """
    if (user_defined_type := get_annotation(type_hint, ZigType)) is not None:
        return user_defined_type.value
    if not isinstance(type_hint, type):
        raise UnsupportedType("Non-builtin type annotation with no annotated zig type")
    if custom_type_map and (override := custom_type_map.get(type_hint)) is not None:
        return override
    if (builtin_type := ZIG_TYPE_MAP.get(type_hint)) is None:
        raise UnsupportedType(str(type_hint))
    return builtin_type


def generate_zig_struct(
    struct_name: str,
    field_pairs: Iterable[tuple[str, TypeHint]],
    defaults: Mapping[str, object] | None = None,
    custom_type_map: dict[type, str] | None = None,
) -> list[str]:
    """Generate Zig struct lines from a name, field pairs, and optional defaults.

    Uses inline field syntax for i64/f64 defaults and ``pub const fname_default``
    for ``[]const u8`` defaults, matching what core.zig's comptime machinery expects.
    """
    _defaults = defaults or {}
    _field_pairs = list(field_pairs)
    lines = [f"pub const {struct_name} = struct {{"]
    for fname, ftype in _field_pairs:
        zig_type = get_zig_type(ftype, custom_type_map)
        base = _base_type(ftype)
        if fname in _defaults and base is not str:
            val = _defaults[fname]
            if base is int:
                assert isinstance(val, int)
                zig_val = str(val)
            elif base is float:
                assert isinstance(val, (int, float))
                zig_val = repr(float(val))
            else:
                raise UnsupportedType(f"no inline default formatter for {base!r}")
            lines.append(f"    {fname}: {zig_type} = {zig_val},")
        else:
            lines.append(f"    {fname}: {zig_type},")
    for fname, ftype in _field_pairs:
        if fname in _defaults and _base_type(ftype) is str:
            lines.append(_zig_default_decl(fname, ftype, _defaults[fname]))
    lines.append("};")
    return lines


def generate_zig_code(
    constants: type[DataclassInstance],
    target_type: GenerationTarget = "module",
    custom_type_map: dict[type, str] | None = None,
) -> list[str]:
    """
    Generates Zig code from a dataclass class.

    Args:
        constants: A dataclass class to convert to Zig code.
        target_type: Either "module" for module-level constants or "struct" for a struct definition.
        custom_type_map: Optional overrides for `ZIG_TYPE_MAP` entries.

    Returns:
        Lines of Zig code.
    """
    type_hints = get_type_hints(constants, include_extras=True)
    class_name = constants.__name__

    if target_type == "module":
        return [
            f"pub const {f.name}: {get_zig_type(type_hints[f.name], custom_type_map)} = {getattr(constants, f.name)};"
            for f in fields(constants)
        ]
    elif target_type == "struct":
        field_pairs = [(f.name, type_hints[f.name]) for f in fields(constants)]
        defaults = {f.name: f.default for f in fields(constants) if f.default is not MISSING}
        return generate_zig_struct(class_name, field_pairs, defaults, custom_type_map)
    else:
        raise ValueError(f"Unknown target_type: {target_type}")


def generate_zig_module_code(module_def: ZigModuleDef) -> list[str]:
    """
    Generates Zig code for a module definition with top-level constants and structs.

    Args:
        module_def: A ZigModuleDef instance defining the module structure.

    Returns:
        Lines of Zig code.
    """
    return module_def.generate_code()
