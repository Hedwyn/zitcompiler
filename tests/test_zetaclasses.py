"""
Test suite for zetaclasses.
Verifies that they match dataclasses behavior.
"""

from __future__ import annotations

from dataclasses import MISSING, dataclass, fields

import pytest

from zitcompiler.zetaclasses import zetaclass


class _Person:
    name: str = "John"
    age: int = 35
    height: float = 1.77


# note: using this syntax instead of PersonDatacls = ...
# to avoid confusing type checkers
@dataclass()
class PersonDatacls(_Person): ...


@zetaclass
class PersonZetacls(_Person): ...


def test_init() -> None:
    person_datacls = PersonDatacls()
    person_zetacls = PersonZetacls()

    for field in fields(PersonDatacls):
        assert getattr(person_datacls, field.name) == getattr(person_zetacls, field.name)


def test_eq() -> None:
    person_zetacls = PersonZetacls()
    assert person_zetacls == PersonZetacls()
    assert person_zetacls != PersonZetacls(name="Jane", age=25, height=1.65)


# ── init=False ────────────────────────────────────────────────────────────────


class _Counter:
    count: int = 0


@dataclass(init=False)
class CounterNoInitDatacls(_Counter): ...


@zetaclass(init=False)
class CounterNoInitZetacls(_Counter): ...


def test_no_init_instantiates_without_args() -> None:
    CounterNoInitDatacls()
    CounterNoInitZetacls()


def test_no_init_rejects_positional_args() -> None:
    extra: list[object] = [42]
    with pytest.raises(TypeError):
        CounterNoInitDatacls(*extra)
    with pytest.raises(TypeError):
        CounterNoInitZetacls(*extra)


# ── eq=False ──────────────────────────────────────────────────────────────────


class _Point:
    x: int = 0
    y: int = 0


@dataclass(eq=False)
class PointNoEqDatacls(_Point): ...


@zetaclass(eq=False)
class PointNoEqZetacls(_Point): ...


# ── dataclass fields ──────────────────────────────────────────────────────────


@dataclass()
class WithDefaultsDatacls:
    required: float
    age: int = 35
    label: str = "hello"
    score: float = 1.5


@zetaclass
class WithDefaultsZetacls:
    required: float
    age: int = 35
    label: str = "hello"
    score: float = 1.5


@zetaclass
class RequiredAfterDefaults:
    age: int = 35
    label: str = "hello"
    score: float = 1.5
    required: float


def test_fields_on_type() -> None:
    dc_fields = {f.name: f for f in fields(WithDefaultsDatacls)}
    zc_fields = {f.name: f for f in fields(WithDefaultsZetacls)}

    assert set(dc_fields) == set(zc_fields)
    for name, dc_f in dc_fields.items():
        zc_f = zc_fields[name]
        assert zc_f.name == dc_f.name
        assert zc_f.default == dc_f.default
    # zetaclass resolves annotations via get_type_hints, so Field.type holds the
    # actual type object rather than a string (as @dataclass does under PEP 563)
    expected_types: dict[str, type] = {"required": float, "age": int, "label": str, "score": float}
    for name, zc_f in zc_fields.items():
        assert zc_f.type == expected_types[name]


def test_fields_on_instance() -> None:
    instance = WithDefaultsZetacls(required=0.0)
    assert fields(instance) == fields(WithDefaultsZetacls)


def test_fields_required_has_missing_default() -> None:
    zc_f = {f.name: f for f in fields(WithDefaultsZetacls)}["required"]
    assert zc_f.default is MISSING
    assert zc_f.default_factory is MISSING  # type: ignore[misc]


def test_fields_with_defaults_match_values() -> None:
    zc_fields = {f.name: f for f in fields(WithDefaultsZetacls)}
    assert zc_fields["age"].default == 35
    assert zc_fields["label"].default == "hello"
    assert zc_fields["score"].default == 1.5


def test_fields_required_after_defaults() -> None:
    zc_fields = {f.name: f for f in fields(RequiredAfterDefaults)}
    assert zc_fields["required"].default is MISSING
    assert zc_fields["age"].default == 35


def test_no_eq_uses_identity() -> None:
    d1, d2 = PointNoEqDatacls(), PointNoEqDatacls()
    z1, z2 = PointNoEqZetacls(), PointNoEqZetacls()
    # Different instances with equal fields are NOT equal (identity comparison)
    assert d1 != d2
    assert z1 != z2
    # Same instance equals itself
    assert d1 == d1
    assert z1 == z1
