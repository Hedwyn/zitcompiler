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
    if kwargs:
        raise NotImplementedError(
            f"zetaclass: keyword arguments not yet supported: {', '.join(sorted(kwargs))}",
        )

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
    zig_init = str(init).lower()
    zig_eq = str(eq).lower()
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
            f".{{ .init = {zig_init}, .eq = {zig_eq} }});",
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
    return type(class_name, (native_type,), {"__dataclass_fields__": dc_fields})


def zetaclass(
    cls: type | None = None,
    **kwargs: Unpack[DataclassKwargs],
) -> type | Callable[[type], type]:
    """Compile and load a native dataclass-compatible type backed by Zig.

    Inspects annotations from cls and its bases, compiles a Zig struct with
    native __init__ (including defaults) and __eq__ slots.

    Accepts the same keyword arguments as @dataclass. Supported: init, eq.
    Any other argument raises NotImplementedError.

    Usable as @zetaclass or @zetaclass(init=False, eq=True, ...).
    """
    if cls is not None:
        return _zetaclass_impl(cls, **kwargs)

    def _decorator(cls: type) -> type:
        return _zetaclass_impl(cls, **kwargs)

    return _decorator
