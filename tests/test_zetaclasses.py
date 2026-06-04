"""
Test suite for zetaclasses.
Verifies that they match dataclasses behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

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
