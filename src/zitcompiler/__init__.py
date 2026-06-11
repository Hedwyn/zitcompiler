"""
Public interface for zitcompiler.

@date: 28.05.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import asyncio
import os
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


def zit_debug(message: str) -> None:
    if os.environ.get("ZITCOMPILER_DEBUG"):
        print(f"[zitcompiler] {message}", file=sys.stdout)  # noqa: T201


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
        f"{caller_module}\x00{lineno}\x00{symbol_names}\x00{obj_type}\x00{module_def!r}"
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
def zitcompiled(
    module_path: Path,
    symbol_name: str,
    obj_type: Literal["func"],
    *,
    module_def: ZigModuleDef | None = None,
) -> Callable[..., object]: ...


@overload
def zitcompiled(
    module_path: Path,
    symbol_name: str,
    *,
    module_def: ZigModuleDef | None = None,
) -> Callable[..., object]: ...


@overload
def zitcompiled(
    module_path: Path,
    symbol_name: str,
    obj_type: Literal["class"],
    *,
    module_def: ZigModuleDef | None = None,
) -> type: ...


@overload
def zitcompiled(
    module_path: Path,
    symbol_name: list[str],
    obj_type: Literal["func"],
    *,
    module_def: ZigModuleDef | None = None,
) -> tuple[Callable[..., object], ...]: ...


@overload
def zitcompiled(
    module_path: Path,
    symbol_name: list[str],
    *,
    module_def: ZigModuleDef | None = None,
) -> tuple[Callable[..., object], ...]: ...


@overload
def zitcompiled(
    module_path: Path,
    symbol_name: list[str],
    obj_type: Literal["class"],
    *,
    module_def: ZigModuleDef | None = None,
) -> tuple[type, ...]: ...


def zitcompiled(
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

    zit_debug(f"{caller_module}:{lineno} — resolving {module_path.name!r} {tuple(names)}")

    try:
        hash_val = _compute_symbol_hash(
            caller_module,
            lineno,
            module_path,
            tuple(names),
            obj_type,
            module_def,
        )
        hash_str = format(hash_val, "08x")[:8]
        modname = caller_module.split(".")[-1] if caller_module else "anonymous"
        funcname = "_".join(names) if names else "anonymous"
        output_path = caller_file.parent / f"_{modname}_{funcname}_{hash_str}{suffix}"
        zit_debug(f"hash={hash_str} -> {output_path.name}")
    except FileNotFoundError:
        # .zig source not available (e.g. installed wheel) — locate pre-compiled artifact
        zit_debug(
            f"source {module_path!r} not found, scanning {caller_file.parent} for pre-compiled artifact"
        )
        modname = caller_module.split(".")[-1] if caller_module else "anonymous"
        funcname = "_".join(names) if names else "anonymous"
        matches = sorted(caller_file.parent.glob(f"_{modname}_{funcname}_????????{suffix}"))
        if not matches:
            raise RuntimeError(
                f"zitcompiler: no pre-compiled artifact for {module_path.name!r} found in "
                f"{caller_file.parent} and source is unavailable for JIT compilation"
            ) from None
        if len(matches) > 1:
            raise RuntimeError(
                f"zitcompiler: ambiguous pre-compiled artifacts for {module_path.name!r}: {matches}"
            ) from None
        output_path = matches[0]
        zit_debug(f"found pre-compiled artifact: {output_path.name}")

    if not output_path.exists():
        stale = [
            p
            for p in caller_file.parent.glob(f"_{modname}_{funcname}_????????{suffix}")
            if p != output_path
        ]
        if stale:
            zit_debug(f"cache miss — stale artifact(s) found: {[p.name for p in stale]}")
        else:
            zit_debug(f"cache miss — no prior artifact found")
        zit_debug(f"compiling {output_path.name}")
        opts = BuildLibOptions(
            module_path=module_path,
            link_python=True,
            output_path=output_path,
            module_def=module_def,
        )
        asyncio.run(zig_build_lib(opts))
        zit_debug(f"compilation done -> {output_path.name}")
    else:
        zit_debug(f"cache hit — {output_path.name}")

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
    "zit_debug",
]
