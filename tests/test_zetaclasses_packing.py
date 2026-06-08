"""
Tests for pack / unpack methods on validated zetaclasses.

@date: 08.06.2026
@author: Baptiste Pestourie
"""

from __future__ import annotations

import pytest

from zitcompiler.zetaclasses import zetaclass


@zetaclass(validate=True, packed=True)
class _NumericOnly:
    x: int = 0
    y: float = 0.0


@zetaclass(validate=True, packed=True)
class _WithStrings:
    name: str = "hello"
    age: int = 0
    score: float = 0.0


@zetaclass(frozen=True, validate=True, packed=True)
class _FrozenNumeric:
    a: int = 1
    b: float = 2.0


# ── pack/unpack option activation ─────────────────────────────────────────────


def test_packed_without_validate_auto_enables_validate() -> None:
    @zetaclass(packed=True)
    class _Auto:
        x: int = 0

    obj = _Auto(x=7)
    assert _Auto.unpack(obj.pack()).x == 7


def test_packed_with_explicit_validate_true_works() -> None:
    @zetaclass(packed=True, validate=True)
    class _Explicit:
        x: int = 0

    obj = _Explicit(x=3)
    assert _Explicit.unpack(obj.pack()).x == 3


def test_packed_with_explicit_validate_false_raises() -> None:
    with pytest.raises(ValueError):

        @zetaclass(packed=True, validate=False)
        class _Bad:
            x: int = 0


def test_pack_unpack_absent_without_packed() -> None:
    @zetaclass(validate=True)
    class _NoPack:
        x: int = 0

    obj = _NoPack(x=1)
    assert not hasattr(obj, "pack")
    assert not hasattr(_NoPack, "unpack")


# ── roundtrip correctness ──────────────────────────────────────────────────────


def test_pack_unpack_numeric_roundtrip() -> None:
    obj = _NumericOnly(x=42, y=3.14)
    data = obj.pack()
    assert isinstance(data, bytes)
    obj2 = _NumericOnly.unpack(data)
    assert obj2.x == obj.x
    assert obj2.y == obj.y


def test_pack_unpack_with_strings_roundtrip() -> None:
    obj = _WithStrings(name="Alice", age=30, score=9.5)
    data = obj.pack()
    assert isinstance(data, bytes)
    obj2 = _WithStrings.unpack(data)
    assert obj2.name == "Alice"
    assert obj2.age == 30
    assert obj2.score == 9.5


def test_pack_unpack_frozen_numeric_roundtrip() -> None:
    obj = _FrozenNumeric(a=7, b=2.718)
    data = obj.pack()
    obj2 = _FrozenNumeric.unpack(data)
    assert obj2.a == 7
    assert obj2.b == 2.718


def test_pack_unpack_string_identity_preserved() -> None:
    obj = _WithStrings(name="Bob", age=25, score=7.0)
    obj2 = _WithStrings.unpack(obj.pack())
    assert obj == obj2


def test_pack_unpack_empty_string() -> None:
    obj = _WithStrings(name="", age=0, score=0.0)
    obj2 = _WithStrings.unpack(obj.pack())
    assert obj2.name == ""
    assert obj == obj2


def test_unpack_wrong_length_raises() -> None:
    with pytest.raises(ValueError):
        _NumericOnly.unpack(b"tooshort")


def test_pack_unpack_numeric_defaults() -> None:
    obj = _NumericOnly()
    obj2 = _NumericOnly.unpack(obj.pack())
    assert obj2.x == 0
    assert obj2.y == 0.0
