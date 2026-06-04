"""
Test suite for zetaclasses.
Verifies that they match dataclasses behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

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


def test_no_eq_uses_identity() -> None:
    d1, d2 = PointNoEqDatacls(), PointNoEqDatacls()
    z1, z2 = PointNoEqZetacls(), PointNoEqZetacls()
    # Different instances with equal fields are NOT equal (identity comparison)
    assert d1 != d2
    assert z1 != z2
    # Same instance equals itself
    assert d1 == d1
    assert z1 == z1
