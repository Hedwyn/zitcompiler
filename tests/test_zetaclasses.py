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


# ── order=True ────────────────────────────────────────────────────────────────


@dataclass(order=True)
class RankedDatacls:
    tier: int = 0
    name: str = ""


@zetaclass(order=True)
class RankedZetacls:
    tier: int = 0
    name: str = ""


def test_order_lt_by_first_field() -> None:
    for cls in (RankedDatacls, RankedZetacls):
        assert cls(1, "b") < cls(2, "a")


def test_order_lt_by_second_field_when_first_equal() -> None:
    for cls in (RankedDatacls, RankedZetacls):
        assert cls(1, "a") < cls(1, "b")


def test_order_le_equal_instances() -> None:
    for cls in (RankedDatacls, RankedZetacls):
        a = cls(1, "x")
        b = cls(1, "x")
        assert a <= b
        assert b <= a


def test_order_gt() -> None:
    for cls in (RankedDatacls, RankedZetacls):
        assert cls(2) > cls(1)


def test_order_ge_equal() -> None:
    for cls in (RankedDatacls, RankedZetacls):
        a = cls(3, "z")
        assert a >= cls(3, "z")


def test_order_false_raises_type_error() -> None:
    z1, z2 = PersonZetacls(), PersonZetacls()
    with pytest.raises(TypeError):
        _ = z1 < z2
    with pytest.raises(TypeError):
        _ = z1 > z2


def test_order_requires_eq() -> None:
    with pytest.raises(ValueError):
        dataclass(eq=False, order=True)(_Point)
    with pytest.raises(ValueError):
        zetaclass(eq=False, order=True)(_Point)


# ── frozen=True ───────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class ImmutablePointDatacls:
    x: float = 0.0
    label: str = ""


@zetaclass(frozen=True)
class ImmutablePointZetacls:
    x: float = 0.0
    label: str = ""


def test_frozen_init_works() -> None:
    for cls in (ImmutablePointDatacls, ImmutablePointZetacls):
        p = cls(1.0, "a")
        assert p.x == 1.0
        assert p.label == "a"


def test_frozen_rejects_numeric_setattr() -> None:
    for cls in (ImmutablePointDatacls, ImmutablePointZetacls):
        with pytest.raises(AttributeError):
            setattr(cls(), "x", 9.0)


def test_frozen_rejects_string_setattr() -> None:
    for cls in (ImmutablePointDatacls, ImmutablePointZetacls):
        with pytest.raises(AttributeError):
            setattr(cls(), "label", "mutated")


def test_frozen_is_hashable() -> None:
    for cls in (ImmutablePointDatacls, ImmutablePointZetacls):
        assert isinstance(hash(cls(1.0, "a")), int)


def test_frozen_equal_instances_have_equal_hash() -> None:
    for cls in (ImmutablePointDatacls, ImmutablePointZetacls):
        a = cls(2.5, "hi")
        b = cls(2.5, "hi")
        assert a == b
        assert hash(a) == hash(b)


def test_frozen_usable_as_dict_key() -> None:
    for cls in (ImmutablePointDatacls, ImmutablePointZetacls):
        a = cls(1.0, "x")
        b = cls(1.0, "x")
        assert {a: "value"}[b] == "value"


# ── unsafe_hash=True ──────────────────────────────────────────────────────────


@dataclass(unsafe_hash=True)
class UnsafeHashDatacls:
    count: int = 0


@zetaclass(unsafe_hash=True)
class UnsafeHashZetacls:
    count: int = 0


def test_unsafe_hash_is_hashable() -> None:
    for cls in (UnsafeHashDatacls, UnsafeHashZetacls):
        assert isinstance(hash(cls(5)), int)


def test_unsafe_hash_equal_instances_have_equal_hash() -> None:
    for cls in (UnsafeHashDatacls, UnsafeHashZetacls):
        assert hash(cls(7)) == hash(cls(7))


def test_unsafe_hash_mutable() -> None:
    for cls in (UnsafeHashDatacls, UnsafeHashZetacls):
        obj = cls(1)
        obj.count = 99
        assert obj.count == 99
