"""
Public interface for zitcompiler.

@date: 28.05.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Literal, assert_never, overload

from ._compiler import BuildLibOptions, zig_build_lib
from ._loader import load_class, load_function
from ._types import (
    Annotation,
    UnsupportedType,
    ZigModuleDef,
    ZigType,
    generate_zig_code,
    generate_zig_module_code,
    get_annotation,
    get_annotations,
    get_zig_type,
    iter_annotations,
)

if TYPE_CHECKING:
    from collections.abc import Callable

type ObjType = Literal["func", "class"]


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: str,
    obj_type: Literal["func"],
    *,
    module_def: ZigModuleDef | None = None,
) -> Callable[..., object]: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: str,
    *,
    module_def: ZigModuleDef | None = None,
) -> Callable[..., object]: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: str,
    obj_type: Literal["class"],
    *,
    module_def: ZigModuleDef | None = None,
) -> type: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: list[str],
    obj_type: Literal["func"],
    *,
    module_def: ZigModuleDef | None = None,
) -> tuple[Callable[..., object], ...]: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: list[str],
    *,
    module_def: ZigModuleDef | None = None,
) -> tuple[Callable[..., object], ...]: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: list[str],
    obj_type: Literal["class"],
    *,
    module_def: ZigModuleDef | None = None,
) -> tuple[type, ...]: ...


def zit_compiled(
    module_path: Path,
    symbol_name: str | list[str],
    obj_type: ObjType = "func",
    *,
    module_def: ZigModuleDef | None = None,
) -> object:
    """Compile and load a Zig module, exposing one or more functions or classes to Python.

    Compiles the Zig module at module_path and loads the specified symbol(s).
    When multiple symbol names are provided, all are loaded from a single compilation.

    Args:
        module_path: Path to the Zig source file.
        symbol_name: Name or sequence of names of symbols to load from the compiled module.
        obj_type: Either "func" or "class"; determines how the symbol is loaded.
        module_def: Optional ZigModuleDef with module-level constants and struct definitions.

    Returns:
        The loaded function or class, or a tuple of them when multiple names are given.
    """
    with tempfile.TemporaryDirectory() as tmp:
        dynlib_name = module_path.name.replace(".zig", ".so")
        opts = BuildLibOptions(
            module_path=module_path,
            link_python=True,
            output_path=Path(tmp) / dynlib_name,
            module_def=module_def,
        )
        dynlib_path = asyncio.run(zig_build_lib(opts))

        names = [symbol_name] if isinstance(symbol_name, str) else list(symbol_name)
        loaded: tuple[type[object], ...] | tuple[Callable[..., object], ...]
        match obj_type:
            case "class":
                loaded = tuple(load_class(dynlib_path, n) for n in names)
            case "func":
                loaded = tuple(load_function(dynlib_path, n) for n in names)
            case _ as unreachable:
                assert_never(unreachable)

        return loaded[0] if isinstance(symbol_name, str) else loaded


__all__ = [
    "Annotation",
    "BuildLibOptions",
    "UnsupportedType",
    "ZigModuleDef",
    "ZigType",
    "generate_zig_code",
    "generate_zig_module_code",
    "get_annotation",
    "get_annotations",
    "get_zig_type",
    "iter_annotations",
    "load_class",
    "load_function",
    "zig_build_lib",
]
