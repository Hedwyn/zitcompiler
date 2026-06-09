"""
Benchmarks for eq/hashes logic.

@date: 08.06.2025
@author: Baptiste Pestourie
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from benchmarks.conftest import bench

if TYPE_CHECKING:
    from pytest_benchmark.fixture import BenchmarkFixture


class _Point:
    x: int
    y: int
    z: int


@bench(_Point, eq=True, order=True)
def test_eq(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    a = cls(1, 2, 3)
    b = cls(1, 2, 3)
    c = cls(4, 5, 6)

    def eq_loop() -> None:
        for _ in range(100):
            _ = a == b
            _ = a == c

    benchmark(eq_loop)


@bench(_Point, eq=True, order=True)
def test_order(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    a = cls(1, 2, 3)
    b = cls(4, 5, 6)

    def order_loop() -> None:
        for _ in range(100):
            _ = a < b
            _ = a <= b
            _ = b > a
            _ = b >= a

    benchmark(order_loop)


@bench(_Point, frozen=True, eq=True)
def test_hash(
    benchmark: BenchmarkFixture,
    cls: type,
) -> None:
    obj = cls(1, 2, 3)

    def hash_loop() -> None:
        for _ in range(100):
            _ = hash(obj)

    benchmark(hash_loop)
