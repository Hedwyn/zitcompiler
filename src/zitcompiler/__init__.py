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
    ZigType,
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
    comptime_params: dict[str, str] | None = None,
) -> Callable[..., object]: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: str,
    *,
    comptime_params: dict[str, str] | None = None,
) -> Callable[..., object]: ...


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: str,
    obj_type: Literal["class"],
    *,
    comptime_params: dict[str, str] | None = None,
) -> type: ...


def zit_compiled(
    module_path: Path,
    symbol_name: str,
    obj_type: ObjType = "func",
    *,
    comptime_params: dict[str, str] | None = None,
) -> object:
    """Compile and load a Zig module, exposing a function or class to Python.

    Compiles the Zig module at module_path and loads the specified symbol.
    Optionally passes compile-time parameters to the Zig compiler.

    Args:
        module_path: Path to the Zig source file.
        symbol_name: Name of the function or class to load from the compiled module.
        obj_type: Either "func" or "class"; determines how the symbol is loaded.
        comptime_params: Compile-time parameters to pass to the Zig compiler.

    Returns:
        The loaded function or class.
    """
    with tempfile.TemporaryDirectory() as tmp:
        dynlib_name = module_path.name.replace(".zig", ".so")
        opts = BuildLibOptions(
            module_path=module_path,
            link_python=True,
            output_path=Path(tmp) / dynlib_name,
            comptime_params=comptime_params,
        )
        dynlib_path = asyncio.run(zig_build_lib(opts))
        match obj_type:
            case "class":
                return load_class(dynlib_path, symbol_name)
            case "func":
                return load_function(dynlib_path, symbol_name)
            case _ as unreachable:
                assert_never(unreachable)


__all__ = [
    "Annotation",
    "BuildLibOptions",
    "UnsupportedType",
    "ZigType",
    "get_annotation",
    "get_annotations",
    "get_zig_type",
    "iter_annotations",
    "load_class",
    "load_function",
    "zig_build_lib",
]
