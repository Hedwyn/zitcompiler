"""
Public interface for zitcompiler.

@date: 28.05.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import asyncio
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, assert_never, overload

from ._compiler import BuildLibOptions, zig_build_lib
from ._loader import load_class, load_function
from ._types import (
    ZIG_TYPE_MAP,
    Annotation,
    UnsupportedType,
    ZigModuleDef,
    ZigType,
    generate_zig_code,
    generate_zig_module_code,
    generate_zig_struct,
    get_annotation,
    get_annotations,
    get_zig_type,
    iter_annotations,
)

if TYPE_CHECKING:
    from collections.abc import Callable

type ObjType = Literal["func", "class"]


def _compute_symbol_hash(
    caller_module: str,
    lineno: int,
    module_path: Path,
    symbol_names: tuple[str, ...],
    obj_type: ObjType,
    module_def: ZigModuleDef | None,
) -> int:
    source_content = module_path.read_bytes()
    metadata = (
        f"{caller_module}\x00{lineno}\x00{module_path}\x00"
        f"{symbol_names}\x00{obj_type}\x00{module_def!r}"
    ).encode()
    return zlib.crc32(source_content + metadata)


@dataclass
class _SymbolRecord:
    module_path: Path
    symbol_names: tuple[str, ...]
    obj_type: ObjType
    module_def: ZigModuleDef | None
    caller_module: str
    lineno: int
    func: object
    output_path: Path

    def hash(self) -> int:
        return _compute_symbol_hash(
            self.caller_module,
            self.lineno,
            self.module_path,
            self.symbol_names,
            self.obj_type,
            self.module_def,
        )


_COMPILED_SYMBOLS: list[_SymbolRecord] = []


def get_all_compiled_symbols() -> list[_SymbolRecord]:
    return _COMPILED_SYMBOLS.copy()


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
    _frame = sys._getframe(1)
    caller_module: str = _frame.f_globals.get("__name__", "")
    lineno: int = _frame.f_lineno
    caller_file = Path(_frame.f_globals.get("__file__", "."))
    names = [symbol_name] if isinstance(symbol_name, str) else list(symbol_name)

    if sys.platform == "win32":
        suffix = ".dll"
    elif sys.platform == "darwin":
        suffix = ".dylib"
    else:
        suffix = ".so"

    hash_val = _compute_symbol_hash(
        caller_module,
        lineno,
        module_path,
        tuple(names),
        obj_type,
        module_def,
    )
    hash_str = format(hash_val, "08x")[:8]
    output_path = caller_file.parent / f"{module_path.stem}___{hash_str}{suffix}"

    if not output_path.exists():
        opts = BuildLibOptions(
            module_path=module_path,
            link_python=True,
            output_path=output_path,
            module_def=module_def,
        )
        asyncio.run(zig_build_lib(opts))

    loaded: tuple[type[object], ...] | tuple[Callable[..., object], ...]
    match obj_type:
        case "class":
            loaded = tuple(load_class(output_path, n) for n in names)
        case "func":
            loaded = tuple(load_function(output_path, n) for n in names)
        case _ as unreachable:
            assert_never(unreachable)

    result: object = loaded[0] if isinstance(symbol_name, str) else loaded
    _COMPILED_SYMBOLS.append(
        _SymbolRecord(
            module_path=module_path,
            symbol_names=tuple(names),
            obj_type=obj_type,
            module_def=module_def,
            caller_module=caller_module,
            lineno=lineno,
            func=result,
            output_path=output_path,
        ),
    )
    return result


__all__ = [
    "ZIG_TYPE_MAP",
    "Annotation",
    "BuildLibOptions",
    "UnsupportedType",
    "ZigModuleDef",
    "ZigType",
    "generate_zig_code",
    "generate_zig_module_code",
    "generate_zig_struct",
    "get_all_compiled_symbols",
    "get_annotation",
    "get_annotations",
    "get_zig_type",
    "iter_annotations",
    "load_class",
    "load_function",
    "zig_build_lib",
]
