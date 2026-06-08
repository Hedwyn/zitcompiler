"""
Test suite for zetaclasses.
Verifies that they match dataclasses behavior.
"""

from __future__ import annotations

import warnings
import weakref
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


# ── kw_only=True ──────────────────────────────────────────────────────────────


@dataclass(kw_only=True)
class KwOnlyDatacls:
    host: str = "localhost"
    port: int = 8080


@zetaclass(kw_only=True)
class KwOnlyZetacls:
    host: str = "localhost"
    port: int = 8080


def test_kw_only_accepts_keyword_args() -> None:
    for cls in (KwOnlyDatacls, KwOnlyZetacls):
        obj = cls(host="example.com", port=443)
        assert obj.host == "example.com"
        assert obj.port == 443


def test_kw_only_rejects_positional_args() -> None:
    for cls in (KwOnlyDatacls, KwOnlyZetacls):
        with pytest.raises(TypeError):
            cls("example.com", 443)  # type: ignore[call-arg]


def test_kw_only_uses_defaults() -> None:
    for cls in (KwOnlyDatacls, KwOnlyZetacls):
        obj = cls()
        assert obj.host == "localhost"
        assert obj.port == 8080


# ── weakref_slot=True ─────────────────────────────────────────────────────────


@zetaclass(weakref_slot=True)
class WeakrefNode:
    value: int = 0


def test_weakref_slot_supports_weakref() -> None:
    node = WeakrefNode(42)
    ref = weakref.ref(node)
    assert ref() is node
    assert ref().value == 42  # type: ignore[union-attr]


def test_weakref_slot_ref_clears_on_delete() -> None:
    node = WeakrefNode(1)
    ref = weakref.ref(node)
    del node
    assert ref() is None


# ── slots=False warning ───────────────────────────────────────────────────────


def test_slots_false_emits_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        @zetaclass(slots=False)
        class _Dummy:
            x: int = 0

    assert len(caught) == 1
    assert issubclass(caught[0].category, UserWarning)
    assert "slots" in str(caught[0].message).lower()


def test_slots_true_no_warning() -> None:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        @zetaclass(slots=True)
        class _Dummy:
            x: int = 0

    assert len(caught) == 0


# ── repr=True ─────────────────────────────────────────────────────────────────


@dataclass()
class ReprDatacls:
    name: str = "John"
    age: int = 35
    height: float = 1.77


@zetaclass
class ReprZetacls:
    name: str = "John"
    age: int = 35
    height: float = 1.77


def _fields_repr(r: str) -> str:
    """Return the '(field=val, ...)' suffix of a dataclass repr."""
    return r[r.index("(") :]


def test_repr_default_instances() -> None:
    assert _fields_repr(repr(ReprDatacls())) == _fields_repr(repr(ReprZetacls()))


def test_repr_custom_values() -> None:
    assert _fields_repr(repr(ReprDatacls("Alice", 30, 1.65))) == _fields_repr(
        repr(ReprZetacls("Alice", 30, 1.65))
    )


def test_repr_string_escaping() -> None:
    # Quotes and special chars in string fields must be properly escaped
    assert _fields_repr(repr(ReprDatacls("O'Brien", 40, 1.70))) == _fields_repr(
        repr(ReprZetacls("O'Brien", 40, 1.70))
    )


def test_repr_false_falls_back_to_object_repr() -> None:
    @dataclass(repr=False)
    class _NoReprDc:
        x: int = 0

    @zetaclass(repr=False)
    class _NoReprZc:
        x: int = 0

    # Both should use object's default repr (address-based), not a field repr
    assert not repr(_NoReprDc()).startswith("_NoReprDc(")
    assert not repr(_NoReprZc()).startswith("_NoReprZc(")


# ── match_args ────────────────────────────────────────────────────────────────


@zetaclass
class MatchTarget:
    x: int = 0
    y: int = 0
    label: str = ""


def test_match_args_default_contains_all_fields() -> None:
    assert MatchTarget.__match_args__ == ("x", "y", "label")


def test_match_args_false_is_empty() -> None:
    @zetaclass(match_args=False)
    class _NoMatchArgs:
        x: int = 0

    assert _NoMatchArgs.__match_args__ == ()


def test_match_args_structural_pattern_matching() -> None:
    obj = MatchTarget(1, 2, "hi")
    match obj:
        case MatchTarget(x=1, label=lbl):
            result = lbl
        case _:
            result = "no match"
    assert result == "hi"


# ── is_zetaclass / is_instance ────────────────────────────────────────────────


@zetaclass
class _IsInstanceA:
    x: int = 0


@zetaclass
class _IsInstanceB:
    y: float = 0.0


class _SubA(_IsInstanceA):
    pass


def test_is_zetaclass_direct() -> None:
    assert _IsInstanceA.is_zetaclass(_IsInstanceA()) is True


def test_is_zetaclass_subclass() -> None:
    assert _IsInstanceA.is_zetaclass(_SubA()) is True


def test_is_zetaclass_other_zetaclass() -> None:
    assert _IsInstanceA.is_zetaclass(_IsInstanceB()) is False


def test_is_zetaclass_non_zetaclass() -> None:
    assert _IsInstanceA.is_zetaclass(object()) is False


def test_is_instance_direct() -> None:
    assert _IsInstanceA.is_instance(_IsInstanceA()) is True


def test_is_instance_subclass() -> None:
    assert _IsInstanceA.is_instance(_SubA()) is True


def test_is_instance_other_zetaclass_is_false() -> None:
    assert _IsInstanceA.is_instance(_IsInstanceB()) is False


def test_is_instance_non_zetaclass_is_false() -> None:
    assert _IsInstanceA.is_instance(object()) is False
