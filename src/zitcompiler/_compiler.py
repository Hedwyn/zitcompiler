"""
Main interface on top of the zig compiler.

@author: Baptiste Pestourie
@date: 28.05.2026
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import sys
import sysconfig
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from ._types import ZigModuleDef

if TYPE_CHECKING:
    from collections.abc import Generator

_logger = logging.getLogger(__name__)


@dataclass
class BuildLibOptions:
    module_path: Path
    link_python: bool = False
    output_path: Path | None = None
    module_def: ZigModuleDef | None = None
    incremental: bool | None = None
    extra_deps: dict[str, Path] | None = None


class ZigCompilationError(OSError): ...


def find_python_dynlib() -> Path:
    """Locate the Python shared library for the current interpreter."""
    ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    if sys.platform == "win32":
        # DLL lives next to the interpreter or in the base prefix, named pythonXY.dll
        dll_name = f"python{sys.version_info.major}{sys.version_info.minor}.dll"
        search_dirs = [
            Path(sys.executable).parent,
            Path(sys.base_prefix),
            Path(sys.base_prefix) / "DLLs",
        ]
        for d in search_dirs:
            candidate = d / dll_name
            if candidate.exists():
                return candidate
    else:
        lib_names = [
            n
            for n in [
                sysconfig.get_config_var("INSTSONAME"),
                sysconfig.get_config_var("LDLIBRARY"),
                f"libpython{ver}.so.1.0",
                f"libpython{ver}.so",
                f"libpython{ver}.dylib",  # macOS non-framework fallback
            ]
            if isinstance(n, str)
        ]
        lib_dirs = [
            d
            for d in [
                sysconfig.get_config_var("LIBDIR"),
                sysconfig.get_config_var("LIBPL"),
            ]
            if isinstance(d, str)
        ]
        for d in lib_dirs:
            for name in lib_names:
                candidate = Path(d) / name
                if candidate.exists():
                    return candidate
    raise FileNotFoundError(f"Could not locate Python {ver} shared library")


@contextlib.contextmanager
def _module_tempfile(module_def: ZigModuleDef) -> Generator[tuple[str, str], None, None]:
    """Create a temporary Zig module from a ZigModuleDef.

    Yields:
        Tuple of (file_path, module_name)
    """
    code = module_def.generate_code()
    zig_source = "\n".join(code)
    suffix = f"{module_def.module_name}.zig"
    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=True) as f:
        f.write(zig_source)
        f.flush()
        yield f.name, module_def.module_name


async def zig_build_lib(opts: BuildLibOptions) -> Path:
    """Compile a Zig module to a shared library.

    Invokes the zig build-lib command with the provided options, optionally
    linking against the Python runtime and passing module definitions.

    Returns the path to the generated shared library.
    """
    output_path = opts.output_path
    if output_path is None:
        if sys.platform == "win32":
            suffix = ".dll"
        elif sys.platform == "darwin":
            suffix = ".dylib"
        else:
            suffix = ".so"
        output_path = Path.cwd() / (opts.module_path.stem + suffix)
    ctx = (
        _module_tempfile(opts.module_def)
        if opts.module_def is not None
        else contextlib.nullcontext()
    )
    with ctx as module_info:
        command = [sys.executable, "-m", "ziglang", "build-lib"]
        all_deps: list[tuple[str, str]] = []
        if module_info is not None:
            module_file, module_name = module_info
            all_deps.append((module_name, module_file))
        if opts.extra_deps:
            all_deps.extend((name, str(path)) for name, path in opts.extra_deps.items())
        if all_deps:
            for dep_name, _ in all_deps:
                command += ["--dep", dep_name]
            command += [f"-Mmain={opts.module_path}"]
            for dep_name, dep_path in all_deps:
                command += [f"-M{dep_name}={dep_path}"]
        else:
            command += [str(opts.module_path)]
        command += [f"-femit-bin={output_path}"]
        if opts.incremental is True:
            if sys.platform not in ("win32", "darwin"):
                _logger.warning(
                    "Incremental compilation (-fincremental) is not yet supported by the Zig elf2 "
                    "linker for shared library targets on ELF platforms. Compilation will likely "
                    "fail. See https://github.com/ziglang/zig/issues/21165"
                )
            command += ["-fincremental"]
        elif opts.incremental is False:
            command += ["-fno-incremental"]
        if opts.link_python:
            python_lib = find_python_dynlib()
            lib_name = (
                python_lib.stem
                if sys.platform == "win32"
                else f"python{sysconfig.get_config_var('LDVERSION')}"
            )
            command += [f"-L{python_lib.parent}", f"-l{lib_name}"]
        _logger.info("Calling %s", " ".join(command))
        proc = await asyncio.create_subprocess_exec(*command)
        await proc.communicate()
        if proc.returncode != 0:
            raise ZigCompilationError(str(proc.returncode))
    return output_path
