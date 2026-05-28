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

from ._compiler import zig_build_lib
from ._loader import load_class, load_function

if TYPE_CHECKING:
    from collections.abc import Callable

type ObjType = Literal["func", "class"]


@overload
def zit_compiled(
    module_path: Path,
    symbol_name: str,
    obj_type: Literal["func"],
) -> Callable[..., object]: ...


@overload
def zit_compiled(module_path: Path, symbol_name: str) -> Callable[..., object]: ...


@overload
def zit_compiled(module_path: Path, symbol_name: str, obj_type: Literal["class"]) -> type: ...


def zit_compiled(module_path: Path, symbol_name: str, obj_type: ObjType = "func") -> object:
    with tempfile.TemporaryDirectory() as tmp:
        dynlib_name = module_path.name.replace(".zig", ".so")
        dynlib_path = asyncio.run(
            zig_build_lib(module_path, link_python=True, output_path=Path(tmp) / dynlib_name),
        )
        match obj_type:
            case "class":
                return load_class(dynlib_path, symbol_name)
            case "func":
                return load_function(dynlib_path, symbol_name)
            case _ as unreachable:
                assert_never(unreachable)


__all__ = [
    "load_class",
    "load_function",
    "zig_build_lib",
]
