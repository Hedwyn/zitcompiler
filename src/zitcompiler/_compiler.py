"""
Main interface on top of the zig compiler.

@author: Baptiste Pestourie
@date: 28.05.2026
"""

from __future__ import annotations

import asyncio
import logging
import sys
import sysconfig
from pathlib import Path

_logger = logging.getLogger(__name__)


class ZigCompilationError(OSError): ...


def find_python_dynlib() -> Path:
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
        lib_names = [n for n in [
            sysconfig.get_config_var("INSTSONAME"),
            sysconfig.get_config_var("LDLIBRARY"),
            f"libpython{ver}.so.1.0",
            f"libpython{ver}.so",
            f"libpython{ver}.dylib",  # macOS non-framework fallback
        ] if n is not None]
        lib_dirs = [d for d in [
            sysconfig.get_config_var("LIBDIR"),
            sysconfig.get_config_var("LIBPL"),
        ] if d is not None]
        for d in lib_dirs:
            for name in lib_names:
                candidate = Path(d) / name
                if candidate.exists():
                    return candidate
    raise FileNotFoundError(f"Could not locate Python {ver} shared library")


async def zig_build_lib(module_path: Path, *, link_python: bool = False) -> None:
    command = [sys.executable, "-m", "ziglang", "build-lib", str(module_path)]
    if link_python:
        python_lib = find_python_dynlib()
        if sys.platform == "win32":
            lib_name = python_lib.stem
        else:
            lib_name = f"python{sysconfig.get_config_var('LDVERSION')}"
        command += [f"-L{python_lib.parent}", f"-l{lib_name}"]
    _logger.info("Calling %s", " ".join(command))
    proc = await asyncio.create_subprocess_exec(*command)
    stdout, stderr = await proc.communicate()
    exit_code = await proc.wait()
    if exit_code != 0:
        raise ZigCompilationError(str(exit_code))
