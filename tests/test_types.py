"""
Test for annotations and type conversions from Python to Zig.

@date: 29.05.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated

import pytest

from zitcompiler import (
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


@pytest.mark.parametrize(
    ("type_hint", "expected_count"),
    [
        pytest.param(Annotated[int, ZigType("i32")], 1, id="single_annotation"),
        pytest.param(
            Annotated[int, ZigType("i32"), ZigType("i64")],
            2,
            id="multiple_annotations",
        ),
        pytest.param(
            Annotated[int, "some string", ZigType("i32"), 42],
            1,
            id="mixed_metadata",
        ),
        pytest.param(int, 0, id="unannotated_type"),
        pytest.param(Annotated[int, "just a string", 42], 0, id="no_annotations"),
    ],
)
def test_iter_annotations(type_hint: object, expected_count: int) -> None:
    """iter_annotations yields Annotation objects based on type and metadata."""
    annotations = list(iter_annotations(type_hint))
    assert len(annotations) == expected_count


@pytest.mark.parametrize(
    ("type_hint", "filter_type", "expected_count"),
    [
        pytest.param(
            Annotated[int, ZigType("i32"), "other"],
            ZigType,
            1,
            id="with_filter_matches",
        ),
        pytest.param(
            Annotated[int, ZigType("i32")],
            None,
            1,
            id="no_filter",
        ),
        pytest.param(
            int,
            ZigType,
            0,
            id="unannotated_type",
        ),
        pytest.param(
            Annotated[int, ZigType("i32"), ZigType("i64")],
            ZigType,
            2,
            id="multiple_matching",
        ),
    ],
)
def test_get_annotations(
    type_hint: object,
    filter_type: type[Annotation] | None,
    expected_count: int,
) -> None:
    """get_annotations filters and returns Annotation objects based on type."""
    annotations = get_annotations(type_hint, filter_type)
    assert len(annotations) == expected_count


def test_get_annotations_with_filter_no_match() -> None:
    """get_annotations returns empty list when no annotations match filter."""

    class CustomAnnotation(Annotation):
        pass

    zig_type = ZigType("i32")
    type_hint = Annotated[int, zig_type]

    annotations = get_annotations(type_hint, CustomAnnotation)

    assert len(annotations) == 0


def test_get_annotation_single_match() -> None:
    """get_annotation returns the single matching annotation."""
    zig_type = ZigType("i32")
    type_hint = Annotated[int, zig_type]

    annotation = get_annotation(type_hint, ZigType)

    assert annotation is zig_type


def test_get_annotation_no_match() -> None:
    """get_annotation returns None when no annotations match."""

    class CustomAnnotation(Annotation):
        pass

    zig_type = ZigType("i32")
    type_hint = Annotated[int, zig_type]

    annotation = get_annotation(type_hint, CustomAnnotation)

    assert annotation is None


def test_get_annotation_unannotated_type() -> None:
    """get_annotation returns None for unannotated type."""
    annotation: Annotation | None = get_annotation(int, ZigType)

    assert annotation is None


def test_get_annotation_multiple_matches_raises() -> None:
    """get_annotation raises TypeError when multiple annotations match."""
    zig_type1 = ZigType("i32")
    zig_type2 = ZigType("i64")
    type_hint = Annotated[int, zig_type1, zig_type2]

    with pytest.raises(TypeError, match="more than one annotation"):
        get_annotation(type_hint, ZigType)


def test_get_zig_type_with_annotation() -> None:
    """get_zig_type returns user-defined type from annotation."""
    expected_type = "custom_zig_type"
    zig_type = ZigType(expected_type)
    type_hint = Annotated[int, zig_type]

    result = get_zig_type(type_hint)

    assert result == expected_type


@pytest.mark.parametrize(
    ("builtin_type", "expected_zig_type"),
    [
        pytest.param(int, "i64", id="int"),
        pytest.param(float, "f64", id="float"),
        pytest.param(str, "[:0]const u8", id="str"),
        pytest.param(bytes, "[]const u8", id="bytes"),
    ],
)
def test_get_zig_type_builtin(builtin_type: type, expected_zig_type: str) -> None:
    """get_zig_type returns correct Zig type for builtin types."""
    result = get_zig_type(builtin_type)
    assert result == expected_zig_type


def test_get_zig_type_annotation_overrides_builtin() -> None:
    """get_zig_type prefers annotation over builtin mapping."""
    zig_type = ZigType("custom_int")
    type_hint = Annotated[int, zig_type]

    result = get_zig_type(type_hint)

    assert result == "custom_int"


def test_get_zig_type_unsupported_non_builtin_no_annotation() -> None:
    """get_zig_type raises UnsupportedType for custom type without annotation."""

    class CustomClass:
        pass

    with pytest.raises(UnsupportedType):
        get_zig_type(CustomClass)


def test_get_zig_type_unsupported_unknown_builtin() -> None:
    """get_zig_type raises UnsupportedType for unknown builtin type."""
    with pytest.raises(UnsupportedType):
        get_zig_type(dict)


def test_get_zig_type_with_generic_type_annotation() -> None:
    """get_zig_type works with generic type with annotation."""
    zig_type = ZigType("list_i32")
    type_hint = Annotated[list, zig_type]

    result = get_zig_type(type_hint)

    assert result == "list_i32"


def test_zig_type_dataclass_behavior() -> None:
    """ZigType is a dataclass and can be compared."""
    zig_type1 = ZigType("i32")
    zig_type2 = ZigType("i32")
    zig_type3 = ZigType("i64")

    assert zig_type1 == zig_type2
    assert zig_type1 != zig_type3


def test_integration_full_workflow_annotated_type() -> None:
    """Integration test: get zig type for annotated type."""
    zig_type = ZigType("custom_i32")
    type_hint = Annotated[int, zig_type]
    zig_type_str = get_zig_type(type_hint)

    assert zig_type_str == "custom_i32"


def test_integration_full_workflow_with_multiple_metadata() -> None:
    """Integration test: get zig type from Annotated with mixed metadata."""
    zig_type = ZigType("special_type")
    type_hint = Annotated[str, "documentation", zig_type, 123]

    result = get_zig_type(type_hint)

    assert result == "special_type"


def test_integration_annotation_lifecycle() -> None:
    """Integration test: create, store, and retrieve annotation."""
    zig_type = ZigType("lifecycle_test")
    type_hint = Annotated[float, zig_type]

    retrieved = get_annotation(type_hint, ZigType)

    assert retrieved is zig_type
    assert retrieved.value == "lifecycle_test"


def test_generate_zig_code_builtin_types() -> None:
    """generate_zig_code produces valid Zig for builtin types."""

    @dataclass
    class Constants:
        count: int = 42
        ratio: float = 3.14

    code = generate_zig_code(Constants)

    assert len(code) == 2
    assert "pub const count: i64 = 42;" in code
    assert "pub const ratio: f64 = 3.14;" in code


def test_generate_zig_code_annotated_types() -> None:
    """generate_zig_code uses annotations for type mapping."""

    @dataclass
    class Constants:
        custom_int: Annotated[int, ZigType("u32")] = 100
        custom_value: Annotated[float, ZigType("f32")] = 2.5

    code = generate_zig_code(Constants)

    assert len(code) == 2
    assert "pub const custom_int: u32 = 100;" in code
    assert "pub const custom_value: f32 = 2.5;" in code


def test_generate_zig_code_struct_target() -> None:
    """generate_zig_code generates struct definition with target_type='struct'."""

    @dataclass
    class Config:
        count: int
        ratio: float

    code = generate_zig_code(Config, target_type="struct")

    assert code[0] == "pub const Config = struct {"
    assert "    count: i64," in code
    assert "    ratio: f64," in code
    assert code[-1] == "};"


def test_generate_zig_code_struct_with_annotations() -> None:
    """generate_zig_code struct respects annotations."""

    @dataclass
    class CustomConfig:
        small_int: Annotated[int, ZigType("u16")]
        small_float: Annotated[float, ZigType("f32")]

    code = generate_zig_code(CustomConfig, target_type="struct")

    assert code[0] == "pub const CustomConfig = struct {"
    assert "    small_int: u16," in code
    assert "    small_float: f32," in code
    assert code[-1] == "};"


def test_generate_zig_code_invalid_target_type() -> None:
    """generate_zig_code raises ValueError for invalid target_type."""

    @dataclass
    class Config:
        value: int

    with pytest.raises(ValueError, match="Unknown target_type"):
        generate_zig_code(Config, target_type="invalid")  # type: ignore


def test_generate_zig_code_compiles() -> None:
    """Generated Zig code compiles successfully."""

    @dataclass
    class Constants:
        threshold: int = 100
        multiplier: float = 2.5

    code_lines = generate_zig_code(Constants)

    zig_code = "\n".join(code_lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "constants.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "constants.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"


def test_generate_zig_code_compiles_with_annotations() -> None:
    """Generated Zig code with custom types compiles successfully."""

    @dataclass
    class Constants:
        small_int: Annotated[int, ZigType("u16")] = 512
        small_float: Annotated[float, ZigType("f32")] = 1.5

    code_lines = generate_zig_code(Constants)

    zig_code = "\n".join(code_lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "constants_annotated.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "constants_annotated.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"


def test_generate_zig_code_struct_code_generation() -> None:
    """generate_zig_code generates valid struct definition."""

    @dataclass
    class Point:
        x: int
        y: int
        z: float

    code = generate_zig_code(Point, target_type="struct")
    zig_code = "\n".join(code)

    expected_lines = [
        "pub const Point = struct {",
        "    x: i64,",
        "    y: i64,",
        "    z: f64,",
        "};",
    ]
    assert code == expected_lines


def test_generate_zig_code_struct_compiles() -> None:
    """Generated Zig struct code compiles successfully."""

    @dataclass
    class Point:
        x: int
        y: int

    code_lines = generate_zig_code(Point, target_type="struct")

    zig_code = "\n".join(code_lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "struct.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "struct.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"


def test_generate_zig_code_struct_with_annotations_compiles() -> None:
    """Generated Zig struct with annotations compiles successfully."""

    @dataclass
    class Config:
        port: Annotated[int, ZigType("u16")]
        timeout: Annotated[int, ZigType("u32")]
        threshold: Annotated[float, ZigType("f32")]

    code_lines = generate_zig_code(Config, target_type="struct")

    zig_code = "\n".join(code_lines)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "config_struct.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "config_struct.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"


def test_zig_module_def_creation() -> None:
    """ZigModuleDef can be created with top_level and structs."""

    @dataclass
    class TopLevel:
        debug: int = 1

    @dataclass
    class Point:
        x: int
        y: int

    @dataclass
    class Color:
        r: Annotated[int, ZigType("u8")]
        g: Annotated[int, ZigType("u8")]
        b: Annotated[int, ZigType("u8")]

    module = ZigModuleDef(top_level=TopLevel, structs=[Point, Color])

    assert module.top_level is TopLevel
    assert len(module.structs) == 2


def test_generate_zig_module_code_with_single_struct() -> None:
    """generate_zig_module_code generates module with top-level and struct."""

    @dataclass
    class TopLevel:
        version: int = 1

    @dataclass
    class Config:
        timeout: int

    module = ZigModuleDef(top_level=TopLevel, structs=[Config])

    code = generate_zig_module_code(module)

    assert "pub const version: i64 = 1;" in code
    assert "pub const Config = struct {" in code
    assert "    timeout: i64," in code
    assert "};" in code


def test_generate_zig_module_code_with_multiple_structs() -> None:
    """generate_zig_module_code generates module with multiple structs."""

    @dataclass
    class TopLevel:
        app_name: Annotated[int, ZigType("u8")] = 0

    @dataclass
    class Point:
        x: int
        y: int

    @dataclass
    class Color:
        r: Annotated[int, ZigType("u8")]

    module = ZigModuleDef(
        top_level=TopLevel,
        structs=[Point, Color],
    )

    code = generate_zig_module_code(module)

    assert "pub const Point = struct {" in code
    assert "pub const Color = struct {" in code
    assert "    x: i64," in code
    assert "    r: u8," in code


def test_generate_zig_module_code_with_annotations() -> None:
    """generate_zig_module_code respects annotations in structs."""

    @dataclass
    class TopLevel:
        max_value: int = 100

    @dataclass
    class Config:
        port: Annotated[int, ZigType("u16")]
        timeout: Annotated[int, ZigType("u32")]

    module = ZigModuleDef(top_level=TopLevel, structs=[Config])

    code = generate_zig_module_code(module)
    zig_code = "\n".join(code)

    assert "pub const max_value: i64 = 100;" in code
    assert "port: u16," in zig_code
    assert "timeout: u32," in zig_code


def test_generate_zig_module_code_without_structs() -> None:
    """generate_zig_module_code handles empty structs list."""

    @dataclass
    class TopLevel:
        version: int = 1
        build: int = 42

    module = ZigModuleDef(top_level=TopLevel, structs=[])

    code = generate_zig_module_code(module)

    assert len(code) == 2
    assert "pub const version: i64 = 1;" in code
    assert "pub const build: i64 = 42;" in code


def test_generate_zig_module_code_compiles() -> None:
    """Generated Zig module code compiles successfully."""

    @dataclass
    class TopLevel:
        debug: int = 1

    @dataclass
    class Point:
        x: int
        y: int

    module = ZigModuleDef(top_level=TopLevel, structs=[Point])

    code = generate_zig_module_code(module)
    zig_code = "\n".join(code)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "module.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "module.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"


def test_generate_zig_module_code_with_multiple_structs_compiles() -> None:
    """Generated Zig module with multiple structs compiles successfully."""

    @dataclass
    class TopLevel:
        version: int = 1

    @dataclass
    class Point:
        x: int
        y: int

    @dataclass
    class Size:
        width: Annotated[int, ZigType("u32")]
        height: Annotated[int, ZigType("u32")]

    module = ZigModuleDef(top_level=TopLevel, structs=[Point, Size])

    code = generate_zig_module_code(module)
    zig_code = "\n".join(code)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "multi_module.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "multi_module.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"


def test_zig_module_def_generate_code_method() -> None:
    """ZigModuleDef.generate_code() method works correctly."""

    @dataclass
    class TopLevel:
        debug: int = 1

    @dataclass
    class Point:
        x: int
        y: int

    module = ZigModuleDef(top_level=TopLevel, structs=[Point])

    code = module.generate_code()

    assert "pub const debug: i64 = 1;" in code
    assert "pub const Point = struct {" in code
    assert "    x: i64," in code


def test_zig_module_def_generate_code_with_annotations() -> None:
    """ZigModuleDef.generate_code() respects annotations."""

    @dataclass
    class TopLevel:
        max_size: int = 1000

    @dataclass
    class Config:
        timeout: Annotated[int, ZigType("u32")]
        retries: Annotated[int, ZigType("u8")]

    module = ZigModuleDef(top_level=TopLevel, structs=[Config])

    code = module.generate_code()
    zig_code = "\n".join(code)

    assert "pub const max_size: i64 = 1000;" in code
    assert "timeout: u32," in zig_code
    assert "retries: u8," in zig_code


def test_zig_module_def_generate_code_method_compiles() -> None:
    """Code generated via ZigModuleDef.generate_code() method compiles."""

    @dataclass
    class TopLevel:
        app_version: int = 2

    @dataclass
    class Resolution:
        width: Annotated[int, ZigType("u32")]
        height: Annotated[int, ZigType("u32")]

    module = ZigModuleDef(top_level=TopLevel, structs=[Resolution])

    code = module.generate_code()
    zig_code = "\n".join(code)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        zig_file = tmppath / "module_method.zig"
        zig_file.write_text(zig_code)
        obj_file = tmppath / "module_method.o"

        result = subprocess.run(
            [sys.executable, "-m", "ziglang", "build-obj", str(zig_file), f"-femit-bin={obj_file}"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Compilation failed:\n{result.stderr}"
