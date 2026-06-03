from __future__ import annotations

import asyncio
import ctypes
from collections.abc import Callable, Generator
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from zitcompiler import BuildLibOptions, zig_build_lib
from zitcompiler._loader import (
    METH_NOARGS,
    METH_VARARGS,
    PyMethodDef,
    _lib_cache,
    _method_def_registry,
    load_class,
    load_function,
)


@pytest.fixture
def cleanup_caches() -> Generator[None, None, None]:
    """Clear caches before and after each test."""
    _lib_cache.clear()
    _method_def_registry.clear()
    yield
    _lib_cache.clear()
    _method_def_registry.clear()


def test_load_function_basic(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function loads a C function and returns a Python callable."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                mock_py_func = MagicMock()
                mock_newex.return_value = mock_py_func

                result = load_function(Path("test.so"), "test_symbol")

                assert result is mock_py_func
                mock_cdll.assert_called_once()


def test_load_function_uses_symbol_as_default_name(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_function uses symbol name if name parameter not provided."""
    captured_method_def: dict[str, PyMethodDef] = {}

    def capture_byref(obj: PyMethodDef) -> PyMethodDef:
        captured_method_def["obj"] = obj
        return obj

    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader.ctypes.byref", side_effect=capture_byref):
                with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                    mock_py_func = MagicMock()
                    mock_newex.return_value = mock_py_func

                    load_function(Path("test.so"), "test_symbol")

                    assert captured_method_def["obj"].ml_name == b"test_symbol"


def test_load_function_uses_custom_name(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_function uses provided name parameter."""
    captured_method_def: dict[str, PyMethodDef] = {}

    def capture_byref(obj: PyMethodDef) -> PyMethodDef:
        captured_method_def["obj"] = obj
        return obj

    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader.ctypes.byref", side_effect=capture_byref):
                with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                    mock_py_func = MagicMock()
                    mock_newex.return_value = mock_py_func

                    load_function(Path("test.so"), "test_symbol", name="custom_func")

                    assert captured_method_def["obj"].ml_name == b"custom_func"


def test_load_function_sets_docstring(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_function sets the function docstring."""
    captured_method_def: dict[str, PyMethodDef] = {}

    def capture_byref(obj: PyMethodDef) -> PyMethodDef:
        captured_method_def["obj"] = obj
        return obj

    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader.ctypes.byref", side_effect=capture_byref):
                with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                    mock_py_func = MagicMock()
                    mock_newex.return_value = mock_py_func

                    doc = b"This is a test function"
                    load_function(Path("test.so"), "test_symbol", doc=doc)

                    assert captured_method_def["obj"].ml_doc == doc


@pytest.mark.parametrize(
    "flags",
    [
        pytest.param(METH_VARARGS, id="varargs"),
        pytest.param(METH_NOARGS, id="noargs"),
    ],
)
def test_load_function_sets_flags(
    cleanup_caches: Generator[None, None, None],
    flags: int,
) -> None:
    """load_function sets correct method flags."""
    captured_method_def: dict[str, PyMethodDef] = {}

    def capture_byref(obj: PyMethodDef) -> PyMethodDef:
        captured_method_def["obj"] = obj
        return obj

    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader.ctypes.byref", side_effect=capture_byref):
                with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                    mock_py_func = MagicMock()
                    mock_newex.return_value = mock_py_func

                    load_function(Path("test.so"), "test_symbol", flags=flags)

                    assert captured_method_def["obj"].ml_flags == flags


def test_load_function_caches_library(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function caches CDLL instances by resolved path."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.sym1 = MagicMock()
        mock_lib.sym2 = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                mock_py_func = MagicMock()
                mock_newex.return_value = mock_py_func

                load_function(Path("test.so"), "sym1")
                assert mock_cdll.call_count == 1

                load_function(Path("test.so"), "sym2")
                assert mock_cdll.call_count == 1  # Still 1, cached


def test_load_function_resolves_relative_paths(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function resolves relative paths before caching."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.sym1 = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                mock_py_func = MagicMock()
                mock_newex.return_value = mock_py_func

                load_function(Path("test.so"), "sym1")
                cdll_arg = mock_cdll.call_args[0][0]
                assert Path(cdll_arg).is_absolute()


def test_load_function_raises_on_null_symbol(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function raises AssertionError if symbol resolves to NULL."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.missing_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = None

            with pytest.raises(AssertionError, match="resolved to NULL"):
                load_function(Path("test.so"), "missing_symbol")


def test_load_function_raises_if_not_callable(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function raises TypeError if loaded symbol is not callable."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                mock_py_func = "not_callable"
                mock_newex.return_value = mock_py_func

                with pytest.raises(TypeError, match="not a Python function"):
                    load_function(Path("test.so"), "test_symbol")


def test_load_function_registers_method_def(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function registers method def to prevent garbage collection."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                mock_py_func = MagicMock()
                mock_newex.return_value = mock_py_func

                load_function(Path("test.so"), "test_symbol")

                assert id(mock_py_func) in _method_def_registry
                assert isinstance(_method_def_registry[id(mock_py_func)], PyMethodDef)


def test_load_function_passes_null_for_self(cleanup_caches: Generator[None, None, None]) -> None:
    """load_function passes None for self parameter to PyCFunction_NewEx."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib
        mock_lib.test_symbol = MagicMock()

        with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
            mock_cast.return_value.value = 0x12345

            with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                mock_py_func = MagicMock()
                mock_newex.return_value = mock_py_func

                load_function(Path("test.so"), "test_symbol")

                # Should be called with (method_def_ptr, None, None)
                call_args = mock_newex.call_args[0]
                assert call_args[1] is None
                assert call_args[2] is None


def test_load_class_basic(cleanup_caches: Generator[None, None, None]) -> None:
    """load_class loads a Python type object from native extension."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_in_dll = MagicMock()
            mock_char.in_dll = MagicMock(return_value=mock_in_dll)

            with patch("zitcompiler._loader.ctypes.addressof") as mock_addressof:
                mock_addressof.return_value = 0x67890

                with patch("zitcompiler._loader._PyType_Ready") as mock_ready:
                    mock_ready.return_value = 0

                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.return_value.value = mock_type

                        result = load_class(Path("test.so"), "TestType")

                        assert result is mock_type


def test_load_class_caches_library(cleanup_caches: Generator[None, None, None]) -> None:
    """load_class caches CDLL instances by resolved path."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_in_dll = MagicMock()
            mock_char.in_dll = MagicMock(return_value=mock_in_dll)

            with patch("zitcompiler._loader.ctypes.addressof"):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.return_value.value = mock_type

                        load_class(Path("test.so"), "Type1")
                        assert mock_cdll.call_count == 1

                        load_class(Path("test.so"), "Type2")
                        assert mock_cdll.call_count == 1  # Cached


def test_load_class_calls_pytype_ready(cleanup_caches: Generator[None, None, None]) -> None:
    """load_class calls PyType_Ready on the loaded type."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_in_dll = MagicMock()
            mock_char.in_dll = MagicMock(return_value=mock_in_dll)

            with patch("zitcompiler._loader.ctypes.addressof") as mock_addressof:
                mock_addressof.return_value = 0x67890

                with patch("zitcompiler._loader._PyType_Ready") as mock_ready:
                    mock_ready.return_value = 0

                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.return_value.value = mock_type

                        load_class(Path("test.so"), "TestType")

                        mock_ready.assert_called_once_with(0x67890)


def test_load_class_raises_on_pytype_ready_failure(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_class raises RuntimeError if PyType_Ready fails."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_in_dll = MagicMock()
            mock_char.in_dll = MagicMock(return_value=mock_in_dll)

            with patch("zitcompiler._loader.ctypes.addressof"):
                with patch("zitcompiler._loader._PyType_Ready", return_value=-1):
                    with pytest.raises(RuntimeError, match="PyType_Ready failed"):
                        load_class(Path("test.so"), "BadType")


def test_load_class_raises_if_result_not_type(cleanup_caches: Generator[None, None, None]) -> None:
    """load_class raises AssertionError if loaded object is not a type."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_in_dll = MagicMock()
            mock_char.in_dll = MagicMock(return_value=mock_in_dll)

            with patch("zitcompiler._loader.ctypes.addressof"):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_cast.return_value.value = "not a type"

                        with pytest.raises(AssertionError, match="is not a type"):
                            load_class(Path("test.so"), "NotAType")


def test_load_class_resolves_relative_paths(cleanup_caches: Generator[None, None, None]) -> None:
    """load_class resolves relative paths before caching."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_in_dll = MagicMock()
            mock_char.in_dll = MagicMock(return_value=mock_in_dll)

            with patch("zitcompiler._loader.ctypes.addressof"):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.return_value.value = mock_type

                        load_class(Path("test.so"), "TestType")
                        cdll_arg = mock_cdll.call_args[0][0]
                        assert Path(cdll_arg).is_absolute()


def _make_cast_side_effect(mock_type: type) -> Callable[..., MagicMock]:
    """Return a ctypes.cast side_effect that yields mock_type for py_object casts."""

    def side_effect(obj: object, typ: object) -> MagicMock:
        m = MagicMock()
        m.value = mock_type if typ is ctypes.py_object else 0x12345
        return m

    return side_effect


def test_load_class_with_methods_binds_to_type(cleanup_caches: Generator[None, None, None]) -> None:
    """load_class with methods dict sets each method as an attribute on the type."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_char.in_dll.return_value = MagicMock()

            with patch("zitcompiler._loader.ctypes.addressof", return_value=0x67890):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.side_effect = _make_cast_side_effect(mock_type)

                        with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                            mock_method = MagicMock()
                            mock_newex.return_value = mock_method

                            result = load_class(
                                Path("test.so"),
                                "TestType",
                                methods={"greet": "c_greet"},
                            )

                            assert result is mock_type
                            mock_newex.assert_called_once()
                            assert result.greet is mock_method


def test_load_class_with_multiple_methods_binds_all(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_class binds every entry in the methods dict to the type."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_char.in_dll.return_value = MagicMock()

            with patch("zitcompiler._loader.ctypes.addressof", return_value=0x67890):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.side_effect = _make_cast_side_effect(mock_type)

                        method_mocks = [MagicMock(), MagicMock()]
                        with patch(
                            "zitcompiler._loader._PyCFunction_NewEx",
                            side_effect=method_mocks,
                        ):
                            result = load_class(
                                Path("test.so"),
                                "TestType",
                                methods={"foo": "c_foo", "bar": "c_bar"},
                            )

                            assert result.foo is method_mocks[0]
                            assert result.bar is method_mocks[1]


def test_load_class_with_methods_registers_method_defs(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_class stores PyMethodDef structs for all bound methods to prevent GC."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_char.in_dll.return_value = MagicMock()

            with patch("zitcompiler._loader.ctypes.addressof", return_value=0x67890):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.side_effect = _make_cast_side_effect(mock_type)

                        with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                            mock_method = MagicMock()
                            mock_newex.return_value = mock_method

                            load_class(
                                Path("test.so"),
                                "TestType",
                                methods={"greet": "c_greet"},
                            )

                            assert id(mock_method) in _method_def_registry
                            assert isinstance(_method_def_registry[id(mock_method)], PyMethodDef)


def test_load_class_without_methods_skips_binding(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_class with methods=None does not call PyCFunction_NewEx."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_char.in_dll.return_value = MagicMock()

            with patch("zitcompiler._loader.ctypes.addressof", return_value=0x67890):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})
                        mock_cast.return_value.value = mock_type

                        with patch("zitcompiler._loader._PyCFunction_NewEx") as mock_newex:
                            load_class(Path("test.so"), "TestType")

                            mock_newex.assert_not_called()


def test_load_class_with_null_method_symbol_raises(
    cleanup_caches: Generator[None, None, None],
) -> None:
    """load_class raises AssertionError if a method C symbol resolves to NULL."""
    with patch("zitcompiler._loader.ctypes.CDLL") as mock_cdll:
        mock_lib = MagicMock()
        mock_cdll.return_value = mock_lib

        with patch("zitcompiler._loader.ctypes.c_char") as mock_char:
            mock_char.in_dll.return_value = MagicMock()

            with patch("zitcompiler._loader.ctypes.addressof", return_value=0x67890):
                with patch("zitcompiler._loader._PyType_Ready", return_value=0):
                    with patch("zitcompiler._loader.ctypes.cast") as mock_cast:
                        mock_type = type("TestType", (), {})

                        def null_method_cast(obj: object, typ: object) -> MagicMock:
                            m = MagicMock()
                            m.value = mock_type if typ is ctypes.py_object else None
                            return m

                        mock_cast.side_effect = null_method_cast

                        with pytest.raises(AssertionError, match="resolved to NULL"):
                            load_class(
                                Path("test.so"),
                                "TestType",
                                methods={"greet": "c_greet"},
                            )


@pytest.mark.parametrize(
    ("constant", "expected_value"),
    [
        pytest.param(METH_VARARGS, 0x0001, id="meth_varargs"),
        pytest.param(METH_NOARGS, 0x0004, id="meth_noargs"),
    ],
)
def test_meth_constant_values(constant: int, expected_value: int) -> None:
    """Test method flag constants have correct values."""
    assert constant == expected_value


@pytest.fixture
def zigmods_dir() -> Path:
    """Path to the test Zig modules directory."""
    return Path(__file__).parent / "zigmods"


def test_load_function_from_compiled(zigmods_dir: Path, tmp_path: Path) -> None:
    """Test loading a function from a compiled module."""
    module_path = zigmods_dir / "hello_world_func.zig"
    output_path = tmp_path / "hello_world_func.so"

    opts = BuildLibOptions(
        module_path=module_path,
        link_python=True,
        output_path=output_path,
    )
    compiled_lib = asyncio.run(zig_build_lib(opts))
    func = load_function(compiled_lib, "hello_world")

    assert callable(func)


def test_call_loaded_function(zigmods_dir: Path, tmp_path: Path) -> None:
    """Test calling a loaded function."""
    module_path = zigmods_dir / "hello_world_func.zig"
    output_path = tmp_path / "hello_world_call.so"

    opts = BuildLibOptions(
        module_path=module_path,
        link_python=True,
        output_path=output_path,
    )
    compiled_lib = asyncio.run(zig_build_lib(opts))
    func: Callable[..., object] = load_function(compiled_lib, "hello_world")
    result = func()

    assert result is None


def test_full_workflow(zigmods_dir: Path, tmp_path: Path) -> None:
    """Test complete workflow: compile, load, and execute."""
    module_path = zigmods_dir / "hello_world_func.zig"
    output_path = tmp_path / "test_integration.so"

    opts = BuildLibOptions(
        module_path=module_path,
        link_python=True,
        output_path=output_path,
    )
    compiled_path = asyncio.run(zig_build_lib(opts))

    func: Callable[..., object] = load_function(compiled_path, "hello_world")
    result = func()

    assert result is None
