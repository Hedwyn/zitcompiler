"""
Utilities to load Python objects exported from compiled native extensions.

@author: Baptiste Pestourie
@date: 28.05.2026
"""

from __future__ import annotations

import ctypes
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

METH_VARARGS = 0x0001
METH_NOARGS = 0x0004


class PyMethodDef(ctypes.Structure):
    _fields_ = [
        ("ml_name", ctypes.c_char_p),
        ("ml_meth", ctypes.c_void_p),
        ("ml_flags", ctypes.c_int),
        ("ml_doc", ctypes.c_char_p),
    ]


_PyCFunction_NewEx = ctypes.pythonapi.PyCFunction_NewEx
_PyCFunction_NewEx.restype = ctypes.py_object
_PyCFunction_NewEx.argtypes = [
    ctypes.POINTER(PyMethodDef),
    ctypes.c_void_p,  # self — NULL for module-level functions
    ctypes.py_object,
]

_PyType_Ready = ctypes.pythonapi.PyType_Ready
_PyType_Ready.restype = ctypes.c_int
_PyType_Ready.argtypes = [ctypes.c_void_p]  # raw pointer — safe before ob_type is set

# Keeps library handles alive — prevents dlclose() from invalidating returned objects.
_lib_cache: dict[Path, ctypes.CDLL] = {}

# Keeps PyMethodDef structs alive — the C function object holds a bare pointer into
# this struct; if it is GC'd the pointer dangles and the interpreter will segfault.
_method_def_registry: dict[int, PyMethodDef] = {}


def load_function(
    path: Path,
    symbol: str,
    *,
    name: str | None = None,
    doc: bytes = b"",
    flags: int = METH_VARARGS,
) -> Callable[..., object]:
    """Load a C function from a native extension and wrap it as a Python callable.

    Args:
        path: Path to the compiled shared library.
        symbol: Name of the exported C function.
        name: Optional Python name for the function; defaults to symbol.
        doc: Optional docstring for the function.
        flags: Method flags (METH_VARARGS or METH_NOARGS).

    Returns:
        A Python callable wrapping the C function.
    """
    resolved = path.resolve()
    if resolved not in _lib_cache:
        _lib_cache[resolved] = ctypes.CDLL(str(resolved))
    lib = _lib_cache[resolved]
    c_func_ptr = getattr(lib, symbol)
    func_addr = ctypes.cast(c_func_ptr, ctypes.c_void_p).value
    assert func_addr is not None, f"Symbol '{symbol}' resolved to NULL"
    method_def = PyMethodDef(
        ml_name=(name or symbol).encode(),
        ml_meth=func_addr,
        ml_flags=flags,
        ml_doc=doc,
    )
    py_func: object = _PyCFunction_NewEx(ctypes.byref(method_def), None, None)
    _method_def_registry[id(py_func)] = method_def
    if not callable(py_func):
        raise TypeError(f"Loaded symbol is not a Python function: {py_func}")
    return py_func


def load_class(
    path: Path,
    symbol: str,
    *,
    methods: dict[str, str] | None = None,
) -> type[object]:
    """Load a Python type object from a native extension.

    Args:
        path: Path to the compiled shared library.
        symbol: Name of the exported PyTypeObject.
        methods: Optional mapping of Python method name -> C function name to bind.

    Returns:
        The loaded type object as a Python class.
    """
    methods = methods or {}
    resolved = path.resolve()
    if resolved not in _lib_cache:
        _lib_cache[resolved] = ctypes.CDLL(str(resolved))
    lib = _lib_cache[resolved]
    addr = ctypes.addressof(ctypes.c_char.in_dll(lib, symbol))
    if _PyType_Ready(addr) < 0:
        raise RuntimeError(f"PyType_Ready failed for '{symbol}'")
    result = ctypes.cast(addr, ctypes.py_object).value
    assert isinstance(result, type), f"'{symbol}' is not a type object, got {type(result)}"
    for py_name, c_name in methods.items():
        c_func_ptr = getattr(lib, c_name)
        func_addr = ctypes.cast(c_func_ptr, ctypes.c_void_p).value
        assert func_addr is not None, f"Symbol '{c_name}' resolved to NULL"
        method_def = PyMethodDef(
            ml_name=py_name.encode(),
            ml_meth=func_addr,
            ml_flags=METH_VARARGS,
            ml_doc=b"",
        )
        py_func: object = _PyCFunction_NewEx(ctypes.byref(method_def), None, None)
        _method_def_registry[id(py_func)] = method_def
        setattr(result, py_name, py_func)
    return result
