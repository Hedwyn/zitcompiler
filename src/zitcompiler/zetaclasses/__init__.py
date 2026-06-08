"""
Implements the zetaclass decorator.
Populates the dataclass-like methods with native code.

@date: 04.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import asyncio
import dataclasses
import os
import tempfile
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict, Unpack, get_type_hints

from zitcompiler import (
    ZIG_TYPE_MAP,
    BuildLibOptions,
    generate_zig_struct,
    load_class,
    zig_build_lib,
)

if TYPE_CHECKING:
    from collections.abc import Callable


class DataclassKwargs(TypedDict, total=False):
    init: bool
    repr: bool
    eq: bool
    order: bool
    unsafe_hash: bool
    frozen: bool
    match_args: bool
    kw_only: bool
    slots: bool
    weakref_slot: bool


_CORE_ZIG = Path(__file__).parent / "core.zig"


def _zetaclass_impl(cls: type, **kwargs: Unpack[DataclassKwargs]) -> type:
    init = kwargs.pop("init", True)
    eq = kwargs.pop("eq", True)
    order = kwargs.pop("order", False)
    frozen = kwargs.pop("frozen", False)
    unsafe_hash = kwargs.pop("unsafe_hash", False)
    kw_only = kwargs.pop("kw_only", False)
    weakref_slot = kwargs.pop("weakref_slot", False)
    repr_opt = kwargs.pop("repr", True)
    match_args = kwargs.pop("match_args", True)
    if "slots" in kwargs:
        if not kwargs.pop("slots"):
            warnings.warn(
                "zetaclass: slots=False has no effect; native struct layout is always slotted",
                UserWarning,
                stacklevel=3,
            )
    kwargs.pop("slots", None)
    if kwargs:
        raise NotImplementedError(
            f"zetaclass: keyword arguments not yet supported: {', '.join(sorted(kwargs))}",
        )
    if order and not eq:
        raise ValueError("zetaclass: eq must be true if order is true")
    hash_opt = frozen or unsafe_hash
    if hash_opt and not eq:
        raise ValueError("zetaclass: cannot use hash with eq=False")

    hints = get_type_hints(cls)
    field_names = list(hints.keys())
    field_pairs = [(n, hints[n]) for n in field_names]

    for _, ftype in field_pairs:
        if ftype not in ZIG_TYPE_MAP:
            raise TypeError(f"zetaclass: unsupported field type {ftype!r}")

    # Collect defaults by walking MRO (closest definition wins)
    defaults: dict[str, object] = {}
    for name in field_names:
        for base in cls.__mro__:
            if name in vars(base) and not isinstance(vars(base)[name], type):
                defaults[name] = vars(base)[name]
                break

    class_name = cls.__name__
    data_type = f"{class_name}Data"

    def _make_boolean(v: bool) -> str:
        return str(v).lower()

    params_src = "\n".join(
        [
            'const core = @import("core");',
            "",
            *generate_zig_struct(data_type, field_pairs, defaults),
            "",
            f"pub const {class_name}Object = core.wrapAsPythonObject({data_type});",
            "",
            f"pub export var {class_name}Type: core.PyTypeObject = "
            f'core.makeTypeObject({class_name}Object, "{class_name}", '
            f".{{ .init = {_make_boolean(init)}, .repr = {_make_boolean(repr_opt)}, "
            f".eq = {_make_boolean(eq)}, .order = {_make_boolean(order)}, "
            f".hash = {_make_boolean(hash_opt)}, .frozen = {_make_boolean(frozen)}, "
            f".kw_only = {_make_boolean(kw_only)}, .weakref_slot = {_make_boolean(weakref_slot)} }});",
        ]
    )

    with tempfile.TemporaryDirectory() as tmp:
        params_path = Path(tmp) / "params.zig"
        params_path.write_text(params_src)
        if (dump_path := os.environ.get("ZETACLASS_DUMP_PATH")) is not None:
            try:
                Path(dump_path).write_text(params_src)
            except OSError as exc:
                raise OSError(
                    f"Failed to dump params source code to {dump_path}"
                    "This happens beucase ZETACLASS_DUMP_PATH is set",
                ) from exc

        out_path = Path(tmp) / f"{class_name}.so"

        build_opts = BuildLibOptions(
            module_path=params_path,
            link_python=True,
            output_path=out_path,
            extra_deps={"core": _CORE_ZIG},
        )
        so_path = asyncio.run(zig_build_lib(build_opts))
        native_type = load_class(so_path, f"{class_name}Type")

    cls.__annotations__ = {n: t for n, t in field_pairs}
    dataclasses.dataclass(cls, init=False, eq=False, repr=False)
    dc_fields: dict[str, object] = cls.__dataclass_fields__
    match_args_tuple = tuple(field_names) if match_args else ()
    return type(
        class_name,
        (native_type,),
        {
            "__dataclass_fields__": dc_fields,
            "__match_args__": match_args_tuple,
        },
    )


def zetaclass(
    cls: type | None = None,
    **kwargs: Unpack[DataclassKwargs],
) -> type | Callable[[type], type]:
    """Drop-in native replacement for @dataclass backed by a JIT-compiled Zig struct.

    Accepts all the same keyword arguments as @dataclass:
      init, repr, eq, order, unsafe_hash, frozen, match_args, kw_only,
      slots, weakref_slot.

    Usable as @zetaclass or @zetaclass(frozen=True, order=True, ...).

    Differences from @dataclass
    ---------------------------
    slots: always effectively True — the underlying Zig struct uses a fixed
        memory layout equivalent to __slots__. Passing slots=False emits a
        UserWarning and is otherwise ignored.

    __hash__: when hash is enabled (frozen=True or unsafe_hash=True) the hash
        value is computed by a native Wyhash over the raw field bytes and will
        differ numerically from the tuple-based hash that @dataclass produces.
        The hash contract (equal objects have equal hashes) is preserved.
    """
    if cls is not None:
        return _zetaclass_impl(cls, **kwargs)

    def _decorator(cls: type) -> type:
        return _zetaclass_impl(cls, **kwargs)

    return _decorator
